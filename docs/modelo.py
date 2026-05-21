# src/flows/si3/cadastro_paciente_flow.py
"""
CadastroPacienteFlow — Cadastro completo de paciente no SI3 (Oracle Forms).

Pressupõe que o login já foi executado via LoginFlow.

Steps:
    CP01  Menu cadastro paciente
    CP02  Pesquisar nome
    CP03  Clicar Novo
    CP04  Nome Social
    CP05  Data Nascimento + Hora
    CP06  Sexo
    CP07  Nacionalidade (2 popups)
    CP08  Mãe
    CP09  Pai
    CP10  Cônjuge
    CP11  Responsável
    CP12  Cor/Etnia
    CP13  Religião
    CP14  Estado Civil
    CP15  Ocupação
    CP16  Situação Familiar
    CP17  Tipo de Deficiência
    CP18  Escolaridade + Frequenta Escola
    CP19  CPF + RG + CNS  (aba Documentos)
    CP20  Aba Endereços
    CP21  Aba Comunicação (celular + e-mail)
    CP22  Gerar Matrícula + Salvar + OCR + salvar estado_jornada.json
    CP23  Sair

Coordenadas:
    TODAS as coordenadas ficam no config.yaml em coordenadas:
    Use python scripts/posicao_mouse.py para capturar cada campo
    que não pode ser localizado por template OpenCV.

Templates em templates/si3/cadastro_paciente/:
    menu_cadastro_paciente.png
    campo_nome_pesquisa.png
    btn_pesquisar.png
    btn_novo.png
    campo_nome_social.png
    btn_ok.png
    btn_ok_nacion.png
    aba_documentos.png
    aba_enderecos.png
    aba_comunicacao.png
    btn_salvar.png
    btn_gerar_matricula.png  (ou coordenada se não tiver template)
"""

import json
import pathlib
import re
import time

import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult
from src.vision.ocr import OcrHelper


# Caminho do arquivo de estado compartilhado entre testes da jornada
_ESTADO_JORNADA_PATH = pathlib.Path("evidence/estado_jornada.json")


def _salvar_estado_jornada(chave: str, valor: str) -> None:
    """Atualiza evidence/estado_jornada.json com a chave/valor fornecidos."""
    _ESTADO_JORNADA_PATH.parent.mkdir(parents=True, exist_ok=True)
    estado = {}
    if _ESTADO_JORNADA_PATH.exists():
        try:
            estado = json.loads(_ESTADO_JORNADA_PATH.read_text(encoding="utf-8"))
        except Exception:
            estado = {}
    estado[chave] = valor
    _ESTADO_JORNADA_PATH.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[estado_jornada] {chave} = {valor} → {_ESTADO_JORNADA_PATH}")


