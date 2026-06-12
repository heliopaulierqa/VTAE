# src/flows/si3/admissao_com_agendamento_flow.py
"""
AdmissaoComAgendamentoFlow — SI3 Oracle Forms
v0.5.15: AB05 corrigido — fluxo completo de 3 telas + guard por titulo de janela.

Historico:
  v0.5.10: migrado para BaseFlow (herda via AdmissaoAmbulatorioFlow).
  v0.5.15: AB05 — fluxo real mapeado em 12/06:
           Tela 1 "Cadastro de Pacientes" (Form_Pac0010, apos AB04)
             -> clica btn_admitir_paciente.png
           Tela 2 "Verificar Agendamento"
             -> clica primeira_linha_grade_ag (selecionar agendamento)
             -> clica btn_admitir_ag (botao Admitir)
           Tela 3 "AMBULATORIO" (formulario de admissao real)
             -> guard: titulo da janela contem "AMBULAT" e nao "VERIFICAR"
           Guard por titulo substitui wait_template como confirmacao —
           campo_unidade_funcional/label_ambulatorio/btn_guia_tiss davam
           score 1.0 mesmo com "Verificar Agendamento" aberta (Oracle Forms
           renderiza elementos de telas adjacentes).

Pendente (Fase 5g):
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
      _step_pesquisar          → AB03: pesquisar paciente
      _step_admitir_paciente   → AB05: 3 telas — Cadastro -> Verificar Agendamento -> Ambulatorio
      _step_unidade_funcional  → AB06: unidade diferente + provedor ja preenchido
      _step_provedor_plano     → AB07: ja preenchido + fechar popups elegibilidade
      _step_medico_responsavel → AB11: MEDICO + TAB sem LOV
    """

    FLOW_NAME = "AdmissaoComAgendamentoFlow"
    _TPL      = "templates/si3/admissao_ambulatorio"
    _TPL_AG   = "templates/si3/agendamento"

    # ----------------------------------------------------------------
    # Helper interno — verifica titulo da janela Oracle Forms
    # ----------------------------------------------------------------

    @staticmethod
    def _titulo_janela_contem(texto: str, excluir: str = None,
                               timeout: float = 10.0) -> bool:
        """
        Aguarda ate timeout segundos que alguma janela aberta contenha `texto`
        no titulo (case-insensitive), opcionalmente excluindo titulos que
        contenham `excluir`.

        Usado no AB05 para confirmar a tela final "AMBULATORIO":
          - Tela 2 (errada se ainda aberta): titulo "Verificar Agendamento"
          - Tela 3 (correta): titulo "AMBULATORIO"

        Retorna True se encontrou, False se esgotou o timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                import pygetwindow as gw
                titulos = gw.getAllTitles()
                for t in titulos:
                    t_upper = t.upper()
                    if texto.upper() in t_upper:
                        if excluir and excluir.upper() in t_upper:
                            continue
                        return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    # ----------------------------------------------------------------
    # AB03 — Pesquisar — tela Cadastro de Pacientes (Form_Pac0010)
    # ----------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            time.sleep(1.5)
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/btn_admitir_paciente.png", timeout=10, threshold=0.7
            )
            if not apareceu:
                raise AssertionError(
                    "AB03: botao 'Admitir paciente' nao apareceu apos pesquisa. "
                    "Verifique se o paciente foi encontrado corretamente."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB03_pesquisa_ag.png")
        return self._step("AB03", "pesquisar paciente com agendamento",
                          fn, observer,
                          confirm_template=f"{self._TPL}/btn_admitir_paciente.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB05 — Admitir Paciente — 3 telas
    #
    # Tela 1 "Cadastro de Pacientes" -> btn_admitir_paciente.png
    # Tela 2 "Verificar Agendamento" -> primeira_linha_grade_ag + btn_admitir_ag
    # Tela 3 "AMBULATORIO"           -> guard por titulo de janela
    #
    # GUARD v0.5.15: verificacao por titulo de janela.
    # wait_template com elemento visual nao funciona como guard final porque
    # Oracle Forms renderiza elementos das telas 2 e 3 simultaneamente
    # (score 1.0 em campo_unidade_funcional, label_ambulatorio, btn_guia_tiss
    # mesmo com "Verificar Agendamento" aberta).
    # O titulo da janela e o unico discriminador confiavel:
    #   "Verificar Agendamento" -> tela 2 ainda aberta -> falha
    #   "AMBULATORIO"           -> tela 3 aberta -> step passa
    # ----------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None) -> StepResult:
        def fn():
            coords = ctx.config.coordenadas

            # Tela 1 — Cadastro de Pacientes: clicar "Admitir paciente"
            # Abre a Tela 2 "Verificar Agendamento"
            ctx.runner.safe_click(f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7)
            time.sleep(2.0)

            # Tela 2 — Verificar Agendamento: selecionar agendamento + Admitir
            x, y = self._coord(coords, "primeira_linha_grade_ag")
            pyautogui.click(x, y); time.sleep(0.5)

            ctx.runner.safe_click(f"{self._TPL}/btn_admitir_verificar_ag.png", threshold=0.7)
            time.sleep(2.0)

            # Fechar popup webservice elegibilidade — pode aparecer ate 2x
            for tentativa in range(2):
                tpl_ok = f"{self._TPL}/btn_ok_convenio.png"
                if ctx.runner.wait_template(tpl_ok, timeout=3.0, threshold=0.7):
                    ctx.runner.safe_click(tpl_ok, threshold=0.7)
                    time.sleep(1.0)
                    print(f"[AB05] Popup elegibilidade fechado (tentativa {tentativa + 1})")
                else:
                    break

            # GUARD: Tela 3 "AMBULATORIO" — unico discriminador confiavel
            titulo_ok = self._titulo_janela_contem(
                texto="AMBULAT",
                excluir="VERIFICAR",
                timeout=10.0,
            )
            if not titulo_ok:
                raise AssertionError(
                    "AB05: formulario de admissao (tela 'AMBULATORIO') nao abriu.\n"
                    "Titulo da janela ainda indica 'Verificar Agendamento'.\n"
                    "Verifique e recalibre as coordenadas:\n"
                    "  primeira_linha_grade_ag — deve clicar na linha do agendamento\n"
                    "  btn_admitir_ag          — deve clicar no botao Admitir\n"
                    "Use: python scripts/posicao_mouse.py"
                )

            print("[AB05] Tela AMBULATORIO confirmada via titulo da janela")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB05_admitir_ag.png")

        return self._step("AB05", "selecionar agendamento e clicar Admitir",
                          fn, observer, validated=True, ctx=ctx)

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