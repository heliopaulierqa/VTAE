from vtae.flows.login_flow import LoginFlow


def test_login_flow_retorna_resultado(ctx):
    result = LoginFlow().execute(ctx)
    assert result.flow_name == "LoginFlow"
    assert len(result.steps) == 3  # L01, L02, L03


def test_login_flow_step_l01_sucesso(ctx):
    result = LoginFlow().execute(ctx)
    step = result.steps[0]
    assert step.step_id == "L01"
    assert step.success is True
    assert step.duration_ms >= 0


def test_login_flow_captura_screenshot(ctx, mock_runner):
    LoginFlow().execute(ctx)
    # 3 steps → 3 screenshots (L01, L02, L03)
    assert mock_runner.screenshot.call_count == 3


def test_login_flow_usa_credenciais_do_contexto(ctx):
    # credenciais vêm do MockConfig definido no conftest.py
    assert ctx.user == "admin"
    assert ctx.password == "admin123"


def test_login_flow_adiciona_resultado_ao_contexto(ctx):
    LoginFlow().execute(ctx)
    assert ctx.all_passed() is True