import pytest
from faker import Faker
from vtae.runners.playwright_runner import PlaywrightRunner
from vtae.core.context import FlowContext
from vtae.core.observer import ExecutionObserver
from vtae.configs.msi3.login_config import LoginConfigMsi3
from vtae.flows.login_flow_msi3 import LoginFlowMsi3
from vtae.flows.frequencia_aplicacao_flow import FrequenciaAplicacaoFlow

fake = Faker("pt_BR")


@pytest.fixture(scope="module")
def ctx_logado():
    """Login compartilhado entre todos os testes do módulo."""
    observer = ExecutionObserver(test_name="msi3_login_session")

    runner = PlaywrightRunner(url=LoginConfigMsi3.URL, headless=False)
    ctx = FlowContext(
        runner=runner,
        config=LoginConfigMsi3,
        evidence_dir=observer.evidence_dir,
    )

    result = LoginFlowMsi3().execute(ctx, observer=observer)
    observer.report(ctx)

    assert result.success, f"Login falhou — testes abortados: {result.failed_steps}"

    yield ctx

    runner.close()


def test_cadastro_frequencia_aplicacao(ctx_logado):
    """
    Cadastra uma nova Frequência de Aplicação no MSI3 com dados únicos.
    Usa Faker para gerar sequência, código e descrição únicos a cada execução.
    """
    observer = ExecutionObserver(test_name="test_cadastro_frequencia")

    # gera dados únicos para evitar registro duplicado
    sequencia = str(fake.random_int(min=100, max=9999))
    codigo = fake.bothify(text="??##").upper()
    descricao = f"TESTE VTAE {fake.bothify(text='????####').upper()}"

    print(f"\n[FAKER] sequencia={sequencia} | codigo={codigo} | descricao={descricao}")

    dados = {
        "sequencia": sequencia,
        "codigo": codigo,
        "descricao": descricao,
        "tipo_aplicacao": "Medicamento",
        "frequencia_tipo_unica": True,
        "qt_dias_semana": "6",
        "qt_24hs": "6",
        "intervalo_hrs": "24",
        "intervalo_min": "12",
        "hora": "12:00",
        "unidade_funcional": "SF - SV FARMACIA",
        "validar_unidade": "SF - SV FARMACIA",
    }

    result = FrequenciaAplicacaoFlow().execute(
        ctx_logado,
        dados=dados,
        observer=observer,
    )

    observer.report(ctx_logado)
    ctx_logado.print_summary()

    assert result.success, f"Fluxo falhou: {result.failed_steps}"
