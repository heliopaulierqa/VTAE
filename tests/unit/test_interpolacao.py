"""
Unitarios da interpolacao — peca 4 do motor.

Como no test_plano.py, o comportamento esperado diante de dado errado e
EXPLODIR: config nao e ambiente (regra 45).

O cache do sorteio e provado trocando a lista DEPOIS da primeira
chamada: se a segunda chamada olhasse o dicionario de novo, devolveria
um valor da lista nova. Sorte nao explica o resultado (regra 46).
"""
import pytest

from vtae.core.exceptions import ConfigError
from vtae.core.motor.interpolacao import Interpolador


def _dados():
    return {
        "nome": "MARIA DA SILVA",
        "sexo_opcoes": ["MASCULINO", "FEMININO"],
        "cor_etnia_opcoes": ["AMARELA", "BRANCA", "PRETA", "PARDA"],
    }


# ── literais ─────────────────────────────────────────────────────────
def test_literal_sem_chaves_volta_igual():
    assert Interpolador(_dados()).resolver("0000") == "0000"


def test_literal_com_chave_solta_volta_igual():
    assert Interpolador(_dados()).resolver("{nome}") == "{nome}"


# ── faker ────────────────────────────────────────────────────────────
def test_faker_devolve_o_valor_ja_gerado():
    assert Interpolador(_dados()).resolver("{faker:nome}") == "MARIA DA SILVA"


def test_faker_ignora_espacos_ao_redor():
    assert Interpolador(_dados()).resolver("  {faker:nome} ") == "MARIA DA SILVA"


# ── sorteio ──────────────────────────────────────────────────────────
def test_sorteio_devolve_valor_da_lista():
    dados = _dados()
    assert Interpolador(dados).resolver("{sorteio:sexo_opcoes}") in dados["sexo_opcoes"]


def test_sorteio_repete_o_valor_na_segunda_chamada():
    dados = _dados()
    interp = Interpolador(dados)
    primeiro = interp.resolver("{sorteio:sexo_opcoes}")
    dados["sexo_opcoes"] = ["OUTRO"]
    assert interp.resolver("{sorteio:sexo_opcoes}") == primeiro


def test_sorteio_de_chaves_diferentes_tem_caches_independentes():
    dados = _dados()
    interp = Interpolador(dados)
    sexo = interp.resolver("{sorteio:sexo_opcoes}")
    cor = interp.resolver("{sorteio:cor_etnia_opcoes}")
    dados["sexo_opcoes"] = ["OUTRO"]
    dados["cor_etnia_opcoes"] = ["OUTRA"]
    assert interp.resolver("{sorteio:sexo_opcoes}") == sexo
    assert interp.resolver("{sorteio:cor_etnia_opcoes}") == cor


# ── erros de configuracao ────────────────────────────────────────────
def test_chave_ausente_explode():
    with pytest.raises(ConfigError, match="ausente"):
        Interpolador(_dados()).resolver("{faker:inexistente}")


def test_prefixo_desconhecido_explode():
    with pytest.raises(ConfigError, match="desconhecido"):
        Interpolador(_dados()).resolver("{banco:nome}")


def test_faker_apontando_para_lista_explode():
    with pytest.raises(ConfigError, match="esperava texto"):
        Interpolador(_dados()).resolver("{faker:sexo_opcoes}")


def test_sorteio_apontando_para_texto_explode():
    with pytest.raises(ConfigError, match="esperava lista"):
        Interpolador(_dados()).resolver("{sorteio:nome}")


def test_sorteio_com_lista_vazia_explode():
    with pytest.raises(ConfigError, match="vazia"):
        Interpolador({"vazia": []}).resolver("{sorteio:vazia}")


def test_interpolacao_parcial_explode():
    with pytest.raises(ConfigError, match="parcial"):
        Interpolador(_dados()).resolver("Sr. {faker:nome}")