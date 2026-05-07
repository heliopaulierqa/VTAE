"""
Componente reutilizável — CadastroPaciente (SI3)

Encapsula o fluxo completo de cadastro de paciente no SI3:
  - preencher_formulario(ctx, observer, dados) → FlowResult
  - salvar_e_sair(ctx, observer)               → FlowResult

Invocável via DSL YAML:
    - action: run_component
      name: si3.cadastro_paciente_component.preencher_formulario
      args:
        dados: <<DADOS>>
"""

from __future__ import annotations

from src.core.result import FlowResult, StepResult
from src.core.types import StepError


def preencher_formulario(ctx, observer=None, dados: dict | None = None) -> FlowResult:
    """
    Preenche o formulário de cadastro de paciente no SI3.
    Assume que o sistema está aberto e o formulário de novo paciente está visível.

    Args:
        ctx:      FlowContext com runner, config e evidence_dir.
        observer: ExecutionObserver opcional.
        dados:    Dict com os campos do paciente. Se None, usa ctx.config.DADOS.
    """
    from src.flows.si3.cadastro_paciente_flow import CadastroPacienteFlow

    if dados is None:
        dados = getattr(ctx.config, "DADOS", {}) or {}

    result = CadastroPacienteFlow().execute(ctx, dados=dados, observer=observer)
    return result


def salvar_e_sair(ctx, observer=None, **kwargs) -> FlowResult:
    """
    Executa a sequência de saída após cadastro: salva e retorna ao menu principal.
    Útil como step final após preencher_formulario.

    Args:
        ctx:      FlowContext com runner, config e evidence_dir.
        observer: ExecutionObserver opcional.
    """
    import time
    import pyautogui

    FLOW_NAME = "salvar_e_sair"
    result = FlowResult(flow_name=FLOW_NAME)

    steps_fns = [
        lambda: _step_salvar(ctx, observer),
        lambda: _step_confirmar(ctx, observer),
        lambda: _step_menu_principal(ctx, observer),
    ]

    for fn in steps_fns:
        step = fn()
        result.steps.append(step)
        if observer:
            observer.log_step_result(step)
        if not step.success:
            break

    ctx.add_result(result)
    if observer:
        observer.log_flow_result(result)
    return result


def _step_salvar(ctx, observer) -> StepResult:
    import time
    step_id = "SAI01"
    if observer:
        observer.log_step_start(step_id, "Salvar cadastro")
    import time as _t
    start = _t.monotonic()
    try:
        ctx.runner.safe_click("templates/si3/btn_salvar.png")
        shot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
        return StepResult(step_id=step_id, success=True,
                          duration_ms=(_t.monotonic() - start) * 1000,
                          screenshot_path=shot)
    except Exception as exc:
        return StepResult(step_id=step_id, success=False,
                          duration_ms=(_t.monotonic() - start) * 1000,
                          error=str(exc))


def _step_confirmar(ctx, observer) -> StepResult:
    import time as _t
    step_id = "SAI02"
    if observer:
        observer.log_step_start(step_id, "Confirmar salvamento")
    start = _t.monotonic()
    try:
        import pyautogui
        pyautogui.press("enter")
        _t.sleep(0.5)
        shot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
        return StepResult(step_id=step_id, success=True,
                          duration_ms=(_t.monotonic() - start) * 1000,
                          screenshot_path=shot)
    except Exception as exc:
        return StepResult(step_id=step_id, success=False,
                          duration_ms=(_t.monotonic() - start) * 1000,
                          error=str(exc))


def _step_menu_principal(ctx, observer) -> StepResult:
    import time as _t
    step_id = "SAI03"
    if observer:
        observer.log_step_start(step_id, "Retornar ao menu principal")
    start = _t.monotonic()
    try:
        ctx.runner.safe_click("templates/si3/menu_principal.png")
        shot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
        return StepResult(step_id=step_id, success=True,
                          duration_ms=(_t.monotonic() - start) * 1000,
                          screenshot_path=shot)
    except Exception as exc:
        return StepResult(step_id=step_id, success=False,
                          duration_ms=(_t.monotonic() - start) * 1000,
                          error=str(exc))
