# tests/unit/test_cadastro_funcionario_flow_sislab.py
"""
Testes unitarios do CadastroFuncionarioFlowSislab — 10 steps (CF01-CF10)
Migracao src/flows/sislab/cadastro_funcionario_flow_sislab.py ->
vtae/flows/sislab/cadastro_funcionario/

Cobre:
    - Todos os 10 steps (sucesso individual)
    - Fallback de clique via coordenada quando o template nao e encontrado
      (_clicar_com_fallback) — CF01, CF02, CF09
    - Dado obrigatorio ausente no config.yaml (CausaFalha.CONFIGURACAO) — CF03-CF08
    - Falha de confirmacao de tela (confirm_template) — CF01, CF02
    - Falha de mensagem de sucesso apos Salvar — CF09
    - Falha de verificacao OCR na grade — CF10
    - Abort chain: qualquer falha interrompe os steps seguintes

Nenhum teste unitario existia ate esta migracao.
"""

from unittest.mock import MagicMock, patch

import pytest

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult
from vtae.flows.sislab.cadastro_funcionario.cadastro_funcionario_flow_sislab import (
    CadastroFuncionarioFlowSislab,
)

MODULE = "vtae.flows.sislab.cadastro_funcionario.cadastro_funcionario_flow_sislab"


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _dados():
    return {
        "nome": "Fulano de Tal",
        "cpf": "12345678900",
        "cargo": "ANALISTA DE RH",
        "departamento": "ADMINISTRACAO",
        "salario": "5000",
        "admissao": "01/15/1990",
    }


def _config(dados=None):
    config = MagicMock()
    config.DADOS = dados if dados is not None else _dados()
    return config


def _runner_ok():
    runner = MagicMock()
    runner.screenshot.return_value = "evidence/step.png"
    runner.safe_click.return_value = True
    runner.wait_template.return_value = True
    runner.type_text.return_value = None
    return runner


def _ctx(runner=None, config=None):
    return FlowContext(
        runner=runner or _runner_ok(),
        config=config or _config(),
        evidence_dir="evidence/",
    )


def _run_with_mocks(runner=None, config=None, ocr_result=(True, "FULANO")):
    with patch(f"{MODULE}.pyautogui") as mock_pyautogui, \
         patch(f"{MODULE}.OcrHelper") as mock_ocr:
        mock_ocr.contem_qualquer_token.return_value = ocr_result
        mock_ocr.ler_regiao.return_value = "texto lido qualquer"
        mock_ocr.salvar_debug.return_value = None
        result = CadastroFuncionarioFlowSislab().execute(_ctx(runner, config))
        return result, mock_pyautogui, mock_ocr


def _run(runner=None, config=None, ocr_result=(True, "FULANO")):
    result, _, _ = _run_with_mocks(runner, config, ocr_result)
    return result


def _wait_template_falha_em(*templates_que_falham):
    def _wt(tpl, *args, **kwargs):
        return not any(t in tpl for t in templates_que_falham)
    return _wt


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert CadastroFuncionarioFlowSislab.FLOW_NAME == "CadastroFuncionarioFlowSislab"

    def test_execute_retorna_flow_result(self):
        assert isinstance(_run(), FlowResult)

    def test_execute_tem_10_steps(self):
        assert len(_run().steps) == 10

    def test_ids_corretos(self):
        ids = [s.step_id for s in _run().steps]
        assert ids == ["CF01", "CF02", "CF03", "CF04", "CF05",
                        "CF06", "CF07", "CF08", "CF09", "CF10"]

    def test_todos_steps_passam_com_runner_ok(self):
        falhos = [s for s in _run().steps if not s.success]
        assert falhos == [], [f"{s.step_id}: {s.error}" for s in falhos]

    def test_flow_sucesso(self):
        assert _run().success is True

    def test_execute_chama_add_result(self):
        ctx = _ctx()
        with patch(f"{MODULE}.pyautogui"), patch(f"{MODULE}.OcrHelper") as mock_ocr:
            mock_ocr.contem_qualquer_token.return_value = (True, "FULANO")
            CadastroFuncionarioFlowSislab().execute(ctx)
        assert ctx.all_passed() is True


# ──────────────────────────────────────────────────────────────────────────────
# CF01 — abrir Funcionarios
# ──────────────────────────────────────────────────────────────────────────────

