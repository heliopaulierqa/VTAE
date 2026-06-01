# src/flows/msi3/tipo_anestesia_flow.py
"""
TipoAnestesiaFlow — MSI3 Oracle APEX (Web + OpenCV hibrido)
v0.5.10: esqueleto BaseFlow — implementar quando tiver acesso ao MSI3.

Historico:
  - Flow original perdido — recriado como esqueleto padrao
  - Quando tiver acesso ao MSI3, implementar os steps seguindo o mesmo
    padrao do FrequenciaAplicacaoFlow (navegacao Playwright + OpenCV)

Prefixo de steps: TA01, TA02, ...

Para implementar:
  1. Mapear os steps no sistema MSI3
  2. Capturar templates em templates/msi3/tipo_anestesia/
  3. Adicionar dados: no config.yaml (configs/msi3/msi3_tipo_anestesia/)
  4. Implementar cada _step_*() seguindo padrao do FrequenciaAplicacaoFlow
  5. Registrar no CLI: vtae run --test tipo_anestesia
  6. Validar 3x antes de considerar estavel
"""

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.flows.msi3.apex_helper import ApexHelper


class TipoAnestesiaFlow(BaseFlow):
    """
    Fluxo de cadastro de Tipo de Anestesia no MSI3.
    Pressupoe que o login ja foi executado via LoginFlowMsi3.

    PENDENTE: implementar steps quando tiver acesso ao MSI3.
    """

    FLOW_NAME = "TipoAnestesiaFlow"
    _TPL = "templates/msi3/tipo_anestesia"

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_ta01(ctx, observer),
            # Adicionar steps conforme mapeamento do sistema
        ]

        for step_fn in steps:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    # ----------------------------------------------------------------
    # TA01 — Esqueleto (substituir pela navegacao real)
    # ----------------------------------------------------------------

    def _step_ta01(self, ctx, observer=None):
        def fn():
            # TODO: implementar navegacao para Tipo de Anestesia no MSI3
            # Seguir padrao do FrequenciaAplicacaoFlow:
            #   FA01 Sistema de Pacientes → FA02 → FA03 → modulo especifico
            raise NotImplementedError(
                "TipoAnestesiaFlow nao implementado.\n"
                "Implementar quando tiver acesso ao MSI3.\n"
                "Ver frequencia_aplicacao_flow.py como referencia."
            )
        return self._step("TA01", "esqueleto — implementar com acesso ao MSI3",
                          fn, observer, ctx=ctx)