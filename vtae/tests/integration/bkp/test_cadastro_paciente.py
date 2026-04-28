import time
import pytest
from faker import Faker
from vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.core.observer import ExecutionObserver
from vtae.configs.si3.login_config import LoginConfigSi3
from vtae.flows.login_flow import LoginFlow
from vtae.flows.cadastro_paciente_flow import CadastroPacienteFlow

fake = Faker("pt_BR")


def test_cadastro_paciente():
    """
    Cadastra um novo paciente no SI3 (Oracle Forms — Desktop).
    Usa Faker para gerar dados únicos a cada execução.
    """
    observer = ExecutionObserver(test_name="test_cadastro_paciente")
    runner = OpenCVRunner(confidence=0.8)
    ctx = FlowContext(
        runner=runner,
        config=LoginConfigSi3,
        evidence_dir=observer.evidence_dir,
    )

    # gera dados únicos para evitar duplicatas
    dados = {
        "nome": fake.name().upper(),
        "data_nascimento": fake.date_of_birth(
            minimum_age=18, maximum_age=80
        ).strftime("%d/%m/%Y"),
        "hora": "00:00",
        "sexo": "MASCULINO",
        "nacionalidade": "BRASILEIRO",
        "estado": "SAO PAULO",
        "cidade": "SAO PAULO",
        "cor_etnia": "PARDA",
        "mae": fake.name_female().upper(),
        "pai": fake.name_male().upper(),
        "cpf": fake.cpf(),
    }

    print(
        f"\n[FAKER] nome={dados['nome']} | "
        f"cpf={dados['cpf']} | "
        f"nascimento={dados['data_nascimento']}"
    )

    # login
    time.sleep(2)  # aguarda o menu carregar completamente
    login_result = LoginFlow().execute(ctx, observer=observer)
    assert login_result.success, f"Login falhou: {login_result.failed_steps}"

    time.sleep(5)  # aguarda o menu principal carregar

    # cadastro
    result = CadastroPacienteFlow().execute(
        ctx,
        dados=dados,
        observer=observer,
    )

    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Cadastro falhou: {result.failed_steps}"
