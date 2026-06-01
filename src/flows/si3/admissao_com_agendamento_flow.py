# src/flows/si3/admissao_com_agendamento_flow.py
"""
AdmissaoComAgendamentoFlow — SI3 Oracle Forms
v0.5.10: migrado para BaseFlow (herda via AdmissaoAmbulatorioFlow).

Mudancas vs v0.5.9c:
  - BUG CORRIGIDO: indentacao incorreta no _step_admitir_paciente —
    o bloco `if not apareceu` estava fora do fn(), causando erro de
    escopo. Corrigido para estar dentro de fn().
  - ctx=ctx adicionado em todos os _step() calls
  - herda BaseFlow via AdmissaoAmbulatorioFlow — sem _step() proprio

Pendente (Fase 5g):
  - Capturar btn_admitir_com_agendamento.png
  - Calibrar coordenadas: primeira_linha_grade_ag, btn_admitir_ag,
    campo_nome_medico_ab
"""

import time

import pyautogui

from src.core.result import StepResult
from src.flows.si3.admissao_ambulatorio_flow import AdmissaoAmbulatorioFlow


class AdmissaoComAgendamentoFlow(AdmissaoAmbulatorioFlow):
    """
    Especializacao do AdmissaoAmbulatorioFlow para pacientes com agendamento.
    Herda 90% do flow base — sobrescreve apenas os steps que diferem:
      _step_pesquisar         → AB03: detecta tela de agendamentos
      _step_admitir_paciente  → AB05: clicar ADMITIR na tela de agendamentos
      _step_unidade_funcional → AB06: unidade diferente + provedor ja preenchido
      _step_provedor_plano    → AB07: ja preenchido + fechar popups elegibilidade
      _step_medico_responsavel → AB11: MEDICO + TAB sem LOV
    """

    FLOW_NAME = "AdmissaoComAgendamentoFlow"
    _TPL      = "templates/si3/admissao_ambulatorio"
    _TPL_AG   = "templates/si3/agendamento"

    # ----------------------------------------------------------------
    # AB03 — Pesquisar — tela com grade de Agendamentos
    # ----------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            time.sleep(1.5)
            tpl_admitir = f"{self._TPL}/btn_admitir_com_agendamento.png"
            if self._tpl_existe(tpl_admitir):
                apareceu = ctx.runner.wait_template(tpl_admitir, timeout=10, threshold=0.7)
            else:
                print("[AB03] AVISO: btn_admitir_com_agendamento.png ausente — "
                      "usando btn_admitir_paciente como fallback")
                apareceu = ctx.runner.wait_template(
                    f"{self._TPL}/btn_admitir_paciente.png", timeout=10, threshold=0.7
                )
            if not apareceu:
                raise AssertionError(
                    "AB03: botao ADMITIR nao apareceu apos pesquisa. "
                    "Verifique se o paciente tem agendamento cadastrado "
                    "e se btn_admitir_com_agendamento.png foi capturado."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB03_pesquisa_ag.png")
        return self._step("AB03", "pesquisar paciente com agendamento",
                          fn, observer,
                          confirm_template=f"{self._TPL}/btn_admitir_paciente.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB05 — Admitir Paciente na tela de agendamentos
    # BUG CORRIGIDO: if not apareceu estava fora do fn() na versao anterior
    # ----------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None) -> StepResult:
        def fn():
            coords = ctx.config.coordenadas

            # 1. Clicar na primeira linha da grade para selecionar o agendamento
            x, y = self._coord(coords, "primeira_linha_grade_ag")
            pyautogui.click(x, y); time.sleep(0.5)

            # 2. Clicar em Admitir
            x, y = self._coord(coords, "btn_admitir_ag")
            pyautogui.click(x, y); time.sleep(2.0)

            # 3. Clicar em Admitir pelo template (com fallback)
            tpl_admitir = f"{self._TPL}/btn_admitir_com_agendamento.png"
            if self._tpl_existe(tpl_admitir):
                ctx.runner.safe_click(tpl_admitir, threshold=0.7)
            else:
                ctx.runner.safe_click(
                    f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7
                )
            time.sleep(2.0)

            # 4. Fechar popup webservice elegibilidade — pode aparecer ate 2x
            for tentativa in range(2):
                tpl_sim = f"{self._TPL}/btn_ok_convenio.png"
                if ctx.runner.wait_template(tpl_sim, timeout=3.0, threshold=0.7):
                    ctx.runner.safe_click(tpl_sim, threshold=0.7)
                    time.sleep(1.0)
                    print(f"[AB05] Popup elegibilidade fechado (tentativa {tentativa + 1})")
                else:
                    break

            # 5. Confirm: formulario de admissao abriu
            # BUG CORRIGIDO: este bloco estava fora de fn() na versao anterior
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/campo_unidade_funcional.png", timeout=10, threshold=0.65
            )
            if not apareceu:
                raise AssertionError(
                    "AB05: formulario de admissao nao abriu apos Admitir. "
                    "Verifique se a primeira linha foi selecionada corretamente "
                    "e se o popup de elegibilidade foi tratado. "
                    "Veja AB05_admitir_ag.png."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB05_admitir_ag.png")
        return self._step("AB05", "selecionar agendamento e clicar Admitir",
                          fn, observer,
                          confirm_template=f"{self._TPL}/campo_unidade_funcional.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB06 — Unidade Funcional — CLINICA DE CARDIOPATIA GERAL
    # ----------------------------------------------------------------

    def _step_unidade_funcional(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            unidade = self._dado(dados, "unidade_funcional", "AB06")
            ctx.runner.click_near(
                f"{self._TPL}/campo_unidade_funcional.png",
                offset_x=200, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(unidade)
            pyautogui.press("tab"); time.sleep(0.5)
            pyautogui.press("tab"); time.sleep(0.5)
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/campo_provedor.png", timeout=8, threshold=0.65
            )
            if not apareceu:
                raise AssertionError(
                    "AB06: campo_provedor nao visivel apos Unidade Funcional."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB06_unidade_ag.png")
        return self._step("AB06", "preencher Unidade Funcional",
                          fn, observer,
                          confirm_template=f"{self._TPL}/campo_provedor.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB07 — Provedor/Plano — ja preenchido + fechar popups elegibilidade
    # ----------------------------------------------------------------

    def _step_provedor_plano(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            for tentativa in range(2):
                tpl_sim = f"{self._TPL}/btn_ok_convenio.png"
                if ctx.runner.wait_template(tpl_sim, timeout=2.0, threshold=0.7):
                    ctx.runner.safe_click(tpl_sim, threshold=0.7)
                    time.sleep(0.8)
                    print(f"[AB07] Popup elegibilidade fechado (tentativa {tentativa+1})")
                else:
                    break
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB07_provedor_ag.png")
        return self._step("AB07",
                          "verificar Provedor/Plano preenchidos do agendamento",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB11 — Medico Responsavel — MEDICO + TAB (sem LOV)
    # ----------------------------------------------------------------

    def _step_medico_responsavel(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            nome_medico = self._dado(ctx.config.DADOS, "nome_medico_ab", "AB11")
            x, y = self._coord(coords, "campo_nome_medico_ab")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(nome_medico)
            pyautogui.press("tab"); time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB11_medico_ag.png")
        return self._step("AB11", "preencher Medico Responsavel por digitacao",
                          fn, observer, ctx=ctx)