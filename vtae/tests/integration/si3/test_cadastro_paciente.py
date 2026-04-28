# vtae/tests/integration/test_cadastro_paciente.py
import time
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
    Cadastra um novo paciente no SI3 (Oracle Forms - Desktop).
    Usa Faker para gerar dados unicos a cada execucao.
    """
    observer = ExecutionObserver(test_name="test_cadastro_paciente")
    runner   = OpenCVRunner(confidence=0.8)
    ctx      = FlowContext(
        runner=runner,
        config=LoginConfigSi3,
        evidence_dir=observer.evidence_dir,
    )

    dados = {
        "nome":            fake.name().upper(),
        "nome_social":     "",          # opcional — preencher se necessario
        "data_nascimento": fake.date_of_birth(
                               minimum_age=18, maximum_age=80
                           ).strftime("%d/%m/%Y"),
        "hora":            "00:00",
        "sexo":            "M",         # M ou F — Oracle Forms aceita 1 char
        "nacionalidade":   "BRASILEIRA",
        "mae":             fake.name_female().upper(),
        "pai":             fake.name_male().upper(),
        "cor_etnia":       "PARDA",
        "cpf":             fake.cpf().replace(".", "").replace("-", ""),
    }

    print(
        f"\n[FAKER] nome={dados['nome']} | "
        f"cpf={dados['cpf']} | "
        f"nascimento={dados['data_nascimento']}"
    )

    # login
    time.sleep(2)
    login_result = LoginFlow().execute(ctx, observer=observer)
    assert login_result.success, f"Login falhou: {login_result.failed_steps}"
    time.sleep(5)

    # cadastro
    result = CadastroPacienteFlow().execute(
        ctx,
        dados=dados,
        observer=observer,
    )
    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Cadastro falhou: {result.failed_steps}"
