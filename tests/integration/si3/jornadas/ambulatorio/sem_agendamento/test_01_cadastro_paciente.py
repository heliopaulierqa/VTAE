# tests/integration/si3/jornadas/ambulatorio/com_agendamento/test_01_cadastro_paciente.py
"""
Jornada Ambulatório com Agendamento — Passo 1: Cadastro do Paciente

Pré-requisitos:
  - SI3 aberto e maximizado na tela de Menu Principal
  - configs/si3/si3_cadastro_paciente/.env com SI3_USER e SI3_PASS

Modo automático (padrão):
  SI3_PACIENTE_ID= (vazio) → cadastra novo paciente

Modo manual (reutilizar paciente existente):
  SI3_PACIENTE_ID=505050 no .env → pula o cadastro
  ATENÇÃO: limpe após o teste para não afetar outras execuções.

Executar individualmente:
  vtae run --test cadastro_paciente_jornada

Executar como parte da jornada:
  vtae run --jornada ambulatorio_com_agendamento
"""
from tests.integration.si3.components.cadastro_paciente_fixture import executar_cadastro


def test_cadastro_paciente_jornada():
    executar_cadastro(
        proximo_passo="vtae run --test agendamento_jornada",
        test_name="test_cadastro_paciente_jornada",
    )