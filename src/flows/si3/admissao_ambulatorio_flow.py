# src/flows/si3/admissao_ambulatorio_flow.py
"""
AdmissaoAmbulatorioFlow — SI3 Oracle Forms
Versao: 0.5.7b — Fase 5c

Presupoe que o login ja foi executado via LoginFlow.
Le o paciente_id do estado_jornada.json gerado pelo test_01 (CadastroPacienteFlow).

Steps:
    AB01  Abrir modulo Ambulatorio (double_click)
    AB02  Informar Identificador (le paciente_id do estado_jornada.json)
    AB03  Pesquisar paciente
    AB04  Aba Enderecos — campo Tipo = RUA + salvar
    AB05  Admitir Paciente (btn_admitir_paciente)
    AB06  Unidade Funcional — 2 TABs apos digitar
    AB07  Provedor / Plano
    AB08  Declarante / Especialidade
    AB09  Obs
    AB10  Origem do Paciente — RESIDENCIA / RESIDENCIA
    AB11  Medico Responsavel — MEDICO + TAB (sleep 3s para carregar)
    AB12  Lista de Procedimentos — CARDIO / CASO NOVO / MEDICO
    AB13  Voltar para tela de admissao
    AB14  Validar Nr Admissao via OCR + salvar estado_jornada.json
    AB15  Sair

Coordenadas (todas em config.yaml -> coordenadas:):
    campo_identificador_amb:   { x, y }
    campo_tipo_endereco_amb:   { x, y }
    campo_declarante:          { x, y }
    campo_especialidade:       { x, y }
    campo_obs_amb:             { x, y }
    campo_origem_tipo:         { x, y }
    campo_medico_nome:         { x, y }
    campo_codigo_proc:         { x, y }
    campo_complemento_proc:    { x, y }
    campo_profissional_proc:   { x, y }

Templates em templates/si3/admissao_ambulatorio/:
    menu_ambulatorio.png
    aba_enderecos.png
    btn_pesquisar.png
    btn_admitir_paciente.png
    campo_unidade_funcional.png
    campo_provedor.png
    campo_plano.png
    btn_lista_procedimentos.png
    btn_voltar.png
    btn_sair.png
    btn_ok_convenio.png      <- popup de convenio (clicar Sim)
    btn_ok_complemento.png   <- botao OK da LOV de complemento

Popups esperados:
    - Popup de elegibilidade do convenio: clicar Sim — comportamento normal
    - Popup de plano inativo: nao deve ocorrer com dados corretos
"""

import re
import time

import pyautogui

from src.core.context import FlowContext
from src.core.estado_jornada import ler as _ler_estado, salvar as _salvar_estado
from src.core.result import CausaFalha, FlowResult, StepResult
from src.vision.ocr import OcrHelper


