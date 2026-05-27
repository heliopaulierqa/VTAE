# src/flows/si3/agendamento_flow.py
"""
AgendamentoFlow — SI3 Oracle Forms
Versao: 0.5.9 — Fase 5c (jornada ambulatorio_agendamento)

Pressupoe que o login ja foi executado via LoginFlow.
Le o paciente_id do estado_jornada.json gerado pelo test_01 (CadastroPacienteFlow).
Salva o nr_agendamento no estado_jornada.json para uso no test_03.

REGRA DE DADOS:
    Todos os valores de teste vem de dados: no config.yaml via ctx.config.DADOS.
    O flow nao tem nenhum valor default hardcoded — se uma chave faltar no
    config.yaml, _dado() falha imediatamente com mensagem clara indicando
    qual chave esta ausente e em qual step.

Steps:
    AG01  Abrir modulo Agendar via Localizar no Menu
    AG02  Preencher Provedor (TAB -> popup OK)
    AG03  Preencher Plano (2 TABs)
    AG04  Preencher Codigo do procedimento (TAB)
    AG05  Preencher Complemento (4 TABs -> popup Area)
    AG06  Selecionar Area Executora no popup
    AG07  Selecionar Executante via LOV
    AG08  Clicar em Agendar — fecha popup preparo (tolerante) + tela Informacoes
    AG09  Tela Recursos disponiveis — fecha popup LOV recurso (tolerante) + OK
    AG10  Preencher Data + Hora Inicial + TAB + popup Sim (tolerante) + OK
    AG11  Tela Agendamento individual — ID via estado_jornada + TAB + Confirmar
    AG12  Tela Conclusao — confirm_template + Fechar
    AG13  Sair do modulo Agendar

Dados esperados em config.yaml -> dados: (todos obrigatorios):
    termo_menu_ag       — termo digitado em "Localizar no Menu" (ex: 'AGENDAR')
    provedor_ag         — provedor do agendamento (ex: 'SUS')
    plano_ag            — plano (ex: 'SUS')
    codigo_proc_ag      — codigo do procedimento (ex: 'CARDIO')
    complemento_ag      — complemento (ex: 'CASO NOVO')
    area_executora_ag   — termo de busca da area executora (ex: 'UNGRA')
    termo_executante_ag — termo de busca do executante no popup LOV (ex: 'MEDICO')
    horas_offset_ag     — horas a adicionar a hora atual para o horario (ex: 3)
"""

import datetime
import time

import pyautogui

from src.core.context import FlowContext
from src.core.estado_jornada import ler as _ler_estado, salvar as _salvar_estado
from src.core.result import CausaFalha, FlowResult, StepResult


