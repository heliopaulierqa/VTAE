from vtae.core.result import StepResult, FlowResult


def test_step_result_sucesso_str():
    step = StepResult(step_id="L01", success=True, duration_ms=120.5)
    assert "✅" in str(step)
    assert "L01" in str(step)


def test_step_result_falha_str():
    step = StepResult(step_id="A01", success=False, duration_ms=50.0, error="Timeout")
    assert "❌" in str(step)
    assert "Timeout" in str(step)


def test_flow_result_sucesso():
    result = FlowResult(flow_name="LoginFlow")
    result.steps.append(StepResult("L01", True, 100.0))
    assert result.success is True
    assert result.total_duration_ms == 100.0


def test_flow_result_falha_parcial():
    result = FlowResult(flow_name="AdmissaoFlow")
    result.steps.append(StepResult("A01", True, 80.0))
    result.steps.append(StepResult("A02", False, 30.0, error="Elemento não encontrado"))
    assert result.success is False
    assert len(result.failed_steps) == 1


def test_flow_result_summary_contem_nome():
    result = FlowResult(flow_name="SuprimentosFlow")
    result.steps.append(StepResult("S01", True, 90.0))
    assert "SuprimentosFlow" in result.summary()
