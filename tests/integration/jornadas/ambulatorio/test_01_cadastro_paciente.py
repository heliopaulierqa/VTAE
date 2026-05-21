# tests/integration/jornadas/ambulatorio/test_01_cadastro_paciente.py
"""
Jornada Ambulatório — Passo 1: Cadastro do Paciente

Pré-requisitos:
  - SI3 aberto e maximizado
  - configs/si3/si3_cadastro_paciente/.env com:
      SI3_USER=seu_usuario
      SI3_PASS=sua_senha

Ao final salva a matrícula gerada em:
  evidence/estado_jornada.json → { "paciente_id": "XXXXXXX" }

Executar individualmente:
  vtae run --test cadastro_paciente_jornada

Executar como parte da jornada:
  vtae run --jornada ambulatorio
"""
import pathlib
import re
import time
from datetime import date

from faker import Faker

from src.config import ConfigLoader
from src.core.context import FlowContext
from src.core.observer import ExecutionObserver
from src.flows.si3.cadastro_paciente_flow import CadastroPacienteFlow
from src.flows.si3.login_flow import LoginFlow
from src.runners.opencv_runner import OpenCVRunner

_fake = Faker("pt_BR")


def _gerar_dados(config) -> dict:
    """Gera dados do paciente mesclando DADOS do config com campos extras."""
    dados = config.DADOS.copy()

    # Data de nascimento com idade controlada (Faker precisa de parâmetros)
    dob = _fake.date_of_birth(minimum_age=18, maximum_age=80)
    dados["data_nascimento"] = dob.strftime("%d/%m/%Y")
    dados["hora"] = "00:00"

    # mae e pai: config.yaml gera como 'nome_mae'/'nome_pai' — mapear para
    # as chaves que o flow usa ('mae'/'pai')
    if "mae" not in dados:
        dados["mae"] = dados.pop("nome_mae", _fake.name())
    if "pai" not in dados:
        dados["pai"] = dados.pop("nome_pai", _fake.name())

    dados.setdefault("nome_social", dados.get("nome", ""))
    dados.setdefault("conjuge",     "")
    dados.setdefault("responsavel", "")

    # Celular faker sem prefixo de país, formato: 1199999999
    #celular_raw = dados.get("celular", _fake.phone_number())
    #celular_sem_prefixo = re.sub(r'^\+?55\s*', '', celular_raw).strip()
    #celular_digits = re.sub(r'[^\d]', '', celular_sem_prefixo)
    #dados["celular"] = celular_digits[:10] if len(celular_digits) >= 10 else celular_sem_prefixo

    return dados


def test_cadastro_paciente_jornada():
    config = ConfigLoader.carregar(
        "si3_cadastro_paciente",
        configs_dir=pathlib.Path("configs/si3"),
    )
    observer = ExecutionObserver(test_name="test_cadastro_paciente_jornada")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    time.sleep(2)  # tempo para sair do terminal antes do flow começar

    # Login
    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    time.sleep(3)

    # Cadastro completo
    dados = _gerar_dados(config)
    result = CadastroPacienteFlow().execute(ctx, dados=dados, observer=observer)

    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Cadastro falhou: {result.failed_steps}"

    # Confirma que o estado_jornada.json foi gerado
    estado = pathlib.Path("evidence/estado_jornada.json")
    assert estado.exists(), "estado_jornada.json não foi criado — verifique CP22"

    import json
    conteudo = json.loads(estado.read_text(encoding="utf-8"))
    assert "paciente_id" in conteudo, "paciente_id não foi salvo no estado_jornada.json"
    print(f"\n✅ paciente_id salvo: {conteudo['paciente_id']}")
    print(f"   Próximo passo: vtae run --test admissao_ambulatorio_jornada\n")