# tests/unit/test_login_si3_flow.py
"""
Testes unitarios do LoginSi3Flow — 3 steps (L01-L03)
Migracao src/flows/si3/login/ -> vtae/flows/si3/login/

Gap fechado nesta migracao: LoginSi3Flow tinha gate de GUI fechado (3x,
22/06) mas NENHUM teste unitario (registrado como pendencia no projeto).

REGRAS (mesmo padrao de test_admissao_ambulatorio_flow.py):
  - mock_sleep autouse (conftest.py) elimina todos os time.sleep reais
  - L03 usa _clicar_aguardar (BaseFlow) — patch("os.path.exists",
    return_value=False) forca o caminho de FALLBACK (sem confirmacao
    visual, executa a acao 1x e retorna True) — mesmo padrao de
    bootstrap ja usado nos outros flows migrados. O caminho "com
    confirmacao" (os.path.exists=True) e testado a parte, isolado,
    espelhando os testes ja existentes de _clicar_aguardar em
    test_base_flow.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from vtae.flows.si3.login.login_si3_flow import LoginSi3Flow
from vtae.core.result import FlowResult


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _config():
    coordenadas = {
        "campo_usuario":  {"x": 200, "y": 150},
        "campo_senha":    {"x": 200, "y": 180},
        "btn_conectar":   {"x": 300, "y": 220},
    }
    config = MagicMock()
    config.coordenadas = coordenadas
    return config


def _dados():
    return {"usuario": "testuser", "senha": "testpass"}


def _runner_ok():
    runner = MagicMock()
    runner.screenshot.return_value = "evidence/step.png"
    runner.wait_template.return_value = True
    runner.type_text.return_value = None
    return runner


def _ctx(runner=None):
    ctx = MagicMock()
    ctx.runner = runner or _runner_ok()
    ctx.config = _config()
    ctx.evidence_dir = "evidence/"
    return ctx


def _run(runner=None, dados=None):
    """
    Bootstrap padrao: os.path.exists=False forca _clicar_aguardar (L03)
    pelo caminho de fallback (sem confirmacao visual) — mesma convencao
    ja usada nos flows de admissao migrados.
    """
    with patch("os.path.exists", return_value=False):
        return LoginSi3Flow().execute(_ctx(runner), dados=dados or _dados())


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert LoginSi3Flow.FLOW_NAME == "LoginSi3Flow"

    def test_execute_retorna_flow_result(self):
        assert isinstance(_run(), FlowResult)

    def test_execute_tem_3_steps(self):
        assert len(_run().steps) == 3

    def test_ids_corretos(self):
        ids = [s.step_id for s in _run().steps]
        assert ids == ["L01", "L02", "L03"]

    def test_todos_steps_passam_com_runner_ok(self):
        falhos = [s for s in _run().steps if not s.success]
        assert falhos == [], [f"{s.step_id}: {s.error}" for s in falhos]

    def test_flow_sucesso(self):
        assert _run().success is True

    def test_execute_chama_add_result(self):
        ctx = _ctx()
        with patch("os.path.exists", return_value=False):
            LoginSi3Flow().execute(ctx, dados=_dados())
        ctx.add_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# L01 — clicar no campo Usuario e digitar
# ──────────────────────────────────────────────────────────────────────────────

class TestL01:

    def test_sucesso(self):
        assert _run().steps[0].success is True

    def test_step_id(self):
        assert _run().steps[0].step_id == "L01"

    def test_digita_usuario(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("testuser" in c for c in chamadas)

    def test_clica_campo_usuario(self):
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch("pyautogui.click") as mock_click:
            LoginSi3Flow().execute(_ctx(runner), dados=_dados())
        assert (200, 150) in [c.args for c in mock_click.call_args_list]

    def test_falha_se_usuario_ausente_no_dados(self):
        dados = _dados()
        del dados["usuario"]
        result = _run(dados=dados)
        l01 = result.steps[0]
        assert l01.success is False
        assert "usuario" in l01.error.lower()


# ──────────────────────────────────────────────────────────────────────────────
# L02 — clicar no campo Senha e digitar
# ──────────────────────────────────────────────────────────────────────────────

class TestL02:

    def test_sucesso(self):
        assert _run().steps[1].success is True

    def test_step_id(self):
        assert _run().steps[1].step_id == "L02"

    def test_digita_senha(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("testpass" in c for c in chamadas)

    def test_clica_campo_senha(self):
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch("pyautogui.click") as mock_click:
            LoginSi3Flow().execute(_ctx(runner), dados=_dados())
        assert (200, 180) in [c.args for c in mock_click.call_args_list]

    def test_falha_se_senha_ausente_no_dados(self):
        dados = _dados()
        del dados["senha"]
        result = _run(dados=dados)
        l02 = result.steps[1]
        assert l02.success is False
        assert "senha" in l02.error.lower()


# ──────────────────────────────────────────────────────────────────────────────
# L03 — clicar em Conectar e confirmar menu principal (_clicar_aguardar)
# ──────────────────────────────────────────────────────────────────────────────

class TestL03:

    def test_sucesso_modo_bootstrap_sem_template(self):
        # os.path.exists=False -> _clicar_aguardar cai no fallback:
        # executa a acao 1x, sem exigir confirmacao visual.
        assert _run().steps[2].success is True

    def test_step_id(self):
        assert _run().steps[2].step_id == "L03"

    def test_validated_true(self):
        assert _run().steps[2].validated is True

    def test_clica_btn_conectar(self):
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch("pyautogui.click") as mock_click:
            LoginSi3Flow().execute(_ctx(runner), dados=_dados())
        assert (300, 220) in [c.args for c in mock_click.call_args_list]

    def test_confirma_via_wait_template_quando_arquivo_existe(self):
        # os.path.exists=True -> _clicar_aguardar exige confirmacao visual
        # via wait_template — runner_ok ja retorna True de primeira.
        runner = _runner_ok()
        with patch("os.path.exists", return_value=True):
            result = LoginSi3Flow().execute(_ctx(runner), dados=_dados())
        l03 = result.steps[2]
        assert l03.success is True
        runner.wait_template.assert_any_call(
            "templates/si3/login/caixa_mensagens_login.png",
            timeout=30, threshold=0.85,
        )

    def test_falha_apos_esgotar_retries_quando_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        with patch("os.path.exists", return_value=True):
            result = LoginSi3Flow().execute(_ctx(runner), dados=_dados())
        l03 = result.steps[2]
        assert l03.success is False
        assert "Tela nao confirmada" in l03.error


# ──────────────────────────────────────────────────────────────────────────────
# Abort on failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_l01_nao_executa_l02_nem_l03(self):
        dados = _dados()
        del dados["usuario"]
        result = _run(dados=dados)
        ids = [s.step_id for s in result.steps]
        assert ids == ["L01"]

    def test_falha_l02_nao_executa_l03(self):
        dados = _dados()
        del dados["senha"]
        result = _run(dados=dados)
        ids = [s.step_id for s in result.steps]
        assert ids == ["L01", "L02"]

    def test_observer_notificado_para_todos_steps_ok(self):
        observer = MagicMock()
        with patch("os.path.exists", return_value=False):
            LoginSi3Flow().execute(_ctx(), dados=_dados(), observer=observer)
        assert observer.log_step_start.call_count == 3
        observer.log_flow_result.assert_called_once()
