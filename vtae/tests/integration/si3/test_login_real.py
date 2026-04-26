from vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.configs.si3.login_config import LoginConfigSi3
from vtae.flows.login_flow import LoginFlow
from vtae.core.observer import ExecutionObserver


def test_login_real():
    observer = ExecutionObserver(test_name="test_login_si3")

    runner = OpenCVRunner(confidence=0.8)
    ctx = FlowContext(
        runner=runner,
        config=LoginConfigSi3,
        evidence_dir=observer.evidence_dir,
    )

    result = LoginFlow().execute(ctx, observer=observer)

    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Login falhou: {result.failed_steps}"
