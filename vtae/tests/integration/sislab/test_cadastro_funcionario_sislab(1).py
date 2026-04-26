# vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py
"""
Teste de integração — Cadastro de Funcionário no SisLab.

Pré-condições:
    - SisLab aberto e maximizado
    - Usuário já autenticado (rodou test_login_sislab.py antes,
      ou chame LoginFlowSislab aqui se preferir um teste end-to-end)

Execução:
    python -m pytest vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py -v -s
"""
from vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.core.observer import ExecutionObserver
from vtae.configs.sislab.cadastro_funcionario_config import CadastroFuncionarioConfigSislab
from vtae.flows.cadastro_funcionario_flow_sislab import CadastroFuncionarioFlowSislab


def test_cadastro_funcionario_sislab():
    observer = ExecutionObserver(test_name="test_cadastro_funcionario_sislab")
    runner   = OpenCVRunner(confidence=0.8)
    ctx      = FlowContext(
        runner=runner,
        config=CadastroFuncionarioConfigSislab,
        evidence_dir=observer.evidence_dir,
    )

    result = CadastroFuncionarioFlowSislab().execute(ctx, observer=observer)
    observer.report(ctx)

    assert result.success, (
        f"Cadastro de funcionário falhou.\n"
        f"Steps com erro: {result.failed_steps}\n"
        f"Dados usados: {CadastroFuncionarioConfigSislab.DADOS}"
    )
