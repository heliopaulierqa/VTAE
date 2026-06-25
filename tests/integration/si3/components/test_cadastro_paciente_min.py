# tests/integration/si3/components/test_cadastro_paciente_min.py

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
    # Dois configs separados — cada um com suas proprias coordenadas.
    # Contrato: NENHUMA coordenada hardcoded no fixture — tudo no YAML.
    # config_login : campo_usuario, campo_senha, btn_conectar, url
    # config       : coordenadas do formulario de cadastro, dados_faker
    # ----------------------------------------------------------------
    config_login = ConfigLoader.carregar(
        "si3_login",
        configs_dir=pathlib.Path("configs/si3"),
    )
    config = ConfigLoader.carregar(
        "si3_cadastro_paciente_min",
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

    # ctx_login: coordenadas do login (campo_usuario, campo_senha, btn_conectar)
    # Usar config_login aqui — LoginSi3Flow precisa das coordenadas do login
    ctx_login = FlowContext(
        runner=runner,
        config=config_login,
        evidence_dir=observer.evidence_dir,
    )
    observer.inject_logger(ctx_login)  # obrigatorio desde v0.5.12

    login = LoginSi3Flow().execute(ctx_login, dados=config_login.DADOS, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    # ctx: coordenadas do cadastro (campo_nome, campo_data_nasc, etc)
    # Usar config aqui — CadastroPacienteMinFlow precisa das coordenadas do formulario
    ctx = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    result = CadastroPacienteMinFlow().execute(ctx, dados=config.DADOS, observer=observer)

    observer.report(ctx)
    ctx.print_summary()

    assert result.success, f"Cadastro falhou: {result.failed_steps}"