from vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.configs.sislab.login_config import LoginConfigSisLab
from vtae.flows.login_flow import LoginFlow
from vtae.core.observer import ExecutionObserver


def test_login_real():
    observer = ExecutionObserver(test_name="test_login_real")

    runner = OpenCVRunner(confidence=0.8)
    ctx = FlowContext(
        runner=runner,
        config=LoginConfigSisLab,
        evidence_dir=observer.evidence_dir,
    )

    result = LoginFlow().execute(ctx, observer=observer)

    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Login falhou: {result.failed_steps}"
