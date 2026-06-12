# tests/integration/jornadas/ambulatorio_agendamento/test_02_agendamento.py
"""
Jornada Ambulatório com Agendamento — Passo 2: Agendamento

Pre-requisito:
  test_01 deve ter rodado e gerado evidence/estado_jornada.json
  com paciente_id preenchido.

Pré-requisitos do sistema:
  - SI3 aberto e maximizado na tela de Menu Principal
  - configs/si3/si3_agendamento/.env com SI3_USER e SI3_PASS

Ao final salva em evidence/estado_jornada.json:
  { "paciente_id": "...", "matricula": "...",
    "data_agendamento": "dd/mm/yyyy", "hora_agendamento": "HHMM" }

Executar individualmente:
  vtae run --test agendamento_jornada

Executar como parte da jornada:
  vtae run --jornada ambulatorio_agendamento
"""
import pathlib

from src.config.loader import ConfigLoader
from src.core.context import FlowContext
from src.core.observer import ExecutionObserver
from src.flows.si3.agendamento_flow import AgendamentoFlow
from src.flows.si3.login_flow import LoginFlow
from src.runners.opencv_runner import OpenCVRunner


def test_agendamento_jornada():
    config   = ConfigLoader.carregar(
        "si3_agendamento",
        configs_dir=pathlib.Path("configs/si3"),
    )
    observer = ExecutionObserver(test_name="test_agendamento_jornada")
    runner = OpenCVRunner(confidence=config.confidence, ocr_engine=config.ocr_engine)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    # Login
    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    # Agendamento
    result = AgendamentoFlow().execute(
        ctx,
        dados=config.DADOS,
        observer=observer,
    )

    try:
        observer.report(ctx)
        ctx.print_summary()
    except Exception as e:
        print(f"[WARNING] Erro ao gerar relatorio: {e}")

    assert result.success, f"Agendamento falhou: {result.failed_steps}"

    print("\n✅ Agendamento concluido")
    print("   Próximo passo: vtae run --test admissao_com_agendamento_jornada\n")