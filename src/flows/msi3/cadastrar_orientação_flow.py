# src/flows/msi3/cadastrar_orientacao_flow.py
"""
CadastrarOrientacaoFlow — MSI3 Oracle APEX (Web + OpenCV hibrido)
v0.5.10: esqueleto BaseFlow com import corrigido.

Mudancas vs versao anterior:
  - BUG CORRIGIDO: import ApexHelper de src.core.apex_helper
    -> corrigido para src.flows.msi3.apex_helper
  - herda BaseFlow
  - estrutura de execute() corrigida (estava fora da classe)

Pendente: implementar os steps OR01-OR07 quando tiver acesso ao MSI3.

Steps planejados:
    OR01 — Sistema de Pacientes
    OR02 — Cadastros Basicos
    OR03 — Orientacao (OpenCV)
    OR04 — Cadastrar Nova Orientacao (OpenCV)
    OR05 — Preencher codigo da orientacao
    OR06 — Preencher orientacao
    OR07 — Clicar em Salvar
"""

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
# CORRIGIDO: import correto do ApexHelper
from src.flows.msi3.apex_helper import ApexHelper


class CadastrarOrientacaoFlow(BaseFlow):
    """
    Fluxo de cadastro de Orientacao no MSI3.
    Pressupoe que o login ja foi executado via LoginFlowMsi3.

    PENDENTE: implementar steps quando tiver acesso ao MSI3.
    Ver FrequenciaAplicacaoFlow como referencia de implementacao.
    """

    FLOW_NAME = "CadastrarOrientacaoFlow"
    _TPL = "templates/msi3/orientacao"

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_or01(ctx, observer),
            # Adicionar OR02-OR07 conforme mapeamento do sistema
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
    # OR01 — Esqueleto (substituir pela navegacao real)
    # ----------------------------------------------------------------

    def _step_or01(self, ctx, observer=None):
        def fn():
            raise NotImplementedError(
                "CadastrarOrientacaoFlow nao implementado.\n"
                "Implementar quando tiver acesso ao MSI3.\n"
                "Ver frequencia_aplicacao_flow.py como referencia."
            )
        return self._step("OR01", "esqueleto — implementar com acesso ao MSI3",
                          fn, observer, ctx=ctx)