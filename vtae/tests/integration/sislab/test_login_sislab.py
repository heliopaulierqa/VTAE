from vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.core.observer import ExecutionObserver
from vtae.configs.sislab.login_config import LoginConfigSisLab
from vtae.flows.login_flow_sislab import LoginFlowSisLab


def test_login_sislab():
    """
    Testa o login do SisLab via OpenCV.
    Com o SisLab aberto e maximizado na tela de login.
    """
    observer = ExecutionObserver(test_name="test_login_sislab")
    runner = OpenCVRunner(confidence=0.8)
    ctx = FlowContext(
        runner=runner,
        config=LoginConfigSisLab,
        evidence_dir=observer.evidence_dir,
    )

    result = LoginFlowSisLab().execute(ctx, observer=observer)
    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Login falhou: {result.failed_steps}"