class CadastroPacienteFlow:
    """
    Fluxo completo de cadastro de paciente no SI3.
    Ao final salva a matrícula gerada em evidence/estado_jornada.json
    para uso nos testes seguintes da jornada do ambulatório.
    """

    FLOW_NAME = "CadastroPacienteFlow"
    _TPL = "templates/si3/cadastro_paciente"

    # Região OCR para leitura da matrícula gerada (ajuste se necessário)
    _REGIAO_MATRICULA = (507, 139, 667, 169)

    # ──────────────────────────────────────────────────────────────────
    # execute
    # ──────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────────────────────────────

    def _coord(self, ctx, nome: str) -> tuple:
        """Lê coordenada do config.yaml. Lança KeyError se não configurada."""
        coords = ctx.config.coordenadas
        if nome not in coords:
            raise KeyError(
                f"Coordenada '{nome}' não encontrada em config.yaml → coordenadas:"
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
        """click_near com fallback para coordenada. Para campos grandes e únicos."""
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

    def _step(self, step_id: str, descricao: str, fn, observer) -> StepResult:
        """Wrapper padrão para todos os steps."""
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
        except Exception as e:
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ──────────────────────────────────────────────────────────────────
    # Steps CP01–CP03: Navegação
    # ──────────────────────────────────────────────────────────────────

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
            # Clica no campo Nome (principal) e Tab para foco correto
            self._clicar_coord(ctx, "campo_nome")
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP03_novo.png")
        return self._step("CP03", "clicar em Novo", fn, observer)

    # ──────────────────────────────────────────────────────────────────
    # Steps CP04–CP18: Formulário principal
    # ──────────────────────────────────────────────────────────────────

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
            # campos pequenos na mesma linha — coordenada direta
            self._preencher_coord(ctx, "campo_data_nasc", dados["data_nascimento"])
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
            self._preencher_coord(ctx, "campo_nacion",
                                  dados.get("nacionalidade", "BRASILEIRA"))
            pyautogui.press("tab")
            time.sleep(2.0)
            # Popup 1 — lista tipo de nacionalidade
            encontrou = ctx.runner.wait_template(f"{self._TPL}/btn_ok.png",
                                                  timeout=8.0, threshold=0.6)
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(1.5)
            # Popup 2 — UF/Estado de nascimento
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
        return self._step("CP08", "Mãe", fn, observer)

    def _step_pai(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_pai", dados["pai"])
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP09_pai.png")
        return self._step("CP09", "Pai", fn, observer)

    def _step_conjuge(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_conjuge", dados.get("conjuge", ""))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP10_conjuge.png")
        return self._step("CP10", "Cônjuge", fn, observer)

    def _step_responsavel(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_responsavel", dados.get("responsavel", ""))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP11_responsavel.png")
        return self._step("CP11", "Responsável", fn, observer)

    def _step_cor_etnia(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_cor_etnia", dados.get("cor_etnia", "PARDA"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP12_cor.png")
        return self._step("CP12", "Cor/Etnia", fn, observer)

    def _step_religiao(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            # Dropdown — digita a primeira letra e Tab confirma
            self._preencher_coord(ctx, "campo_religiao", dados.get("religiao", "CATOLIC"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP13_religiao.png")
        return self._step("CP13", "Religião", fn, observer)

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
        return self._step("CP15", "Ocupação", fn, observer)

    def _step_situacao_familiar(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_sit_familiar",
                                  dados.get("situacao_familiar", "FAMILIA"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP16_sit_familiar.png")
        return self._step("CP16", "Situação Familiar", fn, observer)

    def _step_tipo_deficiencia(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_tipo_defic",
                                  dados.get("tipo_deficiencia", "SEM DEFICI"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP17_defic.png")
        return self._step("CP17", "Tipo de Deficiência", fn, observer)

    def _step_escolaridade(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_escolaridade",
                                  dados.get("escolaridade", "SUPERIOR"))
            pyautogui.press("tab")
            time.sleep(0.3)
            # Campo Frequenta Escola (dropdown logo após)
            self._preencher_coord(ctx, "campo_freq_escola",
                                  dados.get("frequenta_escola", "NAO"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP18_escolar.png")
        return self._step("CP18", "Escolaridade + Frequenta Escola", fn, observer)

    # ──────────────────────────────────────────────────────────────────
    # Steps CP19–CP21: Abas
    # ──────────────────────────────────────────────────────────────────

    def _step_documentos(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            # Clicar na aba Documentos
            self._clicar_aba(ctx, "aba_documentos.png", "aba_documentos")
            time.sleep(0.5)

            # CPF (CIC) — sem pontuação
            cpf = dados["cpf"].replace(".", "").replace("-", "")
            self._preencher_coord(ctx, "campo_cpf", cpf)
            pyautogui.press("tab")
            time.sleep(0.3)

            # RG
            self._preencher_coord(ctx, "campo_rg", dados.get("rg", ""))
            pyautogui.press("tab")
            time.sleep(0.3)

            # CNS (Cartão Nacional de Saúde)
            self._preencher_coord(ctx, "campo_cns", dados.get("cns", ""))
            pyautogui.press("tab")
            time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP19_docs.png")
        return self._step("CP19", "Aba Documentos: CPF + RG + CNS", fn, observer)

    def _step_enderecos(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            # Clicar na aba Endereços
            self._clicar_aba(ctx, "aba_enderecos.png", "aba_enderecos")
            time.sleep(0.5)

            end = dados.get("endereco", {})
            self._preencher_coord(ctx, "campo_cep",         end.get("cep",         "01310100"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_tipo_logr",   end.get("tipo",        "AVENIDA"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_logradouro",  end.get("logradouro",  "DR. ENEAS CARVALHO DE AGUIAR"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_numero",      end.get("numero",      "44"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_complemento", end.get("complemento", "CADASTRO DE TESTE"))
            pyautogui.press("tab"); time.sleep(0.3)
            # campo_tipo_endereco já vem preenchido (RESIDENCIAL) — pular
            self._preencher_coord(ctx, "campo_pais",        end.get("pais",        "BRASIL"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_uf",          end.get("uf",          "SP"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_estado",      end.get("estado",      "SAO PAULO"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_municipio",   end.get("municipio",   "SAO PAULO"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_bairro",      end.get("bairro",      "BELA VISTA"))
            pyautogui.press("tab"); time.sleep(0.3)
            self._preencher_coord(ctx, "campo_ref",         end.get("referencia",  "PROXIMO AO CENTRO"))
            pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP20_endereco.png")
        return self._step("CP20", "Aba Endereços", fn, observer)

    def _step_comunicacao(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            # Clicar na aba Comunicação
            self._clicar_aba(ctx, "aba_comunicacao.png", "aba_comunicacao")
            time.sleep(0.5)

            com = dados.get("comunicacao", {})

            # Linha 1 — celular
            self._preencher_coord(ctx, "campo_com_prioridade_1", "1")
            pyautogui.press("tab"); time.sleep(0.2)
            self._preencher_coord(ctx, "campo_com_tipo_1", "CELULAR")
            pyautogui.press("tab"); time.sleep(0.2)
            self._preencher_coord(ctx, "campo_com_numero_1",
                                  com.get("celular", dados.get("celular", "")))
            pyautogui.press("tab"); time.sleep(0.3)

            # Linha 2 — e-mail
            self._preencher_coord(ctx, "campo_com_prioridade_2", "2")
            pyautogui.press("tab"); time.sleep(0.2)
            self._preencher_coord(ctx, "campo_com_tipo_2", "E-MAIL")
            pyautogui.press("tab"); time.sleep(0.2)
            self._preencher_coord(ctx, "campo_com_numero_2",
                                  com.get("email", dados.get("email", "")))
            pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP21_comunicacao.png")
        return self._step("CP21", "Aba Comunicação: celular + e-mail", fn, observer)

    # ──────────────────────────────────────────────────────────────────
    # Step CP22: Gerar Matrícula + Salvar + OCR + estado_jornada.json
    # ──────────────────────────────────────────────────────────────────

    def _step_gerar_matricula_salvar(self, ctx, observer=None) -> StepResult:
        def fn():
            # 1. Clicar em Gerar Matrícula
            try:
                ctx.runner.safe_click(f"{self._TPL}/btn_gerar_matricula.png", threshold=0.7)
            except Exception:
                self._clicar_coord(ctx, "btn_gerar_matricula")
            time.sleep(2.0)

            # 2. Salvar
            try:
                ctx.runner.safe_click(f"{self._TPL}/btn_salvar.png", threshold=0.7)
            except Exception:
                self._clicar_coord(ctx, "btn_salvar")
            time.sleep(2.5)

            # 3. Screenshot para OCR
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}CP22_matricula.png")

            # 4. OCR — lê a matrícula na região configurada
            texto = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_MATRICULA)
            numeros = re.findall(r"\d+", texto)
            if not numeros:
                OcrHelper.salvar_debug(screenshot_path, self._REGIAO_MATRICULA,
                                       f"{ctx.evidence_dir}CP22_ocr_debug.png")
                raise AssertionError(
                    f"Matrícula não gerada ou OCR não leu.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Veja CP22_ocr_debug.png e ajuste _REGIAO_MATRICULA."
                )
            matricula = numeros[0]
            print(f"[CP22] Matrícula gerada: {matricula}")

            # 5. Salva para uso nos próximos testes da jornada
            _salvar_estado_jornada("paciente_id", matricula)

            return screenshot_path
        return self._step("CP22", "Gerar Matrícula + Salvar + OCR", fn, observer)

    # ──────────────────────────────────────────────────────────────────
    # Step CP23: Sair
    # ──────────────────────────────────────────────────────────────────

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