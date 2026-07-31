"""
Smoke tests do ExecutionObserver — vtae/report/observer.py

Estratégia: isola tudo que toca disco/SO de verdade.
  - _coletar_ambiente() é mockado (ctypes.windll/xrandr variam por SO
    e não são determinísticos em CI).
  - base_dir=tmp_path isola evidence_dir (execution.log/json/report.html).
  - monkeypatch.chdir(tmp_path) isola evidence/flakiness.json, que é
    hardcoded relativo ao cwd em _atualizar_flakiness — não usa
    self.evidence_dir, então precisa desse isolamento à parte.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from vtae.core.context import FlowContext
from vtae.runners.base_runner import BaseRunner
from vtae.core.result import CausaFalha, FlowResult, StepResult
from vtae.report.observer import ExecutionObserver


AMBIENTE_FAKE = {
    "hostname": "host-teste",
    "os": "TesteOS 1.0",
    "python": "3.13.0",
    "resolucao": "1920x1080",
}


def _novo_ctx():
    """FlowContext isolado — usado quando um teste precisa de mais de um."""
    runner = MagicMock(spec=BaseRunner)
    return FlowContext(runner=runner, evidence_dir="evidence/test/")


@pytest.fixture(autouse=True)
def mock_ambiente():
    """Evita ctypes.windll/xrandr reais — determinístico em qualquer SO."""
    with patch("vtae.report.observer._coletar_ambiente", return_value=AMBIENTE_FAKE):
        yield


@pytest.fixture
def observer(tmp_path, monkeypatch):
    """
    ExecutionObserver isolado: cwd vira tmp_path, cobrindo tanto o
    evidence_dir parametrizável quanto o path fixo "evidence/flakiness.json".
    """
    monkeypatch.chdir(tmp_path)
    return ExecutionObserver(test_name="smoke_test", base_dir="evidence")


# ──────────────────────────────────────────────────────────────────────────────
# __init__ / inject_logger
# ──────────────────────────────────────────────────────────────────────────────

class TestInicializacao:

    def test_cria_evidence_dir(self, observer):
        assert os.path.isdir(observer.evidence_dir)

    def test_cria_arquivo_de_log(self, observer):
        assert os.path.exists(observer._log_path)

    def test_inject_logger_seta_logger_no_ctx(self, observer, ctx):
        observer.inject_logger(ctx)
        assert ctx._logger is observer._logger


# ──────────────────────────────────────────────────────────────────────────────
# Logging direto (sem passar por report())
# ──────────────────────────────────────────────────────────────────────────────

class TestLogging:

    def test_log_step_result_ok_escreve_status(self, observer):
        step = StepResult(step_id="L01", success=True, duration_ms=42.0)
        observer.log_step_result(step)
        conteudo = open(observer._log_path, encoding="utf-8").read()
        assert "L01" in conteudo
        assert "OK" in conteudo

    def test_log_step_result_falha_escreve_causa(self, observer):
        step = StepResult(
            step_id="A01", success=False, duration_ms=30.0,
            error="Timeout", causa_falha=CausaFalha.TIMEOUT,
        )
        observer.log_step_result(step)
        conteudo = open(observer._log_path, encoding="utf-8").read()
        assert "FALHOU" in conteudo
        assert "timeout" in conteudo

    def test_log_flow_result_nao_lanca_excecao(self, observer):
        result = FlowResult(flow_name="LoginFlow", steps=[
            StepResult(step_id="L01", success=True, duration_ms=10.0),
        ])
        observer.log_flow_result(result)  # não deve lançar


# ──────────────────────────────────────────────────────────────────────────────
# report() — caso feliz
# ──────────────────────────────────────────────────────────────────────────────

class TestReport:

    def test_execution_json_status_passou(self, observer, ctx):
        step = StepResult(step_id="L01", success=True, duration_ms=100.0)
        ctx.add_result(FlowResult(flow_name="LoginFlow", steps=[step]))

        observer.report(ctx)

        data = json.loads(open(observer._json_path, encoding="utf-8").read())
        assert data["status"] == "PASSOU"
        assert data["summary"]["total_steps"] == 1
        assert data["summary"]["failed_steps"] == 0

    def test_execution_json_status_falhou(self, observer, ctx):
        passou = StepResult(step_id="L01", success=True, duration_ms=100.0)
        falhou = StepResult(
            step_id="A01", success=False, duration_ms=50.0,
            error="Elemento nao encontrado",
            causa_falha=CausaFalha.TEMPLATE_NAO_ENCONTRADO,
        )
        ctx.add_result(FlowResult(flow_name="LoginFlow", steps=[passou]))
        ctx.add_result(FlowResult(flow_name="AdmissaoFlow", steps=[falhou]))

        observer.report(ctx)

        data = json.loads(open(observer._json_path, encoding="utf-8").read())
        assert data["status"] == "FALHOU"
        assert data["summary"]["failed_steps"] == 1

    def test_gera_report_html(self, observer, ctx):
        """Integração real observer -> report_generator, sem mock."""
        step = StepResult(step_id="L01", success=True, duration_ms=100.0)
        ctx.add_result(FlowResult(flow_name="LoginFlow", steps=[step]))

        html_path = observer.report(ctx)

        assert os.path.exists(html_path)


# ──────────────────────────────────────────────────────────────────────────────
# flakiness.json — acúmulo entre execuções
# ──────────────────────────────────────────────────────────────────────────────

class TestFlakiness:

    def test_primeira_execucao_registra_pass_count(self, observer, ctx):
        step = StepResult(step_id="L01", success=True, duration_ms=100.0)
        ctx.add_result(FlowResult(flow_name="LoginFlow", steps=[step]))

        observer.report(ctx)

        historico = json.loads(
            open("evidence/flakiness.json", encoding="utf-8").read()
        )
        assert historico["L01"]["pass_count"] == 1
        assert historico["L01"]["fail_count"] == 0

    def test_segunda_execucao_acumula(self, tmp_path, monkeypatch):
        """Duas rodadas seguidas — confere que pass_count/fail_count somam
        entre execuções. Antes deste teste, _atualizar_flakiness não tinha
        nenhuma cobertura."""
        monkeypatch.chdir(tmp_path)

        obs1 = ExecutionObserver(test_name="smoke_1", base_dir="evidence")
        ctx1 = _novo_ctx()
        ctx1.add_result(FlowResult(
            flow_name="LoginFlow",
            steps=[StepResult(step_id="L01", success=True, duration_ms=100.0)],
        ))
        obs1.report(ctx1)

        obs2 = ExecutionObserver(test_name="smoke_2", base_dir="evidence")
        ctx2 = _novo_ctx()
        ctx2.add_result(FlowResult(
            flow_name="LoginFlow",
            steps=[StepResult(
                step_id="L01", success=False, duration_ms=50.0,
                error="falhou dessa vez",
            )],
        ))
        obs2.report(ctx2)

        historico = json.loads(
            open("evidence/flakiness.json", encoding="utf-8").read()
        )
        assert historico["L01"]["pass_count"] == 1
        assert historico["L01"]["fail_count"] == 1
        assert historico["L01"]["total_execucoes"] == 2
