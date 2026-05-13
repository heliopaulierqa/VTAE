"""
Testes unitários — DSLInterpreter v0.5.3

Cobre v0.5.1 + v0.5.2 + v0.5.3:
  - loop (count, items, <<LOOP.item>>, <<LOOP.index>>, falha em sub-step)
  - if (condição verdadeira, falsa, assert_text, sem then/else, sem condition)
  - _evaluate_condition (assert_visible true/false, assert_text, condição desconhecida)
  - _resolve_loop_step (interpolação de strings e listas)
  - Regressão: todas as ações v0.5.1 e v0.5.2
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
    from src.core.dsl_interpreter import DSLInterpreter
    return DSLInterpreter(mock_ctx)


# ---------------------------------------------------------------------------
# loop — modo count
# ---------------------------------------------------------------------------

class TestLoopCount:
    def test_executa_n_vezes(self, interp, mock_runner):
        definition = {"flow": "x", "steps": [
            {"action": "loop", "count": 3, "steps": [
                {"action": "click", "template": "t.png"},
            ]},
        ]}
        result = interp.run(definition)
        assert result.success
        assert mock_runner.safe_click.call_count == 3

    def test_count_1_executa_uma_vez(self, interp, mock_runner):
        definition = {"flow": "x", "steps": [
            {"action": "loop", "count": 1, "steps": [
                {"action": "click", "template": "t.png"},
            ]},
        ]}
        interp.run(definition)
        assert mock_runner.safe_click.call_count == 1

    def test_count_0_nao_executa(self, interp, mock_runner):
        definition = {"flow": "x", "steps": [
            {"action": "loop", "count": 0, "steps": [
                {"action": "click", "template": "t.png"},
            ]},
        ]}
        result = interp.run(definition)
        assert result.success
        mock_runner.safe_click.assert_not_called()

    def test_falha_em_sub_step_aborta_loop(self, interp, mock_runner):
        mock_runner.wait_template.return_value = False
        definition = {"flow": "x", "steps": [
            {"action": "loop", "count": 3, "steps": [
                {"action": "assert_visible", "template": "t.png"},
            ]},
        ]}
        result = interp.run(definition)
        assert not result.success
        # Deve ter tentado só 1 vez antes de abortar
        assert mock_runner.wait_template.call_count == 1


# ---------------------------------------------------------------------------
# loop — modo items
# ---------------------------------------------------------------------------

class TestLoopItems:
    def test_itera_sobre_lista(self, interp, mock_runner):
        definition = {"flow": "x", "steps": [
            {"action": "loop", "items": ["A", "B", "C"], "steps": [
                {"action": "fill_field", "selector": "#campo", "value": "<<LOOP.item>>"},
            ]},
        ]}
        result = interp.run(definition)
        assert result.success
        calls = mock_runner.fill.call_args_list
        assert calls[0] == call("#campo", "A")
        assert calls[1] == call("#campo", "B")
        assert calls[2] == call("#campo", "C")

    def test_loop_index_comeca_em_1(self, interp, mock_runner):
        captured = []
        mock_runner.type_text.side_effect = lambda v: captured.append(v)
        definition = {"flow": "x", "steps": [
            {"action": "loop", "items": ["X", "Y"], "steps": [
                {"action": "type", "text": "<<LOOP.index>>"},
            ]},
        ]}
        interp.run(definition)
        assert captured == ["1", "2"]

    def test_loop_item_e_index_juntos(self, interp, mock_runner):
        captured = []
        mock_runner.fill.side_effect = lambda sel, val: captured.append(val)
        definition = {"flow": "x", "steps": [
            {"action": "loop", "items": ["ALPHA"], "steps": [
                {"action": "fill_field", "selector": "#c",
                 "value": "<<LOOP.index>>:<<LOOP.item>>"},
            ]},
        ]}
        interp.run(definition)
        assert captured == ["1:ALPHA"]

    def test_lista_vazia_nao_executa(self, interp, mock_runner):
        definition = {"flow": "x", "steps": [
            {"action": "loop", "items": [], "steps": [
                {"action": "click", "template": "t.png"},
            ]},
        ]}
        result = interp.run(definition)
        assert result.success
        mock_runner.safe_click.assert_not_called()

    def test_loop_item_com_dados(self, interp, mock_runner):
        """<<DADOS.*>> e <<LOOP.item>> podem coexistir no mesmo step."""
        captured = []
        mock_runner.fill.side_effect = lambda sel, val: captured.append(val)
        definition = {"flow": "x", "steps": [
            {"action": "loop", "items": ["X"], "steps": [
                {"action": "fill_field", "selector": "#c",
                 "value": "<<DADOS.nome>>-<<LOOP.item>>"},
            ]},
        ]}
        interp.run(definition)
        assert captured == ["MARIA SILVA-X"]


# ---------------------------------------------------------------------------
# loop — validações
# ---------------------------------------------------------------------------

class TestLoopValidacoes:
    def test_sem_steps_levanta_step_error(self, interp):
        result = interp.run({"flow": "x", "steps": [
            {"action": "loop", "count": 2},
        ]})
        assert not result.success
        assert "steps" in result.steps[0].error

    def test_sem_count_e_sem_items_levanta_step_error(self, interp):
        result = interp.run({"flow": "x", "steps": [
            {"action": "loop", "steps": [{"action": "click", "template": "t.png"}]},
        ]})
        assert not result.success
        assert "count" in result.steps[0].error or "items" in result.steps[0].error


# ---------------------------------------------------------------------------
# if — condição verdadeira / falsa
# ---------------------------------------------------------------------------

class TestIf:
    def test_executa_then_quando_condicao_verdadeira(self, interp, mock_runner):
        mock_runner.wait_template.return_value = True
        definition = {"flow": "x", "steps": [
            {"action": "if",
             "condition": {"assert_visible": {"template": "popup.png", "timeout": 1.0}},
             "then": [{"action": "click", "template": "btn_fechar.png"}],
             "else": [{"action": "click", "template": "btn_ok.png"}]},
        ]}
        result = interp.run(definition)
        assert result.success
        calls = [c.args[0] for c in mock_runner.safe_click.call_args_list]
        assert "btn_fechar.png" in calls
        assert "btn_ok.png" not in calls

    def test_executa_else_quando_condicao_falsa(self, interp, mock_runner):
        mock_runner.wait_template.return_value = False
        definition = {"flow": "x", "steps": [
            {"action": "if",
             "condition": {"assert_visible": {"template": "popup.png", "timeout": 1.0}},
             "then": [{"action": "click", "template": "btn_fechar.png"}],
             "else": [{"action": "click", "template": "btn_ok.png"}]},
        ]}
        result = interp.run(definition)
        assert result.success
        calls = [c.args[0] for c in mock_runner.safe_click.call_args_list]
        assert "btn_ok.png" in calls
        assert "btn_fechar.png" not in calls

    def test_sem_else_condicao_falsa_nao_falha(self, interp, mock_runner):
        mock_runner.wait_template.return_value = False
        definition = {"flow": "x", "steps": [
            {"action": "if",
             "condition": {"assert_visible": {"template": "popup.png"}},
             "then": [{"action": "click", "template": "t.png"}]},
        ]}
        result = interp.run(definition)
        assert result.success
        mock_runner.safe_click.assert_not_called()

    def test_falha_em_then_propaga_erro(self, interp, mock_runner):
        mock_runner.wait_template.side_effect = [True, False]
        definition = {"flow": "x", "steps": [
            {"action": "if",
             "condition": {"assert_visible": {"template": "popup.png", "timeout": 0.1}},
             "then": [{"action": "assert_visible", "template": "t.png", "timeout": 0.1}]},
        ]}
        result = interp.run(definition)
        assert not result.success
        assert "then" in result.steps[0].error

    def test_condicao_assert_text_verdadeira(self, interp, mock_runner):
        interp._ocr_read = lambda region: "Cadastro realizado"
        definition = {"flow": "x", "steps": [
            {"action": "if",
             "condition": {"assert_text": {"expected": "Cadastro"}},
             "then": [{"action": "click", "template": "btn.png"}]},
        ]}
        result = interp.run(definition)
        assert result.success
        mock_runner.safe_click.assert_called_once()

    def test_condicao_assert_text_falsa_executa_else(self, interp, mock_runner):
        interp._ocr_read = lambda region: "Erro ao salvar"
        definition = {"flow": "x", "steps": [
            {"action": "if",
             "condition": {"assert_text": {"expected": "Cadastro"}},
             "then": [{"action": "click", "template": "btn_ok.png"}],
             "else": [{"action": "click", "template": "btn_erro.png"}]},
        ]}
        result = interp.run(definition)
        assert result.success
        calls = [c.args[0] for c in mock_runner.safe_click.call_args_list]
        assert "btn_erro.png" in calls


# ---------------------------------------------------------------------------
# if — validações
# ---------------------------------------------------------------------------

class TestIfValidacoes:
    def test_sem_condition_levanta_step_error(self, interp):
        result = interp.run({"flow": "x", "steps": [
            {"action": "if",
             "then": [{"action": "click", "template": "t.png"}]},
        ]})
        assert not result.success
        assert "condition" in result.steps[0].error

    def test_sem_then_e_sem_else_levanta_step_error(self, interp):
        result = interp.run({"flow": "x", "steps": [
            {"action": "if",
             "condition": {"assert_visible": {"template": "t.png"}}},
        ]})
        assert not result.success
        assert "then" in result.steps[0].error or "else" in result.steps[0].error


# ---------------------------------------------------------------------------
# _evaluate_condition
# ---------------------------------------------------------------------------

class TestEvaluateCondition:
    def test_assert_visible_true(self, interp, mock_runner):
        mock_runner.wait_template.return_value = True
        assert interp._evaluate_condition(
            {"assert_visible": {"template": "t.png", "timeout": 1.0}}
        ) is True

    def test_assert_visible_false(self, interp, mock_runner):
        mock_runner.wait_template.return_value = False
        assert interp._evaluate_condition(
            {"assert_visible": {"template": "t.png", "timeout": 1.0}}
        ) is False

    def test_assert_visible_sem_target_retorna_false(self, interp):
        assert interp._evaluate_condition({"assert_visible": {}}) is False

    def test_condicao_desconhecida_retorna_false(self, interp):
        assert interp._evaluate_condition({"hover": {"template": "t.png"}}) is False

    def test_assert_text_true(self, interp):
        interp._ocr_read = lambda region: "texto encontrado"
        assert interp._evaluate_condition(
            {"assert_text": {"expected": "texto"}}
        ) is True

    def test_assert_text_false(self, interp):
        interp._ocr_read = lambda region: "outro conteúdo"
        assert interp._evaluate_condition(
            {"assert_text": {"expected": "ausente"}}
        ) is False


# ---------------------------------------------------------------------------
# _resolve — interpolação LOOP + DADOS
# ---------------------------------------------------------------------------

class TestResolveLoop:
    def test_loop_item_interpolado(self, interp):
        interp._loop_item = "CARGO_X"
        interp._loop_index = 2
        assert interp._resolve("<<LOOP.item>>") == "CARGO_X"

    def test_loop_index_interpolado(self, interp):
        interp._loop_item = "X"
        interp._loop_index = 5
        assert interp._resolve("<<LOOP.index>>") == "5"

    def test_dados_e_loop_juntos(self, interp):
        interp._loop_item = "ITEM"
        interp._loop_index = 1
        assert interp._resolve("<<DADOS.nome>>-<<LOOP.item>>") == "MARIA SILVA-ITEM"

    def test_sem_interpolacao_retorna_original(self, interp):
        assert interp._resolve("texto fixo") == "texto fixo"


# ---------------------------------------------------------------------------
# SUPPORTED_ACTIONS — regressão completa
# ---------------------------------------------------------------------------

class TestSupportedActions:
    def test_contem_todas_as_acoes(self, interp):
        for action in [
            "login", "click", "type", "wait", "screenshot",
            "fill_field", "assert_visible", "assert_text",
            "select_dropdown", "run_component",
            "loop", "if",
        ]:
            assert action in interp.SUPPORTED_ACTIONS

