# vtae/tests/integration/msi3/test_tipo_anestesia.py
"""
Teste de integracao — Cadastro de Tipo de Anestesia no MSI3.

Pre-condicoes:
    - Browser aberto com MSI3 logado (LoginFlowMsi3 executado antes)

Execucao:
    python -m pytest vtae/tests/integration/msi3/test_tipo_anestesia.py -v -s
"""
import time
from faker import Faker
from vtae.runners.playwright_runner import PlaywrightRunner
from vtae.core.context import FlowContext
from vtae.core.observer import ExecutionObserver
from vtae.configs.msi3.login_config import LoginConfigMsi3
from vtae.flows.login_flow_msi3 import LoginFlowMsi3
from vtae.flows.tipo_anestesia_flow import TipoAnestesiaFlow

fake = Faker("pt_BR")


def test_tipo_anestesia():
    # ── login ──────────────────────────────────────────────
    login_observer = ExecutionObserver(test_name="msi3_login_session")
    runner = PlaywrightRunner(
        url=LoginConfigMsi3.URL,
        headless=False,
    )
    login_ctx = FlowContext(
        runner=runner,
        config=LoginConfigMsi3,
        evidence_dir=login_observer.evidence_dir,
    )
    login_result = LoginFlowMsi3().execute(login_ctx, observer=login_observer)
    login_observer.report(login_ctx)
    assert login_result.success, f"Login falhou: {login_result.failed_steps}"

    # ── dados dinamicos ────────────────────────────────────
    dados = {
        "codigo":         fake.bothify(text="###"),
        "tipo_anestesia": fake.random_element(["Geral", "Regional"]),
        "descricao":      f"TESTE VTAE {fake.bothify(text='????####').upper()}",
    }
    print(
        f"\n[FAKER] codigo={dados['codigo']} | "
        f"tipo={dados['tipo_anestesia']} | "
        f"descricao={dados['descricao']}"
    )

    # ── cadastro ───────────────────────────────────────────
    observer = ExecutionObserver(test_name="test_tipo_anestesia")
    ctx = FlowContext(
        runner=runner,       # reutiliza a sessao do login
        config=LoginConfigMsi3,
        evidence_dir=observer.evidence_dir,
    )

    result = TipoAnestesiaFlow().execute(ctx, dados=dados, observer=observer)
    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Fluxo falhou: {result.failed_steps}"
