# src/flows/si3/agendamento_flow.py
"""
AgendamentoFlow — SI3 Oracle Forms
v0.5.10: migrado para BaseFlow.

Mudancas vs v0.5.9:
  - herda BaseFlow — _step(), _dado(), _coord(), _tpl_existe(), _focar_si3()
    e _fechar_popup_ok() removidos (centralizados em BaseFlow ou mantidos
    como helper privado do flow por ser especifico)
  - description propagada automaticamente pelo BaseFlow._step()
  - ctx=ctx adicionado em todos os _step() para confirm_template funcionar
"""

import datetime
import time

import pyautogui

from src.core.context import FlowContext
from src.core.estado_jornada import ler as _ler_estado, salvar as _salvar_estado
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow


class AgendamentoFlow(BaseFlow):

    FLOW_NAME = "AgendamentoFlow"
    _TPL      = "templates/si3/agendamento"
    _TPL_AMB  = "templates/si3/admissao_ambulatorio"

    # ----------------------------------------------------------------
    # Helper privado especifico deste flow — NAO vai para BaseFlow
    # pois depende de ctx (runner) que nao e parametro do BaseFlow
    # ----------------------------------------------------------------

    def _fechar_popup_ok(self, ctx, template: str, timeout: float = 5.0) -> bool:
        """Aguarda popup e clica OK. Retorna True se encontrou."""
        apareceu = ctx.runner.wait_template(template, timeout=timeout, threshold=0.7)
        if apareceu:
            ctx.runner.safe_click(template, threshold=0.7)
            time.sleep(0.5)
        return apareceu

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas

        steps = [
            lambda: self._step_abrir_agendar(ctx, dados, coords, observer),
            lambda: self._step_provedor(ctx, dados, coords, observer),
            lambda: self._step_plano(ctx, dados, coords, observer),
            lambda: self._step_codigo_procedimento(ctx, dados, coords, observer),
            lambda: self._step_complemento(ctx, dados, coords, observer),
            lambda: self._step_area_executora(ctx, dados, coords, observer),
            lambda: self._step_executante(ctx, dados, coords, observer),
            lambda: self._step_clicar_agendar(ctx, coords, observer),
            lambda: self._step_recursos_disponiveis(ctx, coords, observer),
            lambda: self._step_data_hora(ctx, dados, coords, observer),
            lambda: self._step_confirmar_paciente(ctx, coords, observer),
            lambda: self._step_fechar_conclusao(ctx, observer),
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

    # ----------------------------------------------------------------
    # AG01 — Abrir modulo Agendar via Localizar no Menu
    # ----------------------------------------------------------------

    def _step_abrir_agendar(self, ctx, dados: dict, coords, observer=None):
        def fn():
            termo = self._dado(dados, "termo_menu_ag", "AG01")
            x, y = self._coord(coords, "campo_localizar_menu")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo); time.sleep(0.3)
            ctx.runner.safe_click(f"{self._TPL_AMB}/btn_pesquisar_menu.png", threshold=0.7)
            time.sleep(1.0)
            apareceu = ctx.runner.wait_template(
                f"{self._TPL_AMB}/btn_nao_popup.png", timeout=5.0, threshold=0.7
            )
            if not apareceu:
                raise AssertionError(
                    f"Popup 'Continuar Busca?' nao apareceu apos pesquisar '{termo}'."
                )
            ctx.runner.safe_click(f"{self._TPL_AMB}/btn_nao_popup.png", threshold=0.7)
            time.sleep(0.8)
            ctx.runner.double_click(f"{self._TPL}/menu_agendar.png", threshold=0.7)
            time.sleep(1.5)
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/tela_agendar.png", timeout=15.0, threshold=0.7
            )
            if not apareceu:
                raise AssertionError("Tela de Agendar nao abriu. Verifique tela_agendar.png.")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG01_agendar.png")
        return self._step("AG01", "abrir modulo Agendar via Localizar no Menu",
                          fn, observer,
                          confirm_template=f"{self._TPL}/tela_agendar.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AG02 — Provedor
    # ----------------------------------------------------------------

    def _step_provedor(self, ctx, dados: dict, coords, observer=None):
        def fn():
            provedor = self._dado(dados, "provedor_ag", "AG02")
            x, y = self._coord(coords, "campo_provedor_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.8)
            self._fechar_popup_ok(ctx, f"{self._TPL}/btn_ok_popup_ag.png", timeout=4.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG02_provedor.png")
        return self._step("AG02", "preencher Provedor", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG03 — Plano
    # ----------------------------------------------------------------

    def _step_plano(self, ctx, dados: dict, coords, observer=None):
        def fn():
            plano = self._dado(dados, "plano_ag", "AG03")
            x, y = self._coord(coords, "campo_plano_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.3)
            pyautogui.press("tab"); time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG03_plano.png")
        return self._step("AG03", "preencher Plano", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG04 — Codigo do procedimento
    # ----------------------------------------------------------------

    def _step_codigo_procedimento(self, ctx, dados: dict, coords, observer=None):
        def fn():
            codigo = self._dado(dados, "codigo_proc_ag", "AG04")
            x, y = self._coord(coords, "campo_codigo_proc_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(codigo)
            pyautogui.press("tab"); time.sleep(0.8)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG04_codigo.png")
        return self._step("AG04", "preencher Codigo do procedimento", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG05 — Complemento
    # ----------------------------------------------------------------

    def _step_complemento(self, ctx, dados: dict, coords, observer=None):
        def fn():
            complemento = self._dado(dados, "complemento_ag", "AG05")
            x, y = self._coord(coords, "campo_complemento_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(complemento)
            for _ in range(4):
                pyautogui.press("tab"); time.sleep(0.2)
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG05_complemento.png")
        return self._step("AG05", "preencher Complemento", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG06 — Area Executora
    # ----------------------------------------------------------------

    def _step_area_executora(self, ctx, dados: dict, coords, observer=None):
        def fn():
            area = self._dado(dados, "area_executora_ag", "AG06")
            time.sleep(0.5)
            x, y = self._coord(coords, "campo_busca_area_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(area); time.sleep(0.3)
            pyautogui.press("return"); time.sleep(1.0)
            x, y = self._coord(coords, "btn_ok_area_ag")
            pyautogui.click(x, y); time.sleep(0.8)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG06_area.png")
        return self._step("AG06", "selecionar Area Executora", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG07 — Executante via LOV (verify_lov obrigatorio)
    # ----------------------------------------------------------------

    def _step_executante(self, ctx, dados: dict, coords, observer=None):
        def fn():
            termo_exec = self._dado(dados, "termo_executante_ag", "AG07")
            x, y = self._coord(coords, "btn_lov_executante_ag")
            pyautogui.click(x, y); time.sleep(1.5)
            x, y = self._coord(coords, "campo_busca_executante_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(termo_exec); time.sleep(0.3)
            pyautogui.press("return"); time.sleep(1.5)
            x, y = self._coord(coords, "item_medico_executante_ag")
            pyautogui.doubleClick(x, y); time.sleep(1.8)

            regiao_exec = ctx.config.regioes_ocr.get("campo_executante_ag")
            if regiao_exec:
                regiao = (
                    regiao_exec["x1"], regiao_exec["y1"],
                    regiao_exec["x2"], regiao_exec["y2"],
                )
                if not ctx.runner.verify_lov(
                    "Executante", region=regiao,
                    debug_path=f"{ctx.evidence_dir}AG07_executante_verify_debug.png",
                ):
                    raise AssertionError(
                        "Falha de Observabilidade: campo Executante ficou VAZIO apos LOV.\n"
                        f"Termo buscado: '{termo_exec}'\n"
                        "Veja AG07_executante_verify_debug.png."
                    )
            else:
                print("[AG07] AVISO: regioes_ocr.campo_executante_ag nao configurado — "
                      "verify_lov ignorado.")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG07_executante.png")
        return self._step("AG07", "selecionar Executante via LOV",
                          fn, observer, validated=True, ctx=ctx)

    # ----------------------------------------------------------------
    # AG08 — Clicar Agendar + fechar popups
    # ----------------------------------------------------------------

    def _step_clicar_agendar(self, ctx, coords, observer=None):
        def fn():
            if not self._focar_si3():
                print("[AG08] AVISO: nao foi possivel focar SI3 — pip install pygetwindow")
            pyautogui.press("escape"); time.sleep(0.3)
            pyautogui.press("escape"); time.sleep(0.3)
            x, y = self._coord(coords, "btn_agendar_ag")
            pyautogui.click(x, y); time.sleep(2.0)

            tpl_ok = f"{self._TPL}/btn_ok_popup_ag.png"
            if self._tpl_existe(tpl_ok) and ctx.runner.wait_template(tpl_ok, timeout=4.0, threshold=0.7):
                ctx.runner.safe_click(tpl_ok, threshold=0.7)
                time.sleep(0.8)
                print("[AG08] Popup HC-INCOR fechado — OK")

            tpl_info = f"{self._TPL}/tela_info_profissional_ag.png"
            if self._tpl_existe(tpl_info):
                if ctx.runner.wait_template(tpl_info, timeout=4.0, threshold=0.7):
                    x, y = self._coord(coords, "btn_fechar_info_ag")
                    pyautogui.click(x, y); time.sleep(1.5)
                    print("[AG08] Tela Informacoes do Profissional fechada via template")
            else:
                time.sleep(3.0)
                x, y = self._coord(coords, "btn_fechar_info_ag")
                pyautogui.click(x, y); time.sleep(1.5)
                print("[AG08] Tela Informacoes do Profissional fechada por coordenada")

            time.sleep(1.5)
            tpl_rec = f"{self._TPL}/tela_recursos_ag.png"
            if self._tpl_existe(tpl_rec):
                if ctx.runner.wait_template(tpl_rec, timeout=3.0, threshold=0.65):
                    print("[AG08] Tela Recursos detectada — AG09 vai tratar")
                else:
                    print("[AG08] Tela Recursos nao apareceu — indo para Agendamento")
            else:
                print("[AG08] AVISO: tela_recursos_ag.png ausente — capturar")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG08_agendar.png")
        return self._step("AG08", "clicar Agendar e fechar tela Informacoes",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG09 — Tela Recursos disponiveis — tolerante
    # ----------------------------------------------------------------

    def _step_recursos_disponiveis(self, ctx, coords, observer=None):
        def fn():
            self._focar_si3()
            tpl_rec = f"{self._TPL}/tela_recursos_ag.png"
            na_tela_recursos = False
            if self._tpl_existe(tpl_rec):
                na_tela_recursos = ctx.runner.wait_template(tpl_rec, timeout=3.0, threshold=0.65)

            if na_tela_recursos:
                tpl_pop = f"{self._TPL}/popup_recurso_ag.png"
                if self._tpl_existe(tpl_pop) and ctx.runner.wait_template(tpl_pop, timeout=3.0, threshold=0.7):
                    print("[AG09] Popup LOV recurso — selecionando primeiro item")
                    x, y = self._coord(coords, "item_recurso_ag")
                    pyautogui.click(x, y); time.sleep(0.3)
                    x, y = self._coord(coords, "btn_ok_recurso_ag")
                    pyautogui.click(x, y); time.sleep(1.0)
                x, y = self._coord(coords, "btn_ok_recursos_ag")
                pyautogui.click(x, y); time.sleep(1.5)
                print("[AG09] Tela Recursos — clicou OK")
            else:
                print("[AG09] Tela Recursos nao apareceu — prosseguindo")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG09_recursos.png")
        return self._step("AG09", "tela Recursos disponiveis — tolerante",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG10 — Data + Hora Inicial + TAB + popup Sim + OK
    # ----------------------------------------------------------------

    def _step_data_hora(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._focar_si3(); time.sleep(0.5)
            horas_offset = self._dado(dados, "horas_offset_ag", "AG10")
            hoje    = datetime.date.today().strftime("%d/%m/%Y")
            agora   = datetime.datetime.now()
            hora_ag = (agora + datetime.timedelta(hours=int(horas_offset))).strftime("%H:%M")
            print(f"[AG10] Agendando para: {hoje} {hora_ag} (offset: +{horas_offset}h)")

            x, y = self._coord(coords, "campo_data_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(hoje)
            pyautogui.press("tab"); time.sleep(0.5)

            x, y = self._coord(coords, "campo_hora_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(hora_ag)
            pyautogui.press("tab"); time.sleep(1.5)

            if ctx.runner.wait_template(
                f"{self._TPL}/btn_sim_popup_ag.png", timeout=4.0, threshold=0.7
            ):
                ctx.runner.safe_click(f"{self._TPL}/btn_sim_popup_ag.png", threshold=0.7)
                time.sleep(0.8); print("[AG10] Popup sem oferta — clicou Sim")

            _salvar_estado("hora_agendamento", hora_ag)
            _salvar_estado("data_agendamento", hoje)

            x, y = self._coord(coords, "btn_ok_horario_ag")
            pyautogui.click(x, y); time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG10_data_hora.png")
        return self._step("AG10", "preencher Data e Hora Inicial", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG11 — Tela Agendamento individual — ID + TAB + Confirmar
    # ----------------------------------------------------------------

    def _step_confirmar_paciente(self, ctx, coords, observer=None):
        def fn():
            self._focar_si3(); time.sleep(0.5)
            paciente_id = _ler_estado("paciente_id")
            print(f"[AG11] Confirmando agendamento para paciente: {paciente_id}")

            x, y = self._coord(coords, "campo_id_paciente_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(paciente_id)
            pyautogui.press("tab"); time.sleep(2.0)

            x, y = self._coord(coords, "btn_confirmar_ag")
            pyautogui.click(x, y); time.sleep(2.0)

            tpl_conc = f"{self._TPL}/tela_conclusao_ag.png"
            if self._tpl_existe(tpl_conc):
                if not ctx.runner.wait_template(tpl_conc, timeout=10.0, threshold=0.65):
                    raise AssertionError(
                        "AG11: tela Conclusao nao apareceu apos Confirmar.\n"
                        "Causas possiveis:\n"
                        "  1. Paciente ja possui agendamento para este procedimento/data\n"
                        "  2. Convenio/plano nao cobre o procedimento\n"
                        "  3. ID do paciente nao carregou (TAB muito rapido)\n"
                        "Acao: veja AG11_confirmar.png."
                    )
            else:
                print("[AG11] AVISO: tela_conclusao_ag.png ausente — usando timeout fixo")
                time.sleep(3.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG11_confirmar.png")
        return self._step("AG11", "confirmar agendamento do paciente", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG12 — Fechar tela de Conclusao
    # ----------------------------------------------------------------

    def _step_fechar_conclusao(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_fechar_ag.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG12_conclusao.png")
        return self._step("AG12", "fechar tela de Conclusao do agendamento",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AG13 — Sair do modulo Agendar
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_sair_ag.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair_ag.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG13_sair.png")
        return self._step("AG13", "sair para Menu Principal", fn, observer, ctx=ctx)