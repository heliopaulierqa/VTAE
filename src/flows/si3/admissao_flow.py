# src/flows/si3/admissao_flow.py
"""
AdmissaoFlow — Esqueleto mantido para retrocompatibilidade dos testes unitarios.
v0.5.10: migrado para BaseFlow.
"""

import time

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow


class AdmissaoFlow(BaseFlow):
    """Esqueleto de AdmissaoFlow — mantido para retrocompatibilidade."""

    FLOW_NAME = "AdmissaoFlow"

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        for step_fn in [
            lambda: self._step_a01(ctx, observer),
            lambda: self._step_a02(ctx, observer),
        ]:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    def _step_a01(self, ctx, observer=None):
        def fn():
            return ctx.runner.screenshot(f"{ctx.evidence_dir}A01.png")
        return self._step("A01", "step A01 — esqueleto", fn, observer, ctx=ctx)

    def _step_a02(self, ctx, observer=None):
        def fn():
            return ctx.runner.screenshot(f"{ctx.evidence_dir}A02.png")
        return self._step("A02", "step A02 — esqueleto", fn, observer, ctx=ctx)