# tests/integration/jornadas/ambulatorio/test_02_admissao_ambulatorio.py
"""
test_02 — Admissao Ambulatorial
Jornada: ambulatorio — Fase 5c

Pre-requisito:
  test_01 (CadastroPacienteFlow) deve ter rodado e gerado
  evidence/estado_jornada.json com paciente_id preenchido.

Execucao isolada:
  vtae run --test admissao_ambulatorio_jornada

Execucao na jornada completa:
  vtae run --jornada ambulatorio
"""
import pathlib

import pytest

from src.config.loader import ConfigLoader
from src.core.context import FlowContext
from src.core.observer import ExecutionObserver
from src.flows.si3.login_flow import LoginFlow
from src.flows.si3.admissao_ambulatorio_flow import AdmissaoAmbulatorioFlow
from src.runners.opencv_runner import OpenCVRunner


def test_admissao_ambulatorio_jornada():
    config = ConfigLoader.carregar(
        "si3_ambulatorio",
        configs_dir=pathlib.Path("configs/si3")
    )

    observer = ExecutionObserver(test_name="test_admissao_ambulatorio_jornada")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    # Login
    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    # Admissao Ambulatorial — le paciente_id do estado_jornada.json
    result = AdmissaoAmbulatorioFlow().execute(
        ctx,
        dados=config.DADOS,
        observer=observer,
    )
    try:
     observer.report(ctx)
     ctx.print_summary()
    except Exception as e:
       print(f"[WARNING] Erro ao gerar relatorio: {e}")

    assert result.success, f"Admissao Ambulatorial falhou: {result.failed_steps}"