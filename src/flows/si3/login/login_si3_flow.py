# src/flows/si3/login/login_si3_flow.py
"""
Fluxo de login para SI3 (Oracle Forms desktop via Edge).

Templates em templates/si3/login/:
    popup_conexao.png       — confirma SI3 carregado (usado no fixture)
    menu_principal_login.png — confirma login bem-sucedido (score 1.0)

Coordenadas em configs/si3/si3_login/config.yaml:
    campo_usuario, campo_senha, btn_conectar

Abertura do navegador: src/runners/browser_launcher.py (fora deste flow)
"""

import time
import pyautogui

from src.core.result import FlowResult, StepResult
from src.flows.base_flow import BaseFlow


class LoginSi3Flow(BaseFlow):
    FLOW_NAME = "LoginSi3Flow"
    _TPL = "templates/si3/login"

    def execute(self, ctx, dados: dict = None, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas

        for step_fn in [
            lambda: self._step_l01_usuario(ctx, dados, coords, observer),
            lambda: self._step_l02_senha(ctx, dados, coords, observer),
            lambda: self._step_l03_conectar(ctx, coords, observer),
        ]:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break  # abort-on-failure — sempre

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    # ------------------------------------------------------------------
    # L01 — clicar no campo Usuario e digitar
    # ------------------------------------------------------------------
    def _step_l01_usuario(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            usuario = self._dado(dados, "usuario", "L01")
            x, y = self._coord(coords, "campo_usuario")
            pyautogui.click(x, y)
            time.sleep(0.5)  # delay pos-clique minimo (regra 16)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(usuario)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}L01_usuario.png")
        return self._step("L01", "clicar no campo Usuario e digitar", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # L02 — clicar no campo Senha e digitar
    # ------------------------------------------------------------------
    def _step_l02_senha(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            senha = self._dado(dados, "senha", "L02")
            x, y = self._coord(coords, "campo_senha")
            pyautogui.click(x, y)
            time.sleep(0.5)  # delay pos-clique minimo (regra 16)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(senha)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}L02_senha.png")
        return self._step("L02", "clicar no campo Senha e digitar", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # L03 — clicar em Conectar e confirmar menu principal
    # _clicar_aguardar substitui safe_click + time.sleep fixo
    # confirmacao: menu_principal_login.png (score 1.0 no diagnose)
    # ------------------------------------------------------------------
    def _step_l03_conectar(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            x, y = self._coord(coords, "btn_conectar")
            self._clicar_aguardar(
                ctx,
                acao=lambda: pyautogui.click(x, y),
                confirmacao=f"{self._TPL}/menu_principal_login.png",
                timeout=20,    # login pode demorar dependendo do servidor
                threshold=0.7, # score 1.0 no diagnose — threshold conservador
                retries=2,
                label="L03 conectar ao SI3",
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}L03_conectar.png")
        return self._step(
            "L03", "clicar em Conectar e confirmar menu principal",
            fn, observer, validated=True, ctx=ctx
        )