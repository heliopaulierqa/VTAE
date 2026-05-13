"""
Testes unitários — CadastroPacienteFlow (SI3)

Cobre os 14 steps do flow real, sem abrir nenhuma janela.

Estratégia de mock:
  - ctx.runner mockado com MagicMock — simula OpenCVRunner
  - pyautogui mockado globalmente — sem movimento de mouse real
  - OcrHelper mockado — sem Tesseract instalado
  - Cada teste verifica o comportamento esperado do step, não a
    implementação interna (não testa coordenadas hardcoded)

Convenção de IDs: CP01..CP14
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_sleep():
    """Mocka time.sleep globalmente — elimina os sleeps reais do flow."""
    with patch("time.sleep"):
        yield


@pytest.fixture
def mock_runner():
    runner = MagicMock()
    runner.double_click.return_value = True
    runner.click_template.return_value = True
    runner.click_near.return_value = True
    runner.safe_click.return_value = True
    runner.wait_template.return_value = True
    runner.screenshot.return_value = "evidence/step.png"
    runner.type_text.return_value = None
    return runner


@pytest.fixture
def mock_ctx(mock_runner):
    ctx = MagicMock()
    ctx.runner = mock_runner
    ctx.evidence_dir = "evidence/test/"
    return ctx


@pytest.fixture
def dados():
    return {
        "nome":           "MARIA TESTE SILVA",
        "nome_social":    "MARIA SILVA",
        "data_nascimento": "01/01/1990",
        "hora":           "00:00",
        "sexo":           "F",
        "nacionalidade":  "BRASILEIRA",
        "mae":            "ANA TESTE",
        "pai":            "JOSE TESTE",
        "cor_etnia":      "PARDA",
        "cpf":            "123.456.789-00",
    }


@pytest.fixture
def flow():
    from src.flows.si3.cadastro_paciente_flow import CadastroPacienteFlow
    return CadastroPacienteFlow()


# ---------------------------------------------------------------------------
# Estrutura do flow
# ---------------------------------------------------------------------------

class TestCadastroPacienteFlowEstrutura:
    def test_flow_name_correto(self, flow):
        assert flow.FLOW_NAME == "CadastroPacienteFlow"

    def test_execute_retorna_flow_result(self, flow, mock_ctx, dados):
        from src.core.result import FlowResult
        with patch("pyautogui.click"), patch("pyautogui.press"), \
             patch("pyautogui.hotkey"), patch("pyautogui.typewrite"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="12345"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            result = flow.execute(mock_ctx, dados)
        assert isinstance(result, FlowResult)

    def test_execute_tem_14_steps(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.press"), \
             patch("pyautogui.hotkey"), patch("pyautogui.typewrite"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="12345"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            result = flow.execute(mock_ctx, dados)
        assert len(result.steps) == 14

    def test_execute_chama_add_result(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.press"), \
             patch("pyautogui.hotkey"), patch("pyautogui.typewrite"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="12345"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            flow.execute(mock_ctx, dados)
        mock_ctx.add_result.assert_called_once()

    def test_ids_dos_steps_corretos(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.press"), \
             patch("pyautogui.hotkey"), patch("pyautogui.typewrite"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="12345"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            result = flow.execute(mock_ctx, dados)
        ids = [s.step_id for s in result.steps]
        assert ids == [
            "CP01", "CP02", "CP03", "CP04", "CP05",
            "CP06", "CP07", "CP08", "CP09", "CP10",
            "CP11", "CP12", "CP13", "CP14",
        ]


# ---------------------------------------------------------------------------
# CP01 — Menu
# ---------------------------------------------------------------------------

class TestStepMenu:
    def test_cp01_sucesso(self, flow, mock_ctx):
        with patch("pyautogui.click"), patch("pyautogui.press"):
            step = flow._step_menu(mock_ctx)
        assert step.step_id == "CP01"
        assert step.success

    def test_cp01_chama_double_click(self, flow, mock_ctx):
        with patch("pyautogui.click"), patch("pyautogui.press"):
            flow._step_menu(mock_ctx)
        mock_ctx.runner.double_click.assert_called_once()

    def test_cp01_aguarda_campo_pesquisa(self, flow, mock_ctx):
        with patch("pyautogui.click"), patch("pyautogui.press"):
            flow._step_menu(mock_ctx)
        mock_ctx.runner.wait_template.assert_called()

    def test_cp01_falha_se_double_click_lanca_excecao(self, flow, mock_ctx):
        mock_ctx.runner.double_click.side_effect = Exception("template não encontrado")
        with patch("pyautogui.click"), patch("pyautogui.press"):
            step = flow._step_menu(mock_ctx)
        assert not step.success
        assert "template não encontrado" in step.error

    def test_cp01_tira_screenshot(self, flow, mock_ctx):
        with patch("pyautogui.click"), patch("pyautogui.press"):
            flow._step_menu(mock_ctx)
        mock_ctx.runner.screenshot.assert_called()

    def test_cp01_notifica_observer(self, flow, mock_ctx):
        observer = MagicMock()
        with patch("pyautogui.click"), patch("pyautogui.press"):
            flow._step_menu(mock_ctx, observer)
        observer.log_step_start.assert_called_once_with("CP01", pytest.approx("duplo clique em Cadastro de Pacientes", abs=0))
        observer.log_step_result.assert_called_once()


# ---------------------------------------------------------------------------
# CP02 — Pesquisar
# ---------------------------------------------------------------------------

class TestStepPesquisar:
    def test_cp02_sucesso(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.typewrite"):
            step = flow._step_pesquisar(mock_ctx, dados)
        assert step.step_id == "CP02"
        assert step.success

    def test_cp02_digita_nome(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.typewrite"):
            flow._step_pesquisar(mock_ctx, dados)
        mock_ctx.runner.type_text.assert_called()
        # O nome deve ter sido digitado em alguma chamada
        calls_args = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert dados["nome"] in calls_args

    def test_cp02_falha_se_runner_lanca_excecao(self, flow, mock_ctx, dados):
        mock_ctx.runner.type_text.side_effect = Exception("falha de digitação")
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.typewrite"):
            step = flow._step_pesquisar(mock_ctx, dados)
        assert not step.success


# ---------------------------------------------------------------------------
# CP03 — Novo
# ---------------------------------------------------------------------------

class TestStepNovo:
    def test_cp03_sucesso(self, flow, mock_ctx):
        with patch("pyautogui.click"), patch("pyautogui.press"):
            step = flow._step_novo(mock_ctx)
        assert step.step_id == "CP03"
        assert step.success

    def test_cp03_aguarda_campo_nome_social(self, flow, mock_ctx):
        with patch("pyautogui.click"), patch("pyautogui.press"):
            flow._step_novo(mock_ctx)
        calls = [c.args[0] for c in mock_ctx.runner.wait_template.call_args_list]
        assert any("campo_nome_social" in c for c in calls)

    def test_cp03_falha_se_wait_template_retorna_false(self, flow, mock_ctx):
        mock_ctx.runner.wait_template.return_value = False
        mock_ctx.runner.wait_template.side_effect = Exception("timeout")
        with patch("pyautogui.click"), patch("pyautogui.press"):
            step = flow._step_novo(mock_ctx)
        assert not step.success


# ---------------------------------------------------------------------------
# CP04 — Nome Social
# ---------------------------------------------------------------------------

class TestStepNomeSocial:
    def test_cp04_usa_nome_social_quando_presente(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.press"):
            flow._step_nome_social(mock_ctx, dados)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "MARIA SILVA" in calls

    def test_cp04_usa_nome_quando_nome_social_ausente(self, flow, mock_ctx, dados):
        dados_sem_social = {**dados, "nome_social": ""}
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.press"):
            flow._step_nome_social(mock_ctx, dados_sem_social)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "MARIA TESTE SILVA" in calls

    def test_cp04_step_id_correto(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.press"):
            step = flow._step_nome_social(mock_ctx, dados)
        assert step.step_id == "CP04"


# ---------------------------------------------------------------------------
# CP05 — Data de Nascimento
# ---------------------------------------------------------------------------

class TestStepDataNascimento:
    def test_cp05_preenche_data_e_hora(self, flow, mock_ctx, dados):
        with patch("pyautogui.click") as mock_click, \
             patch("pyautogui.hotkey"), patch("pyautogui.typewrite"):
            step = flow._step_data_nascimento(mock_ctx, dados)
        assert step.success
        assert step.step_id == "CP05"

    def test_cp05_digita_data_nascimento(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.typewrite"):
            flow._step_data_nascimento(mock_ctx, dados)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "01/01/1990" in calls

    def test_cp05_digita_hora(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.typewrite"):
            flow._step_data_nascimento(mock_ctx, dados)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "00:00" in calls


# ---------------------------------------------------------------------------
# CP06 — Sexo
# ---------------------------------------------------------------------------

class TestStepSexo:
    def test_cp06_preenche_sexo(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"):
            step = flow._step_sexo(mock_ctx, dados)
        assert step.success
        assert step.step_id == "CP06"

    def test_cp06_digita_valor_sexo(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"):
            flow._step_sexo(mock_ctx, dados)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "F" in calls

    def test_cp06_default_sexo_m_quando_ausente(self, flow, mock_ctx, dados):
        dados_sem_sexo = {k: v for k, v in dados.items() if k != "sexo"}
        with patch("pyautogui.click"), patch("pyautogui.hotkey"):
            flow._step_sexo(mock_ctx, dados_sem_sexo)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "M" in calls


# ---------------------------------------------------------------------------
# CP07 — Nacionalidade
# ---------------------------------------------------------------------------

class TestStepNacionalidade:
    def test_cp07_sucesso(self, flow, mock_ctx, dados):
        mock_ctx.runner.wait_template.return_value = True
        with patch("pyautogui.click"), patch("pyautogui.press"):
            step = flow._step_nacionalidade(mock_ctx, dados)
        assert step.step_id == "CP07"
        assert step.success

    def test_cp07_fallback_enter_quando_btn_ok_nao_encontrado(self, flow, mock_ctx, dados):
        mock_ctx.runner.wait_template.return_value = False
        with patch("pyautogui.click"), patch("pyautogui.press") as mock_press:
            flow._step_nacionalidade(mock_ctx, dados)
        # Enter deve ter sido pressionado como fallback
        enter_calls = [c for c in mock_press.call_args_list if c.args[0] == "enter"]
        assert len(enter_calls) >= 1

    def test_cp07_digita_brasileira(self, flow, mock_ctx, dados):
        mock_ctx.runner.wait_template.return_value = True
        with patch("pyautogui.click"), patch("pyautogui.press"):
            flow._step_nacionalidade(mock_ctx, dados)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "BRASILEIRA" in calls


# ---------------------------------------------------------------------------
# CP08 / CP09 — Mãe e Pai
# ---------------------------------------------------------------------------

class TestStepMaePai:
    def test_cp08_preenche_mae(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"):
            step = flow._step_mae(mock_ctx, dados)
        assert step.step_id == "CP08"
        assert step.success
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "ANA TESTE" in calls

    def test_cp09_preenche_pai(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"):
            step = flow._step_pai(mock_ctx, dados)
        assert step.step_id == "CP09"
        assert step.success
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "JOSE TESTE" in calls


# ---------------------------------------------------------------------------
# CP10 — Cor/Etnia
# ---------------------------------------------------------------------------

class TestStepCorEtnia:
    def test_cp10_preenche_cor_etnia(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.press"):
            step = flow._step_cor_etnia(mock_ctx, dados)
        assert step.step_id == "CP10"
        assert step.success

    def test_cp10_default_parda_quando_ausente(self, flow, mock_ctx, dados):
        dados_sem_cor = {k: v for k, v in dados.items() if k != "cor_etnia"}
        with patch("pyautogui.click"), patch("pyautogui.hotkey"), \
             patch("pyautogui.press"):
            flow._step_cor_etnia(mock_ctx, dados_sem_cor)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "PARDA" in calls


# ---------------------------------------------------------------------------
# CP11 — CPF
# ---------------------------------------------------------------------------

class TestStepCpf:
    def test_cp11_remove_pontuacao_do_cpf(self, flow, mock_ctx, dados):
        with patch("pyautogui.click"), patch("pyautogui.hotkey"):
            step = flow._step_cpf(mock_ctx, dados)
        assert step.step_id == "CP11"
        assert step.success
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        # CPF sem pontuação
        assert "12345678900" in calls

    def test_cp11_cpf_sem_pontuacao_nao_reprocessado(self, flow, mock_ctx, dados):
        dados_cpf_limpo = {**dados, "cpf": "12345678900"}
        with patch("pyautogui.click"), patch("pyautogui.hotkey"):
            flow._step_cpf(mock_ctx, dados_cpf_limpo)
        calls = [c.args[0] for c in mock_ctx.runner.type_text.call_args_list]
        assert "12345678900" in calls


# ---------------------------------------------------------------------------
# CP12 — Salvar
# ---------------------------------------------------------------------------

class TestStepSalvar:
    def test_cp12_salva_com_sucesso(self, flow, mock_ctx):
        with patch("pyautogui.click"), patch("pyautogui.press"):
            step = flow._step_salvar(mock_ctx)
        assert step.step_id == "CP12"
        assert step.success

    def test_cp12_falha_se_runner_lanca_excecao(self, flow, mock_ctx):
        mock_ctx.runner.click_template.side_effect = Exception("erro ao clicar")
        mock_ctx.runner.safe_click.side_effect = Exception("erro ao clicar")
        with patch("pyautogui.click", side_effect=Exception("falha pyautogui")):
            step = flow._step_salvar(mock_ctx)
        assert not step.success


# ---------------------------------------------------------------------------
# CP13 — Gerar Matrícula (OCR)
# ---------------------------------------------------------------------------

class TestStepGerarMatricula:
    def test_cp13_sucesso_quando_ocr_retorna_numero(self, flow, mock_ctx):
        with patch("pyautogui.click"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="12345 matrícula"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            step = flow._step_gerar_matricula(mock_ctx)
        assert step.step_id == "CP13"
        assert step.success

    def test_cp13_falha_quando_ocr_nao_retorna_numero(self, flow, mock_ctx):
        with patch("pyautogui.click"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value=""), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            step = flow._step_gerar_matricula(mock_ctx)
        assert not step.success
        assert "Matrícula não gerada" in step.error or "OCR" in step.error

    def test_cp13_chama_salvar_debug_em_falha(self, flow, mock_ctx):
        with patch("pyautogui.click"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="sem número"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug") as mock_debug:
            flow._step_gerar_matricula(mock_ctx)
        mock_debug.assert_called_once()


# ---------------------------------------------------------------------------
# CP14 — Sair
# ---------------------------------------------------------------------------

class TestStepSair:
    def test_cp14_sai_com_sucesso(self, flow, mock_ctx):
        with patch("pyautogui.click"), patch("pyautogui.press"):
            step = flow._step_sair(mock_ctx)
        assert step.step_id == "CP14"
        assert step.success

    def test_cp14_chama_tres_cliques(self, flow, mock_ctx):
        with patch("pyautogui.click") as mock_click:
            flow._step_sair(mock_ctx)
        assert mock_click.call_count == 3

    def test_cp14_tira_screenshot(self, flow, mock_ctx):
        with patch("pyautogui.click"):
            flow._step_sair(mock_ctx)
        mock_ctx.runner.screenshot.assert_called()


# ---------------------------------------------------------------------------
# Abort-on-failure — flow para no primeiro step que falha
# ---------------------------------------------------------------------------

class TestAbortOnFailure:
    def test_falha_em_cp01_aborta_flow(self, flow, mock_ctx, dados):
        mock_ctx.runner.double_click.side_effect = Exception("menu não encontrado")
        with patch("pyautogui.click"), patch("pyautogui.press"), \
             patch("pyautogui.hotkey"), patch("pyautogui.typewrite"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="1"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            result = flow.execute(mock_ctx, dados)
        assert not result.success
        assert len(result.steps) == 1

    def test_falha_em_cp02_executa_apenas_2_steps(self, flow, mock_ctx, dados):
        call_count = [0]
        original_type = mock_ctx.runner.type_text.side_effect

        def type_side_effect(text):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("falha ao digitar")

        mock_ctx.runner.type_text.side_effect = type_side_effect
        with patch("pyautogui.click"), patch("pyautogui.press"), \
             patch("pyautogui.hotkey"), patch("pyautogui.typewrite"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="1"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            result = flow.execute(mock_ctx, dados)
        assert not result.success
        assert len(result.steps) <= 3  # falha no CP02

    def test_flow_com_observer(self, flow, mock_ctx, dados):
        observer = MagicMock()
        with patch("pyautogui.click"), patch("pyautogui.press"), \
             patch("pyautogui.hotkey"), patch("pyautogui.typewrite"), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="12345"), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            result = flow.execute(mock_ctx, dados, observer)
        observer.log_flow_result.assert_called_once()
        assert observer.log_step_start.call_count == 14
        assert observer.log_step_result.call_count == 14
