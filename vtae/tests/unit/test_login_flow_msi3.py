"""
Testes unitários — LoginFlowMsi3 (MSI3)

Cobre os 5 steps do login web Oracle APEX.

Estratégia de mock:
  - ctx.runner mockado — PlaywrightRunner simulado
  - ctx.runner._page mockado — Playwright page simulado
  - ApexHelper mockado onde necessário

IDs: MW01..MW05
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_sleep():
    """Mocka time.sleep globalmente — elimina sleeps reais dos flows."""
    with patch("time.sleep"):
        yield


@pytest.fixture
def mock_page():
    page = MagicMock()
    page.url = "http://msi3/apex"
    page.frames = [MagicMock()]
    page.keyboard = MagicMock()
    return page


@pytest.fixture
def mock_runner(mock_page):
    runner = MagicMock()
    runner._page = mock_page
    runner.navigate.return_value = None
    runner.wait_template.return_value = True
    runner.fill.return_value = None
    runner.screenshot.return_value = "evidence/step.png"
    return runner


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.URL = "http://msi3/apex/login"
    config.CAMPO_USUARIO = "#P9999_USERNAME"
    config.CAMPO_SENHA = "#P9999_PASSWORD"
    config.TELA_PRINCIPAL = "h3.t-Card-title"
    return config


@pytest.fixture
def mock_ctx(mock_runner, mock_config):
    ctx = MagicMock()
    ctx.runner = mock_runner
    ctx.config = mock_config
    ctx.user = "usuario_teste"
    ctx.password = "senha_teste"
    ctx.evidence_dir = "evidence/test/"
    return ctx


@pytest.fixture
def flow():
    from vtae.flows.login_flow_msi3 import LoginFlowMsi3
    return LoginFlowMsi3()


# ---------------------------------------------------------------------------
# Estrutura do flow
# ---------------------------------------------------------------------------

class TestLoginFlowMsi3Estrutura:
    def test_flow_name_correto(self, flow):
        assert flow.FLOW_NAME == "LoginFlowMsi3"

    def test_execute_retorna_flow_result(self, flow, mock_ctx):
        from vtae.core.result import FlowResult
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"):
            result = flow.execute(mock_ctx)
        assert isinstance(result, FlowResult)

    def test_execute_tem_5_steps(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"):
            result = flow.execute(mock_ctx)
        assert len(result.steps) == 5

    def test_ids_corretos(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"):
            result = flow.execute(mock_ctx)
        ids = [s.step_id for s in result.steps]
        assert ids == ["MW01", "MW02", "MW03", "MW04", "MW05"]

    def test_chama_add_result(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"):
            flow.execute(mock_ctx)
        mock_ctx.add_result.assert_called_once()


# ---------------------------------------------------------------------------
# MW01 — Abrir página
# ---------------------------------------------------------------------------

class TestStepAbrirPagina:
    def test_mw01_navega_para_url_do_config(self, flow, mock_ctx):
        step = flow._step_abrir_pagina(mock_ctx)
        mock_ctx.runner.navigate.assert_called_once_with("http://msi3/apex/login")

    def test_mw01_aguarda_campo_usuario(self, flow, mock_ctx):
        flow._step_abrir_pagina(mock_ctx)
        mock_ctx.runner.wait_template.assert_called_with("#P9999_USERNAME", timeout=15.0)

    def test_mw01_sucesso(self, flow, mock_ctx):
        step = flow._step_abrir_pagina(mock_ctx)
        assert step.step_id == "MW01"
        assert step.success

    def test_mw01_falha_se_navigate_lanca_excecao(self, flow, mock_ctx):
        mock_ctx.runner.navigate.side_effect = Exception("conexão recusada")
        step = flow._step_abrir_pagina(mock_ctx)
        assert not step.success
        assert "conexão recusada" in step.error

    def test_mw01_falha_se_campo_usuario_nao_aparece(self, flow, mock_ctx):
        mock_ctx.runner.wait_template.side_effect = Exception("timeout 15s")
        step = flow._step_abrir_pagina(mock_ctx)
        assert not step.success


# ---------------------------------------------------------------------------
# MW02 — Usuário
# ---------------------------------------------------------------------------

class TestStepUsuario:
    def test_mw02_preenche_campo_usuario(self, flow, mock_ctx):
        step = flow._step_usuario(mock_ctx)
        mock_ctx.runner.fill.assert_called_once_with("#P9999_USERNAME", "usuario_teste")

    def test_mw02_sucesso(self, flow, mock_ctx):
        step = flow._step_usuario(mock_ctx)
        assert step.step_id == "MW02"
        assert step.success

    def test_mw02_falha_se_fill_lanca_excecao(self, flow, mock_ctx):
        mock_ctx.runner.fill.side_effect = Exception("seletor não encontrado")
        step = flow._step_usuario(mock_ctx)
        assert not step.success

    def test_mw02_tira_screenshot(self, flow, mock_ctx):
        flow._step_usuario(mock_ctx)
        mock_ctx.runner.screenshot.assert_called_once()


# ---------------------------------------------------------------------------
# MW03 — Senha
# ---------------------------------------------------------------------------

class TestStepSenha:
    def test_mw03_preenche_campo_senha(self, flow, mock_ctx):
        step = flow._step_senha(mock_ctx)
        mock_ctx.runner.fill.assert_called_once_with("#P9999_PASSWORD", "senha_teste")

    def test_mw03_sucesso(self, flow, mock_ctx):
        step = flow._step_senha(mock_ctx)
        assert step.step_id == "MW03"
        assert step.success

    def test_mw03_falha_se_fill_lanca_excecao(self, flow, mock_ctx):
        mock_ctx.runner.fill.side_effect = Exception("campo senha não encontrado")
        step = flow._step_senha(mock_ctx)
        assert not step.success


# ---------------------------------------------------------------------------
# MW04 — Submeter
# ---------------------------------------------------------------------------

class TestStepSubmeter:
    def test_mw04_pressiona_tab_tab_enter(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"):
            flow._step_submeter(mock_ctx)
        keyboard_calls = [c.args[0] for c in mock_ctx.runner._page.keyboard.press.call_args_list]
        assert keyboard_calls == ["Tab", "Tab", "Enter"]

    def test_mw04_sucesso(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"):
            step = flow._step_submeter(mock_ctx)
        assert step.step_id == "MW04"
        assert step.success

    def test_mw04_falha_se_apex_retorna_erro(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro",
                   side_effect=AssertionError("Credencial inválida")):
            step = flow._step_submeter(mock_ctx)
        assert not step.success
        assert "Credencial inválida" in step.error

    def test_mw04_chama_verificar_sem_erro(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro") as mock_check:
            flow._step_submeter(mock_ctx)
        mock_check.assert_called_once()

    def test_mw04_aguarda_networkidle(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"):
            flow._step_submeter(mock_ctx)
        mock_ctx.runner._page.wait_for_load_state.assert_called_once_with("networkidle")


# ---------------------------------------------------------------------------
# MW05 — Validar
# ---------------------------------------------------------------------------

class TestStepValidar:
    def test_mw05_sucesso_quando_tela_principal_aparece(self, flow, mock_ctx):
        mock_ctx.runner.wait_template.return_value = True
        with patch("vtae.flows.login_flow_msi3.ApexHelper.inspecionar_pagina"):
            step = flow._step_validar(mock_ctx)
        assert step.step_id == "MW05"
        assert step.success

    def test_mw05_falha_quando_tela_principal_nao_aparece(self, flow, mock_ctx):
        mock_ctx.runner.wait_template.return_value = False
        with patch("vtae.flows.login_flow_msi3.ApexHelper.inspecionar_pagina"):
            step = flow._step_validar(mock_ctx)
        assert not step.success

    def test_mw05_chama_inspecionar_pagina_em_falha(self, flow, mock_ctx):
        mock_ctx.runner.wait_template.return_value = False
        with patch("vtae.flows.login_flow_msi3.ApexHelper.inspecionar_pagina") as mock_insp:
            flow._step_validar(mock_ctx)
        mock_insp.assert_called_once()

    def test_mw05_aguarda_tela_principal_com_timeout_15s(self, flow, mock_ctx):
        mock_ctx.runner.wait_template.return_value = True
        with patch("vtae.flows.login_flow_msi3.ApexHelper.inspecionar_pagina"):
            flow._step_validar(mock_ctx)
        mock_ctx.runner.wait_template.assert_called_with(
            "h3.t-Card-title", timeout=15.0
        )


# ---------------------------------------------------------------------------
# Abort-on-failure
# ---------------------------------------------------------------------------

class TestAbortOnFailure:
    def test_falha_em_mw01_aborta_flow(self, flow, mock_ctx):
        mock_ctx.runner.navigate.side_effect = Exception("falha de rede")
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"):
            result = flow.execute(mock_ctx)
        assert not result.success
        assert len(result.steps) == 1

    def test_falha_em_mw04_executa_ate_mw04(self, flow, mock_ctx):
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro",
                   side_effect=AssertionError("credencial inválida")):
            result = flow.execute(mock_ctx)
        assert not result.success
        assert len(result.steps) == 4

    def test_flow_com_observer(self, flow, mock_ctx):
        observer = MagicMock()
        with patch("vtae.flows.login_flow_msi3.ApexHelper.verificar_sem_erro"), \
             patch("vtae.flows.login_flow_msi3.ApexHelper.inspecionar_pagina"):
            result = flow.execute(mock_ctx, observer)
        observer.log_flow_result.assert_called_once()
        assert observer.log_step_start.call_count == 5
        assert observer.log_step_result.call_count == 5
