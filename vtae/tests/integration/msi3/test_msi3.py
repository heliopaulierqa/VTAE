import pytest
from vtae.runners.playwright_runner import PlaywrightRunner
from vtae.core.context import FlowContext
from vtae.core.observer import ExecutionObserver
from vtae.configs.msi3.login_config import LoginConfigMsi3
from vtae.flows.login_flow_msi3 import LoginFlowMsi3


# ──────────────────────────────────────────────
# Fixture compartilhada — reusa o login em todos
# os testes deste arquivo sem fazer login de novo
# ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def ctx_logado():
    """
    Fixture que faz login uma vez e compartilha o contexto
    com todos os testes do módulo.

    Uso em qualquer teste:
        def test_qualquer(ctx_logado):
            # já está logado, só continuar
            ctx_logado.runner.safe_click("seletor_do_proximo_passo")
    """
    observer = ExecutionObserver(test_name="msi3_session")

    with PlaywrightRunner(
        url=LoginConfigMsi3.URL,
        headless=False,
    ) as runner:
        ctx = FlowContext(
            runner=runner,
            config=LoginConfigMsi3,
            evidence_dir=observer.evidence_dir,
        )

        result = LoginFlowMsi3().execute(ctx, observer=observer)
        observer.report(ctx)

        assert result.success, f"Login falhou — testes abortados: {result.failed_steps}"

        yield ctx  # todos os testes recebem o ctx já logado


# ──────────────────────────────────────────────
# Testes
# ──────────────────────────────────────────────

def test_login_msi3():
    """Teste isolado — faz login e valida."""
    observer = ExecutionObserver(test_name="test_login_msi3")

    with PlaywrightRunner(url=LoginConfigMsi3.URL, headless=False) as runner:
        ctx = FlowContext(
            runner=runner,
            config=LoginConfigMsi3,
            evidence_dir=observer.evidence_dir,
        )

        result = LoginFlowMsi3().execute(ctx, observer=observer)
        observer.report(ctx)
        ctx.print_summary()

        assert result.success, f"Login falhou: {result.failed_steps}"


def test_exemplo_reuso(ctx_logado):
    """
    Exemplo de teste que REUTILIZA o login.
    O ctx_logado já está autenticado — só continuar com os próximos steps.
    Substitua o conteúdo pelo seu fluxo real.
    """
    observer = ExecutionObserver(test_name="test_exemplo_reuso")

    # a partir daqui o usuário já está logado no MSI3
    # exemplo: navegar para outra página
    ctx_logado.runner.navigate(
        "https://lebombo.incor.usp.br:8443/apex_protot/r/paciente/home"
    )
    ctx_logado.runner.screenshot(f"{observer.evidence_dir}home.png")

    observer.report(ctx_logado)
