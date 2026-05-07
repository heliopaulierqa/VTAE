"""
Componente reutilizável — ApexForm (MSI3)

Componente genérico para preenchimento de formulários Oracle APEX.
Encapsula o padrão de acesso a frames dialog no MSI3.

Funções:
  - preencher_campos(ctx, observer, campos, frame_url)  → FlowResult
  - aguardar_sucesso(ctx, observer, timeout)            → FlowResult

Invocável via DSL YAML:
    - action: run_component
      name: msi3.apex_form_component.preencher_campos
      args:
        campos:
          - selector: "#P17_NOME"
            value: <<DADOS.nome>>
          - selector: "#P17_CARGO"
            value: <<DADOS.cargo>>
        frame_url: "f?p=152:19:"
"""

from __future__ import annotations

import time
from src.core.result import FlowResult, StepResult
from src.core.types import StepError


def preencher_campos(
    ctx,
    observer=None,
    campos: list[dict] | None = None,
    frame_url: str = "",
    **kwargs,
) -> FlowResult:
    """
    Preenche campos em um formulário APEX, inclusive dentro de frames dialog.

    Args:
        ctx:       FlowContext com runner Playwright e evidence_dir.
        observer:  ExecutionObserver opcional.
        campos:    Lista de dicts com 'selector' e 'value'.
                   Ex: [{"selector": "#P17_NOME", "value": "JOSE"}]
        frame_url: Fragmento de URL para identificar o frame dialog.
                   Ex: "f?p=152:19:" — se vazio, usa a página principal.
    """
    FLOW_NAME = "apex_form_component.preencher_campos"
    result = FlowResult(flow_name=FLOW_NAME)

    if not campos:
        return result

    page = ctx.runner._page

    for i, campo in enumerate(campos, 1):
        step_id = f"AFC{i:02d}"
        selector = campo.get("selector", "")
        value = campo.get("value", "")
        start = time.monotonic()

        if observer:
            observer.log_step_start(step_id, f"Preencher {selector}")

        try:
            if frame_url:
                frame = next(
                    (f for f in page.frames if frame_url in f.url),
                    None,
                )
                if frame is None:
                    raise StepError(
                        f"Frame com URL '{frame_url}' não encontrado. "
                        f"Frames disponíveis: {[f.url for f in page.frames]}"
                    )
                frame.locator(selector).fill(value)
            else:
                page.locator(selector).fill(value)

            shot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=shot)
        except StepError as exc:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(exc))
        except Exception as exc:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=f"[{type(exc).__name__}] {exc}")

        result.steps.append(step)
        if observer:
            observer.log_step_result(step)
        if not step.success:
            break

    ctx.add_result(result)
    if observer:
        observer.log_flow_result(result)
    return result


def aguardar_sucesso(
    ctx,
    observer=None,
    timeout: float = 10.0,
    selector: str = ".t-Alert--success",
    **kwargs,
) -> FlowResult:
    """
    Aguarda mensagem de sucesso em formulário APEX.

    Args:
        ctx:      FlowContext com runner Playwright.
        observer: ExecutionObserver opcional.
        timeout:  Tempo máximo de espera em segundos.
        selector: Seletor CSS da mensagem de sucesso APEX.
                  Default: '.t-Alert--success' (Universal Theme).
    """
    FLOW_NAME = "apex_form_component.aguardar_sucesso"
    result = FlowResult(flow_name=FLOW_NAME)
    step_id = "AFW01"
    start = time.monotonic()

    if observer:
        observer.log_step_start(step_id, f"Aguardar sucesso ({selector})")

    try:
        found = ctx.runner.wait_template(selector, timeout=timeout)
        shot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
        if not found:
            raise StepError(
                f"Mensagem de sucesso '{selector}' não encontrada após {timeout}s."
            )
        step = StepResult(step_id=step_id, success=True,
                          duration_ms=(time.monotonic() - start) * 1000,
                          screenshot_path=shot)
    except StepError as exc:
        step = StepResult(step_id=step_id, success=False,
                          duration_ms=(time.monotonic() - start) * 1000,
                          error=str(exc))
    except Exception as exc:
        step = StepResult(step_id=step_id, success=False,
                          duration_ms=(time.monotonic() - start) * 1000,
                          error=f"[{type(exc).__name__}] {exc}")

    result.steps.append(step)
    if observer:
        observer.log_step_result(step)
    ctx.add_result(result)
    if observer:
        observer.log_flow_result(result)
    return result
