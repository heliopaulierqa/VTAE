# tests/integration/msi3/jornadas/anestesia_pre_operatorio/test_tipo_anestesia.py
"""
Teste de integracao — Cadastro de Tipo de Anestesia no MSI3.

Pre-condicoes:
    - MSI3 acessivel via browser (PlaywrightRunner)
    - Credenciais em configs/msi3/msi3_tipo_anestesia/.env

Execucao:
    vtae run --test tipo_anestesia
"""
import pathlib

import pytest
from faker import Faker

from src.config.loader import ConfigLoader
from src.core.context import FlowContext
from src.core.observer import ExecutionObserver
from src.flows.msi3.login_flow_msi3 import LoginFlowMsi3
from src.flows.msi3.tipo_anestesia_flow import TipoAnestesiaFlow
from src.runners.playwright_runner import PlaywrightRunner

fake = Faker("pt_BR")


@pytest.fixture(scope="module")
def ctx_logado():
    """Login compartilhado entre todos os testes do modulo."""
    config = ConfigLoader.carregar(
        "msi3_tipo_anestesia",
        configs_dir=pathlib.Path("configs/msi3"),
    )

    observer = ExecutionObserver(test_name="msi3_login_session")
    runner = PlaywrightRunner(url=config.url, headless=False)
    ctx = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    observer.inject_logger(ctx)

    result = LoginFlowMsi3().execute(ctx, observer=observer)
    observer.report(ctx)

    assert result.success, f"Login falhou — testes abortados: {result.failed_steps}"

    yield ctx

    runner.close()


def test_cadastro_tipo_anestesia(ctx_logado):
    """
    Cadastra um novo Tipo de Anestesia no MSI3 com dados unicos via Faker.
    Valida que o registro aparece na grade apos confirmar.
    """
    observer = ExecutionObserver(test_name="test_cadastro_tipo_anestesia")

    codigo    = fake.bothify(text="??##").upper()
    descricao = f"TESTE VTAE {fake.bothify(text='????####').upper()}"
    tipo      = fake.random_element(["Geral", "Regional"])

    print(
        f"\n[FAKER] codigo={codigo} | "
        f"descricao={descricao} | "
        f"tipo_anestesia={tipo}"
    )

    dados = {
        "codigo":         codigo,
        "descricao":      descricao,
        "tipo_anestesia": tipo,
    }

    result = TipoAnestesiaFlow().execute(
        ctx_logado,
        dados=dados,
        observer=observer,
    )

    observer.report(ctx_logado)
    ctx_logado.print_summary()

    assert result.success, f"Fluxo falhou: {result.failed_steps}"