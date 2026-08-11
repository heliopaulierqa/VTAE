# tests/unit/test_jab_reader.py
"""
Unitarios do LeitorJab (vtae/runners/jab_reader.py) — peca que faltava
testar desde que a peca 3 do motor (Verificador) passou a depender dele.

pyjab nao precisa estar instalado no ambiente de teste: o LeitorJab
importa 'from pyjab.jabdriver import JABDriver' de dentro de _conectar(),
entao injetamos pyjab e pyjab.jabdriver em sys.modules ANTES de cada
chamada, com um JABDriver fake que devolve ou levanta o que o teste
programar. FAKES em vez de MagicMock (regra 42) — o fake devolve o
programado e registra a FORMA da chamada, MagicMock passaria sem provar
nada.

Cobertura (desenho aprovado por Helio em 06/08):
  1. conecta e le elemento existente
  2. elemento nao encontrado devolve None
  3. falha ao conectar devolve None
  4. falha ao conectar tenta de novo no proximo campo — fix desta sessao
     (ate 06/08 a flag _desistiu tornava a falha permanente; a causa raiz
     medida e uma corrida de startup do Access Bridge, transitoria, nao
     ausencia do driver — ver Projeto v0.1 §2.1)
  5. conexao bem sucedida e cacheada — nao reconecta a cada campo
  6. erro ao PROCURAR um elemento (nao ao conectar) nao derruba a conexao
  7. JAVA_HOME (jab_home) e setado ANTES da tentativa de conexao (regra 31)
"""
import os
import sys
import types

from vtae.runners.jab_reader import LeitorJab


class FakeElemento:
    """Componente Java fake — so o que o LeitorJab usa: .text."""
    def __init__(self, texto):
        self.text = texto


class FakeDriver:
    """
    Substitui pyjab.jabdriver.JABDriver depois de conectado. 'respostas'
    mapeia nome de campo -> lista de FakeElemento (achou) ou uma Exception
    (erro na BUSCA — diferente de erro na CONEXAO, que quem simula e a
    fabrica passada pra _injetar_pyjab).
    """
    def __init__(self, title, timeout, respostas):
        self.title = title
        self.timeout = timeout
        self._respostas = respostas

    def find_elements_by_name(self, nome):
        resposta = self._respostas.get(nome, [])
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def _injetar_pyjab(monkeypatch, fabrica):
    """
    fabrica: callable(title, timeout) -> FakeDriver, ou que levanta uma
    Exception pra simular falha de conexao — e exatamente o que
    _conectar() espera poder capturar de 'from pyjab.jabdriver import
    JABDriver; JABDriver(title=..., timeout=...)'.
    """
    monkeypatch.setitem(sys.modules, "pyjab", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "pyjab.jabdriver",
                        types.SimpleNamespace(JABDriver=fabrica))


# ---------------------------------------------------------------------
# 1. conecta e le elemento existente
# ---------------------------------------------------------------------
def test_conecta_e_le_elemento_existente(monkeypatch):
    def fabrica(title, timeout):
        return FakeDriver(title, timeout,
                          {"sexo": [FakeElemento("MASCULINO")]})
    _injetar_pyjab(monkeypatch, fabrica)

    leitor = LeitorJab(titulo="Form_Pac0010")
    assert leitor.ler("sexo") == "MASCULINO"


# ---------------------------------------------------------------------
# 2. elemento nao encontrado devolve None
# ---------------------------------------------------------------------
def test_elemento_nao_encontrado_devolve_none(monkeypatch):
    def fabrica(title, timeout):
        return FakeDriver(title, timeout, {})  # nada mapeado -> lista vazia
    _injetar_pyjab(monkeypatch, fabrica)

    leitor = LeitorJab(titulo="Form_Pac0010")
    assert leitor.ler("campo_nao_mapeado") is None


# ---------------------------------------------------------------------
# 3. falha ao conectar devolve None
# ---------------------------------------------------------------------
def test_falha_ao_conectar_devolve_none(monkeypatch):
    def fabrica(title, timeout):
        raise Exception("HWND is not Java Window, please check!")
    _injetar_pyjab(monkeypatch, fabrica)

    leitor = LeitorJab(titulo="Form_Pac0010")
    assert leitor.ler("sexo") is None


# ---------------------------------------------------------------------
# 4. falha ao conectar tenta de novo no proximo campo (fix de hoje)
# ---------------------------------------------------------------------
def test_falha_ao_conectar_tenta_de_novo_no_proximo_campo(monkeypatch):
    chamadas = []

    def fabrica(title, timeout):
        chamadas.append((title, timeout))
        if len(chamadas) == 1:
            raise Exception("HWND is not Java Window, please check!")
        return FakeDriver(title, timeout,
                          {"nacionalidade": [FakeElemento("BRASILEIRO")]})
    _injetar_pyjab(monkeypatch, fabrica)

    leitor = LeitorJab(titulo="Form_Pac0010")
    assert leitor.ler("sexo") is None                    # 1a tentativa falha
    assert leitor.ler("nacionalidade") == "BRASILEIRO"   # 2o campo reconecta
    assert len(chamadas) == 2                            # prova a reconexao


# ---------------------------------------------------------------------
# 5. conexao bem sucedida e cacheada
# ---------------------------------------------------------------------
def test_conexao_bem_sucedida_e_cacheada(monkeypatch):
    chamadas = []

    def fabrica(title, timeout):
        chamadas.append((title, timeout))
        return FakeDriver(title, timeout, {
            "sexo": [FakeElemento("FEMININO")],
            "cor_etnia": [FakeElemento("PARDA")],
        })
    _injetar_pyjab(monkeypatch, fabrica)

    leitor = LeitorJab(titulo="Form_Pac0010")
    leitor.ler("sexo")
    leitor.ler("cor_etnia")
    assert len(chamadas) == 1  # so conectou uma vez pros dois campos


# ---------------------------------------------------------------------
# 6. erro ao PROCURAR elemento nao derruba a conexao ja feita
# ---------------------------------------------------------------------
def test_erro_ao_procurar_nao_derruba_conexao(monkeypatch):
    chamadas = []

    def fabrica(title, timeout):
        chamadas.append((title, timeout))
        return FakeDriver(title, timeout, {
            "campo_com_bug": RuntimeError("arvore Java instavel"),
            "cor_etnia": [FakeElemento("AMARELA")],
        })
    _injetar_pyjab(monkeypatch, fabrica)

    leitor = LeitorJab(titulo="Form_Pac0010")
    assert leitor.ler("campo_com_bug") is None      # erro na busca, nao na conexao
    assert leitor.ler("cor_etnia") == "AMARELA"      # conexao (ja feita) segue valendo
    assert len(chamadas) == 1                        # nao reconectou


# ---------------------------------------------------------------------
# 7. JAVA_HOME e setado a partir de jab_home ANTES da conexao (regra 31)
# ---------------------------------------------------------------------
def test_jab_home_setado_antes_da_conexao(monkeypatch):
    monkeypatch.delenv("JAVA_HOME", raising=False)
    visto = {}

    def fabrica(title, timeout):
        visto["java_home"] = os.environ.get("JAVA_HOME")
        return FakeDriver(title, timeout, {})
    _injetar_pyjab(monkeypatch, fabrica)

    leitor = LeitorJab(titulo="Form_Pac0010", jab_home="C:\\jab_home")
    leitor.ler("qualquer_campo")
    assert visto["java_home"] == "C:\\jab_home"
