import time

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult


class LoginFlowSisLab:
    """
    Fluxo de login do SisLab (Desktop — OpenCV).

    Templates necessários em templates/sislab/login/:
        campo_usuario.png
        campo_senha.png
        btn_entrar.png
    """

    FLOW_NAME = "LoginFlowSisLab"

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        for step_fn in [
            self._step_usuario,
            self._step_senha,
            self._step_entrar,
        ]:
            step = step_fn(ctx, observer)
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)

        return result

    def _step_usuario(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "L01"
        if observer:
            observer.log_step_start(step_id, "clicar no campo usuário e digitar")
        start = time.monotonic()
        try:
            ctx.runner.safe_click("templates/sislab/login/campo_usuario.png")
            ctx.runner.type_text(ctx.user)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}L01_usuario.png")
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
        step_id = "L02"
        if observer:
            observer.log_step_start(step_id, "clicar no campo senha e digitar")
        start = time.monotonic()
        try:
            ctx.runner.safe_click("templates/sislab/login/campo_senha.png")
            ctx.runner.type_text(ctx.password)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}L02_senha.png")
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

    def _step_entrar(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "L03"
        if observer:
            observer.log_step_start(step_id, "clicar no botão Entrar")
        start = time.monotonic()
        try:
            ctx.runner.safe_click("templates/sislab/login/btn_entrar.png")
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}L03_entrar.png")
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