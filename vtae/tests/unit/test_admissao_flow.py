from vtae.flows.login_flow import LoginFlow
from vtae.flows.admissao_flow import AdmissaoFlow


def test_admissao_flow_retorna_resultado(ctx):
    result = AdmissaoFlow().execute(ctx)
    assert result.flow_name == "AdmissaoFlow"


def test_admissao_flow_tem_dois_steps(ctx):
    result = AdmissaoFlow().execute(ctx)
    assert len(result.steps) == 2


def test_admissao_flow_ids_corretos(ctx):
    result = AdmissaoFlow().execute(ctx)
    ids = [s.step_id for s in result.steps]
    assert ids == ["A01", "A02"]


def test_admissao_flow_sucesso(ctx):
    result = AdmissaoFlow().execute(ctx)
    assert result.success is True


def test_admissao_apos_login(ctx):
    LoginFlow().execute(ctx)
    result = AdmissaoFlow().execute(ctx)
    assert ctx.all_passed() is True
