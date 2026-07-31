# tests/unit/test_tipo_anestesia_flow.py
"""
Testes unitarios do TipoAnestesiaFlow — 8 steps (TA01-TA08)
Migracao src/flows/msi3/tipo_anestesia_flow.py ->
vtae/flows/msi3/tipo_anestesia/tipo_anestesia_flow.py

Flow web (Playwright puro) — ctx.runner._page e mockado, ApexHelper e
mockado por completo (mesma estrategia usada em test_login_flow_msi3.py:
simular a pagina real do Playwright inteira nao vale a pena quando o
flow so delega a logica de espera/erro para o ApexHelper).

TA01-TA05 sao testados chamando o metodo do step diretamente (nao via
execute()) porque runner._page.locator(...) sempre retorna o MESMO
MagicMock (runner._page.locator.return_value) independente do seletor
passado — testar via execute() completo tornaria as asserções de
"qual step clicou o que" ambíguas entre steps.

Nenhum teste unitario existia ate esta migracao.
"""

from unittest.mock import MagicMock, patch

import pytest

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult
from vtae.flows.msi3.tipo_anestesia.tipo_anestesia_flow import TipoAnestesiaFlow

MODULE = "vtae.flows.msi3.tipo_anestesia.tipo_anestesia_flow"


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _dados():
    return {
        "codigo": "AB12",
        "descricao": "TESTE VTAE ANESTESIA",
        "tipo_anestesia": "Geral",
    }


def _runner_ok():
    runner = MagicMock()
    page = MagicMock()
    page.frames = []
    runner._page = page
    runner.screenshot.return_value = "evidence/step.png"
    runner.wait_template.return_value = True
    return runner


def _ctx(runner=None):
    return FlowContext(
        runner=runner or _runner_ok(),
        config=MagicMock(),
        evidence_dir="evidence/",
    )


def _run_with_mocks(runner=None, dados=None):
    with patch(f"{MODULE}.ApexHelper") as mock_apex:
        result = TipoAnestesiaFlow().execute(
            _ctx(runner), dados=dados if dados is not None else _dados()
        )
        return result, mock_apex


def _run(runner=None, dados=None):
    result, _ = _run_with_mocks(runner, dados)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert TipoAnestesiaFlow.FLOW_NAME == "TipoAnestesiaFlow"

    def test_execute_retorna_flow_result(self):
        assert isinstance(_run(), FlowResult)

    def test_execute_tem_8_steps(self):
        assert len(_run().steps) == 8

    def test_ids_corretos(self):
        ids = [s.step_id for s in _run().steps]
        assert ids == ["TA01", "TA02", "TA03", "TA04", "TA05",
                        "TA06", "TA07", "TA08"]

    def test_todos_steps_passam_com_runner_ok(self):
        falhos = [s for s in _run().steps if not s.success]
        assert falhos == [], [f"{s.step_id}: {s.error}" for s in falhos]

    def test_flow_sucesso(self):
        assert _run().success is True

    def test_execute_chama_add_result(self):
        ctx = _ctx()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow().execute(ctx, dados=_dados())
        assert ctx.all_passed() is True


# ──────────────────────────────────────────────────────────────────────────────
# TA01 — Sistema de Pacientes
# ──────────────────────────────────────────────────────────────────────────────

