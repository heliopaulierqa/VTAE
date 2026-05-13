# vtae/tests/integration/si3/test_login_real.py
"""
Teste de integração — Login SI3

Pré-requisitos:
  - SI3 aberto e maximizado
  - vtae/configs/si3/si3_cadastro_paciente/.env com SI3_USER e SI3_PASS

Executar:
  vtae run --test login_si3
  python -m pytest vtae/tests/integration/si3/test_login_real.py -v -s
"""
import pathlib

from src.config import ConfigLoader
from vtae.core.observer import ExecutionObserver
from vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.flows.login_flow import LoginFlow


def test_login_real():
    config = ConfigLoader.carregar(
        "si3_cadastro_paciente",
        configs_dir=pathlib.Path("vtae/configs/si3"),
    )

    observer = ExecutionObserver(test_name="test_login_si3")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    result = LoginFlow().execute(ctx, observer=observer)

    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Login falhou: {result.failed_steps}"