class AdmissaoAmbulatorioFlow:
    """
    Fluxo de Admissao Ambulatorial no SI3.
    Le o paciente_id do estado_jornada.json (gerado pelo CadastroPacienteFlow).
    Ao final salva o nr_admissao_amb no estado_jornada.json para test_03+.
    """

    FLOW_NAME = "AdmissaoAmbulatorioFlow"
    _TPL = "templates/si3/admissao_ambulatorio"

    # Regiao OCR do Nr Admissao — ajustar com Paint apos primeira execucao
    _REGIAO_NR_ADMISSAO = (10, 40, 200, 70)

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas
        dados = self._resolver_cenario_provedor(dados)  # resolve cenario ativo

        steps = [
            lambda: self._step_abrir_ambulatorio(ctx, observer),
            lambda: self._step_informar_identificador(ctx, coords, observer),
            lambda: self._step_pesquisar(ctx, observer),
            lambda: self._step_tipo_endereco(ctx, coords, observer),
            lambda: self._step_admitir_paciente(ctx, observer),
            lambda: self._step_unidade_funcional(ctx, dados, observer),
            lambda: self._step_provedor_plano(ctx, dados, observer),
            lambda: self._step_declarante_especialidade(ctx, dados, coords, observer),
            lambda: self._step_obs(ctx, dados, coords, observer),
            lambda: self._step_origem_paciente(ctx, dados, coords, observer),
            lambda: self._step_medico_responsavel(ctx, dados, coords, observer),
            lambda: self._step_lista_procedimentos(ctx, dados, coords, observer),
            lambda: self._step_voltar(ctx, observer),
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

    # ----------------------------------------------------------------
    # Helpers internos
    # ----------------------------------------------------------------

    def _coord(self, coords, nome: str) -> tuple:
        """Le coordenada do config.yaml. Lanca KeyError se nao configurada."""
        if nome not in coords:
            raise KeyError(
                f"Coordenada '{nome}' nao encontrada em config.yaml -> coordenadas:"
                f"\nConfigure com posicao_mouse.py e adicione ao config.yaml."
            )
        c = coords[nome]
        return (c["x"], c["y"])

    def _fechar_popups_convenio(self, ctx) -> bool:
        """
        Fecha popups de elegibilidade de convenio (clicar Sim).
        Comportamento esperado quando provedor for convenio.
        Retorna True se encontrou popup.
        """
        encontrou = False
        for _ in range(3):
            try:
                achou = ctx.runner.wait_template(
                    f"{self._TPL}/btn_ok_convenio.png",
                    timeout=2.0, threshold=0.75,
                )
                if achou:
                    ctx.runner.safe_click(f"{self._TPL}/btn_ok_convenio.png", threshold=0.75)
                    time.sleep(0.5)
                    encontrou = True
                else:
                    break
            except Exception:
                break
        return encontrou

    def _step(self, step_id: str, descricao: str, fn, observer) -> StepResult:
        """Wrapper padrao — classifica CausaFalha automaticamente."""
        if observer:
            observer.log_step_start(step_id, descricao)
        start = time.monotonic()
        try:
            screenshot_path = fn()
            step = StepResult(
                step_id=step_id, success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot_path,
            )
        except AssertionError as e:
            msg = str(e).lower()
            causa = CausaFalha.ESTADO_AUSENTE if "estado_ausente" in msg else CausaFalha.SISTEMA
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa,
            )
        except Exception as e:
            causa = CausaFalha.DESCONHECIDA
            msg = str(e).lower()
            if "template" in msg or "not found" in msg:
                causa = CausaFalha.TEMPLATE_NAO_ENCONTRADO
            elif "timeout" in msg:
                causa = CausaFalha.TIMEOUT
            elif "ocr" in msg or "admissao" in msg or "regiao" in msg:
                causa = CausaFalha.OCR_LEITURA
            elif "coordenada" in msg or isinstance(e, KeyError):
                causa = CausaFalha.COORDENADA
            elif "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa,
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ----------------------------------------------------------------
    # AB01 — Adicionar um novo convenio
    # ----------------------------------------------------------------
    def _resolver_cenario_provedor(self, dados: dict) -> dict:
        """
        Resolve o cenario ativo de provedor definido em config.yaml.
        O cenario sobrescreve os campos provedor/plano/carteirinha nos dados.
        """
        cenario_key = dados.get("cenario_provedor", "sus")
        cenarios = dados.get("cenarios_provedor", {})
        cenario = cenarios.get(cenario_key, {})
        if not cenario:
            print(f"[WARNING] cenario_provedor '{cenario_key}' nao encontrado — usando dados base")
        merged = {**dados, **cenario}
        print(f"[AB] cenario_provedor ativo: '{cenario_key}' — provedor: {merged.get('provedor')}")
        return merged

    # ----------------------------------------------------------------
    # AB01 — Abrir modulo Ambulatorio
    # ----------------------------------------------------------------

    def _step_abrir_ambulatorio(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.wait_template(
                f"{self._TPL}/menu_ambulatorio.png", timeout=5, threshold=0.7
            )
            ctx.runner.double_click(f"{self._TPL}/menu_ambulatorio.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/btn_pesquisar.png", timeout=15.0, threshold=0.7
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB01_ambulatorio.png")
        return self._step("AB01", "duplo clique em Ambulatorio", fn, observer)

    # ----------------------------------------------------------------
    # AB02 — Informar Identificador
    # ----------------------------------------------------------------

    def _step_informar_identificador(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            paciente_id = _ler_estado("paciente_id")
            x, y = self._coord(coords, "campo_identificador_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(paciente_id)
            time.sleep(0.3)
            print(f"[AB02] Identificador: {paciente_id}")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB02_identificador.png")
        return self._step("AB02", "informar identificador do paciente", fn, observer)

    # ----------------------------------------------------------------
    # AB03 — Pesquisar
    # ----------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/btn_admitir_paciente.png", timeout=10, threshold=0.7
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB03_pesquisa.png")
        return self._step("AB03", "pesquisar paciente", fn, observer)

    # ----------------------------------------------------------------
    # AB04 — Aba Enderecos: campo Tipo = RUA + salvar
    # ----------------------------------------------------------------

    def _step_tipo_endereco(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            # clica na aba Enderecos
            ctx.runner.safe_click(f"{self._TPL}/aba_enderecos.png", threshold=0.7)
            time.sleep(0.5)

            # campo Tipo — limpa e digita RUA
            x, y = self._coord(coords, "campo_tipo_endereco_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text("RUA")
            pyautogui.press("tab"); time.sleep(0.5)

            # salvar
            pyautogui.hotkey("ctrl", "s")
            time.sleep(1.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB04_tipo_endereco.png")
        return self._step("AB04", "aba Enderecos — campo Tipo = RUA + salvar", fn, observer)

    # ----------------------------------------------------------------
    # AB05 — Admitir Paciente
    # ----------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB05_admitir.png")
        return self._step("AB05", "clicar em Admitir Paciente", fn, observer)

    # ----------------------------------------------------------------
    # AB06 — Unidade Funcional (2 TABs apos digitar)
    # ----------------------------------------------------------------

    def _step_unidade_funcional(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            valor = dados.get("unidade_funcional", "SC MONITORIZACAO AMBULATORIAL")
            ctx.runner.click_near(
                f"{self._TPL}/campo_unidade_funcional.png",
                offset_x=200, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            pyautogui.press("tab"); time.sleep(0.5)  # Sigla preenche automaticamente
            pyautogui.press("tab"); time.sleep(0.5)  # avanca para Provedor
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB06_unidade.png")
        return self._step("AB06", "preencher Unidade Funcional", fn, observer)

    # ----------------------------------------------------------------
    # AB07 — Provedor / Plano
    # ----------------------------------------------------------------

    def _step_provedor_plano(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            provedor = dados.get("provedor", "SUS")
            plano    = dados.get("plano", "SUS")

            ctx.runner.click_near(
                f"{self._TPL}/campo_provedor.png",
                offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.5)

            ctx.runner.click_near(
                f"{self._TPL}/campo_plano.png",
                offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.5)

            # Popup de elegibilidade de convenio — comportamento esperado
            if self._fechar_popups_convenio(ctx):
                print("[AB07] Popup de convenio fechado — comportamento esperado")

            # Carteirinha e validade — apenas para convenio
            if provedor not in ("SUS", "PARTICULAR", "INCOR SIS"):
                carteirinha = dados.get("numero_carteirinha", "")
                validade    = dados.get("validade_carteirinha", "")
                if carteirinha:
                    ctx.runner.click_near(
                        f"{self._TPL}/campo_numero_carteirinha.png",
                        offset_x=100, offset_y=0, threshold=0.65
                    )
                    pyautogui.hotkey("ctrl", "a")
                    ctx.runner.type_text(carteirinha)
                    pyautogui.press("tab"); time.sleep(0.3)
                    if self._fechar_popups_convenio(ctx):
                        print("[AB07] Popup pos-carteirinha fechado")
                if validade:
                    ctx.runner.click_near(
                        f"{self._TPL}/campo_validade_carteirinha.png",
                        offset_x=100, offset_y=0, threshold=0.65
                    )
                    pyautogui.hotkey("ctrl", "a")
                    ctx.runner.type_text(validade)
                    pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB07_provedor.png")
        return self._step("AB07", "preencher Provedor / Plano", fn, observer)

    # ----------------------------------------------------------------
    # AB08 — Declarante / Especialidade
    # ----------------------------------------------------------------

    def _step_declarante_especialidade(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            declarante    = dados.get("declarante", "TESTE AUTOMATIZADO")
            especialidade = dados.get("especialidade", "CAR - CARDIO GERAL")

            x, y = self._coord(coords, "campo_declarante")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(declarante)
            pyautogui.press("tab"); time.sleep(0.3)

            x, y = self._coord(coords, "campo_especialidade")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(especialidade)
            pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB08_declarante.png")
        return self._step("AB08", "preencher Declarante / Especialidade", fn, observer)

    # ----------------------------------------------------------------
    # AB09 — Obs
    # ----------------------------------------------------------------

    def _step_obs(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            valor = dados.get("obs", "ADMISSAO REALIZADA COM FERRAMENTA DE AUTOMACAO DE TESTES")
            x, y = self._coord(coords, "campo_obs_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB09_obs.png")
        return self._step("AB09", "preencher campo Obs", fn, observer)

    # ----------------------------------------------------------------
    # AB10 — Origem do Paciente
    # ----------------------------------------------------------------

    def _step_origem_paciente(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            tipo = dados.get("origem_tipo", "RESIDENCIA")
            x, y = self._coord(coords, "campo_origem_tipo")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(tipo)
            pyautogui.press("tab")
            time.sleep(1.0)  # Entidade preenche automaticamente apos Tab
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB10_origem.png")
        return self._step("AB10", "preencher Origem do Paciente", fn, observer)

    # ----------------------------------------------------------------
    # AB11 — Medico Responsavel (sleep 3s para carregar CRM)
    # ----------------------------------------------------------------

    def _step_medico_responsavel(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            nome = dados.get("medico_nome", "MEDICO")
            x, y = self._coord(coords, "campo_medico_nome")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(nome)
            pyautogui.press("tab")
            time.sleep(3.0)  # aguarda CRM e numero carregarem completamente
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB11_medico.png")
        return self._step("AB11", "preencher Medico Responsavel", fn, observer)

    # ----------------------------------------------------------------
    # AB12 — Lista de Procedimentos
    # ----------------------------------------------------------------

    def _step_lista_procedimentos(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            codigo       = dados.get("codigo_proc", "CARDIO")
            complemento  = dados.get("complemento_proc", "CASO NOVO")
            profissional = dados.get("profissional_proc", "MEDICO")

            # Abre tela de procedimentos
            ctx.runner.safe_click(f"{self._TPL}/btn_lista_procedimentos.png", threshold=0.7)
            time.sleep(1.5)

            # Codigo do procedimento
            x, y = self._coord(coords, "campo_codigo_proc")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(codigo)
            pyautogui.press("tab")
            time.sleep(0.5)  # Procedimento preenche automaticamente

            # Complemento — clica no campo (abre LOV)
            x, y = self._coord(coords, "campo_complemento_proc")
            pyautogui.click(x, y); time.sleep(1.0)  # aguarda LOV abrir
            ctx.runner.type_text(complemento)
            time.sleep(0.5)
            try:
                ctx.runner.safe_click(
                    f"{self._TPL}/btn_ok_complemento.png", threshold=0.7
                )
            except Exception:
                pyautogui.press("enter")
            time.sleep(0.5)

            # Profissional
            x, y = self._coord(coords, "campo_profissional_proc")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(profissional)
            pyautogui.press("tab")
            time.sleep(1.0)  # nome completo preenche automaticamente

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB12_procedimentos.png")
        return self._step("AB12", "preencher Lista de Procedimentos", fn, observer)

    # ----------------------------------------------------------------
    # AB13 — Voltar para tela de admissao
    # ----------------------------------------------------------------

    def _step_voltar(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_voltar.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB13_voltar.png")
        return self._step("AB13", "clicar em Voltar", fn, observer)

    # ----------------------------------------------------------------
    # AB14 — Validar Nr Admissao via OCR + salvar estado_jornada.json
    # ----------------------------------------------------------------

    def _step_validar_admissao(self, ctx, observer=None) -> StepResult:
        def fn():
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB14_validacao.png")

            OcrHelper.salvar_debug(
                screenshot_path, self._REGIAO_NR_ADMISSAO,
                f"{ctx.evidence_dir}AB14_ocr_debug.png"
            )
            texto = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_NR_ADMISSAO)
            numeros = re.findall(r"\d+", texto)

            if not numeros:
                raise AssertionError(
                    f"Nr Admissao nao encontrado — admissao pode ter falhado.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Regiao: {self._REGIAO_NR_ADMISSAO}\n"
                    f"Veja AB14_ocr_debug.png e ajuste _REGIAO_NR_ADMISSAO."
                )

            nr_admissao = numeros[0]
            print(f"[AB14] Nr Admissao Ambulatorio: {nr_admissao}")
            _salvar_estado("nr_admissao_amb", nr_admissao)

            return screenshot_path
        return self._step("AB14", "validar Nr Admissao via OCR", fn, observer)

    # ----------------------------------------------------------------
    # AB15 — Sair
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB15_sair.png")
        return self._step("AB15", "sair para Menu Principal", fn, observer)