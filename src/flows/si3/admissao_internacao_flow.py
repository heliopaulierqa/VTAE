# src/flows/si3/admissao_internacao_flow.py
"""
AdmissaoInternacaoFlow — SI3 Oracle Forms
v0.5.10: migrado para BaseFlow.

Mudancas vs v0.5.4:
  - herda BaseFlow — _step(), _dado(), _coord(), _tpl_existe(), _focar_si3() removidos
  - todos os dados.get("chave", "DEFAULT") substituidos por _dado()
  - assinatura _coord(coords, nome) — nao passa mais ctx
  - description propagada para StepResult via BaseFlow._step()
  - observer.log_step_start/result removidos dos steps — BaseFlow._step() cuida disso
  - log_step_result duplicado no execute() removido
"""

import time

import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.vision.ocr import OcrHelper


class AdmissaoInternacaoFlow(BaseFlow):
    """
    Fluxo de Admissao de Internacao no SI3 (Oracle Forms - Desktop).
    Pressupoe que o login ja foi executado via LoginFlow.

    O ID do paciente e informado via config.DADOS["paciente_id"] —
    nunca hardcoded, em conformidade com a LGPD.

    Templates em templates/si3/admissao_internacao/:
        menu_internacao, campo_identificado, btn_pesquisar,
        aba_endereco, btn_admitir_paciente,
        campo_provedor, campo_plano,
        btn_info_compl, btn_ok_popup,
        opcao_consultorio_interno,
        btn_salvar, btn_sair
    """

    FLOW_NAME = "AdmissaoInternacaoFlow"
    _TPL = "templates/si3/admissao_internacao"

    # Regiao para OCR do Nr Admissao — ajustar conforme resolucao
    _REGIAO_NR_ADMISSAO = (10, 100, 280, 155)

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas

        steps = [
            lambda: self._step_abrir_internacao(ctx, observer),
            lambda: self._step_informar_paciente(ctx, dados, observer),
            lambda: self._step_pesquisar(ctx, observer),
            lambda: self._step_aba_endereco(ctx, observer),
            lambda: self._step_verificar_tipo_endereco(ctx, coords, observer),
            lambda: self._step_admitir_paciente(ctx, observer),
            lambda: self._step_unidade_funcional(ctx, dados, observer),
            lambda: self._step_provedor_plano(ctx, dados, observer),
            lambda: self._step_obs(ctx, dados, coords, observer),
            lambda: self._step_origem_paciente(ctx, dados, coords, observer),
            lambda: self._step_origem_solicitacao(ctx, coords, observer),
            lambda: self._step_profissional_responsavel(ctx, dados, coords, observer),
            lambda: self._step_info_compl(ctx, observer),
            lambda: self._step_numero_medico(ctx, dados, coords, observer),
            lambda: self._step_salvar(ctx, observer),
            lambda: self._step_retornar(ctx, coords, observer),
            lambda: self._step_validar_admissao(ctx, observer),
            lambda: self._step_sair(ctx, observer),
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

    # ------------------------------------------------------------------
    # AI01 — Abrir modulo Internacao
    # ------------------------------------------------------------------

    def _step_abrir_internacao(self, ctx, observer=None):
        def fn():
            ctx.runner.wait_template(
                f"{self._TPL}/menu_internacao.png", timeout=5, threshold=0.7
            )
            ctx.runner.double_click(f"{self._TPL}/menu_internacao.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/campo_identificado.png", timeout=15.0, threshold=0.7
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI01_internacao.png")
        return self._step("AI01", "abrir modulo Internacao via menu",
                          fn, observer,
                          confirm_template=f"{self._TPL}/campo_identificado.png",
                          ctx=ctx)

    # ------------------------------------------------------------------
    # AI02 — Informar ID do paciente
    # ------------------------------------------------------------------

    def _step_informar_paciente(self, ctx, dados: dict, observer=None):
        def fn():
            paciente_id = self._dado(dados, "paciente_id", "AI02")
            found = ctx.runner.click_near(
                f"{self._TPL}/campo_identificado.png",
                offset_x=150, offset_y=0, threshold=0.65
            )
            if not found:
                pyautogui.press("tab"); time.sleep(0.3)
                pyautogui.press("tab"); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(paciente_id)
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI02_paciente.png")
        return self._step("AI02", "informar ID do paciente", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI03 — Pesquisar paciente
    # ------------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/aba_endereco.png", timeout=10, threshold=0.7
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI03_pesquisa.png")
        return self._step("AI03", "pesquisar paciente",
                          fn, observer,
                          confirm_template=f"{self._TPL}/aba_endereco.png",
                          ctx=ctx)

    # ------------------------------------------------------------------
    # AI04 — Clicar na aba Endereco
    # ------------------------------------------------------------------

    def _step_aba_endereco(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/aba_endereco.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI04_endereco.png")
        return self._step("AI04", "clicar na aba Enderecos", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI05 — Campo Tipo do endereco via LOV
    # ------------------------------------------------------------------

    def _step_verificar_tipo_endereco(self, ctx, coords, observer=None):
        def fn():
            lov = coords["lov_tipo_endereco"]
            pyautogui.click(lov["btn_lov_x"], lov["btn_lov_y"]); time.sleep(1.5)
            pyautogui.click(lov["campo_localizar_x"], lov["campo_localizar_y"])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text("RUA"); time.sleep(0.3)
            pyautogui.click(lov["btn_localizar_x"], lov["btn_localizar_y"]); time.sleep(1.0)
            pyautogui.click(lov["btn_ok_x"], lov["btn_ok_y"]); time.sleep(0.5)
            if ctx.runner.is_visible(f"{self._TPL}/btn_ok_popup.png", threshold=0.7):
                ctx.runner.safe_click(f"{self._TPL}/btn_ok_popup.png", threshold=0.7)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI05_tipo_end.png")
        return self._step("AI05", "selecionar RUA no campo Tipo via LOV",
                          fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI06 — Admitir Paciente
    # ------------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI06_admitir.png")
        return self._step("AI06", "clicar em Admitir Paciente", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI07 — Unidade Funcional
    # ------------------------------------------------------------------

    def _step_unidade_funcional(self, ctx, dados: dict, observer=None):
        def fn():
            valor = self._dado(dados, "unidade_funcional", "AI07")
            ctx.runner.type_text(valor)
            pyautogui.press("tab"); time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI07_unidade.png")
        return self._step("AI07", "preencher Unidade Funcional", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI08 — Provedor e Plano
    # ------------------------------------------------------------------

    def _step_provedor_plano(self, ctx, dados: dict, observer=None):
        def fn():
            provedor = self._dado(dados, "provedor", "AI08")
            plano    = self._dado(dados, "plano", "AI08")
            ctx.runner.click_near(
                f"{self._TPL}/campo_provedor.png", offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.5)
            ctx.runner.click_near(
                f"{self._TPL}/campo_plano.png", offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI08_provedor_plano.png")
        return self._step("AI08", "preencher Provedor e Plano", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI09 — Observacao
    # ------------------------------------------------------------------

    def _step_obs(self, ctx, dados: dict, coords, observer=None):
        def fn():
            valor = self._dado(dados, "obs", "AI09")
            x, y = self._coord(coords, "obs")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(valor); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI09_obs.png")
        return self._step("AI09", "preencher campo Obs", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI10 — Origem do Paciente
    # ------------------------------------------------------------------

    def _step_origem_paciente(self, ctx, dados: dict, coords, observer=None):
        def fn():
            tipo = self._dado(dados, "origem_tipo", "AI10")
            x, y = self._coord(coords, "tipo_origem")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(tipo)
            pyautogui.press("tab"); time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI10_origem.png")
        return self._step("AI10", "preencher Origem do Paciente", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI11 — Origem da Solicitacao (dropdown)
    # ------------------------------------------------------------------

    def _step_origem_solicitacao(self, ctx, coords, observer=None):
        def fn():
            x, y = self._coord(coords, "dropdown_origem_solicitacao")
            pyautogui.click(x, y); time.sleep(1.5)
            ctx.runner.safe_click(
                f"{self._TPL}/opcao_consultorio_interno.png", threshold=0.7
            )
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI11_solicitacao.png")
        return self._step("AI11", "selecionar Origem da Solicitacao — dropdown",
                          fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI12 — Profissional Responsavel
    # ------------------------------------------------------------------

    def _step_profissional_responsavel(self, ctx, dados: dict, coords, observer=None):
        def fn():
            matricula = self._dado(dados, "matricula_responsavel", "AI12")
            x, y = self._coord(coords, "matricula_responsavel")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(matricula)
            pyautogui.press("tab"); time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI12_responsavel.png")
        return self._step("AI12", "preencher matricula do Profissional Responsavel",
                          fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI13 — Info. Complementar de Internacao
    # ------------------------------------------------------------------

    def _step_info_compl(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_info_compl.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI13_info_compl.png")
        return self._step("AI13", "clicar em Info. Compl de Internacao",
                          fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI14 — Numero no popup Info. Compl. + OK no popup de profissional
    # ------------------------------------------------------------------

    def _step_numero_medico(self, ctx, dados: dict, coords, observer=None):
        def fn():
            numero = self._dado(dados, "numero_compl", "AI14")
            x, y = self._coord(coords, "numero_medico_popup")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(numero)
            pyautogui.press("tab")
            ctx.runner.wait_template(
                f"{self._TPL}/btn_ok_popup.png", timeout=5, threshold=0.7
            )
            ctx.runner.safe_click(f"{self._TPL}/btn_ok_popup.png", threshold=0.7)
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI14_numero.png")
        return self._step("AI14", "preencher numero e confirmar medico",
                          fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI15 — Salvar
    # ------------------------------------------------------------------

    def _step_salvar(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_salvar.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI15_salvo.png")
        return self._step("AI15", "clicar em Salvar", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI16 — Retornar
    # ------------------------------------------------------------------

    def _step_retornar(self, ctx, coords, observer=None):
        def fn():
            x, y = self._coord(coords, "btn_retornar")
            pyautogui.click(x, y)
            time.sleep(3.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI16_retornar.png")
        return self._step("AI16", "clicar em Retornar", fn, observer, ctx=ctx)

    # ------------------------------------------------------------------
    # AI17 — Validar Nr Admissao via OCR
    # ------------------------------------------------------------------

    def _step_validar_admissao(self, ctx, observer=None):
        def fn():
            import re
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AI17_validacao.png")
            texto = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_NR_ADMISSAO)
            numeros = re.findall(r"\d+", texto)
            if not numeros:
                OcrHelper.salvar_debug(
                    screenshot_path, self._REGIAO_NR_ADMISSAO,
                    f"{ctx.evidence_dir}AI17_ocr_debug.png"
                )
                raise AssertionError(
                    f"Nr Admissao nao encontrado — admissao pode ter falhado.\n"
                    f"Texto lido via OCR: '{texto}'\n"
                    f"Veja AI17_ocr_debug.png e ajuste _REGIAO_NR_ADMISSAO."
                )
            print(f"[AI17] Nr Admissao: {numeros[0]}")
            return screenshot_path
        return self._step("AI17", "validar Nr Admissao via OCR",
                          fn, observer, validated=True, ctx=ctx)

    # ------------------------------------------------------------------
    # AI18 — Sair
    # ------------------------------------------------------------------

    def _step_sair(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI18_sair.png")
        return self._step("AI18", "sair para Menu Principal", fn, observer, ctx=ctx)