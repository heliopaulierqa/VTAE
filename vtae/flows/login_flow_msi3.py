import time

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult


class LoginFlowMsi3:
    """
    Fluxo de login do MSI3 (versão web — Oracle APEX).
    Baseado no código existente, adaptado para o padrão VTAE.

    Reutilização em outros testes:
        from vtae.flows.login_flow_msi3 import LoginFlowMsi3

        def test_qualquer_coisa(page):
            ctx = build_ctx(page)
            LoginFlowMsi3().execute(ctx, observer=observer)
            # a partir daqui o usuário já está logado
            # continue com os próximos steps do seu teste
    """

    FLOW_NAME = "LoginFlowMsi3"

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

    def _step_abrir_pagina(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "MW01"
        if observer:
            observer.log_step_start(step_id, "abrir página de login")
        start = time.monotonic()
        try:
            ctx.runner.navigate(ctx.config.URL)
            ctx.runner.wait_template(ctx.config.CAMPO_USUARIO, timeout=15.0)
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

    def _step_usuario(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "MW02"
        if observer:
            observer.log_step_start(step_id, "preencher campo usuário")
        start = time.monotonic()
        try:
            ctx.runner.fill(ctx.config.CAMPO_USUARIO, ctx.user)
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

    def _step_senha(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "MW03"
        if observer:
            observer.log_step_start(step_id, "preencher campo senha")
        start = time.monotonic()
        try:
            ctx.runner.fill(ctx.config.CAMPO_SENHA, ctx.password)
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

    def _step_submeter(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "MW04"
        if observer:
            observer.log_step_start(step_id, "submeter formulário de login")
        start = time.monotonic()
        try:
            # Tab x2 + Enter — mesma lógica do código original
            ctx.runner._page.keyboard.press("Tab")
            time.sleep(0.5)
            ctx.runner._page.keyboard.press("Tab")
            time.sleep(0.5)
            ctx.runner._page.keyboard.press("Enter")
            time.sleep(1)
            ctx.runner._page.wait_for_load_state("networkidle")
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

    def _step_validar(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "MW05"
        if observer:
            observer.log_step_start(step_id, "validar login bem-sucedido")
        start = time.monotonic()
        try:
            encontrou = ctx.runner.wait_template(
                ctx.config.TELA_PRINCIPAL, timeout=15.0
            )
            if not encontrou:
                raise RuntimeError(
                    f"Tela principal não carregou após 15s. "
                    f"Verifique o seletor TELA_PRINCIPAL no config "
                    f"ou as credenciais."
                )
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}MW05_principal.png")
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
