from vtae.flows.login_flow import LoginFlow


def test_login_flow_retorna_resultado(ctx):
    result = LoginFlow().execute(ctx)
    assert result.flow_name == "LoginFlow"
    assert len(result.steps) == 1


def test_login_flow_step_l01_sucesso(ctx):
    result = LoginFlow().execute(ctx)
    step = result.steps[0]
    assert step.step_id == "L01"
    assert step.success is True
    assert step.duration_ms >= 0


def test_login_flow_captura_screenshot(ctx, mock_runner):
    LoginFlow().execute(ctx)
    mock_runner.screenshot.assert_called_once()


def test_login_flow_usa_credenciais_do_contexto(ctx):
    assert ctx.user == "admin"
    assert ctx.password == "123"


def test_login_flow_adiciona_resultado_ao_contexto(ctx):
    LoginFlow().execute(ctx)
    assert ctx.all_passed() is True
