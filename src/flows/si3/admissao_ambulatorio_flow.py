# src/flows/si3/admissao_ambulatorio_flow.py
"""
AdmissaoAmbulatorioFlow — SI3 Oracle Forms
v0.5.15: AB02 corrigido — restaurado clique+digitacao perdidos em edicao anterior.

Mudancas vs v0.5.10:
  - herda BaseFlow — _step(), _dado(), _coord(), _tpl_existe(), _focar_si3() removidos
  - dados.get("chave", "DEFAULT") em campos obrigatorios substituidos por _dado()
  - campos opcionais (obs, declarante, especialidade) mantidos com .get() + default
  - ctx=ctx adicionado em todos os _step() calls
  - description propagada automaticamente pelo BaseFlow._step()

v0.5.15 — AB02 (12/06/2026):
  - Contrato paciente_id seguindo o mesmo padrao de si3_internacao:
    ${SI3_PACIENTE_ID:-} preenchido no .env -> usa ctx.config.PACIENTE_ID
    (permite rodar admissao standalone sem depender de estado_jornada.json)
    vazio -> le _ler_estado("paciente_id") (fluxo normal da jornada completa)
  - BUGFIX: uma edicao anterior havia removido o bloco de clique+type_text
    do AB02, fazendo o step "passar" em ~70ms sem digitar nada no campo
    Identificador — falso positivo corrigido restaurando o bloco.
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
    # Regiao do Nr Admissao agora vem do config (regioes_ocr.nr_admissao_amb),
    # nao mais hardcoded — padrao do projeto: coordenadas no YAML.

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
            lambda: self._step_salvar(ctx, observer),
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
        """
        Navegacao via 'Localizar no Menu' (padrao AI01 validado).
        Localizar no Menu -> digita AMBULATORIO -> Pesquisar -> Nao -> double_click.
        Confirma chegada pela tela de admissao (titulo_ambulatorio.png, unico).
        """
        def fn():
            termo = self._dado(ctx.config.DADOS, "termo_menu_amb", "AB01")
            self._focar_si3()

            coords = ctx.config.coordenadas
            x, y = self._coord(coords, "campo_localizar_menu")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo); time.sleep(0.3)

            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar_menu.png", threshold=0.7)
            time.sleep(1.0)

            # Popup "Continuar Busca?" -> Nao (condicional)
            tpl_nao = f"{self._TPL}/btn_nao_popup.png"
            if self._tpl_existe(tpl_nao) and ctx.runner.is_visible(tpl_nao, threshold=0.80):
                ctx.runner.safe_click(tpl_nao, threshold=0.80)
                time.sleep(0.5)

            # Double click no item Ambulatorio na arvore
            ctx.runner.double_click(f"{self._TPL}/menu_ambulatorio.png", threshold=0.7)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB01_ambulatorio.png")
        return self._step("AB01", "abrir modulo Ambulatorio via Localizar no Menu",
                          fn, observer,
                          confirm_template=f"{self._TPL}/titulo_ambulatorio.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB02 — Informar Identificador
    # ----------------------------------------------------------------

    def _step_informar_identificador(self, ctx, coords, observer=None):
        """
        Contrato paciente_id (v0.5.15, alinhado com si3_internacao):
          ${SI3_PACIENTE_ID:-} preenchido no .env -> usa ctx.config.PACIENTE_ID
            (permite rodar a admissao standalone, sem depender de
             estado_jornada.json — util para `vtae run --test
             admissao_com_agendamento_jornada` isolado)
          vazio -> le _ler_estado("paciente_id") (fluxo normal da jornada
            completa: cadastro -> agendamento -> admissao)
        """
        def fn():
            paciente_id_env = ctx.config.PACIENTE_ID
            if paciente_id_env:
                paciente_id = paciente_id_env
                print(f"[AB02] paciente_id via .env (SI3_PACIENTE_ID): {paciente_id}")
            else:
                paciente_id = _ler_estado("paciente_id")
                print(f"[AB02] paciente_id via estado_jornada.json: {paciente_id}")

            x, y = self._coord(coords, "campo_identificador_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(paciente_id); time.sleep(0.3)
            print(f"[AB02] Identificador digitado: {paciente_id}")
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
    # AB04 — Aba Enderecos: campo Tipo = RUA (sempre)
    # ----------------------------------------------------------------

    def _step_tipo_endereco(self, ctx, coords, observer=None):
        """
        Campo Tipo (RUA/AVENIDA) e obrigatorio para SUS — se ficar vazio, o SI3
        bloqueia a admissao com o popup da Portaria 257 no AB07.

        Estrategia: SEMPRE apagar o conteudo com BACKSPACE e digitar RUA. Este
        campo Tipo (com LOV anexado) NAO responde a selecao de texto — nem Ctrl+A
        nem Shift+Home limpam (geram concatenacao "RUARUA" e abrem o LOV de Tipos
        de Logradouro por valor invalido). O gesto correto, confirmado manualmente,
        e: clicar -> backspace ate limpar -> digitar -> Tab.
        Mandamos 20 backspaces (cobre qualquer Tipo; backspace em campo vazio nao
        faz nada, entao serve para os dois cenarios):
          - preenchido: backspace apaga o valor antigo, digita RUA
          - vazio: backspace nao tem efeito, digita RUA
        Sem OCR (que lia errado em campo de ~14px e gerava falso "ja preenchido").

        DIVIDA TECNICA CONSCIENTE (10/06/2026): preencher RUA fixo remove a
        variabilidade do Tipo. Para exercitar cenarios reais (viela/avenida/
        vazio->popup), promover para `tipo_endereco` no config.yaml ou um bloco
        `cenarios_endereco`. Deteccao robusta de campo virа com o YOLO (Fase 6).
        """
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/aba_enderecos.png", threshold=0.7)
            time.sleep(0.5)
            self._focar_si3()
            x, y = self._coord(coords, "campo_tipo_endereco_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.press("backspace", presses=20, interval=0.02)  # apaga conteudo
            ctx.runner.type_text("RUA")
            pyautogui.press("tab"); time.sleep(0.5)
            pyautogui.hotkey("ctrl", "s"); time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB04_tipo_endereco.png")
        return self._step("AB04", "aba Enderecos — campo Tipo = RUA",
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
                duplo_clique_item="item_profissional_proc",
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

                # Profissional: digita o nome direto no campo + Tab (sem popup LOV).
                # Padrao Oracle Forms validado manualmente: complemento -> Tab leva ao
                # campo Profissional -> digita o nome completo -> Tab confirma.
                # `profissional` vem do config (proc.get("profissional")), entao aceita
                # qualquer profissional, nao so MEDICO.
                # NOTA: este unico Tab assume que o cursor saiu do complemento. Se o
                # procedimento NAO tiver complemento, revalidar quantos Tabs sao precisos.
                pyautogui.press("tab"); time.sleep(0.5)
                ctx.runner.type_text(profissional); time.sleep(0.3)
                pyautogui.press("tab"); time.sleep(0.5)

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
    # AB14 — Salvar admissao (F10)
    # ----------------------------------------------------------------

    def _step_salvar(self, ctx, observer=None):
        """
        Persiste a admissao na tela principal (apos Voltar) via F10.
        Sem este passo o Oracle Forms nao grava e o Nr. Admissao nao e gerado
        — era a causa do AB14 (agora AB15) ler ''.
        F10 confirmado manualmente (10/06/2026). Botao Salvar (disquete) e
        alternativa mais rapida — trocar por template no futuro se a latencia
        do F10 incomodar.
        """
        def fn():
            self._focar_si3()
            pyautogui.hotkey("f10"); time.sleep(3.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB14_salvar.png")
        return self._step("AB14", "salvar admissao (F10)", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB15 — Validar Nr Admissao via OCR
    # ----------------------------------------------------------------

    def _step_validar_admissao(self, ctx, observer=None):
        """
        Validacao final: OCR le o Nr Admissao na tela (apos salvar no AB14).
        Regiao vem do config (regioes_ocr.nr_admissao_amb) — nunca hardcoded,
        para o time calibrar sem tocar no codigo (padrao do projeto, igual AI19).
        Modo bootstrap: se a regiao estiver zerada {0,0,0,0}, avisa e passa.
        Calibrada: falha se nao encontrar numero.
        Regiao validada 11/06/2026: {x1:35,y1:131,x2:136,y2:155} le '00234746'.
        """
        _ocr = [None]
        def fn():
            regiao = ctx.config.regioes_ocr.get("nr_admissao_amb")
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB15_validacao.png")

            if not regiao or not (regiao["x1"] or regiao["y1"]
                                  or regiao["x2"] or regiao["y2"]):
                print("[AB15] AVISO: regioes_ocr.nr_admissao_amb nao calibrado — "
                      "validacao pulada (modo bootstrap). Calibrar apos 1a execucao.")
                return screenshot_path

            regiao_tupla = (regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"])
            OcrHelper.salvar_debug(
                screenshot_path, regiao_tupla,
                f"{ctx.evidence_dir}AB15_ocr_debug.png"
            )
            texto   = OcrHelper.ler_regiao(screenshot_path, regiao_tupla)
            numeros = re.findall(r"\d+", texto)
            if not numeros:
                raise AssertionError(
                    f"Nr Admissao nao encontrado — admissao pode ter falhado.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Veja AB15_ocr_debug.png e ajuste regioes_ocr.nr_admissao_amb."
                )
            nr_admissao = numeros[0]
            _ocr[0] = nr_admissao
            print(f"[AB15] Nr Admissao Ambulatorio: {nr_admissao}")
            _salvar_estado("nr_admissao_amb", nr_admissao)
            return screenshot_path
        step = self._step("AB15", "validar Nr Admissao via OCR",
                          fn, observer, validated=True, ctx=ctx)
        if step.success and _ocr[0]:
            step.ocr_lido = _ocr[0]
        return step

    # ----------------------------------------------------------------
    # AB16 — Sair
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB16_sair.png")
        return self._step("AB16", "sair para Menu Principal", fn, observer, ctx=ctx)