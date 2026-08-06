# tests/integration/si3/conftest.py
"""
Fixture si3 — peca 5 do motor (Projeto v1.1 Fase 2).

Aposenta o boot manual do test_cadastro_min_motor.py (PROVISORIO, que
morre quando este arquivo nasce). Contrato do teste de producao:

    def test_cadastro_paciente_min(si3):
        resultado = si3.executar("flows/si3/cadastro_min.yaml")
        assert resultado.success

Escopo module: abre o SI3 e loga uma vez por ARQUIVO de teste — jornadas
encadeadas (varios si3.executar() na mesma sessao) e testes soltos no
mesmo arquivo reusam a mesma janela ja logada.
"""
import pathlib
import time

import pytest

from vtae.config import ConfigLoader
from vtae.core.context import FlowContext
from vtae.core.motor.executor import Executor
from vtae.core.motor.plano import carregar
from vtae.core.object_repository import ObjectRepository
from vtae.flows.si3.login.login_flow import LoginFlow
from vtae.report.observer import ExecutionObserver
from vtae.runners.browser_launcher import abrir_si3_navegador
from vtae.runners.jab_reader import LeitorJab
from vtae.runners.opencv_runner import OpenCVRunner

CONFIGS_DIR = pathlib.Path("configs/si3")
TPL_CONEXAO = "templates/si3/login/popup_conexao.png"
TIMEOUT_SI3_ABRIR = 30
PAUSA_POS_LOGIN = 3.0

class SessaoSi3:
    def __init__(self, nome_modulo: str):
        self._nome_modulo = nome_modulo
        self._logado = False
        self._observer = None
        self._runner = None

    def executar(self, caminho_yaml: str):
        plano = carregar(caminho_yaml)
        config = ConfigLoader.carregar(f"si3_{plano.flow}", configs_dir=CONFIGS_DIR)

        if self._observer is None:
            self._observer = ExecutionObserver(test_name=self._nome_modulo)
        if self._runner is None:
            self._runner = OpenCVRunner(confidence=config.confidence,
                                        ocr_engine=config.ocr_engine)
        if not self._logado:
            self._logar(config)

        ctx = FlowContext(runner=self._runner, config=config,
                          evidence_dir=self._observer.evidence_dir)
        self._observer.inject_logger(ctx)
        leitor = self._montar_leitor(plano, config)

        try:
            resultado = Executor(ctx, observer=self._observer,
                                 leitor_exato=leitor).executar(caminho_yaml)
        finally:
            self._observer.report(ctx)
            ctx.print_summary()
        return resultado
    

    def _logar(self, config):
        config_login = ConfigLoader.carregar("si3_login", configs_dir=CONFIGS_DIR)
        abrir_si3_navegador(url=config_login.url)
        if not self._runner.wait_template(TPL_CONEXAO, timeout=TIMEOUT_SI3_ABRIR,
                                          threshold=0.75):
            raise TimeoutError(
                f"SI3 nao abriu — popup Conexao nao detectado em "
                f"{TIMEOUT_SI3_ABRIR}s.")

        ctx_login = FlowContext(runner=self._runner, config=config,
                                evidence_dir=self._observer.evidence_dir)
        self._observer.inject_logger(ctx_login)
        login = LoginFlow().execute(ctx_login, observer=self._observer)
        if not login.success:
            raise AssertionError(f"Login falhou: {login.failed_steps}")
        time.sleep(PAUSA_POS_LOGIN)
        self._logado = True

    def _montar_leitor(self, plano, config):
        titulo = ObjectRepository.from_yaml(plano.objetos).titulo_jab()
        if titulo is None:
            return None
        return LeitorJab(titulo=titulo, jab_home=config.DADOS.get("jab_home_fake"))
    

@pytest.fixture(scope="module")
def si3(request):
    yield SessaoSi3(nome_modulo=request.module.__name__.rsplit(".", 1)[-1])    