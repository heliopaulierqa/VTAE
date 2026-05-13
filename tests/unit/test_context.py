from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult


def test_context_credenciais_via_config(ctx):
    assert ctx.user == "admin"
    assert ctx.password == "admin123"


def test_context_credenciais_via_dict(mock_runner):
    ctx = FlowContext(
        runner=mock_runner,
        credentials={"user": "outro_user", "password": "outra_senha"},
    )
    assert ctx.user == "outro_user"
    assert ctx.password == "outra_senha"


def test_context_credenciais_dict_tem_prioridade(mock_runner):
    """credentials= tem prioridade sobre config=."""
    class _Config:
        USER     = "admin"
        PASSWORD = "admin123"

    ctx = FlowContext(
        runner=mock_runner,
        config=_Config,
        credentials={"user": "override"},
    )
    assert ctx.user == "override"


def test_context_all_passed_sem_resultados(ctx):
    assert ctx.all_passed() is True


def test_context_all_passed_com_falha(ctx):
    result = FlowResult(flow_name="TestFlow")
    result.steps.append(StepResult("X01", False, 10.0, error="falhou"))
    ctx.add_result(result)
    assert ctx.all_passed() is False