class TestTa01:

    def test_sucesso(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_sistema_pacientes(_ctx(runner), observer=None)
        assert step.success is True

    def test_validated_true_via_confirm_template(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_sistema_pacientes(_ctx(runner), observer=None)
        assert step.validated is True

    def test_clica_card_sistema_pacientes(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow()._step_sistema_pacientes(_ctx(runner), observer=None)
        runner._page.locator.assert_any_call(
            "h3.t-Card-title", has_text="Sistema de Pacientes"
        )
        runner._page.locator.return_value.click.assert_called()

    def test_chama_aguardar_spinner(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper") as mock_apex:
            TipoAnestesiaFlow()._step_sistema_pacientes(_ctx(runner), observer=None)
        mock_apex.aguardar_spinner.assert_called_once_with(runner)

    def test_falha_se_card_cirurgia_novo_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_sistema_pacientes(_ctx(runner), observer=None)
        assert step.success is False


# ──────────────────────────────────────────────────────────────────────────────
# TA02 — Cirurgia (NOVO)
# ──────────────────────────────────────────────────────────────────────────────

class TestTa02:

    def test_sucesso(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_cirurgia_novo(_ctx(runner), observer=None)
        assert step.success is True

    def test_clica_card_cirurgia_novo(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow()._step_cirurgia_novo(_ctx(runner), observer=None)
        runner._page.locator.assert_any_call(
            "h3.t-Card-title", has_text="Cirurgia (NOVO)"
        )

    def test_falha_se_card_cadastros_basicos_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_cirurgia_novo(_ctx(runner), observer=None)
        assert step.success is False


# ──────────────────────────────────────────────────────────────────────────────
# TA03 — Cadastros Basicos
# ──────────────────────────────────────────────────────────────────────────────

class TestTa03:

    def test_sucesso(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_cadastros_basicos(_ctx(runner), observer=None)
        assert step.success is True

    def test_clica_card_cadastros_basicos(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow()._step_cadastros_basicos(_ctx(runner), observer=None)
        runner._page.locator.assert_any_call(
            "h3.t-Card-title", has_text="Cadastros Básicos"
        )

    def test_falha_se_card_intra_operatorio_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_cadastros_basicos(_ctx(runner), observer=None)
        assert step.success is False


# ──────────────────────────────────────────────────────────────────────────────
# TA04 — Intra-operatorio
# ──────────────────────────────────────────────────────────────────────────────

class TestTa04:

    def test_sucesso(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_intra_operatorio(_ctx(runner), observer=None)
        assert step.success is True

    def test_clica_card_intra_operatorio(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow()._step_intra_operatorio(_ctx(runner), observer=None)
        runner._page.locator.assert_any_call(
            "h3.t-Card-title", has_text="Intra-operatório"
        )

    def test_falha_se_card_tipo_anestesia_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_intra_operatorio(_ctx(runner), observer=None)
        assert step.success is False


# ──────────────────────────────────────────────────────────────────────────────
# TA05 — Tipo Anestesia
# ──────────────────────────────────────────────────────────────────────────────

class TestTa05:

    def test_sucesso(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_tipo_anestesia(_ctx(runner), observer=None)
        assert step.success is True

    def test_clica_card_tipo_anestesia(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow()._step_tipo_anestesia(_ctx(runner), observer=None)
        runner._page.locator.assert_any_call(
            "h3.t-Card-title", has_text="Tipo Anestesia"
        )

    def test_falha_se_botao_novo_tipo_anestesia_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_tipo_anestesia(_ctx(runner), observer=None)
        assert step.success is False


# ──────────────────────────────────────────────────────────────────────────────
# TA06 — Novo Tipo Anestesia (sem confirm_template)
# ──────────────────────────────────────────────────────────────────────────────

class TestTa06:

    def test_sucesso(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_novo_tipo_anestesia(_ctx(runner), observer=None)
        assert step.success is True

    def test_nao_validado_sem_confirm_template(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_novo_tipo_anestesia(_ctx(runner), observer=None)
        assert step.validated is None

    def test_clica_botao_novo_tipo_anestesia(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow()._step_novo_tipo_anestesia(_ctx(runner), observer=None)
        runner._page.locator.assert_any_call(
            "button, a", has_text="Novo Tipo Anestesia"
        )


# ──────────────────────────────────────────────────────────────────────────────
# TA07 — Preencher formulario
# ──────────────────────────────────────────────────────────────────────────────

class TestTa07:

    def test_sucesso(self):
        runner = _runner_ok()
        step = TipoAnestesiaFlow()._step_preencher_formulario(_ctx(runner), _dados(), observer=None)
        assert step.success is True

    def test_step_id(self):
        runner = _runner_ok()
        step = TipoAnestesiaFlow()._step_preencher_formulario(_ctx(runner), _dados(), observer=None)
        assert step.step_id == "TA07"

    def test_preenche_codigo_e_descricao(self):
        runner = _runner_ok()
        TipoAnestesiaFlow()._step_preencher_formulario(_ctx(runner), _dados(), observer=None)
        campo = runner._page.locator.return_value.first
        chamadas = [str(c) for c in campo.fill.call_args_list]
        assert any("AB12" in c for c in chamadas)
        assert any("TESTE VTAE ANESTESIA" in c for c in chamadas)

    def test_seleciona_tipo_anestesia(self):
        runner = _runner_ok()
        TipoAnestesiaFlow()._step_preencher_formulario(_ctx(runner), _dados(), observer=None)
        campo = runner._page.locator.return_value.first
        campo.select_option.assert_called_once_with(label="Geral")

    def test_falha_se_codigo_ausente(self):
        runner = _runner_ok()
        dados = {k: v for k, v in _dados().items() if k != "codigo"}
        step = TipoAnestesiaFlow()._step_preencher_formulario(_ctx(runner), dados, observer=None)
        assert step.success is False
        assert "codigo" in step.error

    def test_falha_se_descricao_ausente(self):
        runner = _runner_ok()
        dados = {k: v for k, v in _dados().items() if k != "descricao"}
        step = TipoAnestesiaFlow()._step_preencher_formulario(_ctx(runner), dados, observer=None)
        assert step.success is False
        assert "descricao" in step.error

    def test_falha_se_tipo_anestesia_ausente(self):
        runner = _runner_ok()
        dados = {k: v for k, v in _dados().items() if k != "tipo_anestesia"}
        step = TipoAnestesiaFlow()._step_preencher_formulario(_ctx(runner), dados, observer=None)
        assert step.success is False
        assert "tipo_anestesia" in step.error

    def test_usa_frame_quando_formulario_esta_em_iframe(self):
        runner = _runner_ok()
        frame_sem_form = MagicMock()
        frame_sem_form.locator.return_value.count.return_value = 0
        frame_com_form = MagicMock()
        frame_com_form.locator.return_value.count.return_value = 3
        runner._page.frames = [frame_sem_form, frame_com_form]

        step = TipoAnestesiaFlow()._step_preencher_formulario(_ctx(runner), _dados(), observer=None)

        assert step.success is True
        # o campo codigo deve ter sido preenchido no frame, nao na pagina principal
        campo_frame = frame_com_form.locator.return_value.first
        chamadas = [str(c) for c in campo_frame.fill.call_args_list]
        assert any("AB12" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# TA08 — Confirmar + validar na grade
# ──────────────────────────────────────────────────────────────────────────────

class TestTa08:

    def test_sucesso_com_codigo(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_confirmar(_ctx(runner), _dados(), observer=None)
        assert step.success is True

    def test_validated_true(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            step = TipoAnestesiaFlow()._step_confirmar(_ctx(runner), _dados(), observer=None)
        assert step.validated is True

    def test_clica_botao_confirmar(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow()._step_confirmar(_ctx(runner), _dados(), observer=None)
        runner._page.locator.assert_any_call(
            "button:has-text('Confirmar'), input[value='Confirmar']"
        )
        runner._page.locator.return_value.first.click.assert_called_once()

    def test_verifica_registro_na_grade_quando_codigo_presente(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper") as mock_apex:
            TipoAnestesiaFlow()._step_confirmar(_ctx(runner), _dados(), observer=None)
        mock_apex.verificar_registro_na_grade.assert_called_once_with(
            runner, texto="AB12", seletor_tabela=".t-Report-report table, table"
        )

    def test_nao_verifica_grade_quando_codigo_vazio(self):
        runner = _runner_ok()
        dados = {**_dados(), "codigo": ""}
        with patch(f"{MODULE}.ApexHelper") as mock_apex:
            step = TipoAnestesiaFlow()._step_confirmar(_ctx(runner), dados, observer=None)
        assert step.success is True
        mock_apex.verificar_registro_na_grade.assert_not_called()

    def test_falha_quando_registro_nao_encontrado_na_grade(self):
        runner = _runner_ok()
        with patch(f"{MODULE}.ApexHelper") as mock_apex:
            mock_apex.verificar_registro_na_grade.side_effect = AssertionError(
                "Texto 'AB12' não encontrado na grade."
            )
            step = TipoAnestesiaFlow()._step_confirmar(_ctx(runner), _dados(), observer=None)
        assert step.success is False
        assert "não encontrado na grade" in step.error


# ──────────────────────────────────────────────────────────────────────────────
# Abort on failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_ta01_nao_executa_demais_steps(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        result = _run(runner)
        ids = [s.step_id for s in result.steps]
        assert ids == ["TA01"]

    def test_falha_ta07_interrompe_antes_de_ta08(self):
        dados = {k: v for k, v in _dados().items() if k != "codigo"}
        result = _run(dados=dados)
        ids = [s.step_id for s in result.steps]
        assert ids == ["TA01", "TA02", "TA03", "TA04", "TA05", "TA06", "TA07"]

    def test_observer_notificado_para_todos_steps_ok(self):
        observer = MagicMock()
        with patch(f"{MODULE}.ApexHelper"):
            TipoAnestesiaFlow().execute(_ctx(), dados=_dados(), observer=observer)
        assert observer.log_step_start.call_count == 8
        observer.log_flow_result.assert_called_once()
