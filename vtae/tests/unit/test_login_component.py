import pytest
from vtae.components.login_component import LoginComponent
from vtae.core.context import FlowContext


def test_login_component_executa_com_sucesso(ctx):
    result = LoginComponent().execute(ctx)
    assert result.success is True


def test_login_component_sem_credenciais_levanta_erro(mock_runner):
    ctx_sem_cred = FlowContext(runner=mock_runner)
    with pytest.raises(ValueError, match="credenciais"):
        LoginComponent().execute(ctx_sem_cred)
