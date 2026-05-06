"""
Testes unitários — DSLInterpreter v0.5.1

Imports baseados na estrutura real do projeto:
  - DSLInterpreter  → vtae.core.dsl_interpreter
  - StepError       → src.core.types
  - FlowResult      → src.core.result
  - patch path      → vtae.core.dsl_interpreter.DSLInterpreter._ocr_read
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_runner():
    runner = MagicMock()
    runner.safe_click.return_value = None
    runner.click_near.return_value = None
    runner.type_text.return_value = None
    runner.fill.return_value = None
    runner.wait_template.return_value = True
    runner.screenshot.return_value = "evidence/step.png"
    return runner


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.sistema = "si3"
    config.DADOS = {
        "nome": "MARIA SILVA",
        "cpf": "12345678900",
        "data_nascimento": "01/01/1990",
    }
    return config


@pytest.fixture
def mock_ctx(mock_runner, mock_config):
    ctx = MagicMock()
    ctx.runner = mock_runner
    ctx.config = mock_config
    ctx.evidence_dir = "evidence/test/"
    ctx.add_result.return_value = None
    return ctx


@pytest.fixture
def interp(mock_ctx):
    from vtae.core.dsl_interpreter import DSLInterpreter
    return DSLInterpreter(mock_ctx)


# ---------------------------------------------------------------------------
# _resolve
# ---------------------------------------------------------------------------

class TestResolve:
    def test_sem_interpolacao(self, interp):
        assert interp._resolve("texto fixo") == "texto fixo"

    def test_interpolacao_simples(self, interp):
        assert interp._resolve("<<DADOS.nome>>") == "MARIA SILVA"

    def test_interpolacao_composta(self, interp):
        result = interp._resolve("Nome: <<DADOS.nome>>, CPF: <<DADOS.cpf>>")
        assert result == "Nome: MARIA SILVA, CPF: 12345678900"

    def test_chave_ausente_levanta_step_error(self, interp):
        from src.core.types import StepError
        with pytest.raises(StepError, match="<<DADOS.inexistente>>"):
            interp._resolve("<<DADOS.inexistente>>")

    def test_dados_vazio_levanta_step_error(self, interp, mock_config):
        mock_config.DADOS = {}
        from src.core.types import StepError
        with pytest.raises(StepError):
            interp._resolve("<<DADOS.nome>>")


# ---------------------------------------------------------------------------
# fill_field
# ---------------------------------------------------------------------------

class TestFillField:
    def test_template_sem_offset_usa_safe_click(self, interp, mock_runner):
        step = {"action": "fill_field", "template": "templates/label.png", "value": "teste"}
        interp._action_fill_field(1, step)
        mock_runner.safe_click.assert_called_once_with("templates/label.png")
        mock_runner.type_text.assert_called_once_with("teste")

    def test_template_com_offset_usa_click_near(self, interp, mock_runner):
        step = {"action": "fill_field", "template": "templates/label_nome.png", "offset_x": 200, "value": "MARIA"}
        interp._action_fill_field(1, step)
        mock_runner.click_near.assert_called_once_with("templates/label_nome.png", offset_x=200, offset_y=0)
        mock_runner.type_text.assert_called_once_with("MARIA")

    def test_selector_usa_fill(self, interp, mock_runner):
        step = {"action": "fill_field", "selector": "#P17_NOME", "value": "JOSE"}
        interp._action_fill_field(1, step)
        mock_runner.fill.assert_called_once_with("#P17_NOME", "JOSE")

    def test_interpolacao_dados(self, interp, mock_runner):
        step = {"action": "fill_field", "selector": "#P17_NOME", "value": "<<DADOS.nome>>"}
        interp._action_fill_field(1, step)
        mock_runner.fill.assert_called_once_with("#P17_NOME", "MARIA SILVA")

    def test_sem_template_e_sem_selector_levanta_step_error(self, interp):
        from src.core.types import StepError
        step = {"action": "fill_field", "value": "algo"}
        with pytest.raises(StepError, match="template.*selector"):
            interp._action_fill_field(1, step)

    def test_value_vazio_preenche_string_vazia(self, interp, mock_runner):
        step = {"action": "fill_field", "selector": "#campo", "value": ""}
        interp._action_fill_field(1, step)
        mock_runner.fill.assert_called_once_with("#campo", "")

    def test_offset_y_negativo(self, interp, mock_runner):
        step = {"action": "fill_field", "template": "templates/label.png", "offset_y": -30, "value": "x"}
        interp._action_fill_field(1, step)
        mock_runner.click_near.assert_called_once_with("templates/label.png", offset_x=0, offset_y=-30)


# ---------------------------------------------------------------------------
# assert_visible
# ---------------------------------------------------------------------------

class TestAssertVisible:
    def test_template_encontrado_retorna_screenshot(self, interp, mock_runner):
        mock_runner.wait_template.return_value = True
        step = {"action": "assert_visible", "template": "templates/msg.png"}
        path = interp._action_assert_visible(1, step)
        assert path == "evidence/step.png"

    def test_template_nao_encontrado_levanta_step_error(self, interp, mock_runner):
        mock_runner.wait_template.return_value = False
        from src.core.types import StepError
        step = {"action": "assert_visible", "template": "templates/msg.png", "timeout": 2.0}
        with pytest.raises(StepError, match="assert_visible falhou"):
            interp._action_assert_visible(1, step)

    def test_selector_web_encontrado(self, interp, mock_runner):
        mock_runner.wait_template.return_value = True
        step = {"action": "assert_visible", "selector": "#sucesso"}
        interp._action_assert_visible(1, step)
        mock_runner.wait_template.assert_called_once_with("#sucesso", timeout=5.0)

    def test_timeout_customizado(self, interp, mock_runner):
        mock_runner.wait_template.return_value = True
        step = {"action": "assert_visible", "template": "t.png", "timeout": 15.0}
        interp._action_assert_visible(1, step)
        mock_runner.wait_template.assert_called_once_with("t.png", timeout=15.0)

    def test_sem_template_e_sem_selector_levanta_step_error(self, interp):
        from src.core.types import StepError
        step = {"action": "assert_visible"}
        with pytest.raises(StepError, match="template.*selector"):
            interp._action_assert_visible(1, step)

    def test_screenshot_tirado_mesmo_em_falha(self, interp, mock_runner):
        mock_runner.wait_template.return_value = False
        mock_runner.screenshot.return_value = "evidence/DSL01.png"
        from src.core.types import StepError
        step = {"action": "assert_visible", "template": "t.png"}
        with pytest.raises(StepError):
            interp._action_assert_visible(1, step)
        mock_runner.screenshot.assert_called_once()


# ---------------------------------------------------------------------------
# assert_text
# ---------------------------------------------------------------------------

class TestAssertText:
    def test_web_selector_texto_correto(self, interp, mock_runner):
        mock_runner._page.locator.return_value.first.text_content.return_value = "Ativo"
        step = {"action": "assert_text", "selector": "#P17_STATUS", "expected": "Ativo"}
        with patch("vtae.core.dsl_interpreter.DSLInterpreter._web_get_text", return_value="Ativo"):
            interp._action_assert_text(1, step)

    def test_web_case_insensitive(self, interp, mock_runner):
        step = {"action": "assert_text", "selector": "#msg", "expected": "cadastro realizado"}
        with patch("vtae.core.dsl_interpreter.DSLInterpreter._web_get_text", return_value="CADASTRO REALIZADO"):
            interp._action_assert_text(1, step)

    def test_ocr_desktop_texto_correto(self, interp, mock_runner):
        with patch("vtae.core.dsl_interpreter.DSLInterpreter._ocr_read", return_value="Cadastro realizado com sucesso"):
            step = {"action": "assert_text", "expected": "Cadastro realizado"}
            interp._action_assert_text(1, step)

    def test_ocr_desktop_texto_errado_levanta_step_error(self, interp, mock_runner):
        with patch("vtae.core.dsl_interpreter.DSLInterpreter._ocr_read", return_value="Erro ao salvar registro"):
            from src.core.types import StepError
            step = {"action": "assert_text", "expected": "Cadastro realizado"}
            with pytest.raises(StepError, match="assert_text falhou"):
                interp._action_assert_text(1, step)

    def test_ocr_com_region(self, interp, mock_runner):
        with patch("vtae.core.dsl_interpreter.DSLInterpreter._ocr_read", return_value="ok") as mock_ocr:
            step = {"action": "assert_text", "expected": "ok", "region": [0, 620, 1366, 660]}
            interp._action_assert_text(1, step)
            mock_ocr.assert_called_once_with([0, 620, 1366, 660])

    def test_expected_vazio_levanta_step_error(self, interp):
        from src.core.types import StepError
        step = {"action": "assert_text", "expected": ""}
        with pytest.raises(StepError, match="expected"):
            interp._action_assert_text(1, step)

    def test_interpolacao_expected(self, interp, mock_runner):
        with patch("vtae.core.dsl_interpreter.DSLInterpreter._ocr_read", return_value="MARIA SILVA cadastrada"):
            step = {"action": "assert_text", "expected": "<<DADOS.nome>>"}
            interp._action_assert_text(1, step)


# ---------------------------------------------------------------------------
# FlowResult — integração run()
# ---------------------------------------------------------------------------

class TestFlowResult:
    def _def(self):
        return {"flow": "teste_dsl", "steps": [{"action": "assert_visible", "template": "t.png"}]}

    def test_run_retorna_flow_result(self, interp, mock_runner):
        from src.core.result import FlowResult
        mock_runner.wait_template.return_value = True
        result = interp.run(self._def())
        assert isinstance(result, FlowResult)

    def test_run_step_sucesso(self, interp, mock_runner):
        mock_runner.wait_template.return_value = True
        result = interp.run(self._def())
        assert result.success
        assert len(result.steps) == 1
        assert result.steps[0].success

    def test_run_step_falha_aborta_flow(self, interp, mock_runner):
        mock_runner.wait_template.return_value = False
        definition = {"flow": "abort", "steps": [
            {"action": "assert_visible", "template": "t1.png"},
            {"action": "assert_visible", "template": "t2.png"},
        ]}
        result = interp.run(definition)
        assert not result.success
        assert len(result.steps) == 1

    def test_run_chama_ctx_add_result(self, interp, mock_runner, mock_ctx):
        mock_runner.wait_template.return_value = True
        interp.run(self._def())
        mock_ctx.add_result.assert_called_once()

    def test_run_flow_vazio(self, interp):
        result = interp.run({"flow": "vazio", "steps": []})
        assert result.success
        assert result.steps == []

    def test_run_com_observer(self, mock_ctx, mock_runner):
        from vtae.core.dsl_interpreter import DSLInterpreter
        observer = MagicMock()
        mock_runner.wait_template.return_value = True
        interp = DSLInterpreter(mock_ctx, observer=observer)
        interp.run({"flow": "obs_test", "steps": [{"action": "assert_visible", "template": "t.png"}]})
        observer.log_flow_start.assert_called_once_with("obs_test")
        observer.log_step_result.assert_called_once()
        observer.log_flow_result.assert_called_once()


# ---------------------------------------------------------------------------
# Ações desconhecidas
# ---------------------------------------------------------------------------

class TestUnknownAction:
    def test_acao_desconhecida_levanta_value_error(self, interp):
        with pytest.raises(ValueError, match="Ação desconhecida"):
            interp.run({"flow": "x", "steps": [{"action": "hover"}]})


# ---------------------------------------------------------------------------
# Ações legadas — smoke tests
# ---------------------------------------------------------------------------

class TestLegacyActions:
    def test_click_template(self, interp, mock_runner):
        interp.run({"flow": "x", "steps": [{"action": "click", "template": "t.png"}]})
        mock_runner.safe_click.assert_called_with("t.png")

    def test_click_sem_template_e_sem_selector(self, interp):
        result = interp.run({"flow": "x", "steps": [{"action": "click"}]})
        assert not result.success
        assert "template" in result.steps[0].error or "selector" in result.steps[0].error

    def test_type_com_texto_fixo(self, interp, mock_runner):
        interp.run({"flow": "x", "steps": [{"action": "type", "text": "hello"}]})
        mock_runner.type_text.assert_called_with("hello")

    def test_wait_timeout_customizado(self, interp, mock_runner):
        mock_runner.wait_template.return_value = True
        interp.run({"flow": "x", "steps": [{"action": "wait", "template": "t.png", "timeout": 20.0}]})
        mock_runner.wait_template.assert_called_with("t.png", timeout=20.0)

    def test_wait_timeout_levanta_step_error(self, interp, mock_runner):
        mock_runner.wait_template.return_value = False
        result = interp.run({"flow": "x", "steps": [{"action": "wait", "template": "t.png"}]})
        assert not result.success
        assert "timeout" in result.steps[0].error.lower()

    def test_screenshot_salva_caminho_correto(self, interp, mock_runner):
        mock_runner.screenshot.return_value = "evidence/test/minha_foto.png"
        result = interp.run({"flow": "x", "steps": [{"action": "screenshot", "name": "minha_foto.png"}]})
        assert result.success
        mock_runner.screenshot.assert_called_with("evidence/test/minha_foto.png")
