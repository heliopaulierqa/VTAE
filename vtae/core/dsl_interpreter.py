"""
DSL Interpreter — v0.5.1
Executa testes definidos em YAML sem necessidade de código Python.

Ações suportadas (v0.5.1):
    fill_field      — preenche campo via template (click_near) ou seletor CSS
    assert_visible  — verifica se template ou seletor está visível na tela
    assert_text     — verifica texto via OCR (desktop) ou seletor (web)
    click           — clica em template ou seletor
    wait            — aguarda template ou seletor aparecer
    type            — digita texto no campo ativo (desktop)
    screenshot      — captura tela com nome configurável
    login           — executa o LoginFlow do sistema configurado no ctx

Interpolação de dados:
    Qualquer campo de texto aceita <<DADOS.campo>> — substituído pelo valor
    gerado pelo Faker via config.DADOS (ex: <<DADOS.nome>>, <<DADOS.cpf>>).

Exemplo de YAML:
    flow: cadastro_paciente
    sistema: si3
    steps:
      - action: login
      - action: fill_field
        template: templates/si3/label_nome.png
        offset_x: 200
        value: <<DADOS.nome>>
      - action: assert_visible
        template: templates/si3/msg_sucesso.png
        timeout: 5.0
"""

from __future__ import annotations

import re
import time
from typing import Any

from src.core.result import FlowResult, StepResult
from src.core.types import RunnerError, StepError


_DADOS_RE = re.compile(r"<<DADOS\.(\w+)>>")


def _interpolate(value: str, dados: dict[str, Any]) -> str:
    def _replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in dados:
            raise StepError(
                f"Interpolação falhou: <<DADOS.{key}>> não existe em config.DADOS. "
                f"Chaves disponíveis: {sorted(dados.keys())}"
            )
        return str(dados[key])
    return _DADOS_RE.sub(_replace, value)


