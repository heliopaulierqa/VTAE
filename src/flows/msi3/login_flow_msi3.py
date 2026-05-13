# src/flows/msi3/login_flow.py
import time

from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult
from src.flows.msi3.apex_helper import ApexHelper


class LoginFlowMsi3:
    """
    Fluxo de login do MSI3 (Oracle APEX — web).
    Migrado de vtae/flows/login_flow_msi3.py
    """

    FLOW_NAME = "LoginFlowMsi3"

    # Seletores CSS do formulário de login do APEX
    CAMPO_USUARIO  = "#P9999_USERNAME"
    CAMPO_SENHA    = "#P9999_PASSWORD"
    TELA_PRINCIPAL = "h3.t-Card-title"

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        for step_fn in [
            self._step_abrir_pagina,
            self._step_usuario,
            self._step_senha,
            self._step_submeter,
            self._step_validar,
        ]:
            step = step_fn(ctx, observer)
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    def _step_abrir_pagina(self, ctx, observer=None) -> StepResult:
        step_id = "MW01"
        if observer:
            observer.log_step_start(step_id, "abrir página de login")
        start = time.monotonic()
        try:
            ctx.runner.navigate(ctx.config.url)
            ctx.runner.wait_template(self.CAMPO_USUARIO, timeout=15.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}MW01_pagina.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_usuario(self, ctx, observer=None) -> StepResult:
        step_id = "MW02"
        if observer:
            observer.log_step_start(step_id, "preencher campo usuário")
        start = time.monotonic()
        try:
            ctx.runner.fill(self.CAMPO_USUARIO, ctx.user)
            time.sleep(0.5)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}MW02_usuario.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_senha(self, ctx, observer=None) -> StepResult:
        step_id = "MW03"
        if observer:
            observer.log_step_start(step_id, "preencher campo senha")
        start = time.monotonic()
        try:
            ctx.runner.fill(self.CAMPO_SENHA, ctx.password)
            time.sleep(0.5)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}MW03_senha.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_submeter(self, ctx, observer=None) -> StepResult:
        step_id = "MW04"
        if observer:
            observer.log_step_start(step_id, "submeter formulário de login")
        start = time.monotonic()
        try:
            ctx.runner._page.keyboard.press("Tab")
            time.sleep(0.5)
            ctx.runner._page.keyboard.press("Tab")
            time.sleep(0.5)
            ctx.runner._page.keyboard.press("Enter")
            time.sleep(1)
            ctx.runner._page.wait_for_load_state("networkidle")
            ApexHelper.verificar_sem_erro(ctx.runner)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}MW04_submetido.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_validar(self, ctx, observer=None) -> StepResult:
        step_id = "MW05"
        if observer:
            observer.log_step_start(step_id, "validar login bem-sucedido")
        start = time.monotonic()
        try:
            encontrou = ctx.runner.wait_template(self.TELA_PRINCIPAL, timeout=15.0)
            if not encontrou:
                raise RuntimeError(
                    "Tela principal não carregou após 15s. "
                    "Verifique credenciais ou seletor TELA_PRINCIPAL."
                )
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}MW05_principal.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            try:
                info = ApexHelper.inspecionar_pagina(ctx.runner)
                print(f"[MW05 debug] URL: {info['url']} | "
                      f"Título: {info['titulo']} | Erro APEX: {info['erro']}")
            except Exception:
                pass
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step