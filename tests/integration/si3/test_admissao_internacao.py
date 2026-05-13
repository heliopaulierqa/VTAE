# vtae/tests/integration/si3/test_admissao_internacao.py
"""
Teste de integração — Admissão de Internação (SI3)

Pré-requisitos:
  - SI3 aberto e maximizado
  - vtae/configs/si3/si3_internacao/.env com:
      SI3_USER=seu_usuario
      SI3_PASS=sua_senha
      SI3_PACIENTE_ID=id_do_paciente_de_teste

Executar:
  vtae run --test admissao_internacao
  python -m pytest vtae/tests/integration/si3/test_admissao_internacao.py -v -s
"""
import pathlib
import time

from src.config import ConfigLoader
from src.core.observer import ExecutionObserver
from src.runners.opencv_runner import OpenCVRunner
from src.core.context import FlowContext
from src.flows.si3.login_flow import LoginFlow
from src.flows.si3.admissao_internacao_flow import AdmissaoInternacaoFlow


def test_admissao_internacao():
    config = ConfigLoader.carregar(
        "si3_internacao",
        configs_dir=pathlib.Path("configs/si3"),
    )

    observer = ExecutionObserver(test_name="test_admissao_internacao")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    time.sleep(2)
    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"
    time.sleep(5)

    result = AdmissaoInternacaoFlow().execute(
        ctx,
        dados=config.DADOS,
        observer=observer,
    )

    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Admissão de Internação falhou: {result.failed_steps}"

