"""
Unitarios da camada de espera — peca 2 do motor.

Mesma linha do test_resolvedor: ObjectRepository real + runner falso que
registra a FORMA das chamadas (regra 42). O pygetwindow e injetado em
sys.modules, entao os testes valem com ou sem a biblioteca instalada.
"""
import sys

from vtae.core.motor.esperas import Esperas
from vtae.core.object_repository import ObjectRepository


class RunnerFalso:
    def __init__(self, achou=True):
        self._achou = achou
        self.chamadas = []

    def wait_template(self, template, timeout=None, threshold=None):
        self.chamadas.append((template, timeout))
        return self._achou


class LoggerFalso:
    def __init__(self):
        self.mensagens = []

    def info(self, msg):
        self.mensagens.append(msg)


class JanelasFalsas:
    """Imita o modulo pygetwindow: so precisa de getAllTitles()."""
    def __init__(self, titulos):
        self._titulos = titulos

    def getAllTitles(self):
        return self._titulos


OBJETOS = {
    "campo_nome_social": {"template": "templates/ancora.png"},
    "com_template": {"tipo": "botao", "template": "templates/btn.png"},
    "so_coordenada": {"tipo": "texto", "coordenada": {"x": 10, "y": 20}},
}


def _esperas(runner=None, logger=None, com_ancora=True):
    tela = {"ancora": "campo_nome_social"} if com_ancora else {}
    repo = ObjectRepository(dict(OBJETOS), tela=tela)
    return Esperas(repo, runner or RunnerFalso(), logger)


def test_elemento_nao_declarado_e_falha():
    logger = LoggerFalso()
    assert _esperas(logger=logger).esperar_visivel("nao_existe") is False
    assert "nao declarado" in logger.mensagens[0]


def test_elemento_com_template_espera_o_proprio_template():
    runner = RunnerFalso(achou=True)
    assert _esperas(runner).esperar_visivel("com_template", timeout=3.0) is True
    assert runner.chamadas == [("templates/btn.png", 3.0)]


def test_elemento_so_coordenada_cai_na_ancora_da_tela():
    runner = RunnerFalso(achou=True)
    assert _esperas(runner).esperar_visivel("so_coordenada") is True
    # espera a ancora, nao o elemento — que nao tem o que esperar
    assert runner.chamadas == [("templates/ancora.png", 10.0)]


def test_sem_template_e_sem_ancora_avisa_e_segue():
    runner = RunnerFalso()
    logger = LoggerFalso()
    esperas = _esperas(runner, logger, com_ancora=False)
    # segue em frente, mas o log registra que nao havia o que esperar
    assert esperas.esperar_visivel("so_coordenada") is True
    assert runner.chamadas == []
    assert any("sem condicao" in m for m in logger.mensagens)


def test_template_nao_aparece_no_prazo_e_falha():
    runner = RunnerFalso(achou=False)
    logger = LoggerFalso()
    assert _esperas(runner, logger).esperar_visivel("com_template") is False
    assert any("timeout" in m for m in logger.mensagens)


def test_janela_ja_ausente_devolve_true(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygetwindow",
                        JanelasFalsas(["SI3 - Cadastro"]))
    assert _esperas().esperar_janela_sumir("Lista de UF") is True


def test_janela_que_nao_some_estoura_o_timeout(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygetwindow",
                        JanelasFalsas(["Lista de UF"]))
    logger = LoggerFalso()
    assert _esperas(logger=logger).esperar_janela_sumir(
        "Lista de UF", timeout=0.5) is False
    assert any("ainda" in m or "aberta" in m for m in logger.mensagens)


def test_pygetwindow_ausente_falha_com_aviso(monkeypatch):
    # None em sys.modules faz o import levantar ImportError
    monkeypatch.setitem(sys.modules, "pygetwindow", None)
    logger = LoggerFalso()
    assert _esperas(logger=logger).esperar_janela_sumir("qualquer") is False
    assert any("pygetwindow" in m for m in logger.mensagens)


def test_janela_ja_presente_devolve_true(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygetwindow",
                        JanelasFalsas(["Lista de UF"]))
    assert _esperas().esperar_janela_aparecer("Lista de UF") is True


def test_janela_que_nao_abre_estoura_o_timeout(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygetwindow",
                        JanelasFalsas(["SI3 - Cadastro"]))
    logger = LoggerFalso()
    assert _esperas(logger=logger).esperar_janela_aparecer(
        "Lista de UF", timeout=0.5) is False
    assert any("nao abriu" in m for m in logger.mensagens)


def test_aparecer_sem_pygetwindow_falha_com_aviso(monkeypatch):
    monkeypatch.setitem(sys.modules, "pygetwindow", None)
    logger = LoggerFalso()
    assert _esperas(logger=logger).esperar_janela_aparecer("qualquer") is False
    assert any("pygetwindow" in m for m in logger.mensagens)