# tests/integration/components/cadastro_paciente_fixture.py
"""
Componente reutilizável — Cadastro de Paciente SI3.

Encapsula toda a lógica de Login + CadastroPacienteFlow para que
qualquer jornada possa cadastrar um paciente novo sem duplicar código.

Uso em qualquer test_01:
    from tests.integration.components.cadastro_paciente_fixture import (
        executar_cadastro,
        gerar_dados,
    )

    def test_cadastro_paciente_jornada():
        executar_cadastro(proximo_passo="vtae run --test admissao_ambulatorio_jornada")

Boas práticas aplicadas:
    - Lógica de negócio em componente, não no teste
    - Geração de dados isolada em _gerar_dados() — testável unitariamente
    - observer.report() sempre chamado, mesmo se o teste falhar (try/finally)
    - estado_jornada.json validado ao final — garante que o próximo step tem dados
    - Sem import de fixtures pytest — compatível com vtae run e pytest direto
"""
import json
import pathlib
import time

from faker import Faker

from src.config import ConfigLoader
from src.core.context import FlowContext
from src.core.observer import ExecutionObserver
from src.flows.si3.cadastro_paciente_flow import CadastroPacienteFlow
from src.flows.si3.login_flow import LoginFlow
from src.runners.opencv_runner import OpenCVRunner

_fake = Faker("pt_BR")

# Caminho padrão do estado compartilhado entre testes da jornada
_ESTADO_PATH = pathlib.Path("evidence/estado_jornada.json")


def gerar_dados(config) -> dict:
    """
    Gera dados do paciente mesclando DADOS do config com campos dinâmicos.

    Separado em função pública para:
      - Ser testável unitariamente (sem abrir o SI3)
      - Permitir override em testes específicos

    Args:
        config: SystemConfig carregado pelo ConfigLoader

    Returns:
        dict com todos os campos esperados pelo CadastroPacienteFlow
    """
    dados = config.DADOS.copy()

    # Data de nascimento — Faker com faixa de idade controlada
    dob = _fake.date_of_birth(minimum_age=18, maximum_age=80)
    dados["data_nascimento"] = dob.strftime("%d/%m/%Y")
    dados["hora"] = "00:00"

    # config.yaml gera 'nome_mae'/'nome_pai' — flow espera 'mae'/'pai'
    if "mae" not in dados:
        dados["mae"] = dados.pop("nome_mae", _fake.name())
    if "pai" not in dados:
        dados["pai"] = dados.pop("nome_pai", _fake.name())

    dados.setdefault("nome_social", dados.get("nome", ""))
    dados.setdefault("conjuge",     "")
    dados.setdefault("responsavel", "")

    return dados


def executar_cadastro(
    proximo_passo: str = "",
    test_name: str = "test_cadastro_paciente_jornada",
    configs_dir: pathlib.Path = pathlib.Path("configs/si3"),
    config_name: str = "si3_cadastro_paciente",
    pausa_inicial: float = 2.0,
    pausa_pos_login: float = 3.0,
) -> dict:
    """
    Executa Login + CadastroPacienteFlow e valida o estado gerado.

    Reutilizável em qualquer jornada que precise de um paciente novo.
    Sempre chama observer.report() ao final, mesmo em caso de falha.

    Args:
        proximo_passo:   mensagem exibida ao final indicando o próximo teste
        test_name:       nome da execução (aparece no evidence/ e no report.html)
        configs_dir:     pasta base das configs do sistema
        config_name:     nome da config a carregar (subpasta em configs_dir)
        pausa_inicial:   segundos de pausa antes de iniciar (sair do terminal)
        pausa_pos_login: segundos de pausa após login (sistema carregar)

    Returns:
        dict com { "paciente_id": "...", "matricula": "..." }

    Raises:
        AssertionError: se Login, Cadastro ou estado_jornada.json falharem
    """
    config   = ConfigLoader.carregar(config_name, configs_dir=configs_dir)
    observer = ExecutionObserver(test_name=test_name)
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )

    time.sleep(pausa_inicial)

    # REGRA: apenas UM cadastro por execução.
    # Se paciente_id estiver no .env → reutiliza, pula o cadastro.
    # Se vazio → cadastra novo paciente automaticamente.
    # Cada jornada tem seu proprio .env — isolamento garantido.
    paciente_id_env = getattr(config, "PACIENTE_ID", "").strip()

    if paciente_id_env:
        print(f"\n[cadastro] Reutilizando paciente_id do .env: {paciente_id_env}")
        print(f"[cadastro] Cadastro pulado — paciente ja existe.")
        _salvar_estado("paciente_id", paciente_id_env)
        if proximo_passo:
            print(f"   Próximo passo: {proximo_passo}\n")
        return {"paciente_id": paciente_id_env}

    try:
        # Login
        login = LoginFlow().execute(ctx, observer=observer)
        assert login.success, f"Login falhou: {login.failed_steps}"

        time.sleep(pausa_pos_login)

        # Cadastro completo — gera paciente novo
        dados  = gerar_dados(config)
        result = CadastroPacienteFlow().execute(ctx, dados=dados, observer=observer)

        assert result.success, f"Cadastro falhou: {result.failed_steps}"

    finally:
        # Sempre gera o relatório — mesmo se o teste falhou
        try:
            observer.report(ctx)
            ctx.print_summary()
        except Exception as e:
            print(f"[WARNING] Erro ao gerar relatório: {e}")

    # Valida estado_jornada.json — garante que o próximo step tem dados
    assert _ESTADO_PATH.exists(), (
        "estado_jornada.json não foi criado — verifique CP22 no CadastroPacienteFlow"
    )
    conteudo = json.loads(_ESTADO_PATH.read_text(encoding="utf-8"))
    assert "paciente_id" in conteudo, (
        "paciente_id não foi salvo no estado_jornada.json — verifique CP22"
    )

    paciente_id = conteudo["paciente_id"]
    matricula   = conteudo.get("matricula", "")

    print(f"\n✅ paciente_id salvo: {paciente_id}")
    if matricula:
        print(f"   matricula: {matricula}")
    if proximo_passo:
        print(f"   Próximo passo: {proximo_passo}\n")

    return conteudo