"""
DSL Interpreter — v0.5.3
Executa testes definidos em YAML sem necessidade de código Python.

Ações suportadas (v0.5.3):
    fill_field      — preenche campo via template (click_near) ou seletor CSS
    assert_visible  — verifica se template ou seletor está visível na tela
    assert_text     — verifica texto via OCR (desktop) ou seletor (web)
    select_dropdown — seleciona opção em dropdown por valor
    run_component   — executa componente Python reutilizável
    loop            — executa bloco de steps N vezes ou para cada item de uma lista
    if              — executa bloco 'then' se condição for verdadeira, senão 'else'
    click           — clica em template ou seletor
    wait            — aguarda template ou seletor aparecer
    type            — digita texto no campo ativo (desktop)
    screenshot      — captura tela com nome configurável
    login           — executa o LoginFlow do sistema configurado no ctx

Interpolação de dados:
    <<DADOS.campo>>  — substituído por config.DADOS[campo]
    <<LOOP.item>>    — dentro de loop, substituído pelo item corrente da lista
    <<LOOP.index>>   — índice corrente do loop (começa em 1)

Exemplo de YAML — loop por contagem:
    - action: loop
      count: 3
      steps:
        - action: click
          template: templates/si3/btn_novo.png

Exemplo de YAML — loop por lista:
    - action: loop
      items:
        - ANALISTA
        - ASSISTENTE
        - COORDENADOR
      steps:
        - action: fill_field
          selector: "#P17_CARGO"
          value: <<LOOP.item>>

Exemplo de YAML — if/else:
    - action: if
      condition:
        assert_visible:
          template: templates/si3/popup_erro.png
          timeout: 2.0
      then:
        - action: click
          template: templates/si3/btn_fechar_popup.png
      else:
        - action: assert_visible
          template: templates/si3/msg_sucesso.png
"""

from __future__ import annotations

import re
import time
import importlib
from typing import Any

from src.core.result import FlowResult, StepResult
from src.core.types import RunnerError, StepError


_DADOS_RE = re.compile(r"<<DADOS\.(\w+)>>")
_LOOP_RE = re.compile(r"<<LOOP\.(item|index)>>")


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


def _interpolate_loop(value: str, item: Any, index: int) -> str:
    """Substitui <<LOOP.item>> e <<LOOP.index>> pelo valor corrente do loop."""
    def _replace(match: re.Match) -> str:
        key = match.group(1)
        if key == "item":
            return str(item)
        if key == "index":
            return str(index)
        return match.group(0)
    return _LOOP_RE.sub(_replace, value)


