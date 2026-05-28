# tests/integration/si3/jornadas/internacao/test_01_cadastro_paciente.py
"""
Jornada Internação — Passo 1: Cadastro do Paciente

Pré-requisitos:
  - SI3 aberto e maximizado na tela de Menu Principal
  - configs/si3/si3_cadastro_paciente/.env com SI3_USER e SI3_PASS

Ao final salva em evidence/estado_jornada.json:
  { "paciente_id": "XXXXXXX", "matricula": "XXXXXXXX-X" }

Modo automático (padrão):
  SI3_PACIENTE_ID= (vazio no .env) → cadastra novo paciente

Modo manual (reutilizar paciente existente):
  SI3_PACIENTE_ID=505050 no .env → pula o cadastro, usa o ID informado
  ATENÇÃO: limpe o SI3_PACIENTE_ID após o teste para não afetar outras execuções.

Executar individualmente:
  vtae run --test cadastro_paciente_internacao_jornada

Executar como parte da jornada:
  vtae run --jornada internacao
"""
from tests.integration.si3.components.cadastro_paciente_fixture import executar_cadastro


def test_cadastro_paciente_jornada():
    executar_cadastro(
        proximo_passo="vtae run --test admissao_internacao_jornada",
        test_name="test_cadastro_paciente_internacao_jornada",
    )