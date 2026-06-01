# src/flows/si3/admissao_ambulatorio_flow.py
"""
AdmissaoAmbulatorioFlow — SI3 Oracle Forms
v0.5.10: migrado para BaseFlow.

Mudancas vs v0.5.7c:
  - herda BaseFlow — _step(), _dado(), _coord(), _tpl_existe(), _focar_si3() removidos
  - dados.get("chave", "DEFAULT") em campos obrigatorios substituidos por _dado()
  - campos opcionais (obs, declarante, especialidade) mantidos com .get() + default
  - ctx=ctx adicionado em todos os _step() calls
  - description propagada automaticamente pelo BaseFlow._step()
"""

import re
import time

import pyautogui

from src.core.context import FlowContext
from src.core.estado_jornada import ler as _ler_estado, salvar as _salvar_estado
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.vision.ocr import OcrHelper


class AdmissaoAmbulatorioFlow(BaseFlow):

    FLOW_NAME = "AdmissaoAmbulatorioFlow"
    _TPL = "templates/si3/admissao_ambulatorio"
    _REGIAO_NR_ADMISSAO = (10, 40, 200, 70)

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas
        dados  = self._resolver_cenario_provedor(dados)

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
            lambda: self._step_medico_responsavel(ctx, coords, observer),
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
    # Helpers privados especificos deste flow
    # ----------------------------------------------------------------

    def _resolver_cenario_provedor(self, dados: dict) -> dict:
        """Resolve o cenario ativo de provedor — sobrescreve provedor/plano/carteirinha."""
        cenario_key = dados.get("cenario_provedor", "sus")
        cenarios    = dados.get("cenarios_provedor", {})
        cenario     = cenarios.get(cenario_key, {})
        if not cenario:
            print(f"[WARNING] cenario_provedor '{cenario_key}' nao encontrado — usando dados base")
        merged = {**dados, **cenario}
        print(f"[AB] cenario_provedor ativo: '{cenario_key}' — provedor: {merged.get('provedor')}")
        return merged

    def _fechar_popups_convenio(self, ctx) -> bool:
        """Fecha popups de elegibilidade de convenio. Retorna True se encontrou."""
        encontrou = False
        for _ in range(3):
            try:
                achou = ctx.runner.wait_template(
                    f"{self._TPL}/btn_ok_convenio.png", timeout=2.0, threshold=0.75,
                )
                if achou:
                    ctx.runner.safe_click(f"{self._TPL}/btn_ok_convenio.png", threshold=0.75)
                    time.sleep(0.5); encontrou = True
                else:
                    break
            except Exception:
                break
        return encontrou

    def _selecionar_via_lov(self, ctx, coords,
                             btn_lov: str, campo_localizar: str, termo: str,
                             btn_localizar: str, btn_ok: str,
                             duplo_clique_item: str = None) -> None:
        """Fluxo padrao de LOV."""
        x, y = self._coord(coords, btn_lov)
        pyautogui.click(x, y); time.sleep(1.5)
        x, y = self._coord(coords, campo_localizar)
        pyautogui.click(x, y); time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(termo); time.sleep(0.3)
        x, y = self._coord(coords, btn_localizar)
        pyautogui.click(x, y); time.sleep(1.5)
        if duplo_clique_item:
            x, y = self._coord(coords, duplo_clique_item)
            pyautogui.doubleClick(x, y); time.sleep(1.0)
        else:
            x, y = self._coord(coords, btn_ok)
            pyautogui.click(x, y); time.sleep(0.5)

    # ----------------------------------------------------------------
    # AB01 — Abrir modulo Ambulatorio
    # ----------------------------------------------------------------

    def _step_abrir_ambulatorio(self, ctx, observer=None):
        def fn():
            ctx.runner.wait_template(
                f"{self._TPL}/menu_ambulatorio.png", timeout=5, threshold=0.7
            )
            ctx.runner.double_click(f"{self._TPL}/menu_ambulatorio.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/btn_pesquisar.png", timeout=15.0, threshold=0.7
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB01_ambulatorio.png")
        return self._step("AB01", "duplo clique em Ambulatorio",
                          fn, observer,
                          confirm_template=f"{self._TPL}/btn_pesquisar.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB02 — Informar Identificador
    # ----------------------------------------------------------------

    def _step_informar_identificador(self, ctx, coords, observer=None):
        def fn():
            paciente_id = _ler_estado("paciente_id")
            x, y = self._coord(coords, "campo_identificador_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(paciente_id); time.sleep(0.3)
            print(f"[AB02] Identificador: {paciente_id}")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB02_identificador.png")
        return self._step("AB02", "informar identificador do paciente", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB03 — Pesquisar
    # ----------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/btn_admitir_paciente.png", timeout=10, threshold=0.7
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB03_pesquisa.png")
        return self._step("AB03", "pesquisar paciente",
                          fn, observer,
                          confirm_template=f"{self._TPL}/btn_admitir_paciente.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB04 — Aba Enderecos: campo Tipo = RUA se vazio
    # ----------------------------------------------------------------

    def _step_tipo_endereco(self, ctx, coords, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/aba_enderecos.png", threshold=0.7)
            time.sleep(0.5)
            screenshot_check = ctx.runner.screenshot(f"{ctx.evidence_dir}AB04_check.png")
            x, y = self._coord(coords, "campo_tipo_endereco_amb")
            regiao_tipo = (x - 10, y - 10, x + 120, y + 12)
            tipo_lido = OcrHelper.ler_regiao(screenshot_check, regiao_tipo).strip()
            print(f"[AB04] Campo Tipo lido: '{tipo_lido}'")
            if tipo_lido:
                print("[AB04] Campo Tipo ja preenchido — pulando")
            else:
                print("[AB04] Campo Tipo vazio — digitando RUA")
                pyautogui.click(x, y); time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text("RUA")
                pyautogui.press("tab"); time.sleep(0.5)
                pyautogui.hotkey("ctrl", "s"); time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB04_tipo_endereco.png")
        return self._step("AB04", "aba Enderecos — campo Tipo = RUA se vazio",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB05 — Admitir Paciente
    # ----------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB05_admitir.png")
        return self._step("AB05", "clicar em Admitir Paciente", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB06 — Unidade Funcional
    # ----------------------------------------------------------------

    def _step_unidade_funcional(self, ctx, dados: dict, observer=None):
        def fn():
            valor = self._dado(dados, "unidade_funcional", "AB06")
            ctx.runner.click_near(
                f"{self._TPL}/campo_unidade_funcional.png",
                offset_x=200, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(valor)
            pyautogui.press("tab"); time.sleep(0.5)
            pyautogui.press("tab"); time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB06_unidade.png")
        return self._step("AB06", "preencher Unidade Funcional", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB07 — Provedor / Plano
    # ----------------------------------------------------------------

    def _step_provedor_plano(self, ctx, dados: dict, observer=None):
        def fn():
            provedor = self._dado(dados, "provedor", "AB07")
            plano    = self._dado(dados, "plano", "AB07")
            ctx.runner.click_near(
                f"{self._TPL}/campo_provedor.png", offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.5)
            ctx.runner.click_near(
                f"{self._TPL}/campo_plano.png", offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.5)
            if self._fechar_popups_convenio(ctx):
                print("[AB07] Popup de convenio fechado")
            if provedor not in ("SUS", "PARTICULAR", "INCOR SIS"):
                carteirinha = dados.get("numero_carteirinha", "")
                validade    = dados.get("validade_carteirinha", "")
                if carteirinha:
                    ctx.runner.click_near(
                        f"{self._TPL}/campo_numero_carteirinha.png",
                        offset_x=100, offset_y=0, threshold=0.65
                    )
                    pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(carteirinha)
                    pyautogui.press("tab"); time.sleep(0.3)
                    if self._fechar_popups_convenio(ctx):
                        print("[AB07] Popup pos-carteirinha fechado")
                if validade:
                    ctx.runner.click_near(
                        f"{self._TPL}/campo_validade_carteirinha.png",
                        offset_x=100, offset_y=0, threshold=0.65
                    )
                    pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(validade)
                    pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB07_provedor.png")
        return self._step("AB07", "preencher Provedor e Plano", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB08 — Declarante / Especialidade
    # ----------------------------------------------------------------

    def _step_declarante_especialidade(self, ctx, dados: dict, coords, observer=None):
        def fn():
            # declarante e especialidade sao opcionais — fallback definido no config.yaml
            declarante    = dados.get("declarante",    "TESTE AUTOMATIZADO")
            especialidade = dados.get("especialidade", "CAR - CARDIO GERAL")
            x, y = self._coord(coords, "campo_declarante")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(declarante)
            pyautogui.press("tab"); time.sleep(0.3)
            x, y = self._coord(coords, "campo_especialidade")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(especialidade)
            pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB08_declarante.png")
        return self._step("AB08", "preencher Declarante e Especialidade",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB09 — Obs
    # ----------------------------------------------------------------

    def _step_obs(self, ctx, dados: dict, coords, observer=None):
        def fn():
            valor = dados.get("obs", "ADMISSAO REALIZADA COM FERRAMENTA DE AUTOMACAO DE TESTES")
            x, y = self._coord(coords, "campo_obs_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(valor); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB09_obs.png")
        return self._step("AB09", "preencher campo Obs", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB10 — Origem do Paciente
    # ----------------------------------------------------------------

    def _step_origem_paciente(self, ctx, dados: dict, coords, observer=None):
        def fn():
            tipo = self._dado(dados, "origem_tipo", "AB10")
            x, y = self._coord(coords, "campo_origem_tipo")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(tipo)
            pyautogui.press("tab"); time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB10_origem.png")
        return self._step("AB10", "preencher Origem do Paciente", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB11 — Medico Responsavel via LOV
    # ----------------------------------------------------------------

    def _step_medico_responsavel(self, ctx, coords, observer=None):
        def fn():
            self._selecionar_via_lov(
                ctx, coords,
                btn_lov="btn_lov_medico",
                campo_localizar="campo_localizar_medico",
                termo="%medico",
                btn_localizar="btn_localizar_medico",
                btn_ok="btn_localizar_medico",
                duplo_clique_item="item_medico_informatica",
            )
            time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB11_medico.png")
        return self._step("AB11", "selecionar Medico Responsavel via LOV",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB12 — Lista de Procedimentos
    # ----------------------------------------------------------------

    def _step_lista_procedimentos(self, ctx, dados: dict, coords, observer=None):
        def fn():
            procedimentos = self._dado(dados, "procedimentos", "AB12")
            if not procedimentos:
                raise AssertionError(
                    "Nenhum procedimento configurado em dados.procedimentos no config.yaml."
                )
            ctx.runner.safe_click(f"{self._TPL}/btn_lista_procedimentos.png", threshold=0.7)
            time.sleep(1.5)

            for i, proc in enumerate(procedimentos):
                codigo         = proc.get("codigo", "")
                complemento    = proc.get("complemento", "")
                area_executora = proc.get("area_executora", "")
                profissional   = proc.get("profissional", "MEDICO")
                print(f"[AB12] Procedimento {i+1}: {codigo} / {complemento}")

                if i > 0:
                    x, y = self._coord(coords, "proxima_linha_proc")
                    pyautogui.click(x, y + (i * 18)); time.sleep(0.3)

                self._selecionar_via_lov(
                    ctx, coords,
                    btn_lov="btn_lov_codigo_proc",
                    campo_localizar="campo_localizar_proc",
                    termo=codigo,
                    btn_localizar="btn_localizar_proc",
                    btn_ok="btn_ok_proc",
                )
                time.sleep(0.5)

                area_para_digitar = area_executora.strip()
                if area_para_digitar:
                    x, y = self._coord(coords, "campo_localizar_area")
                    pyautogui.click(x, y); time.sleep(0.3)
                    pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(area_para_digitar)
                    x, y = self._coord(coords, "btn_localizar_area")
                    pyautogui.click(x, y); time.sleep(1.0)
                x, y = self._coord(coords, "btn_ok_area_executora")
                pyautogui.click(x, y); time.sleep(0.5)
                pyautogui.press("tab"); time.sleep(0.3)
                pyautogui.press("tab"); time.sleep(0.3)

                if complemento:
                    self._selecionar_via_lov(
                        ctx, coords,
                        btn_lov="btn_lov_complemento",
                        campo_localizar="campo_localizar_complemento",
                        termo=complemento,
                        btn_localizar="btn_localizar_complemento",
                        btn_ok="btn_ok_complemento",
                    )
                    time.sleep(0.5)

                self._selecionar_via_lov(
                    ctx, coords,
                    btn_lov="btn_lov_profissional_proc",
                    campo_localizar="campo_localizar_profissional",
                    termo=f"%{profissional}",
                    btn_localizar="btn_localizar_profissional",
                    btn_ok="btn_ok_profissional",
                    duplo_clique_item="item_medico_informatica",
                )
                time.sleep(0.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB12_procedimentos.png")
        return self._step("AB12", "preencher Lista de Procedimentos", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB13 — Voltar
    # ----------------------------------------------------------------

    def _step_voltar(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_voltar.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB13_voltar.png")
        return self._step("AB13", "clicar em Voltar", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB14 — Validar Nr Admissao via OCR
    # ----------------------------------------------------------------

    def _step_validar_admissao(self, ctx, observer=None):
        def fn():
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB14_validacao.png")
            OcrHelper.salvar_debug(
                screenshot_path, self._REGIAO_NR_ADMISSAO,
                f"{ctx.evidence_dir}AB14_ocr_debug.png"
            )
            texto   = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_NR_ADMISSAO)
            numeros = re.findall(r"\d+", texto)
            if not numeros:
                raise AssertionError(
                    f"Nr Admissao nao encontrado — admissao pode ter falhado.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Veja AB14_ocr_debug.png e ajuste _REGIAO_NR_ADMISSAO."
                )
            nr_admissao = numeros[0]
            print(f"[AB14] Nr Admissao Ambulatorio: {nr_admissao}")
            _salvar_estado("nr_admissao_amb", nr_admissao)
            return screenshot_path
        return self._step("AB14", "validar Nr Admissao via OCR",
                          fn, observer, validated=True, ctx=ctx)

    # ----------------------------------------------------------------
    # AB15 — Sair
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB15_sair.png")
        return self._step("AB15", "sair para Menu Principal", fn, observer, ctx=ctx)