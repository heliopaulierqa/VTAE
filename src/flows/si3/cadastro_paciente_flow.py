# src/flows/si3/cadastro_paciente_flow.py
"""
CadastroPacienteFlow - Cadastro completo de paciente no SI3 (Oracle Forms).

Presupoe que o login ja foi executado via LoginFlow.

Steps:
    CP01  Menu cadastro paciente
    CP02  Pesquisar nome
    CP03  Clicar Novo
    CP04  Nome Social
    CP05  Data Nascimento + Hora
    CP06  Sexo
    CP07  Nacionalidade (2 popups)
    CP08  Mae
    CP09  Pai
    CP10  Conjuge
    CP11  Responsavel
    CP12  Cor/Etnia
    CP13  Religiao
    CP14  Estado Civil
    CP15  Ocupacao
    CP16  Situacao Familiar
    CP17  Tipo de Deficiencia
    CP18  Escolaridade + Frequenta Escola
    CP19  CPF + RG + CNS  (aba Documentos)
    CP20  Aba Enderecos
    CP21  Aba Comunicacao (celular + e-mail)
    CP22  Gerar Matricula + Salvar + OCR + salvar estado_jornada.json
    CP23  Sair

Coordenadas:
    TODAS as coordenadas ficam no config.yaml em coordenadas:
    Use python scripts/posicao_mouse.py para capturar cada campo
    que nao pode ser localizado por template OpenCV.

Templates em templates/si3/cadastro_paciente/:
    menu_cadastro_paciente.png
    campo_nome_pesquisa.png
    btn_pesquisar.png
    btn_novo.png
    campo_nome_social.png
    btn_ok.png
    btn_ok_nacion.png
    btn_ok_erro.png   <- popup de erro Oracle Forms (FRM-* / HC-INCOR)
    aba_documentos.png
    aba_enderecos.png
    aba_comunicacao.png
    btn_salvar.png
    btn_gerar_matricula.png  (ou coordenada se nao tiver template)

Regra de popup Oracle Forms:
    - Popups ESPERADOS (CP21 salvar, CP22 gerar matricula): fechados silenciosamente
      pelo proprio step com _fechar_popups_oracle() — registra WARNING no log, nao falha
    - Popups INESPERADOS: o step lanca AssertionError manualmente quando necessario
    - O wrapper _step NAO verifica popup automaticamente — cada step e responsavel

Estado da jornada:
    - CP22 salva paciente_id via src.core.estado_jornada.salvar()
    - test_02+ leem via src.core.estado_jornada.ler("paciente_id")
    - Falha na leitura gera CausaFalha.ESTADO_AUSENTE
"""

import re
import time
from datetime import date, timedelta

import pyautogui
import pyperclip

from src.core.context import FlowContext
from src.core.estado_jornada import salvar as _salvar_estado_jornada  # helper centralizado
from src.core.result import CausaFalha, FlowResult, StepResult
from src.vision.ocr import OcrHelper


