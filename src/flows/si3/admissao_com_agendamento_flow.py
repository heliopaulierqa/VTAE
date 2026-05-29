# src/flows/si3/admissao_com_agendamento_flow.py
"""
AdmissaoComAgendamentoFlow — SI3 Oracle Forms
Versao: 0.5.9c — Fase 5e

Fluxo: CADASTRO → AGENDAMENTO → ADMISSÃO COM AGENDAMENTO

Pressupoe que login, cadastro e agendamento ja foram executados.
Le paciente_id e dados do agendamento do estado_jornada.json.

Diferenças vs AdmissaoAmbulatorioFlow:

  AB03: Apos pesquisar, aparece tela com grade de Agendamentos
        (Nome, Horario, Descricao do Procedimento, Complemento)
        → clicar em ADMITIR (botao diferente do fluxo sem agendamento)

  AB04: Aba Enderecos — igual ao flow base (reutilizado)

  AB05: Clicar ADMITIR na tela de agendamentos — botao diferente

  AB06: Unidade Funcional — valor diferente (CLINICA DE CARDIOPATIA GERAL)
        Provedor/Plano JA VEM PREENCHIDO do agendamento — apenas verificar

  AB07: Provedor/Plano — ja preenchido; tratar popup de webservice elegibilidade
        (pode aparecer 2x — clicar Sim em ambos)

  AB11: Medico responsavel — digitar MEDICO + TAB (nao via LOV como no flow base)

  AB12: Lista de procedimentos — igual ao flow base (reutilizado)

Steps:
    AB01  Abrir modulo Ambulatorio (igual ao flow base)
    AB02  Informar Identificador (igual ao flow base)
    AB03  Pesquisar — tela de resultado mostra grade de Agendamentos
    AB04  Aba Enderecos (igual ao flow base)
    AB05  Clicar ADMITIR na tela de agendamentos
    AB06  Unidade Funcional — CLINICA DE CARDIOPATIA GERAL
    AB07  Provedor/Plano — ja preenchido; fechar popups elegibilidade
    AB08  Declarante / Especialidade (igual ao flow base)
    AB09  Obs (igual ao flow base)
    AB10  Origem do Paciente (igual ao flow base)
    AB11  Medico responsavel — MEDICO + TAB (sem LOV)
    AB12  Lista de Procedimentos (igual ao flow base)
    AB13  Voltar para tela de admissao (igual ao flow base)
    AB14  Validar Nr Admissao via OCR (igual ao flow base)
    AB15  Sair (igual ao flow base)
"""

import time

import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult
from src.flows.si3.admissao_ambulatorio_flow import AdmissaoAmbulatorioFlow


