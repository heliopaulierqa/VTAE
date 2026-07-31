# tests/unit/test_login_flow_sislab.py
"""
Testes unitarios do LoginFlowSisLab — 3 steps (L01-L03)
Migracao src/flows/sislab/login_flow_sislab.py -> vtae/flows/sislab/login/

Estrutura identica ao LoginFlow do SI3 (mesmo padrao de BaseFlow, ctx.user/
ctx.password), so muda o diretorio de templates (templates/sislab/login/).
Nenhum teste unitario existia ate esta migracao.
"""

from unittest.mock import MagicMock, patch

import pytest

from vtae.core.context import FlowContext
from vtae.flows.sislab.login.login_flow_sislab import LoginFlowSisLab
from vtae.core.result import FlowResult


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _runner_ok():
    runner = MagicMock()
    runner.screenshot.return_value = "evidence/step.png"
    runner.safe_click.return_value = True
    runner.type_text.return_value = None
    return runner


def _ctx(runner=None):
    config = MagicMock()
    config.USER = "testuser"
    config.PASSWORD = "testpass"
    return FlowContext(runner=runner or _runner_ok(), config=config, evidence_dir="evidence/")


def _run(runner=None):
    return LoginFlowSisLab().execute(_ctx(runner))


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert LoginFlowSisLab.FLOW_NAME == "LoginFlowSisLab"

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
        LoginFlowSisLab().execute(ctx)
        assert ctx.all_passed() is True


# ──────────────────────────────────────────────────────────────────────────────
# L01 — clicar no campo Usuario e digitar
# ──────────────────────────────────────────────────────────────────────────────

class TestL01:

    def test_sucesso(self):
        assert _run().steps[0].success is True

    def test_step_id(self):
        assert _run().steps[0].step_id == "L01"

    def test_clica_campo_usuario(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call("templates/sislab/login/campo_usuario.png")

    def test_digita_usuario_do_contexto(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("testuser" in c for c in chamadas)

    def test_falha_se_safe_click_lanca_excecao(self):
        runner = _runner_ok()

        def _safe_click(tpl, *args, **kwargs):
            if "campo_usuario.png" in tpl:
                raise Exception("template nao encontrado")
            return True

        runner.safe_click.side_effect = _safe_click
        result = _run(runner)
        assert result.steps[0].success is False
        assert len(result.steps) == 1


# ──────────────────────────────────────────────────────────────────────────────
# L02 — clicar no campo Senha e digitar
# ──────────────────────────────────────────────────────────────────────────────

class TestL02:

    def test_sucesso(self):
        assert _run().steps[1].success is True

    def test_step_id(self):
        assert _run().steps[1].step_id == "L02"

    def test_clica_campo_senha(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call("templates/sislab/login/campo_senha.png")

    def test_digita_senha_do_contexto(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("testpass" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# L03 — clicar em Entrar
# ──────────────────────────────────────────────────────────────────────────────

class TestL03:

    def test_sucesso(self):
        assert _run().steps[2].success is True

    def test_step_id(self):
        assert _run().steps[2].step_id == "L03"

    def test_clica_btn_entrar(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call("templates/sislab/login/btn_entrar.png")


# ──────────────────────────────────────────────────────────────────────────────
# Abort on failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_l01_nao_executa_l02_nem_l03(self):
        runner = _runner_ok()

        def _safe_click(tpl, *args, **kwargs):
            if "campo_usuario.png" in tpl:
                raise Exception("template nao encontrado")
            return True

        runner.safe_click.side_effect = _safe_click
        result = _run(runner)
        ids = [s.step_id for s in result.steps]
        assert ids == ["L01"]

    def test_observer_notificado_para_todos_steps_ok(self):
        observer = MagicMock()
        LoginFlowSisLab().execute(_ctx(), observer=observer)
        assert observer.log_step_start.call_count == 3
        observer.log_flow_result.assert_called_once()
