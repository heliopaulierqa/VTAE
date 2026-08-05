"""
O piloto contra os arquivos REAIS — sem tela.

Este e o unico teste que le flows/si3/cadastro_min.yaml,
objects/si3/cadastro_min.yaml, o steps.py e o config.yaml de verdade e
passa tudo pela validacao antecipada. Ele prova, antes de qualquer
clique, que:

  - todo campo citado no YAML existe no objects/
  - todo tipo tem a mecanica que exige (btn_ok, campo_localizar...)
  - todo step nomeado tem funcao registrada no STEPS
  - toda interpolacao {faker:X}/{sorteio:X} existe no config.yaml

E a regra 11 (medir antes de confiar) aplicada ao piloto: um nome errado
aqui custaria uma jornada inteira na tela real para aparecer.

Depende do diretorio corrente ser a raiz do repo — como o pytest ja roda
de la (rootdir do pyproject.toml), os caminhos relativos do YAML valem.
"""
import importlib
from pathlib import Path

from vtae.config.loader import ConfigLoader
from vtae.core.motor.plano import carregar
from vtae.core.motor.validacao import validar
from vtae.core.object_repository import ObjectRepository

CAMINHO_FLOW = "flows/si3/cadastro_min.yaml"


def _config(monkeypatch):
    # As credenciais nao importam aqui, mas o schema as exige. os.environ
    # tem prioridade maxima no ConfigLoader, entao isto funciona em
    # qualquer maquina, com ou sem .env.
    monkeypatch.setenv("SI3_USER", "usuario_de_teste")
    monkeypatch.setenv("SI3_PASS", "senha_de_teste")
    return ConfigLoader.carregar("si3_cadastro_paciente_min",
                                 configs_dir=Path("configs/si3"))


def test_piloto_passa_na_validacao_antecipada(monkeypatch):
    config = _config(monkeypatch)
    plano = carregar(CAMINHO_FLOW)
    objetos = ObjectRepository.from_yaml(plano.objetos)
    modulo = importlib.import_module(plano.steps_python)

    # Nao explodir E o assert: validar() levanta ConfigError com a lista
    # inteira de problemas quando o piloto esta incoerente.
    validar(plano, objetos, modulo.STEPS, config.DADOS)

    assert plano.flow == "cadastro_paciente_min"


def test_piloto_aponta_para_o_objects_novo(monkeypatch):
    """
    Guarda da pendencia 7: existem dois objects/cadastro_min.yaml no
    disco, com 19 nomes diferentes entre eles. O motor usa o de si3/;
    o antigo morre com o flow antigo na Fase 3.
    """
    plano = carregar(CAMINHO_FLOW)
    assert plano.objetos == "objects/si3/cadastro_min.yaml"
