# vtae/tests/integration/si3/test_admissao_internacao.py
"""
Teste de integração — Admissão de Internação (SI3)

Pré-requisitos:
  - SI3 aberto e maximizado
  - Login já realizado (ou usar a fixture abaixo que faz o login)
  - vtae/configs/si3_internacao/.env com:
      SI3_USER=seu_usuario
      SI3_PASS=sua_senha
      SI3_PACIENTE_ID=id_do_paciente_de_teste

Executar:
  vtae run --test admissao_internacao
  python -m pytest vtae/tests/integration/si3/test_admissao_internacao.py -v -s
"""

import pathlib
from src.config import ConfigLoader
from vtae.core.observer import ExecutionObserver
from vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.flows.login_flow import LoginFlow
from src.flows.si3.admissao_internacao_flow import AdmissaoInternacaoFlow


def test_admissao_internacao():
    # ── Config ────────────────────────────────────────────────────────
    config = ConfigLoader.carregar(
        "si3_internacao",
        configs_dir=pathlib.Path("vtae/configs/si3")
    )

    # ── Observer e Runner ─────────────────────────────────────────────
    observer = ExecutionObserver(test_name="test_admissao_internacao")
    runner = OpenCVRunner(confidence=config.confidence)

    # ── Contexto ──────────────────────────────────────────────────────
    ctx = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir
    )

    # ── Login ─────────────────────────────────────────────────────────
    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    # ── Admissão de Internação ────────────────────────────────────────
    result = AdmissaoInternacaoFlow().execute(
        ctx,
        dados=config.DADOS,
        observer=observer
    )

    # ── Relatório ─────────────────────────────────────────────────────
    observer.report(ctx)
    ctx.print_summary()

    # ── Asserção final ────────────────────────────────────────────────
    assert result.success, f"Admissão de Internação falhou: {result.failed_steps}"