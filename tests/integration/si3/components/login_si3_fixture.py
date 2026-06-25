# tests/integration/si3/jornadas/cadastro_min/test_cadastro_paciente_min.py

import pathlib

from src.config import ConfigLoader
from src.core.context import FlowContext
from src.core.observer import ExecutionObserver
from src.flows.si3.login.login_si3_flow import LoginSi3Flow
from src.flows.si3.cadastro_min.cadastro_paciente_min_flow import CadastroPacienteMinFlow
from src.runners.opencv_runner import OpenCVRunner
from src.runners.browser_launcher import abrir_si3_navegador


def test_cadastro_paciente_min_flow():
    # ----------------------------------------------------------------
    # Config do cadastro — coordenadas, dados_faker, regioes_ocr
    # ----------------------------------------------------------------
    config = ConfigLoader.carregar(
        "si3_cadastro_paciente_min",
        configs_dir=pathlib.Path("configs/si3"),
    )

    # Config do login — credenciais e URL do SI3
    config_login = ConfigLoader.carregar(
        "si3_login",
        configs_dir=pathlib.Path("configs/si3"),
    )

    observer = ExecutionObserver(test_name="test_cadastro_paciente_min_flow")

    # Runner ANTES do browser_launcher — wait_template precisa dele
    runner = OpenCVRunner(confidence=config.confidence, ocr_engine=config.ocr_engine)

    # Abre o Edge e dispara o SI3 (janela nativa Oracle Forms)
    abrir_si3_navegador(url=config_login.url)

    # Confirmacao de carregamento via template — sem sleep fixo
    # threshold=0.75: score maximo real 0.79 (diagnose validado)
    ok = runner.wait_template(
        "templates/si3/login/popup_conexao.png",
        timeout=30,
        threshold=0.75,
    )
    if not ok:
        raise TimeoutError("SI3 nao abriu — popup Conexao nao detectado em 30s")

    ctx = FlowContext(runner=runner, config=config, evidence_dir=observer.evidence_dir)
    observer.inject_logger(ctx)  # obrigatorio desde v0.5.12

    # Login — reutiliza LoginSi3Flow com dados do config_login
    login = LoginSi3Flow().execute(ctx, dados=config_login.DADOS, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    # Cadastro minimo de paciente
    result = CadastroPacienteMinFlow().execute(ctx, dados=config.DADOS, observer=observer)

    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Cadastro falhou: {result.failed_steps}"