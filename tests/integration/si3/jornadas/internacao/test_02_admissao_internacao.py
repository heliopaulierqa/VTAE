# tests/integration/si3/jornadas/internacao/test_02_admissao_internacao.py
"""
Jornada Internação — Passo 2: Admissão de Internação

Pré-requisitos:
  test_01 deve ter rodado e gerado evidence/estado_jornada.json
  com paciente_id preenchido.

Pré-requisitos do sistema:
  - SI3 aberto e maximizado na tela de Menu Principal
  - configs/si3/si3_internacao/.env com SI3_USER e SI3_PASS

Executar individualmente:
  vtae run --test admissao_internacao_jornada

Executar como parte da jornada:
  vtae run --jornada internacao
"""
import pathlib

from src.config import ConfigLoader
from src.core.context import FlowContext
from src.core.observer import ExecutionObserver
from src.flows.si3.admissao_internacao_flow import AdmissaoInternacaoFlow
from src.flows.si3.login_flow import LoginFlow
from src.runners.opencv_runner import OpenCVRunner


def test_admissao_internacao_jornada():
    config   = ConfigLoader.carregar(
        "si3_internacao",
        configs_dir=pathlib.Path("configs/si3"),
    )
    observer = ExecutionObserver(test_name="test_admissao_internacao_jornada")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )
    observer.inject_logger(ctx)

    # Login
    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    # Admissão de internação
    result = AdmissaoInternacaoFlow().execute(
        ctx,
        dados=config.DADOS,
        observer=observer,
    )

    try:
        observer.report(ctx)
        ctx.print_summary()
    except Exception as e:
        print(f"[WARNING] Erro ao gerar relatório: {e}")

    assert result.success, f"Admissão de Internação falhou: {result.failed_steps}"

    print("\n✅ Admissão de internação concluída")
    print("   Jornada internacao completa: Cadastro → Admissão ✅\n")