"""
Testes unitários — DSLInterpreter v0.5.2

Cobre:
  - select_dropdown desktop (mode: type, mode: arrow)
  - select_dropdown web (selector + fill + Enter)
  - select_dropdown validações (sem target, sem value)
  - run_component (sucesso, falha, import inválido, name inválido, args <<DADOS>>)
  - Regressão: 38 testes v0.5.1 continuam passando (importados via conftest)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call


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
        "cargo": "ANALISTA DE RH",
        "cpf": "12345678900",
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
# select_dropdown — desktop mode: type (default)
# ---------------------------------------------------------------------------

class TestSelectDropdownDesktopType:
    def test_clica_e_digita_valor(self, interp, mock_runner):
        with patch("pyautogui.press") as mock_press:
            step = {
                "action": "select_dropdown",
                "template": "templates/si3/label_cargo.png",
                "offset_x": 200,
                "value": "ANALISTA",
            }
            interp._action_select_dropdown(1, step)
        mock_runner.click_near.assert_called_once_with(
            "templates/si3/label_cargo.png", offset_x=200, offset_y=0
        )
        mock_runner.type_text.assert_called_once_with("ANALISTA")
        mock_press.assert_called_once_with("enter")

    def test_sem_offset_usa_safe_click(self, interp, mock_runner):
        with patch("pyautogui.press"):
            step = {
                "action": "select_dropdown",
                "template": "templates/si3/label_cargo.png",
                "value": "ANALISTA",
            }
            interp._action_select_dropdown(1, step)
        mock_runner.safe_click.assert_called_once_with("templates/si3/label_cargo.png")

    def test_interpolacao_value(self, interp, mock_runner):
        with patch("pyautogui.press"):
            step = {
                "action": "select_dropdown",
                "template": "templates/label.png",
                "value": "<<DADOS.cargo>>",
            }
            interp._action_select_dropdown(1, step)
        mock_runner.type_text.assert_called_once_with("ANALISTA DE RH")

    def test_tira_screenshot(self, interp, mock_runner):
        with patch("pyautogui.press"):
            step = {
                "action": "select_dropdown",
                "template": "t.png",
                "value": "X",
                "id": "SD01",
            }
            path = interp._action_select_dropdown(1, step)
        assert path == "evidence/step.png"
        mock_runner.screenshot.assert_called_once_with("evidence/test/SD01.png")


# ---------------------------------------------------------------------------
# select_dropdown — desktop mode: arrow
# ---------------------------------------------------------------------------

class TestSelectDropdownDesktopArrow:
    def test_pressiona_setas_e_enter(self, interp, mock_runner):
        with patch("pyautogui.press") as mock_press:
            step = {
                "action": "select_dropdown",
                "template": "templates/si3/label_cargo.png",
                "value": "ANALISTA",
                "mode": "arrow",
                "arrows": 3,
            }
            interp._action_select_dropdown(1, step)
        calls = mock_press.call_args_list
        assert calls.count(call("down")) == 3
        assert calls[-1] == call("enter")

    def test_arrows_default_e_1(self, interp, mock_runner):
        with patch("pyautogui.press") as mock_press:
            step = {
                "action": "select_dropdown",
                "template": "t.png",
                "value": "X",
                "mode": "arrow",
            }
            interp._action_select_dropdown(1, step)
        calls = mock_press.call_args_list
        assert calls.count(call("down")) == 1
        assert calls[-1] == call("enter")

    def test_nao_digita_em_mode_arrow(self, interp, mock_runner):
        with patch("pyautogui.press"):
            step = {
                "action": "select_dropdown",
                "template": "t.png",
                "value": "X",
                "mode": "arrow",
                "arrows": 2,
            }
            interp._action_select_dropdown(1, step)
        mock_runner.type_text.assert_not_called()


# ---------------------------------------------------------------------------
# select_dropdown — web
# ---------------------------------------------------------------------------

class TestSelectDropdownWeb:
    def test_usa_fill_e_enter(self, interp, mock_runner):
        page_mock = MagicMock()
        mock_runner._page = page_mock
        step = {
            "action": "select_dropdown",
            "selector": "#P17_CARGO",
            "value": "ANALISTA",
        }
        interp._action_select_dropdown(1, step)
        mock_runner.fill.assert_called_once_with("#P17_CARGO", "ANALISTA")
        page_mock.locator.assert_called_once_with("#P17_CARGO")
        page_mock.locator.return_value.press.assert_called_once_with("Enter")

    def test_interpolacao_web(self, interp, mock_runner):
        page_mock = MagicMock()
        mock_runner._page = page_mock
        step = {
            "action": "select_dropdown",
            "selector": "#P17_CARGO",
            "value": "<<DADOS.cargo>>",
        }
        interp._action_select_dropdown(1, step)
        mock_runner.fill.assert_called_once_with("#P17_CARGO", "ANALISTA DE RH")


# ---------------------------------------------------------------------------
# select_dropdown — validações
# ---------------------------------------------------------------------------

class TestSelectDropdownValidacoes:
    def test_sem_template_e_sem_selector(self, interp):
        from src.core.types import StepError
        step = {"action": "select_dropdown", "value": "X"}
        with pytest.raises(StepError, match="template.*selector"):
            interp._action_select_dropdown(1, step)

    def test_sem_value(self, interp):
        from src.core.types import StepError
        step = {"action": "select_dropdown", "template": "t.png", "value": ""}
        with pytest.raises(StepError, match="value"):
            interp._action_select_dropdown(1, step)

    def test_via_run_falha_registra_no_step(self, interp, mock_runner):
        result = interp.run({"flow": "x", "steps": [
            {"action": "select_dropdown", "value": "X"},
        ]})
        assert not result.success
        assert "template" in result.steps[0].error or "selector" in result.steps[0].error


# ---------------------------------------------------------------------------
# run_component
# ---------------------------------------------------------------------------

class TestRunComponent:
    def _fake_module(self, fn_name="preencher_formulario", return_value=None):
        """Cria módulo falso com função que retorna return_value."""
        mod = MagicMock()
        fn = MagicMock(return_value=return_value)
        setattr(mod, fn_name, fn)
        return mod

    def test_importa_e_executa_componente(self, interp, mock_ctx):
        fake_mod = self._fake_module()
        with patch("importlib.import_module", return_value=fake_mod):
            step = {
                "action": "run_component",
                "name": "si3.cadastro_paciente_component.preencher_formulario",
            }
            result = interp.run({"flow": "x", "steps": [step]})
        assert result.success
        fake_mod.preencher_formulario.assert_called_once_with(mock_ctx, None)

    def test_passa_args_resolvidos(self, interp, mock_ctx):
        fake_mod = self._fake_module()
        with patch("importlib.import_module", return_value=fake_mod):
            step = {
                "action": "run_component",
                "name": "si3.cadastro_paciente_component.preencher_formulario",
                "args": {"dados": "<<DADOS>>"},
            }
            interp.run({"flow": "x", "steps": [step]})
        call_kwargs = fake_mod.preencher_formulario.call_args
        assert call_kwargs.kwargs["dados"] == {
            "nome": "MARIA SILVA",
            "cargo": "ANALISTA DE RH",
            "cpf": "12345678900",
        }

    def test_args_com_interpolacao_de_campo(self, interp, mock_ctx):
        fake_mod = self._fake_module()
        with patch("importlib.import_module", return_value=fake_mod):
            step = {
                "action": "run_component",
                "name": "si3.comp.fn",
                "args": {"nome": "<<DADOS.nome>>"},
            }
            interp.run({"flow": "x", "steps": [step]})
        call_kwargs = fake_mod.fn.call_args
        assert call_kwargs.kwargs["nome"] == "MARIA SILVA"

    def test_componente_retorna_flow_result_falha(self, interp):
        flow_result_falha = MagicMock()
        flow_result_falha.success = False
        flow_result_falha.failed_steps = ["CP01"]
        fake_mod = self._fake_module(return_value=flow_result_falha)
        with patch("importlib.import_module", return_value=fake_mod):
            step = {
                "action": "run_component",
                "name": "si3.comp.preencher_formulario",
            }
            result = interp.run({"flow": "x", "steps": [step]})
        assert not result.success
        assert "falhou" in result.steps[0].error

    def test_import_invalido_registra_falha(self, interp):
        with patch("importlib.import_module", side_effect=ImportError("não encontrado")):
            result = interp.run({"flow": "x", "steps": [
                {"action": "run_component", "name": "si3.inexistente.fn"},
            ]})
        assert not result.success
        assert "não foi possível importar" in result.steps[0].error

    def test_name_invalido_sem_tres_partes(self, interp):
        result = interp.run({"flow": "x", "steps": [
            {"action": "run_component", "name": "si3.comp"},
        ]})
        assert not result.success
        assert "Formato esperado" in result.steps[0].error

    def test_name_vazio(self, interp):
        result = interp.run({"flow": "x", "steps": [
            {"action": "run_component", "name": ""},
        ]})
        assert not result.success
        assert "name" in result.steps[0].error

    def test_funcao_nao_existe_no_modulo(self, interp):
        fake_mod = MagicMock(spec=[])  # spec vazio — nenhum atributo
        with patch("importlib.import_module", return_value=fake_mod):
            result = interp.run({"flow": "x", "steps": [
                {"action": "run_component", "name": "si3.comp.fn_inexistente"},
            ]})
        assert not result.success
        assert "não encontrado" in result.steps[0].error

    def test_componente_retorna_none_conta_como_sucesso(self, interp):
        fake_mod = self._fake_module(return_value=None)
        with patch("importlib.import_module", return_value=fake_mod):
            result = interp.run({"flow": "x", "steps": [
                {"action": "run_component", "name": "si3.comp.fn"},
            ]})
        assert result.success


# ---------------------------------------------------------------------------
# SUPPORTED_ACTIONS — regressão v0.5.1 + v0.5.2
# ---------------------------------------------------------------------------

class TestSupportedActions:
    def test_contem_todas_as_acoes_v051(self, interp):
        for action in ["login", "click", "type", "wait", "screenshot",
                       "fill_field", "assert_visible", "assert_text"]:
            assert action in interp.SUPPORTED_ACTIONS

    def test_contem_acoes_v052(self, interp):
        assert "select_dropdown" in interp.SUPPORTED_ACTIONS
        assert "run_component" in interp.SUPPORTED_ACTIONS