class DSLInterpreter:
    """
    Interpreta e executa um teste definido em YAML.
    Gera FlowResult/StepResult compatíveis com ExecutionObserver e report.html.
    """

    SUPPORTED_ACTIONS = {
        "login", "click", "type", "wait", "screenshot",
        "fill_field", "assert_visible", "assert_text",
    }

    def __init__(self, ctx, observer=None) -> None:
        self.ctx = ctx
        self.observer = observer

    def run(self, test_definition: dict[str, Any]) -> FlowResult:
        flow_name = test_definition.get("flow", "unknown")
        raw_steps = test_definition.get("steps", [])
        result = FlowResult(flow_name=flow_name)

        if self.observer:
            self.observer.log_flow_start(flow_name)

        print(f"[DSL] Executando flow: {flow_name} ({len(raw_steps)} steps)")

        for i, step_def in enumerate(raw_steps, 1):
            action = step_def.get("action")
            if action not in self.SUPPORTED_ACTIONS:
                raise ValueError(
                    f"Ação desconhecida: '{action}'. Suportadas: {sorted(self.SUPPORTED_ACTIONS)}"
                )
            step = self._execute_action(i, step_def)
            result.steps.append(step)
            if self.observer:
                self.observer.log_step_result(step)
            if not step.success:
                print(f"[DSL] ✗ Step {i:02d} ({action}) falhou — abortando flow.")
                break

        self.ctx.add_result(result)
        if self.observer:
            self.observer.log_flow_result(result)
        return result

    def _execute_action(self, index: int, step: dict) -> StepResult:
        action = step["action"]
        step_id = step.get("id", f"DSL{index:02d}")
        if self.observer:
            self.observer.log_step_start(step_id, action)
        print(f"[DSL] Step {index:02d} [{step_id}]: {action}")
        start = time.monotonic()
        try:
            screenshot_path = self._dispatch(action, index, step)
            return StepResult(
                step_id=step_id, success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot_path,
            )
        except (StepError, RunnerError) as exc:
            return StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(exc),
            )
        except Exception as exc:
            return StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=f"[{type(exc).__name__}] {exc}",
            )

    def _dispatch(self, action: str, index: int, step: dict) -> str | None:
        handlers = {
            "login":          self._action_login,
            "click":          self._action_click,
            "type":           self._action_type,
            "wait":           self._action_wait,
            "screenshot":     self._action_screenshot,
            "fill_field":     self._action_fill_field,
            "assert_visible": self._action_assert_visible,
            "assert_text":    self._action_assert_text,
        }
        return handlers[action](index, step)

    def _action_login(self, index: int, step: dict) -> str | None:
        sistema = getattr(self.ctx.config, "sistema", None)
        try:
            if sistema == "si3":
                from src.flows.si3.login_flow import LoginFlow
            elif sistema == "sislab":
                from src.flows.sislab.login_flow import LoginFlow
            elif sistema == "msi3":
                from src.flows.msi3.login_flow_msi3 import LoginFlowMsi3 as LoginFlow
            else:
                from vtae.flows.login_flow import LoginFlow  # type: ignore[import]
        except ImportError as exc:
            raise StepError(f"LoginFlow não encontrado para sistema '{sistema}': {exc}") from exc
        flow_result = LoginFlow().execute(self.ctx, observer=self.observer)
        if not flow_result.success:
            raise StepError(f"LoginFlow falhou: {flow_result.failed_steps}")
        return None

    def _action_click(self, index: int, step: dict) -> str | None:
        template = step.get("template")
        selector = step.get("selector")
        if not template and not selector:
            raise StepError("'click' requer 'template' (desktop) ou 'selector' (web).")
        self.ctx.runner.safe_click(template or selector)
        return self._maybe_screenshot(index, step)

    def _action_type(self, index: int, step: dict) -> str | None:
        text = self._resolve(step.get("text", ""))
        self.ctx.runner.type_text(text)
        return self._maybe_screenshot(index, step)

    def _action_wait(self, index: int, step: dict) -> str | None:
        template = step.get("template")
        selector = step.get("selector")
        timeout = float(step.get("timeout", 10.0))
        target = template or selector
        if not target:
            raise StepError("'wait' requer 'template' ou 'selector'.")
        found = self.ctx.runner.wait_template(target, timeout=timeout)
        if not found:
            raise StepError(f"'wait' timeout após {timeout}s aguardando: {target}")
        return None

    def _action_screenshot(self, index: int, step: dict) -> str | None:
        name = step.get("name", f"step_{index:02d}.png")
        return self.ctx.runner.screenshot(f"{self.ctx.evidence_dir}{name}")

    def _action_fill_field(self, index: int, step: dict) -> str | None:
        value = self._resolve(step.get("value", ""))
        template = step.get("template")
        selector = step.get("selector")
        if not template and not selector:
            raise StepError("'fill_field' requer 'template' (desktop) ou 'selector' (web).")
        if template:
            offset_x = int(step.get("offset_x", 0))
            offset_y = int(step.get("offset_y", 0))
            if offset_x or offset_y:
                self.ctx.runner.click_near(template, offset_x=offset_x, offset_y=offset_y)
            else:
                self.ctx.runner.safe_click(template)
            self.ctx.runner.type_text(value)
        else:
            self.ctx.runner.fill(selector, value)
        return self._auto_screenshot(index, step)

    def _action_assert_visible(self, index: int, step: dict) -> str | None:
        template = step.get("template")
        selector = step.get("selector")
        timeout = float(step.get("timeout", 5.0))
        target = template or selector
        if not target:
            raise StepError("'assert_visible' requer 'template' (desktop) ou 'selector' (web).")
        found = self.ctx.runner.wait_template(target, timeout=timeout)
        screenshot_path = self._auto_screenshot(index, step)
        if not found:
            raise StepError(f"assert_visible falhou: '{target}' não encontrado após {timeout}s.")
        return screenshot_path

    def _action_assert_text(self, index: int, step: dict) -> str | None:
        expected = self._resolve(step.get("expected", ""))
        selector = step.get("selector")
        if not expected:
            raise StepError("'assert_text' requer campo 'expected'.")
        if selector:
            found_text = self._web_get_text(selector)
            screenshot_path = self._auto_screenshot(index, step)
            if expected.lower() not in found_text.lower():
                raise StepError(
                    f"assert_text falhou: esperado '{expected}' em '{selector}', "
                    f"encontrado '{found_text}'."
                )
        else:
            region = step.get("region")
            found_text = self._ocr_read(region)
            screenshot_path = self._auto_screenshot(index, step)
            if expected.lower() not in found_text.lower():
                raise StepError(
                    f"assert_text falhou: esperado '{expected}' via OCR, "
                    f"texto lido: '{found_text[:200]}'."
                )
        return screenshot_path

    def _resolve(self, value: str) -> str:
        if "<<DADOS." not in value:
            return value
        dados = getattr(self.ctx.config, "DADOS", {}) or {}
        return _interpolate(value, dados)

    def _auto_screenshot(self, index: int, step: dict) -> str | None:
        step_id = step.get("id", f"DSL{index:02d}")
        return self.ctx.runner.screenshot(f"{self.ctx.evidence_dir}{step_id}.png")

    def _maybe_screenshot(self, index: int, step: dict) -> str | None:
        if step.get("screenshot", False):
            return self._auto_screenshot(index, step)
        return None

    def _web_get_text(self, selector: str) -> str:
        try:
            page = self.ctx.runner._page
            return page.locator(selector).first.text_content(timeout=5000) or ""
        except Exception as exc:
            raise StepError(f"assert_text: não foi possível ler '{selector}': {exc}") from exc

    def _ocr_read(self, region: list[int] | None) -> str:
        try:
            from src.vision.ocr_helper import OcrHelper
        except ImportError as exc:
            raise StepError(f"assert_text (OCR) requer OcrHelper: {exc}") from exc
        if region:
            x, y, w, h = region
            return OcrHelper.ler_regiao(x, y, w, h)
        return OcrHelper.ler_tela_inteira()
