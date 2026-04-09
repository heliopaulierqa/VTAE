from vtae.flows.login_flow import LoginFlow
from vtae.flows.suprimentos_flow import SuprimentosFlow


def test_suprimentos_flow_retorna_resultado(ctx):
    result = SuprimentosFlow().execute(ctx)
    assert result.flow_name == "SuprimentosFlow"


def test_suprimentos_flow_tem_dois_steps(ctx):
    result = SuprimentosFlow().execute(ctx)
    assert len(result.steps) == 2


def test_suprimentos_flow_ids_corretos(ctx):
    result = SuprimentosFlow().execute(ctx)
    ids = [s.step_id for s in result.steps]
    assert ids == ["S01", "S02"]


def test_suprimentos_flow_sucesso(ctx):
    result = SuprimentosFlow().execute(ctx)
    assert result.success is True


def test_suprimentos_apos_login(ctx):
    LoginFlow().execute(ctx)
    result = SuprimentosFlow().execute(ctx)
    assert ctx.all_passed() is True
