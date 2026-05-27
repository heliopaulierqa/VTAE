# tests/integration/jornadas/ambulatorio/test_01_cadastro_paciente.py
"""
Jornada Ambulatório — Passo 1: Cadastro do Paciente

Pré-requisitos:
  - SI3 aberto e maximizado na tela de Menu Principal
  - configs/si3/si3_cadastro_paciente/.env com SI3_USER e SI3_PASS

Ao final salva em evidence/estado_jornada.json:
  { "paciente_id": "XXXXXXX", "matricula": "XXXXXXXX-X" }

Executar individualmente:
  vtae run --test cadastro_paciente_jornada

Executar como parte da jornada:
  vtae run --jornada ambulatorio
  vtae run --jornada ambulatorio --repeat 3
"""
from tests.integration.components.cadastro_paciente_fixture import executar_cadastro


def test_cadastro_paciente_jornada():
    executar_cadastro(
        proximo_passo="vtae run --test admissao_ambulatorio_jornada",
        test_name="test_cadastro_paciente_jornada",
    )