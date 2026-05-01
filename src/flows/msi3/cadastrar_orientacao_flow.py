# src/flows/msi3/cadastrar_orientacao_flow.py
import time
import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult
from src.flows.msi3.apex_helper import ApexHelper
from src.runners.opencv_runner import OpenCVRunner


class CadastrarOrientacaoFlow:
    """
    Fluxo de cadastro de orientação no MSI3 (Oracle APEX - Web).
    Pressupõe que o login já foi executado via LoginFlowMsi3.

    Navegação:
        sidebar "Sistema de Pacientes"
        → card "Cadastros Básicos"    (OpenCV — sem href CSS)
        → card "Orientação"           (OpenCV — sem href CSS)
        → botão "Cadastrar Nova Orientação" (OpenCV)
        → preenche Código e Descrição (Playwright via frame)
        → clica Salvar

    Templates em templates/msi3/orientacao/:
        card_cadastros_basicos.png
        card_orientacao.png
        btn_cadastrar_nova_orientacao.png

    IDs no DevTools (frame f?p=...):
        #P_ORNT_CD   → Código
        #P_ORNT_DS   → Descrição
        B<id>        → botão Salvar (inspecionar no DevTools)
    """

    FLOW_NAME = "CadastrarOrientacaoFlow"

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        """
        Args:
            ctx: FlowContext com runner já autenticado (PlaywrightRunner).
            dados: {
                "codigo":    "ORT01",
                "descricao": "DESCRIÇÃO DA ORIENTAÇÃO",
            }
        """
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_sistema_pacientes(ctx, observer),
            lambda: self._step_cadastros_basicos(ctx, observer),
            lambda: self._step_card_orientacao(ctx, observer),
            lambda: self._step_btn_nova_orientacao(ctx, observer),
            lambda: self._step_preencher_formulario(ctx, dados, observer),
            lambda: self._step_salvar(ctx, dados, observer),
        ]

        for step_fn in steps:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    # ------------------------------------------------------------------ #
    #  Navegação                                                           #
    # ------------------------------------------------------------------ #

    def _step_sistema_pacientes(self, ctx, observer=None) -> StepResult:
        step_id = "CO01"
        if observer:
            observer.log_step_start(step_id, "sidebar Sistema de Pacientes")
        start = time.monotonic()
        try:
            ctx.runner._page.get_by_role("link", name="Sistema de Pacientes").click()
            ApexHelper.aguardar_spinner(ctx.runner)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CO01_sidebar.png")
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

    def _step_cadastros_basicos(self, ctx, observer=None) -> StepResult:
        step_id = "CO02"
        if observer:
            observer.log_step_start(step_id, "card Cadastros Básicos (OpenCV)")
        start = time.monotonic()
        try:
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/orientacao/card_cadastros_basicos.png")
            ApexHelper.aguardar_spinner(ctx.runner)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CO02_cadastros.png")
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

    def _step_card_orientacao(self, ctx, observer=None) -> StepResult:
        step_id = "CO03"
        if observer:
            observer.log_step_start(step_id, "card Orientação (OpenCV)")
        start = time.monotonic()
        try:
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/orientacao/card_orientacao.png")

            # polling de URL — padrão MSI3 após clique OpenCV
            deadline = time.monotonic() + 15.0
            while time.monotonic() < deadline:
                info = ApexHelper.inspecionar_pagina(ctx.runner)
                if "orientacao" in info.get("url", "").lower() or "ornt" in info.get("url", "").lower():
                    break
                time.sleep(0.5)

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CO03_orientacao.png")
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

    def _step_btn_nova_orientacao(self, ctx, observer=None) -> StepResult:
        step_id = "CO04"
        if observer:
            observer.log_step_start(step_id, "botão Cadastrar Nova Orientação (OpenCV)")
        start = time.monotonic()
        try:
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/orientacao/btn_cadastrar_nova_orientacao.png")
            time.sleep(1.5)  # aguarda dialog abrir
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CO04_nova.png")
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

    # ------------------------------------------------------------------ #
    #  Formulário (frame de dialog)                                        #
    # ------------------------------------------------------------------ #

    def _step_preencher_formulario(self, ctx, dados: dict, observer=None) -> StepResult:
        """
        Formulário em frame de dialog — acesso via page.frames.
        IDs a confirmar no DevTools: #P_ORNT_CD e #P_ORNT_DS.
        """
        step_id = "CO05"
        if observer:
            observer.log_step_start(step_id, "preencher Código e Descrição")
        start = time.monotonic()
        try:
            frame = self._encontrar_frame(ctx, "#P_ORNT_CD")
            if frame is None:
                raise RuntimeError(
                    "Frame do formulário de orientação não encontrado.\n"
                    "Verifique os IDs dos campos no DevTools."
                )

            frame.locator("#P_ORNT_CD").fill(dados["codigo"])
            time.sleep(0.3)
            frame.locator("#P_ORNT_DS").fill(dados["descricao"])
            time.sleep(0.3)

            ApexHelper.verificar_sem_erro(ctx.runner)

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CO05_form.png")
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

    def _step_salvar(self, ctx, dados: dict, observer=None) -> StepResult:
        """
        Clica no botão Salvar dentro do frame e valida na grade.
        Confirmar o ID do botão Salvar no DevTools e atualizar _BTN_SALVAR_ID.
        """
        step_id = "CO06"
        if observer:
            observer.log_step_start(step_id, "clicar Salvar e validar grade")
        start = time.monotonic()

        # TODO: confirmar ID real no DevTools e atualizar aqui
        _BTN_SALVAR_ID = "B_SALVAR_ORIENTACAO"

        try:
            frame = self._encontrar_frame(ctx, "#P_ORNT_CD")
            if frame is None:
                raise RuntimeError("Frame do formulário não encontrado no step Salvar.")

            frame.locator(f"[id='{_BTN_SALVAR_ID}']").first.click()
            ApexHelper.aguardar_spinner(ctx.runner)
            ApexHelper.verificar_sem_erro(ctx.runner)
            ApexHelper.verificar_registro_na_grade(ctx.runner, texto=dados["codigo"])

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CO06_salvo.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            info = ApexHelper.inspecionar_pagina(ctx.runner)
            print(f"[CO06] falhou — {info}")
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    # ------------------------------------------------------------------ #
    #  Helper interno                                                       #
    # ------------------------------------------------------------------ #

    def _encontrar_frame(self, ctx, selector_id: str):
        """
        Itera pelos frames da página e retorna o primeiro que contém o seletor.
        Padrão MSI3 — formulários em dialog abrem em frame separado.
        """
        for frame in ctx.runner._page.frames:
            try:
                if frame.locator(selector_id).count() > 0:
                    return frame
            except Exception:
                pass
        return None