class AdmissaoComAgendamentoFlow(AdmissaoAmbulatorioFlow):
    """
    Especialização do AdmissaoAmbulatorioFlow para pacientes com agendamento.

    Herda 90% do flow base — sobrescreve apenas os steps que diferem:
      _step_pesquisar        → AB03: detecta tela de agendamentos
      _step_admitir_paciente → AB05: clica ADMITIR na tela de agendamentos
      _step_unidade_funcional → AB06: unidade diferente + provedor ja preenchido
      _step_provedor_plano   → AB07: ja preenchido + fechar popups elegibilidade
      _step_medico_responsavel → AB11: MEDICO + TAB sem LOV
    """

    FLOW_NAME = "AdmissaoComAgendamentoFlow"
    _TPL      = "templates/si3/admissao_ambulatorio"
    _TPL_AG   = "templates/si3/agendamento"

    # ----------------------------------------------------------------
    # AB03 — Pesquisar — tela com grade de Agendamentos
    # ----------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None) -> StepResult:
        """
        Diferente do flow base: quando o paciente tem agendamento,
        a tela de resultado mostra uma grade de Agendamentos com
        Nome, Horario, Descricao do Procedimento e Complemento.
        O botao que aparece e ADMITIR (nao btn_admitir_paciente do flow base).
        """
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            time.sleep(1.5)

            # Com agendamento: aparece tela de agendamentos com botao ADMITIR
            tpl_admitir = f"{self._TPL}/btn_admitir_com_agendamento.png"
            import os
            if os.path.exists(tpl_admitir):
                apareceu = ctx.runner.wait_template(tpl_admitir, timeout=10, threshold=0.7)
            else:
                # Template ainda nao capturado — usar btn_admitir_paciente como fallback
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
        return self._step("AB03", "pesquisar paciente com agendamento", fn, observer,
                          confirm_template=f"{self._TPL}/btn_admitir_paciente.png")

    # ----------------------------------------------------------------
    # AB05 — Admitir Paciente na tela de agendamentos
    # ----------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None) -> StepResult:
        """
        AB05 — Seleciona primeiro agendamento da grade e clica em Admitir.
        Estratégia: sempre escolhe a primeira linha (de cima para baixo) — determinístico.
        Depois trata popup de webservice de elegibilidade (pode aparecer até 2x).
        """
        def fn():
            coords = ctx.config.coordenadas

    # 1. Clicar na primeira linha da grade para selecionar o agendamento 
            x, y = self._coord(coords, "primeira_linha_grade_ag")
            pyautogui.click(x, y)
            time.sleep(0.5)

     # 2. Clicar em Admitir (canto inferior direito da tela de agendamentos)
            x, y = self._coord(coords, "btn_admitir_ag")
            pyautogui.click(x, y)
            time.sleep(2.0)           



            # Tenta template especifico; fallback para btn_admitir_paciente
            import os
            tpl_admitir = f"{self._TPL}/btn_admitir_com_agendamento.png"
            if os.path.exists(tpl_admitir):
                ctx.runner.safe_click(tpl_admitir, threshold=0.7)
            else:
                ctx.runner.safe_click(
                    f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7
                )
            time.sleep(2.0)

            # 3. Fechar popup webservice elegibilidade — pode aparecer até 2x
            for tentativa in range(2):
                tpl_sim = f"{self._TPL}/btn_ok_convenio.png"
                if ctx.runner.wait_template(tpl_sim, timeout=3.0, threshold=0.7):
                   ctx.runner.safe_click(tpl_sim, threshold=0.7)
                   time.sleep(1.0) 
                   print(f"[AB05] Popup elegibilidade fechado (tentativa {tentativa + 1})")
                else:
                     break

            # 4. Confirm: formulário de admissão abriu
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
        return self._step("AB05", "selecionar agendamento e clicar Admitir", fn, observer,
                          confirm_template=f"{self._TPL}/campo_unidade_funcional.png")     

           

    # ----------------------------------------------------------------
    # AB06 — Unidade Funcional — CLINICA DE CARDIOPATIA GERAL
    # ----------------------------------------------------------------

    def _step_unidade_funcional(self, ctx, dados: dict, observer=None) -> StepResult:
        """
        Diferenca: unidade funcional e CLINICA DE CARDIOPATIA GERAL (UNCAR).
        O Provedor/Plano ja vem preenchido do agendamento — nao limpar.
        """
        def fn():
            unidade = self._dado(dados, "unidade_funcional", "AB06")

            ctx.runner.click_near(
                f"{self._TPL}/campo_unidade_funcional.png",
                offset_x=200, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(unidade)
            pyautogui.press("tab"); time.sleep(0.5)  # Sigla carrega automaticamente
            pyautogui.press("tab"); time.sleep(0.5)  # avanca para Provedor

            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/campo_provedor.png", timeout=8, threshold=0.65
            )
            if not apareceu:
                raise AssertionError(
                    "AB06: campo_provedor nao visivel apos Unidade Funcional. "
                    "Unidade pode nao ter sido aceita."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB06_unidade_ag.png")
        return self._step("AB06", "preencher Unidade Funcional", fn, observer,
                          confirm_template=f"{self._TPL}/campo_provedor.png")

    # ----------------------------------------------------------------
    # AB07 — Provedor/Plano — ja preenchido + fechar popups elegibilidade
    # ----------------------------------------------------------------

    def _step_provedor_plano(self, ctx, dados: dict, observer=None) -> StepResult:
        """
        Com agendamento, Provedor e Plano ja vem preenchidos automaticamente.
        Apenas fechar popups de elegibilidade que possam aparecer.
        Nao sobrescreve os campos — apenas trata os popups.
        """
        def fn():
            # Provedor/Plano ja preenchido do agendamento — nao alterar
            # Apenas fechar popups de elegibilidade se aparecerem
            for tentativa in range(2):
                tpl_sim = f"{self._TPL}/btn_ok_convenio.png"
                if ctx.runner.wait_template(tpl_sim, timeout=2.0, threshold=0.7):
                    ctx.runner.safe_click(tpl_sim, threshold=0.7)
                    time.sleep(0.8)
                    print(f"[AB07] Popup elegibilidade fechado (tentativa {tentativa+1})")
                else:
                    break

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB07_provedor_ag.png")
        return self._step("AB07", "verificar Provedor/Plano preenchidos do agendamento",
                          fn, observer)

    # ----------------------------------------------------------------
    # AB11 — Medico Responsavel — MEDICO + TAB (sem LOV)
    # ----------------------------------------------------------------

    def _step_medico_responsavel(self, ctx, coords, observer=None) -> StepResult:
        """
        Diferenca: nao usa LOV. Digita MEDICO + TAB e o Forms carrega
        automaticamente MEDICO (SOH PARA USO DA INFORMATICA).
        """
        def fn():
            nome_medico = self._dado(ctx.config.DADOS, "nome_medico_ab", "AB11")

            x, y = self._coord(coords, "campo_nome_medico_ab")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(nome_medico)
            pyautogui.press("tab"); time.sleep(1.5)  # aguarda Forms carregar

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB11_medico_ag.png")
        return self._step("AB11", "preencher Medico Responsavel por digitacao", fn, observer)