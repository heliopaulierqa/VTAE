# src/flows/sislab/login_flow.py
"""
LoginFlowSisLab — SisLab Oracle Forms (Desktop)
v0.5.10: migrado para BaseFlow.
Templates em templates/sislab/login/
"""

import time

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow


class LoginFlowSisLab(BaseFlow):

    FLOW_NAME = "LoginFlowSisLab"
    _TPL = "templates/sislab/login"

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        for step_fn in [
            lambda: self._step_usuario(ctx, observer),
            lambda: self._step_senha(ctx, observer),
            lambda: self._step_entrar(ctx, observer),
        ]:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    def _step_usuario(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/campo_usuario.png")
            ctx.runner.type_text(ctx.user)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}L01_usuario.png")
        return self._step("L01", "clicar no campo usuario e digitar",
                          fn, observer, ctx=ctx)

    def _step_senha(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/campo_senha.png")
            ctx.runner.type_text(ctx.password)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}L02_senha.png")
        return self._step("L02", "clicar no campo senha e digitar",
                          fn, observer, ctx=ctx)

    def _step_entrar(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_entrar.png")
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}L03_entrar.png")
        return self._step("L03", "clicar no botao Entrar",
                          fn, observer, ctx=ctx)