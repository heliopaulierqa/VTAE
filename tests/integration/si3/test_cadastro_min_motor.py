# tests/integration/si3/test_cadastro_min_motor.py
"""
PROVISORIO — o primeiro teste que poe o motor na tela real.

Mesma estrutura de boot do test_cadastro_paciente_min.py (familia A):
abre o SI3, confirma o carregamento por template, loga e so entao roda o
cadastro. A UNICA diferenca e o que roda o cadastro: aqui e o Executor
lendo flows/si3/cadastro_min.yaml, nao o CadastroPacienteMinFlow.

Este arquivo MORRE quando a fixture da peca 5 nascer (pendencia #6): ela
substitui todo o boot abaixo pelo teste de 3 linhas do v1.1 §4.

Pre-requisitos:
  - SI3 FECHADO (o teste abre) — ou aberto, que o login roda por cima
  - configs/si3/si3_login/.env e configs/si3/si3_cadastro_paciente_min/.env
    com SI3_USER e SI3_PASS

Executar:
  pytest tests/integration/si3/test_cadastro_min_motor.py -s

Os tres caminhos de nacionalidade saem do sorteio em
dados.nacionalidade_opcoes do config.yaml. Para o gate por caminho,
reduza a lista a um valor so e rode 3x.
"""
import pathlib
import time

from vtae.config import ConfigLoader
from vtae.core.context import FlowContext
from vtae.core.motor.executor import Executor
from vtae.core.object_repository import ObjectRepository
from vtae.flows.si3.login.login_flow import LoginFlow
from vtae.report.observer import ExecutionObserver
from vtae.runners.browser_launcher import abrir_si3_navegador
from vtae.runners.jab_reader import LeitorJab
from vtae.runners.opencv_runner import OpenCVRunner

CAMINHO_FLOW = "flows/si3/cadastro_min.yaml"
OBJETOS = "objects/si3/cadastro_min.yaml"
CONFIGS_DIR = pathlib.Path("configs/si3")

# threshold 0.75: score maximo real 0.79 (diagnose validado, familia A)
TPL_CONEXAO = "templates/si3/login/popup_conexao.png"
TIMEOUT_SI3_ABRIR = 30

PAUSA_POS_LOGIN = 3.0


def test_cadastro_min_pelo_motor():
    # Dois configs, duas responsabilidades (regra 22 e regra 40):
    # si3_login  -> url do SI3 + coordenadas campo_usuario/senha/conectar
    # config     -> dados_faker e dados: do formulario de cadastro
    config_login = ConfigLoader.carregar("si3_login", configs_dir=CONFIGS_DIR)
    config = ConfigLoader.carregar("si3_cadastro_paciente_min",
                                   configs_dir=CONFIGS_DIR)

    observer = ExecutionObserver(test_name="test_cadastro_min_pelo_motor")

    # Runner ANTES do launcher — wait_template precisa dele.
    runner = OpenCVRunner(confidence=config.confidence,
                          ocr_engine=config.ocr_engine)

    # Abre o Edge e dispara o SI3 (janela nativa Oracle Forms).
    abrir_si3_navegador(url=config_login.url)

    # Espera por CONDICAO, nao por tempo (regra 51). E tambem o que
    # impede o login de digitar credenciais na area de trabalho quando o
    # SI3 nao subiu.
    if not runner.wait_template(TPL_CONEXAO, timeout=TIMEOUT_SI3_ABRIR,
                                threshold=0.75):
        raise TimeoutError(
            f"SI3 nao abriu — popup Conexao nao detectado em "
            f"{TIMEOUT_SI3_ABRIR}s.")

    # UM ctx so, com o config do cadastro. LoginFlow clica os campos por
    # TEMPLATE (safe_click) e le as credenciais de ctx.user/ctx.password,
    # entao nao precisa das coordenadas do si3_login.
    #
    # Por que LoginFlow e nao LoginSi3Flow: o LoginSi3Flow clica em
    # coordenada fixa (campo_usuario {x:340,y:263}, medida com a janela
    # maximizada). Em 05/08 10:41 isso digitou "io.paulier" no Usuario —
    # perdeu os 3 primeiros caracteres — e deixou a Senha vazia, porque o
    # clique caiu na borda do campo. No mesmo dia, as 10:19, o LoginFlow
    # achou os dois campos por template ("match em escala 0.8x"): a
    # janela do SI3 nao esta no tamanho em que as coordenadas foram
    # medidas, e template se adapta a isso, coordenada nao.
    #
    # Sem ObjectRepository aqui de proposito: o motor carrega os objetos
    # pela linha 'objetos:' do YAML de flow, que aponta para
    # objects/si3/cadastro_min.yaml. Injetar o repositorio antigo
    # ressuscitaria objects/cadastro_min.yaml (pendencia #5).
    ctx = FlowContext(runner=runner, config=config,
                      evidence_dir=observer.evidence_dir)
    observer.inject_logger(ctx)

    login = LoginFlow().execute(ctx, observer=observer)
    assert login.success, f"Login falhou: {login.failed_steps}"

    time.sleep(PAUSA_POS_LOGIN)

    # Camada exata. A tela declara 'camada_exata: pyjab' no objects/, mas
    # sem um leitor injetado o Verificador degrada TODO campo lov/lov_lista
    # para OCR — foi o que fez 'PRETA' virar 'PRETA 2 ='. O titulo da
    # janela Java sai do proprio objects/ (regra 40: locator nao se
    # digita no teste); ler o repositorio aqui e provisorio, some com a
    # fixture da peca 5.
    leitor = LeitorJab(
        titulo=ObjectRepository.from_yaml(OBJETOS).titulo_jab(),
        jab_home=config.DADOS.get("jab_home_fake"),
    )

    try:
        resultado = Executor(ctx, observer=observer,
                             leitor_exato=leitor).executar(CAMINHO_FLOW)
        assert resultado.success, (
            f"Cadastro min pelo motor falhou: {resultado.failed_steps}")
    finally:
        # O relatorio sai mesmo quando falha — e ai que ele serve.
        try:
            observer.report(ctx)
            ctx.print_summary()
        except Exception as erro:
            print(f"[WARNING] Erro ao gerar relatorio: {erro}")
