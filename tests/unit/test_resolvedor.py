"""
Unitarios do Resolvedor de alvo — peca 2 do motor.

Usa o ObjectRepository REAL (ele aceita um dict de objetos direto, entao
nao ha motivo para falsificar) e um runner falso que registra a FORMA das
chamadas, nao so que houve chamada (regra 42).
"""
import dataclasses

import pytest

from vtae.core.motor.resolvedor import Alvo, Resolvedor
from vtae.core.object_repository import ObjectRepository


@dataclasses.dataclass
class MatchFalso:
    """Imita o retorno de TemplateMatcher.find_best: tem .x e .y."""
    x: int
    y: int


class RunnerFalso:
    def __init__(self, achado=None):
        self._achado = achado
        self.templates_pedidos = []

    def find_template(self, template, threshold=None):
        self.templates_pedidos.append(template)
        return self._achado


class LoggerFalso:
    def __init__(self):
        self.mensagens = []

    def info(self, msg):
        self.mensagens.append(msg)


OBJETOS = {
    "so_coordenada": {"tipo": "texto", "coordenada": {"x": 63, "y": 159}},
    "so_template": {"tipo": "botao", "template": "templates/btn.png"},
    "os_dois": {
        "tipo": "texto",
        "coordenada": {"x": 172, "y": 259},
        "template": "templates/campo_nome_pesquisa.png",
    },
    "so_seletor": {"tipo": "texto", "seletor": "#P1_NOME"},
    "sem_locator": {"tipo": "resultado", "regiao_ocr": {"x1": 1, "y1": 2, "x2": 3, "y2": 4}},
}


def _resolvedor(runner=None, logger=None):
    repo = ObjectRepository(dict(OBJETOS), tela={"titulo_jab": "Form_Teste"})
    return Resolvedor(repo, runner or RunnerFalso(), logger)


def test_elemento_nao_declarado_devolve_none():
    logger = LoggerFalso()
    assert _resolvedor(logger=logger).resolver("nao_existe") is None
    assert "nao declarado" in logger.mensagens[0]


def test_so_coordenada_nao_consulta_a_tela():
    runner = RunnerFalso()
    alvo = _resolvedor(runner).resolver("so_coordenada")
    assert alvo == Alvo("coordenada", ponto=(63, 159))
    assert alvo.degradado is False
    # forma: elemento sem template nao pode custar uma busca na tela
    assert runner.templates_pedidos == []


def test_template_encontrado_usa_o_ponto_do_match():
    runner = RunnerFalso(achado=MatchFalso(x=800, y=400))
    alvo = _resolvedor(runner).resolver("os_dois")
    assert alvo.estrategia == "template"
    # o ponto vem do match na tela, NAO da coordenada declarada (172, 259)
    assert alvo.ponto == (800, 400)
    assert alvo.degradado is False
    assert runner.templates_pedidos == ["templates/campo_nome_pesquisa.png"]


def test_template_falho_com_coordenada_degrada_e_avisa():
    runner = RunnerFalso(achado=None)
    logger = LoggerFalso()
    alvo = _resolvedor(runner, logger).resolver("os_dois")
    assert alvo == Alvo("coordenada", ponto=(172, 259), degradado=True)
    assert any("DEGRADACAO" in m for m in logger.mensagens)


def test_template_falho_sem_coordenada_devolve_none():
    runner = RunnerFalso(achado=None)
    logger = LoggerFalso()
    assert _resolvedor(runner, logger).resolver("so_template") is None
    assert any("inalcancavel" in m for m in logger.mensagens)


def test_seletor_web_nao_consulta_a_tela():
    runner = RunnerFalso()
    alvo = _resolvedor(runner).resolver("so_seletor")
    assert alvo == Alvo("seletor", seletor="#P1_NOME")
    assert alvo.ponto is None
    assert runner.templates_pedidos == []


def test_elemento_sem_nenhum_locator_devolve_none():
    logger = LoggerFalso()
    assert _resolvedor(logger=logger).resolver("sem_locator") is None
    assert any("inalcancavel" in m for m in logger.mensagens)


def test_alvo_e_imutavel():
    alvo = Alvo("coordenada", ponto=(1, 2))
    with pytest.raises(dataclasses.FrozenInstanceError):
        alvo.ponto = (9, 9)


def test_elemento_devolve_copia_e_nao_o_dicionario_interno():
    repo = ObjectRepository(dict(OBJETOS))
    copia = repo.elemento("so_coordenada")
    copia["tipo"] = "adulterado"
    assert repo.elemento("so_coordenada")["tipo"] == "texto"