class DSLInterpreter:
    """
    Interpreta e executa um teste definido em YAML.
    Gera FlowResult/StepResult compatíveis com ExecutionObserver e report.html.
    """

    SUPPORTED_ACTIONS = {
        "login", "click", "type", "wait", "screenshot",
        "fill_field", "assert_visible", "assert_text",
        "select_dropdown", "run_component",
        # v0.5.3
        "loop", "if",
    }

    def __init__(self, ctx, observer=None) -> None:
        self.ctx = ctx
        self.observer = observer
        # Contexto do loop corrente — preenchido durante execução de loop
        self._loop_item: Any = None
        self._loop_index: int = 0

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
            "login":            self._action_login,
            "click":            self._action_click,
            "type":             self._action_type,
            "wait":             self._action_wait,
            "screenshot":       self._action_screenshot,
            "fill_field":       self._action_fill_field,
            "assert_visible":   self._action_assert_visible,
            "assert_text":      self._action_assert_text,
            "select_dropdown":  self._action_select_dropdown,
            "run_component":    self._action_run_component,
            "loop":             self._action_loop,
            "if":               self._action_if,
        }
        return handlers[action](index, step)

    # ------------------------------------------------------------------
    # Handlers — ações legadas (v0.5.1 / v0.5.2)
    # ------------------------------------------------------------------

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
                from src.flows.login_flow import LoginFlow  # type: ignore[import]
        except ImportError as exc:
            raise StepError(f"LoginFlow não encontrado para sistema '{sistema}': {exc}") from exc
        flow_result = LoginFlow().execute(self.ctx, observer=self.observer)
        if not flow_result.success:
            raise StepError(f"LoginFlow falhou: {flow_result.failed_steps}")
        return None

    def _action_click(self, index: int, step: dict) -> str | None:
        template = self._resolve(step.get("template") or "")
        selector = self._resolve(step.get("selector") or "")
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

    def _action_select_dropdown(self, index: int, step: dict) -> str | None:
        import pyautogui
        value = self._resolve(step.get("value", ""))
        template = step.get("template")
        selector = step.get("selector")
        mode = step.get("mode", "type")
        if not template and not selector:
            raise StepError("'select_dropdown' requer 'template' (desktop) ou 'selector' (web).")
        if not value:
            raise StepError("'select_dropdown' requer campo 'value'.")
        if template:
            offset_x = int(step.get("offset_x", 0))
            offset_y = int(step.get("offset_y", 0))
            if offset_x or offset_y:
                self.ctx.runner.click_near(template, offset_x=offset_x, offset_y=offset_y)
            else:
                self.ctx.runner.safe_click(template)
            if mode == "arrow":
                arrows = int(step.get("arrows", 1))
                for _ in range(arrows):
                    pyautogui.press("down")
                    time.sleep(0.1)
                pyautogui.press("enter")
            else:
                self.ctx.runner.type_text(value)
                time.sleep(0.2)
                pyautogui.press("enter")
        else:
            self.ctx.runner.fill(selector, value)
            time.sleep(0.1)
            page = self.ctx.runner._page
            page.locator(selector).press("Enter")
        return self._auto_screenshot(index, step)

    def _action_run_component(self, index: int, step: dict) -> str | None:
        name = step.get("name", "")
        if not name:
            raise StepError("'run_component' requer campo 'name'.")
        parts = name.split(".")
        if len(parts) < 3:
            raise StepError(
                f"'run_component' name inválido: '{name}'. "
                f"Formato esperado: <sistema>.<modulo>.<funcao>"
            )
        sistema, modulo, funcao = parts[0], parts[1], parts[2]
        module_path = f"src.components.{sistema}.{modulo}"
        try:
            mod = importlib.import_module(module_path)
        except ImportError as exc:
            raise StepError(
                f"run_component: não foi possível importar '{module_path}': {exc}"
            ) from exc
        if not hasattr(mod, funcao):
            raise StepError(f"run_component: '{funcao}' não encontrado em '{module_path}'.")
        raw_args = step.get("args", {}) or {}
        resolved_args = {}
        for k, v in raw_args.items():
            if v == "<<DADOS>>":
                resolved_args[k] = getattr(self.ctx.config, "DADOS", {}) or {}
            elif isinstance(v, str):
                resolved_args[k] = self._resolve(v)
            else:
                resolved_args[k] = v
        component_fn = getattr(mod, funcao)
        result = component_fn(self.ctx, self.observer, **resolved_args)
        if result is not None and hasattr(result, "success") and not result.success:
            raise StepError(
                f"run_component '{name}' falhou: {getattr(result, 'failed_steps', '')}"
            )
        return self._auto_screenshot(index, step)

    # ------------------------------------------------------------------
    # Handlers — v0.5.3
    # ------------------------------------------------------------------

    def _action_loop(self, index: int, step: dict) -> str | None:
        """
        Executa um bloco de steps repetidamente.

        Modo count — repete N vezes:
            - action: loop
              count: 3
              steps:
                - action: click
                  template: templates/si3/btn_novo.png

        Modo items — itera sobre lista, expondo <<LOOP.item>> e <<LOOP.index>>:
            - action: loop
              items:
                - ANALISTA
                - ASSISTENTE
              steps:
                - action: fill_field
                  selector: "#P17_CARGO"
                  value: <<LOOP.item>>
        """
        sub_steps = step.get("steps")
        if not sub_steps:
            raise StepError("'loop' requer campo 'steps' com pelo menos uma ação.")

        items = step.get("items")
        count = step.get("count")

        if items is not None:
            iterations = list(items)
        elif count is not None:
            iterations = list(range(1, int(count) + 1))
        else:
            raise StepError("'loop' requer 'count' (número) ou 'items' (lista).")

        for loop_index, loop_item in enumerate(iterations, 1):
            self._loop_item = loop_item
            self._loop_index = loop_index
            print(f"[DSL]   loop [{loop_index}/{len(iterations)}]: item={loop_item}")

            for sub_i, sub_step in enumerate(sub_steps, 1):
                sub_action = sub_step.get("action")
                if sub_action not in self.SUPPORTED_ACTIONS:
                    raise ValueError(
                        f"Ação desconhecida em loop: '{sub_action}'."
                    )
                # Resolve interpolações de loop nos campos do sub_step
                resolved_sub = self._resolve_loop_step(sub_step)
                sub_result = self._execute_action(sub_i, resolved_sub)
                if not sub_result.success:
                    raise StepError(
                        f"Loop falhou na iteração {loop_index}, step {sub_i} "
                        f"({sub_action}): {sub_result.error}"
                    )

        self._loop_item = None
        self._loop_index = 0
        return None

    def _action_if(self, index: int, step: dict) -> str | None:
        """
        Executa bloco 'then' se condição for verdadeira, senão bloco 'else'.
        A condição é avaliada por assert_visible (não levanta erro — retorna bool).

        YAML:
            - action: if
              condition:
                assert_visible:
                  template: templates/si3/popup_erro.png
                  timeout: 2.0
              then:
                - action: click
                  template: templates/si3/btn_fechar.png
              else:
                - action: assert_visible
                  template: templates/si3/msg_sucesso.png
        """
        condition = step.get("condition")
        then_steps = step.get("then", [])
        else_steps = step.get("else", [])

        if not condition:
            raise StepError("'if' requer campo 'condition'.")
        if not then_steps and not else_steps:
            raise StepError("'if' requer pelo menos 'then' ou 'else'.")

        condition_result = self._evaluate_condition(condition)
        branch = then_steps if condition_result else else_steps
        branch_name = "then" if condition_result else "else"

        print(f"[DSL]   if → condição={'verdadeira' if condition_result else 'falsa'}, executando '{branch_name}'")

        for sub_i, sub_step in enumerate(branch, 1):
            sub_action = sub_step.get("action")
            if sub_action not in self.SUPPORTED_ACTIONS:
                raise ValueError(f"Ação desconhecida em if/{branch_name}: '{sub_action}'.")
            sub_result = self._execute_action(sub_i, sub_step)
            if not sub_result.success:
                raise StepError(
                    f"if/{branch_name} falhou no step {sub_i} "
                    f"({sub_action}): {sub_result.error}"
                )

        return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _evaluate_condition(self, condition: dict) -> bool:
        """
        Avalia uma condição sem levantar exceção — retorna True/False.
        Suporta: assert_visible (template ou selector).
        """
        if "assert_visible" in condition:
            cfg = condition["assert_visible"]
            template = cfg.get("template")
            selector = cfg.get("selector")
            timeout = float(cfg.get("timeout", 2.0))
            target = template or selector
            if not target:
                return False
            return bool(self.ctx.runner.wait_template(target, timeout=timeout))

        if "assert_text" in condition:
            cfg = condition["assert_text"]
            expected = self._resolve(cfg.get("expected", ""))
            selector = cfg.get("selector")
            try:
                if selector:
                    found = self._web_get_text(selector)
                else:
                    found = self._ocr_read(cfg.get("region"))
                return expected.lower() in found.lower()
            except Exception:
                return False

        return False

    def _resolve(self, value: str) -> str:
        """Interpola <<DADOS.campo>> e <<LOOP.*>> no valor."""
        if not isinstance(value, str):
            return value
        if "<<DADOS." in value:
            dados = getattr(self.ctx.config, "DADOS", {}) or {}
            value = _interpolate(value, dados)
        if "<<LOOP." in value:
            value = _interpolate_loop(value, self._loop_item, self._loop_index)
        return value

    def _resolve_loop_step(self, step: dict) -> dict:
        """Retorna cópia do step com todos os valores string resolvidos para o loop."""
        resolved = {}
        for k, v in step.items():
            if isinstance(v, str):
                resolved[k] = self._resolve(v)
            elif isinstance(v, list):
                resolved[k] = [self._resolve(i) if isinstance(i, str) else i for i in v]
            else:
                resolved[k] = v
        return resolved

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