class TestCf01:

    def test_sucesso(self):
        assert _run().steps[0].success is True

    def test_validated_true_via_confirm_template(self):
        assert _run().steps[0].validated is True

    def test_espera_menu_principal(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [c.args[0] for c in runner.wait_template.call_args_list]
        assert "templates/sislab/menu/menu_principal.png" in chamadas

    def test_clica_btn_funcionarios_via_template(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/sislab/menu/btn_funcionarios.png", threshold=0.7
        )

    def test_fallback_coordenada_quando_template_falha(self):
        runner = _runner_ok()

        def _safe_click(tpl, *args, **kwargs):
            if "btn_funcionarios.png" in tpl:
                raise Exception("template nao encontrado")
            return True

        runner.safe_click.side_effect = _safe_click
        result, mock_pyautogui, _ = _run_with_mocks(runner)
        assert result.steps[0].success is True
        mock_pyautogui.click.assert_any_call(79, 233)

    def test_falha_quando_tela_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.side_effect = _wait_template_falha_em(
            "tela_cadastro_funcionario.png"
        )
        result = _run(runner)
        assert result.steps[0].success is False
        assert len(result.steps) == 1


# ──────────────────────────────────────────────────────────────────────────────
# CF02 — clicar Novo
# ──────────────────────────────────────────────────────────────────────────────

class TestCf02:

    def test_sucesso(self):
        assert _run().steps[1].success is True

    def test_validated_true_via_confirm_template(self):
        assert _run().steps[1].validated is True

    def test_clica_btn_novo_via_template(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/sislab/funcionario/btn_novo.png", threshold=0.7
        )

    def test_espera_campo_nome(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [c.args[0] for c in runner.wait_template.call_args_list]
        assert "templates/sislab/funcionario/campo_nome.png" in chamadas

    def test_fallback_coordenada_quando_template_falha(self):
        runner = _runner_ok()

        def _safe_click(tpl, *args, **kwargs):
            if "btn_novo.png" in tpl:
                raise Exception("template nao encontrado")
            return True

        runner.safe_click.side_effect = _safe_click
        result, mock_pyautogui, _ = _run_with_mocks(runner)
        assert result.steps[1].success is True
        mock_pyautogui.click.assert_any_call(25, 146)

    def test_falha_quando_campo_nome_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.side_effect = _wait_template_falha_em("campo_nome.png")
        result = _run(runner)
        assert result.steps[1].success is False
        ids = [s.step_id for s in result.steps]
        assert ids == ["CF01", "CF02"]


# ──────────────────────────────────────────────────────────────────────────────
# CF03 — preencher Nome
# ──────────────────────────────────────────────────────────────────────────────

class TestCf03:

    def test_sucesso(self):
        assert _run().steps[2].success is True

    def test_digita_nome(self):
        runner = _runner_ok()
        _run(runner)
        runner.type_text.assert_any_call("Fulano de Tal")

    def test_pressiona_tab(self):
        runner = _runner_ok()
        _, mock_pyautogui, _ = _run_with_mocks(runner)
        mock_pyautogui.press.assert_any_call("tab")

    def test_falha_se_nome_ausente_no_config(self):
        config = _config(dados={k: v for k, v in _dados().items() if k != "nome"})
        result = _run(config=config)
        assert result.steps[2].success is False
        assert "nome" in result.steps[2].error
        assert result.steps[2].causa_falha.name == "CONFIGURACAO"


# ──────────────────────────────────────────────────────────────────────────────
# CF04 — preencher CPF
# ──────────────────────────────────────────────────────────────────────────────

class TestCf04:

    def test_sucesso(self):
        assert _run().steps[3].success is True

    def test_digita_cpf(self):
        runner = _runner_ok()
        _run(runner)
        runner.type_text.assert_any_call("12345678900")

    def test_pressiona_tab_3x(self):
        runner = _runner_ok()
        _, mock_pyautogui, _ = _run_with_mocks(runner)
        tabs = [c for c in mock_pyautogui.press.call_args_list if c.args == ("tab",)]
        assert len(tabs) >= 4  # CF03 (1x) + CF04 (3x)

    def test_falha_se_cpf_ausente_no_config(self):
        config = _config(dados={k: v for k, v in _dados().items() if k != "cpf"})
        result = _run(config=config)
        assert result.steps[3].success is False
        assert "cpf" in result.steps[3].error


# ──────────────────────────────────────────────────────────────────────────────
# CF05 — selecionar Cargo
# ──────────────────────────────────────────────────────────────────────────────

class TestCf05:

    def test_sucesso(self):
        assert _run().steps[4].success is True

    def test_pressiona_down_na_posicao_do_cargo(self):
        # Chama o step isoladamente — CF06 usa a mesma tecla "down" e
        # contaminaria a contagem se o flow inteiro fosse executado.
        runner = _runner_ok()
        with patch(f"{MODULE}.pyautogui") as mock_pyautogui:
            step = CadastroFuncionarioFlowSislab()._step_selecionar_cargo(
                _ctx(runner), observer=None
            )
        assert step.success is True
        downs = [c for c in mock_pyautogui.press.call_args_list if c.args == ("down",)]
        assert len(downs) == 2  # _CARGO_POSICAO = 2

    def test_falha_se_cargo_ausente_no_config(self):
        config = _config(dados={k: v for k, v in _dados().items() if k != "cargo"})
        result = _run(config=config)
        assert result.steps[4].success is False
        assert "cargo" in result.steps[4].error


# ──────────────────────────────────────────────────────────────────────────────
# CF06 — selecionar Departamento
# ──────────────────────────────────────────────────────────────────────────────

class TestCf06:

    def test_sucesso(self):
        assert _run().steps[5].success is True

    def test_falha_se_departamento_ausente_no_config(self):
        config = _config(dados={k: v for k, v in _dados().items() if k != "departamento"})
        result = _run(config=config)
        assert result.steps[5].success is False
        assert "departamento" in result.steps[5].error


# ──────────────────────────────────────────────────────────────────────────────
# CF07 — preencher Salario
# ──────────────────────────────────────────────────────────────────────────────

class TestCf07:

    def test_sucesso(self):
        assert _run().steps[6].success is True

    def test_digita_salario(self):
        runner = _runner_ok()
        _run(runner)
        runner.type_text.assert_any_call("5000")

    def test_falha_se_salario_ausente_no_config(self):
        config = _config(dados={k: v for k, v in _dados().items() if k != "salario"})
        result = _run(config=config)
        assert result.steps[6].success is False
        assert "salario" in result.steps[6].error


# ──────────────────────────────────────────────────────────────────────────────
# CF08 — preencher Data de Admissao
# ──────────────────────────────────────────────────────────────────────────────

class TestCf08:

    def test_sucesso(self):
        assert _run().steps[7].success is True

    def test_digita_admissao(self):
        runner = _runner_ok()
        _run(runner)
        runner.type_text.assert_any_call("01/15/1990")

    def test_falha_se_admissao_ausente_no_config(self):
        config = _config(dados={k: v for k, v in _dados().items() if k != "admissao"})
        result = _run(config=config)
        assert result.steps[7].success is False
        assert "admissao" in result.steps[7].error


# ──────────────────────────────────────────────────────────────────────────────
# CF09 — salvar + validar mensagem de sucesso
# ──────────────────────────────────────────────────────────────────────────────

class TestCf09:

    def test_sucesso(self):
        assert _run().steps[8].success is True

    def test_validated_true(self):
        assert _run().steps[8].validated is True

    def test_clica_btn_salvar_via_template(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/sislab/funcionario/btn_salvar.png", threshold=0.7
        )

    def test_fallback_coordenada_quando_template_falha(self):
        runner = _runner_ok()

        def _safe_click(tpl, *args, **kwargs):
            if "btn_salvar.png" in tpl:
                raise Exception("template nao encontrado")
            return True

        runner.safe_click.side_effect = _safe_click
        result, mock_pyautogui, _ = _run_with_mocks(runner)
        assert result.steps[8].success is True
        mock_pyautogui.click.assert_any_call(85, 148)

    def test_falha_quando_msg_sucesso_nao_aparece(self):
        runner = _runner_ok()
        runner.wait_template.side_effect = _wait_template_falha_em("msg_sucesso.png")
        result = _run(runner)
        assert result.steps[8].success is False
        ids = [s.step_id for s in result.steps]
        assert ids[-1] == "CF09"
        assert "sucesso" in result.steps[8].error.lower()


# ──────────────────────────────────────────────────────────────────────────────
# CF10 — verificar nome na grade via OCR
# ──────────────────────────────────────────────────────────────────────────────

class TestCf10:

    def test_sucesso(self):
        assert _run().steps[9].success is True

    def test_validated_true(self):
        assert _run().steps[9].validated is True

    def test_ocr_chamado_com_tokens_do_nome(self):
        runner = _runner_ok()
        _, _, mock_ocr = _run_with_mocks(runner)
        _, kwargs = mock_ocr.contem_qualquer_token.call_args
        assert kwargs["tokens"] == "FULANO DE TAL".split()

    def test_falha_quando_ocr_nao_encontra_nome(self):
        runner = _runner_ok()
        result = _run(runner, ocr_result=(False, None))
        assert result.steps[9].success is False
        assert "nao encontrado na grade" in result.steps[9].error

    def test_falha_chama_salvar_debug(self):
        runner = _runner_ok()
        _, _, mock_ocr = _run_with_mocks(runner, ocr_result=(False, None))
        mock_ocr.salvar_debug.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Abort on failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_cf01_nao_executa_demais_steps(self):
        runner = _runner_ok()
        runner.wait_template.side_effect = _wait_template_falha_em(
            "tela_cadastro_funcionario.png"
        )
        result = _run(runner)
        ids = [s.step_id for s in result.steps]
        assert ids == ["CF01"]

    def test_falha_cf05_interrompe_antes_de_cf06(self):
        config = _config(dados={k: v for k, v in _dados().items() if k != "cargo"})
        result = _run(config=config)
        ids = [s.step_id for s in result.steps]
        assert ids == ["CF01", "CF02", "CF03", "CF04", "CF05"]

    def test_observer_notificado_para_todos_steps_ok(self):
        observer = MagicMock()
        with patch(f"{MODULE}.pyautogui"), patch(f"{MODULE}.OcrHelper") as mock_ocr:
            mock_ocr.contem_qualquer_token.return_value = (True, "FULANO")
            CadastroFuncionarioFlowSislab().execute(_ctx(), observer=observer)
        assert observer.log_step_start.call_count == 10
        observer.log_flow_result.assert_called_once()
