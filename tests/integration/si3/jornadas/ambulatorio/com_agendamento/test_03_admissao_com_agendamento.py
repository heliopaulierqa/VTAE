# tests/integration/jornadas/ambulatorio_agendamento/test_03_admissao_com_agendamento.py
"""
Jornada Ambulatório com Agendamento — Passo 3: Admissão com Agendamento

Pre-requisitos:
  test_01 deve ter gerado evidence/estado_jornada.json com paciente_id
  test_02 deve ter gerado data_agendamento e hora_agendamento no estado_jornada.json

Pre-requisitos do sistema:
  - SI3 aberto e maximizado na tela de Menu Principal
  - configs/si3/si3_ambulatorio/.env com SI3_USER e SI3_PASS

Ao final salva em evidence/estado_jornada.json:
  { "paciente_id": "...", "matricula": "...",
    "data_agendamento": "...", "hora_agendamento": "...",
    "nr_admissao_ag": "..." }

Executar individualmente:
  vtae run --test admissao_com_agendamento_jornada

Executar como parte da jornada completa:
  vtae run --jornada ambulatorio_agendamento
"""
import pathlib

from src.config.loader import ConfigLoader
from src.core.context import FlowContext
from src.core.observer import ExecutionObserver
from src.flows.si3.admissao_com_agendamento_flow import AdmissaoComAgendamentoFlow
from src.flows.si3.login_flow import LoginFlow
from src.runners.opencv_runner import OpenCVRunner


def test_admissao_com_agendamento_jornada():
    config   = ConfigLoader.carregar(
        "si3_ambulatorio",
        configs_dir=pathlib.Path("configs/si3"),
    )
    observer = ExecutionObserver(test_name="test_admissao_com_agendamento_jornada")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )
    observer.inject_logger(ctx)

    # Login
    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    # Admissao com agendamento
    result = AdmissaoComAgendamentoFlow().execute(
        ctx,
        dados=config.DADOS,
        observer=observer,
    )

    try:
        observer.report(ctx)
        ctx.print_summary()
    except Exception as e:
        print(f"[WARNING] Erro ao gerar relatorio: {e}")

    assert result.success, f"Admissao com agendamento falhou: {result.failed_steps}"

    print("\n✅ Admissão com agendamento concluída")
    print("   Jornada ambulatorio_agendamento completa: "
          "Cadastro → Agendamento → Admissão ✅\n")