class CadastroPacienteFlow:
    """
    Fluxo completo de cadastro de paciente no SI3.
    Ao final salva a matricula gerada em evidence/estado_jornada.json
    para uso nos testes seguintes da jornada do ambulatorio.
    """

    FLOW_NAME = "CadastroPacienteFlow"
    _TPL = "templates/si3/cadastro_paciente"

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        steps = [
            lambda: self._step_menu(ctx, observer),
            lambda: self._step_pesquisar(ctx, dados, observer),
            lambda: self._step_novo(ctx, observer),
            lambda: self._step_nome_social(ctx, dados, observer),
            lambda: self._step_data_nascimento(ctx, dados, observer),
            lambda: self._step_sexo(ctx, dados, observer),
            lambda: self._step_nacionalidade(ctx, dados, observer),
            lambda: self._step_mae(ctx, dados, observer),
            lambda: self._step_pai(ctx, dados, observer),
            lambda: self._step_conjuge(ctx, dados, observer),
            lambda: self._step_responsavel(ctx, dados, observer),
            lambda: self._step_cor_etnia(ctx, dados, observer),
            lambda: self._step_religiao(ctx, dados, observer),
            lambda: self._step_estado_civil(ctx, dados, observer),
            lambda: self._step_ocupacao(ctx, dados, observer),
            lambda: self._step_situacao_familiar(ctx, dados, observer),
            lambda: self._step_tipo_deficiencia(ctx, dados, observer),
            lambda: self._step_escolaridade(ctx, dados, observer),
            lambda: self._step_documentos(ctx, dados, observer),
            lambda: self._step_enderecos(ctx, dados, observer),
            lambda: self._step_comunicacao(ctx, dados, observer),
            lambda: self._step_gerar_matricula_salvar(ctx, observer),
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

    def _coord(self, ctx, nome: str) -> tuple:
        """Le coordenada do config.yaml. Lanca KeyError se nao configurada."""
        coords = ctx.config.coordenadas
        if nome not in coords:
            raise KeyError(
                f"Coordenada '{nome}' nao encontrada em config.yaml -> coordenadas:"
                f"\nConfigure com posicao_mouse.py e adicione ao config.yaml."
            )
        c = coords[nome]
        return (c["x"], c["y"])

    def _clicar_coord(self, ctx, nome: str) -> None:
        x, y = self._coord(ctx, nome)
        pyautogui.click(x, y)
        time.sleep(0.3)

    def _preencher_coord(self, ctx, nome: str, valor: str) -> None:
        """Clique direto + limpar + digitar. Para campos pequenos."""
        x, y = self._coord(ctx, nome)
        pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor)
        time.sleep(0.2)

    def _preencher_template(self, ctx, template: str, nome_coord: str,
                             valor: str, offset_x: int = 150) -> None:
        """click_near com fallback para coordenada. Para campos grandes e unicos."""
        try:
            ctx.runner.click_near(f"{self._TPL}/{template}", offset_x=offset_x,
                                  offset_y=0, threshold=0.65)
        except Exception:
            x, y = self._coord(ctx, nome_coord)
            pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor)
        time.sleep(0.2)

    def _clicar_aba(self, ctx, template: str, nome_coord: str) -> None:
        """Clica em aba por template com fallback para coordenada."""
        try:
            ctx.runner.safe_click(f"{self._TPL}/{template}", threshold=0.7)
        except Exception:
            x, y = self._coord(ctx, nome_coord)
            pyautogui.click(x, y)
        time.sleep(0.5)

    def _fechar_popups_oracle(self, ctx) -> bool:
        """
        Fecha popups de erro Oracle Forms (FRM-* / HC-INCOR) se aparecerem.
        Retorna True se encontrou e fechou pelo menos um popup.
        Retorna False se nao encontrou nenhum popup.
        Uso: steps que sabem que podem receber popup fecham silenciosamente.
        """
        encontrou_popup = False
        for _ in range(6):
            try:
                encontrou = ctx.runner.wait_template(
                    f"{self._TPL}/btn_ok_erro.png",
                    timeout=2.0, threshold=0.75,
                )
                if encontrou:
                    ctx.runner.safe_click(f"{self._TPL}/btn_ok_erro.png", threshold=0.75)
                    time.sleep(0.5)
                    encontrou_popup = True
                else:
                    break
            except Exception:
                break
        return encontrou_popup

    def _step(self, step_id: str, descricao: str, fn, observer) -> StepResult:
        """
        Wrapper padrao para todos os steps.
        Nao verifica popup automaticamente — cada step e responsavel
        por tratar popups esperados dentro do proprio fn().
        Classifica CausaFalha automaticamente pelo tipo de excecao.
        """
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
            if "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            else:
                causa = CausaFalha.SISTEMA
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
                causa_falha=causa,
            )
        except Exception as e:
            causa = CausaFalha.DESCONHECIDA
            msg = str(e).lower()
            if "template" in msg or "not found" in msg:
                causa = CausaFalha.TEMPLATE_NAO_ENCONTRADO
            elif "timeout" in msg:
                causa = CausaFalha.TIMEOUT
            elif "ocr" in msg or "matricula" in msg or "regiao" in msg:
                causa = CausaFalha.OCR_LEITURA
            elif "coordenada" in msg or isinstance(e, KeyError):
                causa = CausaFalha.COORDENADA
            elif "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
                causa_falha=causa,
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ----------------------------------------------------------------
    # Steps CP01-CP03: Navegacao
    # ----------------------------------------------------------------

    def _step_menu(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.double_click(f"{self._TPL}/menu_cadastro_paciente.png", threshold=0.7)
            ctx.runner.wait_template(f"{self._TPL}/campo_nome_pesquisa.png",
                                     timeout=15.0, threshold=0.7)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP01_menu.png")
        return self._step("CP01", "duplo clique em Cadastro de Pacientes", fn, observer)

    def _step_pesquisar(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_template(ctx, "campo_nome_pesquisa.png",
                                     "campo_nome_pesquisa", dados["nome"])
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP02_pesquisa.png")
        return self._step("CP02", f"pesquisar: {dados['nome']}", fn, observer)

    def _step_novo(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_novo.png", threshold=0.7)
            ctx.runner.wait_template(f"{self._TPL}/campo_nome_social.png",
                                     timeout=15.0, threshold=0.7)
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP03_novo.png")
        return self._step("CP03", "clicar em Novo", fn, observer)

    # ----------------------------------------------------------------
    # Steps CP04-CP18: Formulario principal
    # ----------------------------------------------------------------

    def _step_nome_social(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            valor = dados.get("nome_social", "") or dados.get("nome", "")
            self._preencher_template(ctx, "campo_nome_social.png",
                                     "campo_nome_social", valor)
            pyautogui.press("tab")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP04_social.png")
        return self._step("CP04", "Nome Social", fn, observer)

    def _step_data_nascimento(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_data_nascimento", dados["data_nascimento"])
            self._preencher_coord(ctx, "campo_hora", dados.get("hora", "00:00"))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP05_data.png")
        return self._step("CP05", "Data Nascimento + Hora", fn, observer)

    def _step_sexo(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_sexo", dados.get("sexo", "M"))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP06_sexo.png")
        return self._step("CP06", f"Sexo: {dados.get('sexo', 'M')}", fn, observer)

    def _step_nacionalidade(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_nacionalidade",
                                  dados.get("nacionalidade", "BRASILEIRA"))
            pyautogui.press("tab")
            time.sleep(2.0)
            encontrou = ctx.runner.wait_template(f"{self._TPL}/btn_ok.png",
                                                  timeout=8.0, threshold=0.6)
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(1.5)
            ctx.runner.type_text("SP")
            pyautogui.press("tab")
            time.sleep(0.5)
            ctx.runner.type_text("SAO PAULO")
            time.sleep(0.3)
            encontrou2 = ctx.runner.wait_template(f"{self._TPL}/btn_ok_nacion.png",
                                                   timeout=8.0, threshold=0.6)
            if encontrou2:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok_nacion.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP07_nacion.png")
        return self._step("CP07", "Nacionalidade", fn, observer)

    def _step_mae(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_mae", dados["mae"])
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP08_mae.png")
        return self._step("CP08", "Mae", fn, observer)

    def _step_pai(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_pai", dados["pai"])
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP09_pai.png")
        return self._step("CP09", "Pai", fn, observer)

    def _step_conjuge(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_conjuge", dados.get("conjuge", ""))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP10_conjuge.png")
        return self._step("CP10", "Conjuge", fn, observer)

    def _step_responsavel(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_responsavel", dados.get("responsavel", ""))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP11_responsavel.png")
        return self._step("CP11", "Responsavel", fn, observer)

    def _step_cor_etnia(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_cor_etnia", dados.get("cor_etnia", "PARDA"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP12_cor.png")
        return self._step("CP12", "Cor/Etnia", fn, observer)

    def _step_religiao(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_religiao", dados.get("religiao", "CATOLICA"))
            pyautogui.press("tab")
            time.sleep(1.5)
            encontrou = ctx.runner.wait_template(
                f"{self._TPL}/btn_ok.png", timeout=8.0, threshold=0.6,
            )
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP13_religiao.png")
        return self._step("CP13", "Religiao", fn, observer)

    def _step_estado_civil(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_estado_civil",
                                  dados.get("estado_civil", "SOLTEIRO"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP14_civil.png")
        return self._step("CP14", "Estado Civil", fn, observer)

    def _step_ocupacao(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_ocupacao",
                                  dados.get("ocupacao", "ESTUDANTE"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP15_ocupacao.png")
        return self._step("CP15", "Ocupacao", fn, observer)

    def _step_situacao_familiar(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_situacao_familiar",
                                  dados.get("situacao_familiar", "SEM INFORMACAO"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP16_sit_familiar.png")
        return self._step("CP16", "Situacao Familiar", fn, observer)

    def _step_tipo_deficiencia(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_tipo_deficiencia",
                                  dados.get("tipo_deficiencia", ""))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP17_defic.png")
        return self._step("CP17", "Tipo de Deficiencia", fn, observer)

    def _step_escolaridade(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_escolaridade",
                                  dados.get("escolaridade", "SUPERIOR INCOMPLETO"))
            pyautogui.press("tab")
            time.sleep(1.5)
            encontrou = ctx.runner.wait_template(
                f"{self._TPL}/btn_ok.png", timeout=8.0, threshold=0.6,
            )
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP18_escolar.png")
        return self._step("CP18", "Escolaridade", fn, observer)

    # ----------------------------------------------------------------
    # Steps CP19-CP21: Abas
    # ----------------------------------------------------------------

    def _step_documentos(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            time.sleep(0.5)

            pyautogui.click(262, 424); time.sleep(0.3)
            pyperclip.copy(dados.get("rg", "44643579X"))
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(637, 427); time.sleep(0.3)
            pyperclip.copy("SSP")
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(780, 426); time.sleep(0.3)
            pyperclip.copy("SP")
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(868, 424); time.sleep(0.3)
            # sempre 30 dias atras — nunca anterior ao nascimento, nunca futuro
            data_emissao = (date.today() - timedelta(days=30)).strftime("%d/%m/%Y")
            pyperclip.copy(data_emissao)
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            cpf = dados["cpf"].replace(".", "").replace("-", "")
            pyautogui.click(262, 450); time.sleep(0.3)
            pyperclip.copy(cpf)
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(257, 476); time.sleep(0.3)
            pyperclip.copy("726337961670004")
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP19_docs.png")
        return self._step("CP19", "Aba Documentos: RG + CPF + CNS", fn, observer)

    def _step_enderecos(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._clicar_aba(ctx, "aba_enderecos.png", "aba_enderecos")
            time.sleep(0.5)
            end = dados.get("endereco", {})

            self._preencher_coord(ctx, "campo_cep", end.get("cep", "01310100"))
            pyautogui.press("tab"); time.sleep(2.5)

            screenshot_cep = ctx.runner.screenshot(f"{ctx.evidence_dir}CP20_cep_check.png")
            logradouro_lido = OcrHelper.ler_regiao(screenshot_cep, (214, 424, 528, 444)).strip()
            print(f"[CP20] Logradouro apos CEP: '{logradouro_lido}'")

            if logradouro_lido:
                print("[CP20] Auto-preenchimento OK - preenchendo apenas Numero e Complemento")
                self._preencher_coord(ctx, "campo_numero_endereco",      end.get("numero",      "44"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_complemento_endereco", end.get("complemento", "CADASTRO DE TESTE"))
                pyautogui.press("tab"); time.sleep(0.3)
            else:
                print("[CP20] Auto-preenchimento falhou - preenchendo todos os campos")
                self._preencher_coord(ctx, "campo_tipo_endereco",        end.get("tipo",        "AVENIDA"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_logradouro",           end.get("logradouro",  "DR. ENEAS CARVALHO DE AGUIAR"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_numero_endereco",      end.get("numero",      "44"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_complemento_endereco", end.get("complemento", "CADASTRO DE TESTE"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_pais_endereco",        end.get("pais",        "BRASIL"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_uf_endereco",          end.get("uf",          "SP"))
                pyautogui.press("tab"); time.sleep(0.3)
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_municipio_endereco",   end.get("municipio",   "SAO PAULO"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_bairro",               end.get("bairro",      "BELA VISTA"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_referencia_endereco",  end.get("referencia",  "PROXIMO AO CENTRO"))
                pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP20_endereco.png")
        return self._step("CP20", "Aba Enderecos", fn, observer)

    def _step_comunicacao(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._clicar_aba(ctx, "aba_comunicacao.png", "aba_comunicacao")
            time.sleep(0.5)

            com = dados.get("comunicacao", {})

            # Linha 1 - celular
            self._preencher_coord(ctx, "campo_comunicacao_prioridade_l1", "1")
            pyautogui.press("tab"); time.sleep(0.2)
            pyautogui.click(*self._coord(ctx, "campo_comunicacao_lov_l1")); time.sleep(1.5)
            pyautogui.click(82, 142); time.sleep(0.3)
            ctx.runner.type_text("CELULAR")
            pyautogui.click(113, 354); time.sleep(1.0)
            pyautogui.click(221, 355); time.sleep(0.5)
            self._preencher_coord(ctx, "campo_comunicacao_numero_l1",
                                  com.get("celular", dados.get("celular", "")))
            pyautogui.press("tab"); time.sleep(0.3)

            # Linha 2 - e-mail
            self._preencher_coord(ctx, "campo_comunicacao_prioridade_l2", "2")
            pyautogui.press("tab"); time.sleep(0.2)
            pyautogui.click(*self._coord(ctx, "campo_comunicacao_lov_l2")); time.sleep(1.5)
            pyautogui.click(82, 142); time.sleep(0.3)
            ctx.runner.type_text("E-MAIL")
            pyautogui.click(113, 354); time.sleep(1.0)
            pyautogui.click(221, 355); time.sleep(0.5)
            self._preencher_coord(ctx, "campo_comunicacao_numero_l2", "teste@teste.com")
            pyautogui.press("tab"); time.sleep(0.3)

            # Salvar antes de gerar matricula
            pyautogui.click(58, 66); time.sleep(2.5)

            # Popup apos salvar e comportamento esperado no SI3 — fechar silenciosamente
            if self._fechar_popups_oracle(ctx):
                print("[CP21] Popup Oracle Forms fechado apos salvar — comportamento esperado")

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP21_comunicacao.png")
        return self._step("CP21", "Aba Comunicacao: celular + e-mail", fn, observer)

    # ----------------------------------------------------------------
    # Step CP22: Gerar Matricula + Salvar + OCR + estado_jornada.json
    # ----------------------------------------------------------------

    def _step_gerar_matricula_salvar(self, ctx, observer=None) -> StepResult:
        def fn():
            # 1. Clicar em Gerar Matricula
            try:
                ctx.runner.safe_click(f"{self._TPL}/btn_gerar_matricula.png", threshold=0.7)
            except Exception:
                self._clicar_coord(ctx, "btn_gerar_matricula")
            time.sleep(2.0)

            # 2. Salvar
            pyautogui.click(58, 66); time.sleep(3.0)

            # Popup apos salvar e comportamento esperado — fechar silenciosamente
            if self._fechar_popups_oracle(ctx):
                print("[CP22] Popup Oracle Forms fechado apos salvar — comportamento esperado")

            # 3. Screenshot para OCR
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}CP22_matricula.png")

            # 4. Le regiao OCR do config.yaml
            r = ctx.config.regioes_ocr["matricula"]
            regiao_tuple = (r["x1"], r["y1"], r["x2"], r["y2"])

            # 5. OCR
            OcrHelper.salvar_debug(screenshot_path, regiao_tuple,
                                   f"{ctx.evidence_dir}CP22_ocr_debug.png")
            texto = OcrHelper.ler_regiao(screenshot_path, regiao_tuple)
            numeros = re.findall(r"\d+", texto)
            if not numeros:
                raise AssertionError(
                    f"Matricula nao gerada ou OCR nao leu.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Regiao usada: {regiao_tuple}\n"
                    f"Veja CP22_ocr_debug.png e ajuste regioes_ocr.matricula no config.yaml."
                )
            matricula = numeros[0]
            print(f"[CP22] Matricula gerada: {matricula}")

            # 6. Salva via helper centralizado — disponivel para test_02+
            _salvar_estado_jornada("paciente_id", matricula)

            return screenshot_path
        return self._step("CP22", "Gerar Matricula + Salvar + OCR", fn, observer)

    # ----------------------------------------------------------------
    # Step CP23: Sair
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None) -> StepResult:
        def fn():
            self._clicar_coord(ctx, "btn_sair_1")
            time.sleep(1.5)
            self._clicar_coord(ctx, "btn_sair_2")
            time.sleep(1.5)
            self._clicar_coord(ctx, "btn_sair_menu")
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP23_menu.png")
        return self._step("CP23", "sair para o Menu Principal", fn, observer)