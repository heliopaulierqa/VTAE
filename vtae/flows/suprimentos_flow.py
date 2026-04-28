import time

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult


class SuprimentosFlow:
    """
    Fluxo de suprimentos. Pressupõe que LoginFlow já foi executado.
    """

    FLOW_NAME = "SuprimentosFlow"

    def execute(self, ctx: FlowContext) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        result.steps.append(self._step_abrir_modulo(ctx))
        result.steps.append(self._step_listar_pedidos(ctx))
        ctx.add_result(result)
        return result

    def _step_abrir_modulo(self, ctx: FlowContext) -> StepResult:
        step_id = "S01"
        start = time.monotonic()
        try:
            ctx.runner.safe_click("templates/suprimentos/btn_modulo.png")
            ctx.runner.wait_template("templates/suprimentos/tela_suprimentos.png")
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}suprimentos/S01_modulo.png")
            return StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            return StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000, error=str(e))

    def _step_listar_pedidos(self, ctx: FlowContext) -> StepResult:
        step_id = "S02"
        start = time.monotonic()
        try:
            ctx.runner.wait_template("templates/suprimentos/lista_pedidos.png")
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}suprimentos/S02_lista.png")
            return StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            return StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000, error=str(e))
