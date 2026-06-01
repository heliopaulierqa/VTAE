# src/flows/si3/cadastro_paciente_flow.py
"""
CadastroPacienteFlow - Cadastro completo de paciente no SI3 (Oracle Forms).
v0.5.10: migrado para BaseFlow.

Mudancas vs versao anterior:
  - herda BaseFlow — _step(), _dado(), _coord(), _tpl_existe(), _focar_si3() removidos
  - _coord(ctx, nome) -> _coord(coords, nome): nao passa mais ctx, recebe coords direto
  - dados.get("chave", "DEFAULT") substituidos por _dado() nos campos obrigatorios
  - campos opcionais com fallback mantidos (ex: conjuge, responsavel — podem ser vazios)
  - description propagada para StepResult via BaseFlow._step()
  - ctx=ctx adicionado em todos os _step() calls

Nota sobre campos opcionais:
  Campos que legalmente podem ser vazios (conjuge, responsavel, tipo_deficiencia,
  obs, complemento de endereco) continuam usando .get() com default vazio "".
  Campos obrigatorios para o cadastro funcionem (nome, mae, cpf, data_nascimento)
  usam _dado() — falham imediatamente se ausentes do config.yaml.
"""

import re
import time
from datetime import date, timedelta

import pyautogui
import pyperclip

from src.core.context import FlowContext
from src.core.estado_jornada import salvar as _salvar_estado_jornada
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.vision.ocr import OcrHelper


