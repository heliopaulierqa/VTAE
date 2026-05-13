# src/flows/si3/suprimentos_flow.py
import time
from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult


class SuprimentosFlow:
    """Esqueleto de SuprimentosFlow — mantido para retrocompatibilidade dos testes unitários."""

    FLOW_NAME = "SuprimentosFlow"

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        for step_fn in [self._step_s01, self._step_s02]:
            step = step_fn(ctx, observer)
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    def _step_s01(self, ctx, observer=None) -> StepResult:
        step_id = "S01"
        start = time.monotonic()
        try:
            ctx.runner.screenshot(f"{ctx.evidence_dir}S01.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        return step

    def _step_s02(self, ctx, observer=None) -> StepResult:
        step_id = "S02"
        start = time.monotonic()
        try:
            ctx.runner.screenshot(f"{ctx.evidence_dir}S02.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        return step