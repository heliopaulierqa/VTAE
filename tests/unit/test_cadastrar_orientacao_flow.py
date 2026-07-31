# tests/unit/test_cadastrar_orientacao_flow.py
"""
Testes unitarios do CadastrarOrientacaoFlow — 1 step (OR01)
Migracao src/flows/msi3/cadastrar_orientação_flow.py ->
vtae/flows/msi3/cadastro_orientacao/cadastrar_orientacao_flow.py
(arquivo renomeado sem acento na migracao — nenhuma mudanca de logica)

Este flow e um ESQUELETO INTENCIONAL — OR01 sempre lanca
NotImplementedError, aguardando acesso ao MSI3 para implementar os
steps reais (OR01-OR07). Os testes aqui confirmam esse comportamento
de placeholder, nao uma jornada completa.

Nenhum teste unitario existia ate esta migracao.
"""

from unittest.mock import MagicMock

import pytest

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult
from vtae.flows.msi3.cadastro_orientacao.cadastrar_orientacao_flow import (
    CadastrarOrientacaoFlow,
)


def _ctx(runner=None):
    return FlowContext(
        runner=runner or MagicMock(),
        config=MagicMock(),
        evidence_dir="evidence/",
    )


def _run(dados=None):
    return CadastrarOrientacaoFlow().execute(_ctx(), dados=dados or {})


class TestEstrutura:

    def test_flow_name_correto(self):
        assert CadastrarOrientacaoFlow.FLOW_NAME == "CadastrarOrientacaoFlow"

    def test_execute_retorna_flow_result(self):
        assert isinstance(_run(), FlowResult)

    def test_execute_tem_1_step(self):
        assert len(_run().steps) == 1

    def test_flow_sempre_falha(self):
        # Esqueleto intencional — OR01 sempre lanca NotImplementedError
        assert _run().success is False

    def test_execute_chama_add_result(self):
        ctx = _ctx()
        CadastrarOrientacaoFlow().execute(ctx, dados={})
        assert ctx.all_passed() is False


class TestOr01:

    def test_step_id(self):
        assert _run().steps[0].step_id == "OR01"

    def test_falha_com_not_implemented(self):
        step = _run().steps[0]
        assert step.success is False
        assert "nao implementado" in step.error.lower()

    def test_observer_notificado(self):
        observer = MagicMock()
        CadastrarOrientacaoFlow().execute(_ctx(), dados={}, observer=observer)
        observer.log_step_start.assert_called_once_with(
            "OR01", "esqueleto — implementar com acesso ao MSI3"
        )
        observer.log_flow_result.assert_called_once()