class CadastroPacienteFlow(BaseFlow):
    """
    Fluxo completo de cadastro de paciente no SI3.
    Ao final salva a matricula gerada em evidence/estado_jornada.json
    para uso nos testes seguintes da jornada.
    """

    FLOW_NAME = "CadastroPacienteFlow"
    _TPL = "templates/si3/cadastro_paciente"

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        # coords passado como argumento para _coord() — padrao BaseFlow
        coords = ctx.config.coordenadas

        steps = [
            lambda: self._step_menu(ctx, observer),
            lambda: self._step_pesquisar(ctx, dados, coords, observer),
            lambda: self._step_novo(ctx, observer),
            lambda: self._step_nome_social(ctx, dados, coords, observer),
            lambda: self._step_data_nascimento(ctx, dados, coords, observer),
            lambda: self._step_sexo(ctx, dados, coords, observer),
            lambda: self._step_nacionalidade(ctx, dados, coords, observer),
            lambda: self._step_mae(ctx, dados, coords, observer),
            lambda: self._step_pai(ctx, dados, coords, observer),
            lambda: self._step_conjuge(ctx, dados, coords, observer),
            lambda: self._step_responsavel(ctx, dados, coords, observer),
            lambda: self._step_cor_etnia(ctx, dados, coords, observer),
            lambda: self._step_religiao(ctx, dados, coords, observer),
            lambda: self._step_estado_civil(ctx, dados, coords, observer),
            lambda: self._step_ocupacao(ctx, dados, coords, observer),
            lambda: self._step_situacao_familiar(ctx, dados, coords, observer),
            lambda: self._step_tipo_deficiencia(ctx, dados, coords, observer),
            lambda: self._step_escolaridade(ctx, dados, coords, observer),
            lambda: self._step_documentos(ctx, dados, coords, observer),
            lambda: self._step_enderecos(ctx, dados, coords, observer),
            lambda: self._step_comunicacao(ctx, dados, coords, observer),
            lambda: self._step_gerar_matricula_salvar(ctx, observer),
            lambda: self._step_sair(ctx, coords, observer),
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
    # Nao vao para BaseFlow pois dependem de ctx ou sao especificos do Oracle Forms
    # ----------------------------------------------------------------

    def _clicar_coord(self, ctx, coords, nome: str) -> None:
        """Clique direto em coordenada. Wrapper de conveniencia."""
        x, y = self._coord(coords, nome)
        pyautogui.click(x, y); time.sleep(0.3)

    def _preencher_coord(self, ctx, coords, nome: str, valor: str) -> None:
        """Clique + limpar + digitar. Para campos pequenos."""
        x, y = self._coord(coords, nome)
        pyautogui.click(x, y); time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor); time.sleep(0.2)

    def _preencher_template(self, ctx, coords, template: str,
                             nome_coord: str, valor: str, offset_x: int = 150) -> None:
        """click_near com fallback para coordenada. Para campos grandes e unicos."""
        try:
            ctx.runner.click_near(f"{self._TPL}/{template}",
                                  offset_x=offset_x, offset_y=0, threshold=0.65)
        except Exception:
            x, y = self._coord(coords, nome_coord)
            pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor); time.sleep(0.2)

    def _clicar_aba(self, ctx, coords, template: str, nome_coord: str) -> None:
        """Clica em aba por template com fallback para coordenada."""
        try:
            ctx.runner.safe_click(f"{self._TPL}/{template}", threshold=0.7)
        except Exception:
            x, y = self._coord(coords, nome_coord)
            pyautogui.click(x, y)
        time.sleep(0.5)

    def _fechar_popups_oracle(self, ctx) -> bool:
        """
        Fecha popups de erro Oracle Forms (FRM-* / HC-INCOR) se aparecerem.
        Retorna True se encontrou e fechou pelo menos um popup.
        """
        encontrou_popup = False
        for _ in range(6):
            try:
                encontrou = ctx.runner.wait_template(
                    f"{self._TPL}/btn_ok_erro.png", timeout=2.0, threshold=0.75,
                )
                if encontrou:
                    ctx.runner.safe_click(f"{self._TPL}/btn_ok_erro.png", threshold=0.75)
                    time.sleep(0.5); encontrou_popup = True
                else:
                    break
            except Exception:
                break
        return encontrou_popup

    # ----------------------------------------------------------------
    # CP01–CP03: Navegacao
    # ----------------------------------------------------------------

    def _step_menu(self, ctx, observer=None):
        def fn():
            ctx.runner.double_click(f"{self._TPL}/menu_cadastro_paciente.png", threshold=0.7)
            ctx.runner.wait_template(f"{self._TPL}/campo_nome_pesquisa.png",
                                     timeout=15.0, threshold=0.7)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP01_menu.png")
        return self._step("CP01", "duplo clique em Cadastro de Pacientes",
                          fn, observer,
                          confirm_template=f"{self._TPL}/campo_nome_pesquisa.png",
                          ctx=ctx)

    def _step_pesquisar(self, ctx, dados: dict, coords, observer=None):
        def fn():
            nome = self._dado(dados, "nome", "CP02")
            self._preencher_template(ctx, coords, "campo_nome_pesquisa.png",
                                     "campo_nome_pesquisa", nome)
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP02_pesquisa.png")
        return self._step("CP02", "pesquisar paciente pelo nome", fn, observer, ctx=ctx)

    def _step_novo(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_novo.png", threshold=0.7)
            ctx.runner.wait_template(f"{self._TPL}/campo_nome_social.png",
                                     timeout=15.0, threshold=0.7)
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP03_novo.png")
        return self._step("CP03", "clicar em Novo",
                          fn, observer,
                          confirm_template=f"{self._TPL}/campo_nome_social.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # CP04–CP18: Formulario principal
    # ----------------------------------------------------------------

    def _step_nome_social(self, ctx, dados: dict, coords, observer=None):
        def fn():
            # nome_social e opcional — fallback para nome
            valor = dados.get("nome_social", "") or self._dado(dados, "nome", "CP04")
            self._preencher_template(ctx, coords, "campo_nome_social.png",
                                     "campo_nome_social", valor)
            pyautogui.press("tab")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP04_social.png")
        return self._step("CP04", "preencher Nome Social", fn, observer, ctx=ctx)

    def _step_data_nascimento(self, ctx, dados: dict, coords, observer=None):
        def fn():
            data  = self._dado(dados, "data_nascimento", "CP05")
            hora  = dados.get("hora", "00:00")   # hora e opcional
            self._preencher_coord(ctx, coords, "campo_data_nascimento", data)
            self._preencher_coord(ctx, coords, "campo_hora", hora)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP05_data.png")
        return self._step("CP05", "preencher Data de Nascimento e Hora",
                          fn, observer, ctx=ctx)

    def _step_sexo(self, ctx, dados: dict, coords, observer=None):
        def fn():
            sexo = self._dado(dados, "sexo", "CP06")
            self._preencher_coord(ctx, coords, "campo_sexo", sexo)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP06_sexo.png")
        return self._step("CP06", "preencher Sexo", fn, observer, ctx=ctx)

    def _step_nacionalidade(self, ctx, dados: dict, coords, observer=None):
        def fn():
            nac = self._dado(dados, "nacionalidade", "CP07")
            self._preencher_coord(ctx, coords, "campo_nacionalidade", nac)
            pyautogui.press("tab"); time.sleep(2.0)
            encontrou = ctx.runner.wait_template(f"{self._TPL}/btn_ok.png",
                                                  timeout=8.0, threshold=0.6)
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(1.5)
            ctx.runner.type_text("SP"); pyautogui.press("tab"); time.sleep(0.5)
            ctx.runner.type_text("SAO PAULO"); time.sleep(0.3)
            encontrou2 = ctx.runner.wait_template(f"{self._TPL}/btn_ok_nacion.png",
                                                   timeout=8.0, threshold=0.6)
            if encontrou2:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok_nacion.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP07_nacion.png")
        return self._step("CP07", "preencher Nacionalidade", fn, observer, ctx=ctx)

    def _step_mae(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._preencher_coord(ctx, coords, "campo_mae", self._dado(dados, "mae", "CP08"))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP08_mae.png")
        return self._step("CP08", "preencher nome da Mae", fn, observer, ctx=ctx)

    def _step_pai(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._preencher_coord(ctx, coords, "campo_pai", self._dado(dados, "pai", "CP09"))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP09_pai.png")
        return self._step("CP09", "preencher nome do Pai", fn, observer, ctx=ctx)

    def _step_conjuge(self, ctx, dados: dict, coords, observer=None):
        def fn():
            # conjuge e opcional — pode ser vazio
            self._preencher_coord(ctx, coords, "campo_conjuge", dados.get("conjuge", ""))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP10_conjuge.png")
        return self._step("CP10", "preencher Conjuge", fn, observer, ctx=ctx)

    def _step_responsavel(self, ctx, dados: dict, coords, observer=None):
        def fn():
            # responsavel e opcional
            self._preencher_coord(ctx, coords, "campo_responsavel",
                                  dados.get("responsavel", ""))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP11_responsavel.png")
        return self._step("CP11", "preencher Responsavel", fn, observer, ctx=ctx)

    def _step_cor_etnia(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._preencher_coord(ctx, coords, "campo_cor_etnia",
                                  self._dado(dados, "cor_etnia", "CP12"))
            pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP12_cor.png")
        return self._step("CP12", "preencher Cor/Etnia", fn, observer, ctx=ctx)

    def _step_religiao(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._preencher_coord(ctx, coords, "campo_religiao",
                                  self._dado(dados, "religiao", "CP13"))
            pyautogui.press("tab"); time.sleep(1.5)
            encontrou = ctx.runner.wait_template(
                f"{self._TPL}/btn_ok.png", timeout=8.0, threshold=0.6,
            )
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP13_religiao.png")
        return self._step("CP13", "preencher Religiao", fn, observer, ctx=ctx)

    def _step_estado_civil(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._preencher_coord(ctx, coords, "campo_estado_civil",
                                  self._dado(dados, "estado_civil", "CP14"))
            pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP14_civil.png")
        return self._step("CP14", "preencher Estado Civil", fn, observer, ctx=ctx)

    def _step_ocupacao(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._preencher_coord(ctx, coords, "campo_ocupacao",
                                  self._dado(dados, "ocupacao", "CP15"))
            pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP15_ocupacao.png")
        return self._step("CP15", "preencher Ocupacao", fn, observer, ctx=ctx)

    def _step_situacao_familiar(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._preencher_coord(ctx, coords, "campo_situacao_familiar",
                                  self._dado(dados, "situacao_familiar", "CP16"))
            pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP16_sit_familiar.png")
        return self._step("CP16", "preencher Situacao Familiar", fn, observer, ctx=ctx)

    def _step_tipo_deficiencia(self, ctx, dados: dict, coords, observer=None):
        def fn():
            # tipo_deficiencia e opcional — pode ser vazio
            self._preencher_coord(ctx, coords, "campo_tipo_deficiencia",
                                  dados.get("tipo_deficiencia", ""))
            pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP17_defic.png")
        return self._step("CP17", "preencher Tipo de Deficiencia", fn, observer, ctx=ctx)

    def _step_escolaridade(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._preencher_coord(ctx, coords, "campo_escolaridade",
                                  self._dado(dados, "escolaridade", "CP18"))
            pyautogui.press("tab"); time.sleep(1.5)
            encontrou = ctx.runner.wait_template(
                f"{self._TPL}/btn_ok.png", timeout=8.0, threshold=0.6,
            )
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP18_escolar.png")
        return self._step("CP18", "preencher Escolaridade", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # CP19–CP21: Abas
    # ----------------------------------------------------------------

    def _step_documentos(self, ctx, dados: dict, coords, observer=None):
        def fn():
            time.sleep(0.5)
            rg  = self._dado(dados, "rg", "CP19")
            cpf = self._dado(dados, "cpf", "CP19").replace(".", "").replace("-", "")

            pyautogui.click(262, 424); time.sleep(0.3)
            pyperclip.copy(rg); pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(637, 427); time.sleep(0.3)
            pyperclip.copy("SSP"); pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(780, 426); time.sleep(0.3)
            pyperclip.copy("SP"); pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(868, 424); time.sleep(0.3)
            data_emissao = (date.today() - timedelta(days=30)).strftime("%d/%m/%Y")
            pyperclip.copy(data_emissao); pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(262, 450); time.sleep(0.3)
            pyperclip.copy(cpf); pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(257, 476); time.sleep(0.3)
            pyperclip.copy("726337961670004"); pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP19_docs.png")
        return self._step("CP19", "preencher Aba Documentos: RG + CPF + CNS",
                          fn, observer, ctx=ctx)

    def _step_enderecos(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._clicar_aba(ctx, coords, "aba_enderecos.png", "aba_enderecos")
            time.sleep(0.5)
            end = dados.get("endereco", {})
            cep = self._dado(end, "cep", "CP20") if end else self._dado(dados, "cep", "CP20")

            self._preencher_coord(ctx, coords, "campo_cep", cep)
            pyautogui.press("tab"); time.sleep(2.5)

            screenshot_cep = ctx.runner.screenshot(f"{ctx.evidence_dir}CP20_cep_check.png")
            logradouro_lido = OcrHelper.ler_regiao(
                screenshot_cep, (214, 424, 528, 444)
            ).strip()
            print(f"[CP20] Logradouro apos CEP: '{logradouro_lido}'")

            if logradouro_lido:
                print("[CP20] Auto-preenchimento OK — preenchendo Numero e Complemento")
                self._preencher_coord(ctx, coords, "campo_numero_endereco",
                                      end.get("numero", "44"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_complemento_endereco",
                                      end.get("complemento", "CADASTRO DE TESTE"))
                pyautogui.press("tab"); time.sleep(0.3)
            else:
                print("[CP20] Auto-preenchimento falhou — preenchendo todos os campos")
                self._preencher_coord(ctx, coords, "campo_tipo_endereco",
                                      end.get("tipo", "AVENIDA"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_logradouro",
                                      end.get("logradouro", "DR. ENEAS CARVALHO DE AGUIAR"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_numero_endereco",
                                      end.get("numero", "44"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_complemento_endereco",
                                      end.get("complemento", "CADASTRO DE TESTE"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_pais_endereco",
                                      end.get("pais", "BRASIL"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_uf_endereco",
                                      end.get("uf", "SP"))
                pyautogui.press("tab"); time.sleep(0.3)
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_municipio_endereco",
                                      end.get("municipio", "SAO PAULO"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_bairro",
                                      end.get("bairro", "BELA VISTA"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, coords, "campo_referencia_endereco",
                                      end.get("referencia", "PROXIMO AO CENTRO"))
                pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP20_endereco.png")
        return self._step("CP20", "preencher Aba Enderecos", fn, observer, ctx=ctx)

    def _step_comunicacao(self, ctx, dados: dict, coords, observer=None):
        def fn():
            self._clicar_aba(ctx, coords, "aba_comunicacao.png", "aba_comunicacao")
            time.sleep(0.5)
            com = dados.get("comunicacao", {})

            # Linha 1 — celular
            self._preencher_coord(ctx, coords, "campo_comunicacao_prioridade_l1", "1")
            pyautogui.press("tab"); time.sleep(0.2)
            x, y = self._coord(coords, "campo_comunicacao_lov_l1")
            pyautogui.click(x, y); time.sleep(1.5)
            pyautogui.click(82, 142); time.sleep(0.3)
            ctx.runner.type_text("CELULAR")
            pyautogui.click(113, 354); time.sleep(1.0)
            pyautogui.click(221, 355); time.sleep(0.5)
            self._preencher_coord(ctx, coords, "campo_comunicacao_numero_l1",
                                  com.get("celular", dados.get("celular", "")))
            pyautogui.press("tab"); time.sleep(0.3)

            # Linha 2 — e-mail
            self._preencher_coord(ctx, coords, "campo_comunicacao_prioridade_l2", "2")
            pyautogui.press("tab"); time.sleep(0.2)
            x, y = self._coord(coords, "campo_comunicacao_lov_l2")
            pyautogui.click(x, y); time.sleep(1.5)
            pyautogui.click(82, 142); time.sleep(0.3)
            ctx.runner.type_text("E-MAIL")
            pyautogui.click(113, 354); time.sleep(1.0)
            pyautogui.click(221, 355); time.sleep(0.5)
            self._preencher_coord(ctx, coords, "campo_comunicacao_numero_l2",
                                  "teste@teste.com")
            pyautogui.press("tab"); time.sleep(0.3)

            # Salvar antes de gerar matricula
            pyautogui.click(58, 66); time.sleep(2.5)
            if self._fechar_popups_oracle(ctx):
                print("[CP21] Popup Oracle Forms fechado apos salvar — comportamento esperado")

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP21_comunicacao.png")
        return self._step("CP21", "preencher Aba Comunicacao: celular e email",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # CP22: Gerar Matricula + Salvar + OCR + estado_jornada.json
    # ----------------------------------------------------------------

    def _step_gerar_matricula_salvar(self, ctx, observer=None):
        def fn():
            try:
                ctx.runner.safe_click(f"{self._TPL}/btn_gerar_matricula.png", threshold=0.7)
            except Exception:
                x, y = self._coord(ctx.config.coordenadas, "btn_gerar_matricula")
                pyautogui.click(x, y)
            time.sleep(2.0)

            pyautogui.click(58, 66); time.sleep(3.0)
            if self._fechar_popups_oracle(ctx):
                print("[CP22] Popup Oracle Forms fechado apos salvar — comportamento esperado")

            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}CP22_matricula.png")
            r = ctx.config.regioes_ocr["matricula"]
            regiao_tuple = (r["x1"], r["y1"], r["x2"], r["y2"])

            OcrHelper.salvar_debug(screenshot_path, regiao_tuple,
                                   f"{ctx.evidence_dir}CP22_ocr_debug.png")
            texto   = OcrHelper.ler_regiao(screenshot_path, regiao_tuple)
            numeros = re.findall(r"\d+", texto)
            if not numeros:
                raise AssertionError(
                    f"Matricula nao gerada ou OCR nao leu.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Regiao: {regiao_tuple}\n"
                    f"Veja CP22_ocr_debug.png e ajuste regioes_ocr.matricula no config.yaml."
                )
            matricula = numeros[0]
            print(f"[CP22] Matricula gerada: {matricula}")
            _salvar_estado_jornada("paciente_id", matricula)
            return screenshot_path
        return self._step("CP22", "gerar Matricula + Salvar + OCR",
                          fn, observer, validated=True, ctx=ctx)

    # ----------------------------------------------------------------
    # CP23: Sair
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, coords, observer=None):
        def fn():
            self._clicar_coord(ctx, coords, "btn_sair_1"); time.sleep(1.5)
            self._clicar_coord(ctx, coords, "btn_sair_2"); time.sleep(1.5)
            self._clicar_coord(ctx, coords, "btn_sair_menu"); time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP23_menu.png")
        return self._step("CP23", "sair para o Menu Principal", fn, observer, ctx=ctx)