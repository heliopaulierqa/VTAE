"""
Componente reutilizável — CadastroFuncionario (SisLab)

Encapsula o fluxo completo de cadastro de funcionário no SisLab:
  - preencher_formulario(ctx, observer, dados) → FlowResult

Invocável via DSL YAML:
    - action: run_component
      name: sislab.cadastro_funcionario_component.preencher_formulario
      args:
        dados: <<DADOS>>
"""

from __future__ import annotations

from src.core.result import FlowResult


def preencher_formulario(ctx, observer=None, dados: dict | None = None) -> FlowResult:
    """
    Preenche o formulário de cadastro de funcionário no SisLab.
    Assume que o sistema está aberto e o formulário de novo funcionário está visível.

    Args:
        ctx:      FlowContext com runner, config e evidence_dir.
        observer: ExecutionObserver opcional.
        dados:    Dict com os campos do funcionário. Se None, usa ctx.config.DADOS.
    """
    from src.flows.sislab.cadastro_funcionario_flow_sislab import CadastroFuncionarioFlow

    if dados is None:
        dados = getattr(ctx.config, "DADOS", {}) or {}

    result = CadastroFuncionarioFlow().execute(ctx, dados=dados, observer=observer)
    return result
