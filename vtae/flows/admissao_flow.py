import time

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult


class AdmissaoFlow:
    """
    Fluxo de admissão. Pressupõe que LoginFlow já foi executado.
    """

    FLOW_NAME = "AdmissaoFlow"

    def execute(self, ctx: FlowContext) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        result.steps.append(self._step_abrir_modulo(ctx))
        result.steps.append(self._step_nova_admissao(ctx))
        ctx.add_result(result)
        return result

    def _step_abrir_modulo(self, ctx: FlowContext) -> StepResult:
        step_id = "A01"
        start = time.monotonic()
        try:
            ctx.runner.safe_click("templates/admissao/btn_modulo.png")
            ctx.runner.wait_template("templates/admissao/tela_admissao.png")
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}admissao/A01_modulo.png")
            return StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            return StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000, error=str(e))

    def _step_nova_admissao(self, ctx: FlowContext) -> StepResult:
        step_id = "A02"
        start = time.monotonic()
        try:
            ctx.runner.safe_click("templates/admissao/btn_nova.png")
            ctx.runner.wait_template("templates/admissao/form_admissao.png")
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}admissao/A02_form.png")
            return StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            return StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000, error=str(e))
