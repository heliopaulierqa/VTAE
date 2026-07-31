from vtae.config import ConfigLoader
from vtae.core.context import FlowContext
from vtae.report.observer import ExecutionObserver
from vtae.flows.sislab.login.login_flow_sislab import LoginFlowSisLab
from vtae.runners.opencv_runner import OpenCVRunner


def test_login_sislab():
    """
    Testa o login do SisLab via OpenCV.
    Com o SisLab aberto e maximizado na tela de login.
    """
    config = ConfigLoader.carregar("sislab")

    observer = ExecutionObserver(test_name="test_login_sislab")
    runner = OpenCVRunner(confidence=config.confidence)
    ctx = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )
    observer.inject_logger(ctx)

    result = LoginFlowSisLab().execute(ctx, observer=observer)
    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Login falhou: {result.failed_steps}"
