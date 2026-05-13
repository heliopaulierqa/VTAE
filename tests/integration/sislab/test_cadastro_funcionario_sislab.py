# vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py
"""
Teste de integração — Cadastro de Funcionário no SisLab.
Fluxo end-to-end: Login → Cadastro de Funcionário.

Pré-condições:
    - SisLab aberto e maximizado
    - Tela de login visível

Execução:
    python -m pytest vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py -v -s
"""
from vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.core.observer import ExecutionObserver
from vtae.flows.login_flow_sislab import LoginFlowSisLab
from vtae.flows.cadastro_funcionario_flow_sislab import CadastroFuncionarioFlowSislab
from src.config import ConfigLoader


def test_cadastro_funcionario_sislab():
    config   = ConfigLoader.carregar("sislab")
    observer = ExecutionObserver(test_name="test_cadastro_funcionario_sislab")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    # Login
    login_result = LoginFlowSisLab().execute(ctx, observer=observer)
    assert login_result.success, (
        f"Login falhou — abortando cadastro.\n"
        f"Steps com erro: {login_result.failed_steps}"
    )

    # Cadastro
    result = CadastroFuncionarioFlowSislab().execute(ctx, observer=observer)
    observer.report(ctx)

    assert result.success, (
        f"Cadastro de funcionário falhou.\n"
        f"Steps com erro: {result.failed_steps}\n"
        f"Dados usados: {config.DADOS}"
    )
