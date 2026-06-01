# src/flows/msi3/login_flow.py
"""
LoginFlowMsi3 — MSI3 Oracle APEX (Web)
v0.5.10: migrado para BaseFlow.

Mudancas vs versao anterior:
  - herda BaseFlow — _step() centralizado com description
  - ctx=ctx em todos os _step() calls
  - description propagada para StepResult

Regras MSI3:
  - NUNCA navegar por URL direta apos login — invalida sessao APEX
  - networkidle nao funciona apos cliques OpenCV — usar polling de URL
  - Formularios dialog abrem em frame separado — acessar via page.frames
"""

import time

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.flows.msi3.apex_helper import ApexHelper


class LoginFlowMsi3(BaseFlow):

    FLOW_NAME = "LoginFlowMsi3"

    # Seletores CSS validados no MSI3 (APEX 23.1)
    CAMPO_USUARIO  = "#P9999_USERNAME"
    CAMPO_SENHA    = "#P9999_PASSWORD"
    TELA_PRINCIPAL = "h3.t-Card-title"

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        for step_fn in [
            lambda: self._step_abrir_pagina(ctx, observer),
            lambda: self._step_usuario(ctx, observer),
            lambda: self._step_senha(ctx, observer),
            lambda: self._step_submeter(ctx, observer),
            lambda: self._step_validar(ctx, observer),
        ]:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    def _step_abrir_pagina(self, ctx, observer=None):
        def fn():
            ctx.runner.navigate(ctx.config.url)
            ctx.runner.wait_template(self.CAMPO_USUARIO, timeout=15.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}MW01_pagina.png")
        return self._step("MW01", "abrir pagina de login do MSI3",
                          fn, observer,
                          confirm_template=self.CAMPO_USUARIO,
                          ctx=ctx)

    def _step_usuario(self, ctx, observer=None):
        def fn():
            ctx.runner.fill(self.CAMPO_USUARIO, ctx.user)
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}MW02_usuario.png")
        return self._step("MW02", "preencher campo usuario",
                          fn, observer, ctx=ctx)

    def _step_senha(self, ctx, observer=None):
        def fn():
            ctx.runner.fill(self.CAMPO_SENHA, ctx.password)
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}MW03_senha.png")
        return self._step("MW03", "preencher campo senha",
                          fn, observer, ctx=ctx)

    def _step_submeter(self, ctx, observer=None):
        def fn():
            ctx.runner._page.keyboard.press("Tab");  time.sleep(0.5)
            ctx.runner._page.keyboard.press("Tab");  time.sleep(0.5)
            ctx.runner._page.keyboard.press("Enter"); time.sleep(1.0)
            ctx.runner._page.wait_for_load_state("networkidle")
            ApexHelper.verificar_sem_erro(ctx.runner)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}MW04_submetido.png")
        return self._step("MW04", "submeter formulario de login",
                          fn, observer, ctx=ctx)

    def _step_validar(self, ctx, observer=None):
        def fn():
            encontrou = ctx.runner.wait_template(self.TELA_PRINCIPAL, timeout=15.0)
            if not encontrou:
                raise RuntimeError(
                    "Tela principal nao carregou apos 15s. "
                    "Verifique credenciais ou seletor TELA_PRINCIPAL."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}MW05_principal.png")
        return self._step("MW05", "validar login — tela principal carregada",
                          fn, observer,
                          confirm_template=self.TELA_PRINCIPAL,
                          validated=True,
                          ctx=ctx)