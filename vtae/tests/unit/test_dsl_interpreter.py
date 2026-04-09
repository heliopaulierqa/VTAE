import pytest
from vtae.dsl.interpreter import DSLInterpreter


def test_dsl_executa_login(ctx):
    interp = DSLInterpreter(ctx)
    interp.run({
        "flow": "login",
        "steps": [{"action": "login"}],
    })
    assert ctx.all_passed() is True


def test_dsl_executa_click(ctx):
    interp = DSLInterpreter(ctx)
    interp.run({
        "flow": "teste",
        "steps": [{"action": "click", "template": "templates/btn.png"}],
    })
    ctx.runner.safe_click.assert_called_with("templates/btn.png")


def test_dsl_executa_type(ctx):
    interp = DSLInterpreter(ctx)
    interp.run({
        "flow": "teste",
        "steps": [{"action": "type", "text": "hello"}],
    })
    ctx.runner.type_text.assert_called_with("hello")


def test_dsl_acao_invalida_levanta_erro(ctx):
    interp = DSLInterpreter(ctx)
    with pytest.raises(ValueError, match="Ação desconhecida"):
        interp.run({
            "flow": "teste",
            "steps": [{"action": "voar"}],
        })


def test_dsl_click_sem_template_levanta_erro(ctx):
    interp = DSLInterpreter(ctx)
    with pytest.raises(ValueError, match="template"):
        interp.run({
            "flow": "teste",
            "steps": [{"action": "click"}],
        })