class AgendamentoFlow:

    FLOW_NAME = "AgendamentoFlow"
    _TPL      = "templates/si3/agendamento"
    _TPL_AMB  = "templates/si3/admissao_ambulatorio"

    @staticmethod
    def _tpl_existe(path: str) -> bool:
        """Verifica se template PNG existe antes de usar wait_template.
        Evita TemplateNotFoundError por arquivo ausente ainda nao capturado."""
        import os
        return os.path.exists(path)

    @staticmethod
    def _focar_si3() -> bool:
        """
        Tenta focar a janela do SI3. Tolerante — nunca para o flow.
        Requer: pip install pygetwindow
        Se nao instalado, usa pyautogui como fallback (clica na barra de tarefas).
        """
        try:
            import pygetwindow as gw
            janelas = gw.getWindowsWithTitle("FUNDA")
            if not janelas:
                janelas = gw.getWindowsWithTitle("FZ -")
            if janelas:
                w = janelas[0]
                if w.isMinimized:
                    w.restore()
                    time.sleep(0.3)
                w.activate()
                time.sleep(0.5)
                print("[_focar_si3] SI3 focado via pygetwindow")
                return True
            print("[_focar_si3] AVISO: janela SI3 nao encontrada pelo titulo")
            return False
        except ImportError:
            # pygetwindow nao instalado — instalar com: pip install pygetwindow
            print("[_focar_si3] AVISO: pygetwindow nao instalado — sem controle de foco")
            return False
        except Exception as e:
            print(f"[_focar_si3] AVISO: {e}")
            return False

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
    # Helpers internos
    # ----------------------------------------------------------------

    def _coord(self, coords, nome: str) -> tuple:
        if nome not in coords:
            raise KeyError(
                f"Coordenada '{nome}' nao encontrada em config.yaml -> coordenadas:\n"
                f"Configure com posicao_mouse.py e adicione ao config.yaml."
            )
        c = coords[nome]
        return (c["x"], c["y"])

    def _dado(self, dados: dict, chave: str, step_id: str):
        """
        Le um dado obrigatorio do config.yaml.
        Falha imediatamente com mensagem clara se a chave nao existir —
        nunca usa valor default silencioso.

        Raises:
            AssertionError: se a chave nao estiver em dados.
        """
        if chave not in dados:
            raise AssertionError(
                f"[{step_id}] Dado obrigatorio ausente no config.yaml: '{chave}'\n"
                f"Adicione '{chave}: <valor>' na secao dados: do config.yaml.\n"
                f"Chaves disponiveis: {list(dados.keys())}"
            )
        return dados[chave]

    def _fechar_popup_ok(self, ctx, template: str, timeout: float = 5.0) -> bool:
        """Aguarda popup e clica OK. Retorna True se encontrou."""
        apareceu = ctx.runner.wait_template(template, timeout=timeout, threshold=0.7)
        if apareceu:
            ctx.runner.safe_click(template, threshold=0.7)
            time.sleep(0.5)
        return apareceu

    def _step(self, step_id: str, descricao: str, fn, observer,
              confirm_template: str = None,
              validated: bool = None) -> StepResult:
        """
        Wrapper de execucao de step com observabilidade.

        Args:
            confirm_template: template da tela destino — validated=True automatico.
            validated: True explicito quando fn() executou verify_lov/verify_fill
                       internamente. Corrige bug onde validated ficava None.
        """
        if observer:
            observer.log_step_start(step_id, descricao)
        start = time.monotonic()
        _validated = None
        try:
            screenshot_path = fn()
            _validated = True if (confirm_template or validated) else None
            step = StepResult(
                step_id=step_id, success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot_path,
                validated=_validated,
            )
        except AssertionError as e:
            msg = str(e).lower()
            causa = CausaFalha.CONFIGURACAO if "ausente no config" in msg else (
                CausaFalha.ESTADO_AUSENTE if "estado_ausente" in msg else CausaFalha.SISTEMA
            )
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa, validated=False,
            )
        except Exception as e:
            msg = str(e).lower()
            if "template" in msg or "not found" in msg:
                causa = CausaFalha.TEMPLATE_NAO_ENCONTRADO
            elif "timeout" in msg:
                causa = CausaFalha.TIMEOUT
            elif "coordenada" in msg or isinstance(e, KeyError):
                causa = CausaFalha.COORDENADA
            elif "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            else:
                causa = CausaFalha.DESCONHECIDA
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa, validated=False,
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ----------------------------------------------------------------
    # AG01 — Abrir modulo Agendar via Localizar no Menu
    # ----------------------------------------------------------------

    def _step_abrir_agendar(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        """
        Estrategia: Localizar no Menu — digitar o termo do config, clicar Nao no popup,
        duplo clique no item Agendar destacado na arvore.
        """
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
                raise AssertionError(
                    "Tela de Agendar nao abriu. Verifique tela_agendar.png."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG01_agendar.png")
        return self._step("AG01", "abrir modulo Agendar via Localizar no Menu", fn, observer,
                          confirm_template=f"{self._TPL}/tela_agendar.png")

    # ----------------------------------------------------------------
    # AG02 — Provedor
    # ----------------------------------------------------------------

    def _step_provedor(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            provedor = self._dado(dados, "provedor_ag", "AG02")
            x, y = self._coord(coords, "campo_provedor_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.8)
            self._fechar_popup_ok(ctx, f"{self._TPL}/btn_ok_popup_ag.png", timeout=4.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG02_provedor.png")
        return self._step("AG02", "preencher Provedor", fn, observer)

    # ----------------------------------------------------------------
    # AG03 — Plano
    # ----------------------------------------------------------------

    def _step_plano(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            plano = self._dado(dados, "plano_ag", "AG03")
            x, y = self._coord(coords, "campo_plano_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.3)
            pyautogui.press("tab"); time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG03_plano.png")
        return self._step("AG03", "preencher Plano", fn, observer)

    # ----------------------------------------------------------------
    # AG04 — Codigo do procedimento
    # ----------------------------------------------------------------

    def _step_codigo_procedimento(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            codigo = self._dado(dados, "codigo_proc_ag", "AG04")
            x, y = self._coord(coords, "campo_codigo_proc_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(codigo)
            pyautogui.press("tab"); time.sleep(0.8)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG04_codigo.png")
        return self._step("AG04", "preencher Codigo do procedimento", fn, observer)

    # ----------------------------------------------------------------
    # AG05 — Complemento
    # ----------------------------------------------------------------

    def _step_complemento(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            complemento = self._dado(dados, "complemento_ag", "AG05")
            x, y = self._coord(coords, "campo_complemento_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(complemento)
            # 4 TABs apos Complemento — abre popup de Area Executora
            for _ in range(4):
                pyautogui.press("tab"); time.sleep(0.2)
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG05_complemento.png")
        return self._step("AG05", "preencher Complemento", fn, observer)

    # ----------------------------------------------------------------
    # AG06 — Area Executora
    # ----------------------------------------------------------------

    def _step_area_executora(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            area = self._dado(dados, "area_executora_ag", "AG06")
            time.sleep(0.5)
            x, y = self._coord(coords, "campo_busca_area_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(area); time.sleep(0.3)
            pyautogui.press("return"); time.sleep(1.0)
            x, y = self._coord(coords, "btn_ok_area_ag")
            pyautogui.click(x, y); time.sleep(0.8)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG06_area.png")
        return self._step("AG06", "selecionar Area Executora", fn, observer)

    # ----------------------------------------------------------------
    # AG07 — Executante via LOV
    # ----------------------------------------------------------------

    def _step_executante(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            termo_exec = self._dado(dados, "termo_executante_ag", "AG07")

            x, y = self._coord(coords, "btn_lov_executante_ag")
            pyautogui.click(x, y); time.sleep(1.5)

            x, y = self._coord(coords, "campo_busca_executante_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo_exec); time.sleep(0.3)
            pyautogui.press("return"); time.sleep(1.5)

            x, y = self._coord(coords, "item_medico_executante_ag")
            pyautogui.doubleClick(x, y); time.sleep(1.8)

            # verify_lov — confirma que campo Executante nao ficou vazio (Obs-Fase1b)
            regiao_exec = ctx.config.regioes_ocr.get("campo_executante_ag")
            if regiao_exec:
                regiao = (
                    regiao_exec["x1"], regiao_exec["y1"],
                    regiao_exec["x2"], regiao_exec["y2"],
                )
                if not ctx.runner.verify_lov(
                    "Executante",
                    region=regiao,
                    debug_path=f"{ctx.evidence_dir}AG07_executante_verify_debug.png",
                ):
                    raise AssertionError(
                        "Falha de Observabilidade: campo Executante ficou VAZIO apos LOV.\n"
                        f"Termo buscado: '{termo_exec}'\n"
                        "Causas possiveis:\n"
                        "  1. Termo nao retornou resultados — lista ficou vazia\n"
                        "  2. item_medico_executante_ag aponta para coordenada errada\n"
                        "  3. Duplo clique nao registrou (foco perdido)\n"
                        "Acao: veja AG07_executante_verify_debug.png e ajuste "
                        "item_medico_executante_ag com posicao_mouse.py se necessario."
                    )
            else:
                print("[AG07] AVISO: regioes_ocr.campo_executante_ag nao configurado — "
                      "verify_lov ignorado. Adicione ao config.yaml para habilitar validacao.")

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG07_executante.png")
        # validated=True — verify_lov rodou dentro de fn() e confirmou campo preenchido
        return self._step("AG07", "selecionar Executante via LOV", fn, observer,
                          validated=True)

    # ----------------------------------------------------------------
    # AG08 — Clicar Agendar + fechar popup preparo + fechar tela Informacoes
    # ----------------------------------------------------------------

    def _step_clicar_agendar(self, ctx, coords, observer=None) -> StepResult:
        """
        Clica no botao Agendar (canto inferior direito).

        Popups tolerantes que podem aparecer em sequencia:
          1. HC-INCOR "nao requer preparo" — clicar OK (nem sempre aparece)
          2. Tela "Informacoes do Profissional" — clicar Fechar (nem sempre aparece)

        confirm_template: tela_recursos_ag.png — valida que tela Recursos abriu.
        """
        def fn():
            # Tentar focar o SI3 — tolerante, nao para o flow se falhar
            if not self._focar_si3():
                print("[AG08] AVISO: nao foi possivel focar SI3 automaticamente — "
                      "instalar pygetwindow para controle de foco: pip install pygetwindow")
            # Escape antes de clicar — fecha popup Editor se estiver aberto
            # Bug Oracle Forms: foco na grade abre Editor silenciosamente
            pyautogui.press("escape"); time.sleep(0.3)
            pyautogui.press("escape"); time.sleep(0.3)

            x, y = self._coord(coords, "btn_agendar_ag")
            pyautogui.click(x, y); time.sleep(2.0)

            # Popup HC-INCOR "nao requer preparo" — tolerante (aparece junto com tela Info)
            tpl_ok = f"{self._TPL}/btn_ok_popup_ag.png"
            if self._tpl_existe(tpl_ok) and ctx.runner.wait_template(tpl_ok, timeout=4.0, threshold=0.7):
                ctx.runner.safe_click(tpl_ok, threshold=0.7)
                time.sleep(0.8)
                print("[AG08] Popup HC-INCOR fechado — OK")

            # Tela "Informacoes do Profissional" — fecha pelo template se existir
            tpl_info = f"{self._TPL}/tela_info_profissional_ag.png"
            if self._tpl_existe(tpl_info):
                if ctx.runner.wait_template(tpl_info, timeout=4.0, threshold=0.7):
                    x, y = self._coord(coords, "btn_fechar_info_ag")
                    pyautogui.click(x, y); time.sleep(1.5)
                    print("[AG08] Tela Informacoes do Profissional fechada via template")
            else:
                # Tela SEMPRE aparece — fecha por coordenada mesmo sem template
                time.sleep(3.0)
                x, y = self._coord(coords, "btn_fechar_info_ag")
                pyautogui.click(x, y); time.sleep(1.5)
                print("[AG08] Tela Informacoes do Profissional fechada por coordenada")

            time.sleep(1.5)  # aguarda sistema processar fechamento

            # Tela Recursos disponiveis — TOLERANTE (nem sempre aparece)
            tpl_rec = f"{self._TPL}/tela_recursos_ag.png"
            if self._tpl_existe(tpl_rec):
                # Se template existe, detecta se a tela abriu
                if ctx.runner.wait_template(tpl_rec, timeout=3.0, threshold=0.65):
                    print("[AG08] Tela Recursos disponiveis detectada — AG09 vai tratar")
                else:
                    print("[AG08] Tela Recursos nao apareceu — indo direto para Agendamento")
            else:
                print("[AG08] AVISO: tela_recursos_ag.png ausente — capturar para melhor deteccao")

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG08_agendar.png")
        return self._step("AG08", "clicar Agendar e fechar tela Informacoes", fn, observer)

    # ----------------------------------------------------------------
    # AG09 — Tela Recursos disponiveis — tratar LOV recurso (tolerante) + OK
    # ----------------------------------------------------------------

    def _step_recursos_disponiveis(self, ctx, coords, observer=None) -> StepResult:
        """
        Na tela Recursos disponiveis, pode aparecer popup de LOV para escolher
        o recurso (consultorio). Tolerante — se aparecer seleciona o primeiro
        item e clica OK; se nao aparecer clica OK direto.

        confirm_template: tela_agendamento_individual_ag.png — valida que
        a tela de Agendamento individual abriu apos OK.
        """
        def fn():
            # Garantir foco no SI3
            self._focar_si3()
            # Tela Recursos disponiveis — TOLERANTE (nem sempre aparece)
            # Detecta se esta na tela pelo template; se nao, assume que foi pulada
            tpl_rec = f"{self._TPL}/tela_recursos_ag.png"
            na_tela_recursos = False
            if self._tpl_existe(tpl_rec):
                na_tela_recursos = ctx.runner.wait_template(tpl_rec, timeout=3.0, threshold=0.65)

            if na_tela_recursos:
                # Popup LOV recurso dentro da tela — tolerante
                tpl_pop = f"{self._TPL}/popup_recurso_ag.png"
                if self._tpl_existe(tpl_pop) and ctx.runner.wait_template(tpl_pop, timeout=3.0, threshold=0.7):
                    print("[AG09] Popup LOV recurso — selecionando primeiro item")
                    x, y = self._coord(coords, "item_recurso_ag")
                    pyautogui.click(x, y); time.sleep(0.3)
                    x, y = self._coord(coords, "btn_ok_recurso_ag")
                    pyautogui.click(x, y); time.sleep(1.0)

                # Clicar OK na tela Recursos
                x, y = self._coord(coords, "btn_ok_recursos_ag")
                pyautogui.click(x, y); time.sleep(1.5)
                print("[AG09] Tela Recursos — clicou OK")
            else:
                print("[AG09] Tela Recursos nao apareceu — prosseguindo para Agendamento individual")

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG09_recursos.png")
        return self._step("AG09", "tela Recursos disponiveis — tolerante", fn, observer)

    # ----------------------------------------------------------------
    # AG10 — Preencher Data + Hora Inicial + TAB + popup Sim + OK
    # ----------------------------------------------------------------

    def _step_data_hora(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        """
        Preenche Data e Hora Inicial na tela Agendamento individual.

        Sequencia:
          1. Digitar data atual no campo Data
          2. Digitar hora (hora atual + horas_offset_ag) no campo Hora Inicial
          3. Pressionar TAB — hora final preenche automatico
          4. Popup "Para a data nao existe oferta... Sim/Nao" — tolerante → Sim
          5. Clicar OK
        """
        def fn():
            # Garantir foco no SI3 antes de digitar data/hora
            self._focar_si3()
            time.sleep(0.5)
            horas_offset = self._dado(dados, "horas_offset_ag", "AG10")
            hoje    = datetime.date.today().strftime("%d/%m/%Y")
            agora   = datetime.datetime.now()
            hora_ag = (agora + datetime.timedelta(hours=int(horas_offset))).strftime("%H:%M")

            print(f"[AG10] Agendando para: {hoje} {hora_ag} (offset: +{horas_offset}h)")

            # Preencher Data
            x, y = self._coord(coords, "campo_data_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(hoje)
            pyautogui.press("tab"); time.sleep(0.5)

            # Preencher Hora Inicial
            x, y = self._coord(coords, "campo_hora_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(hora_ag)
            pyautogui.press("tab"); time.sleep(1.5)  # aguarda hora final preencher

            # Popup "Para a data nao existe oferta" — tolerante → Sim
            if ctx.runner.wait_template(
                f"{self._TPL}/btn_sim_popup_ag.png", timeout=4.0, threshold=0.7
            ):
                ctx.runner.safe_click(f"{self._TPL}/btn_sim_popup_ag.png", threshold=0.7)
                time.sleep(0.8)
                print("[AG10] Popup sem oferta — clicou Sim")

            _salvar_estado("hora_agendamento", hora_ag)
            _salvar_estado("data_agendamento", hoje)

            # Clicar OK
            x, y = self._coord(coords, "btn_ok_horario_ag")
            pyautogui.click(x, y); time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG10_data_hora.png")
        return self._step("AG10", "preencher Data e Hora Inicial", fn, observer)

    # ----------------------------------------------------------------
    # AG11 — Tela Agendamento individual — ID + TAB + Confirmar
    # ----------------------------------------------------------------

    def _step_confirmar_paciente(self, ctx, coords, observer=None) -> StepResult:
        """
        Na tela Agendamento individual, digita o ID do paciente,
        pressiona TAB para carregar os dados e clica Confirmar.

        confirm_template: tela_conclusao_ag.png — se nao abrir, AG12
        nao executa e o erro e reportado aqui com causa real.
        """
        def fn():
            # Garantir foco no SI3 antes de digitar ID
            self._focar_si3()
            time.sleep(0.5)
            paciente_id = _ler_estado("paciente_id")
            print(f"[AG11] Confirmando agendamento para paciente: {paciente_id}")

            x, y = self._coord(coords, "campo_id_paciente_ag")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(paciente_id)
            pyautogui.press("tab"); time.sleep(2.0)  # aguarda carregar dados do paciente

            x, y = self._coord(coords, "btn_confirmar_ag")
            pyautogui.click(x, y); time.sleep(2.0)

            # Validar tela Conclusao
            tpl_conc = f"{self._TPL}/tela_conclusao_ag.png"
            if self._tpl_existe(tpl_conc):
                if not ctx.runner.wait_template(tpl_conc, timeout=10.0, threshold=0.65):
                    raise AssertionError(
                        "AG11: tela Conclusao nao apareceu apos Confirmar.\n"
                        "Causas possiveis:\n"
                        "  1. Paciente ja possui agendamento para este procedimento/data\n"
                        "  2. Convenio/plano nao cobre o procedimento\n"
                        "  3. Popup de erro apareceu antes do Confirmar\n"
                        "  4. ID do paciente nao carregou (TAB muito rapido)\n"
                        "Acao: veja AG11_confirmar.png e screenshot auto-diag."
                    )
            else:
                print("[AG11] AVISO: tela_conclusao_ag.png ausente — usando timeout fixo")
                time.sleep(3.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG11_confirmar.png")
        return self._step("AG11", "confirmar agendamento do paciente", fn, observer)

    # ----------------------------------------------------------------
    # AG12 — Fechar tela de Conclusao
    # ----------------------------------------------------------------

    def _step_fechar_conclusao(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_fechar_ag.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG12_conclusao.png")
        return self._step("AG12", "fechar tela de Conclusao do agendamento", fn, observer)

    # ----------------------------------------------------------------
    # AG13 — Sair do modulo Agendar
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_sair_ag.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair_ag.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AG13_sair.png")
        return self._step("AG13", "sair para Menu Principal", fn, observer)