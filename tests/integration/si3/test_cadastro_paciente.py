# vtae/tests/integration/si3/test_cadastro_paciente.py
"""
Teste de integração — Cadastro de Paciente (SI3)

Pré-requisitos:
  - SI3 aberto e maximizado
  - vtae/configs/si3/si3_cadastro_paciente/.env com SI3_USER e SI3_PASS

Executar:
  vtae run --test cadastro_paciente
  python -m pytest vtae/tests/integration/si3/test_cadastro_paciente.py -v -s

Nota: dados gerados via Faker manual — date_of_birth requer parâmetros
(minimum_age, maximum_age) que o ConfigLoader não suporta via YAML.
"""
import pathlib
import time
from faker import Faker

from src.config import ConfigLoader
from src.core.observer import ExecutionObserver
from src.runners.opencv_runner import OpenCVRunner
from src.core.context import FlowContext
from src.flows.si3.login_flow import LoginFlow
from src.flows.si3.cadastro_paciente_flow import CadastroPacienteFlow

fake = Faker("pt_BR")


def test_cadastro_paciente():
    config = ConfigLoader.carregar(
        "si3_cadastro_paciente",
        configs_dir=pathlib.Path("configs/si3"),
    )

    observer = ExecutionObserver(test_name="test_cadastro_paciente")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    # Faker manual — necessário por parâmetros específicos do date_of_birth
    dados = {
        "nome":            fake.name().upper(),
        "nome_social":     "",
        "data_nascimento": fake.date_of_birth(
                               minimum_age=18, maximum_age=80
                           ).strftime("%d/%m/%Y"),
        "hora":            "00:00",
        "sexo":            "M",
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

    time.sleep(2)
    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"
    time.sleep(5)

    result = CadastroPacienteFlow().execute(ctx, dados=dados, observer=observer)
    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Cadastro falhou: {result.failed_steps}"