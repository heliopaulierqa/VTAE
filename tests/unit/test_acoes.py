"""
Unitarios das acoes — peca 4 do motor.

Resolvedor e ObjectRepository sao os de verdade (fake antes de mock,
regra 42). Esperas e falso de proposito: o esperar_janela_* real
consulta as janelas do Windows, e aqui nao ha janela nenhuma — ele tem
os 11 unitarios dele.
"""
import pytest

from vtae.core.exceptions import StepError
from vtae.core.motor.acoes import BACKSPACES, Acoes
from vtae.core.motor.resolvedor import Resolvedor
from vtae.core.motor.validacao import CHAVES_POR_TIPO
from vtae.core.object_repository import ObjectRepository

TELA = {"titulo_janela": "Cadastro De Pacientes"}

OBJETOS = {
    "nome": {"tipo": "texto", "coordenada": {"x": 10, "y": 20}},
    "nascimento": {"tipo": "data", "coordenada": {"x": 11, "y": 21}},
    "sexo": {"tipo": "lov", "coordenada": {"x": 12, "y": 22},
             "btn_ok": "btn_ok_lov"},
    "cor_etnia": {"tipo": "lov_lista", "coordenada": {"x": 13, "y": 23},
                  "campo_localizar": "campo_localizar_lov",
                  "btn_ok": "btn_ok_lov", "titulo_janela": "Grupo etnico"},
    "btn_ok_lov": {"tipo": "botao", "coordenada": {"x": 90, "y": 91}},
    "campo_localizar_lov": {"tipo": "texto", "coordenada": {"x": 80, "y": 81}},
    "so_template": {"tipo": "texto", "template": "t.png",
                    "coordenada": {"x": 70, "y": 71}},
    "inalcancavel": {"tipo": "texto"},
}


class FakeRunner:
    def __init__(self, focou=True):
        self.chamadas = []
        self._focou = focou

    def click_xy(self, x, y):
        self.chamadas.append(("click", x, y))

    def double_click_xy(self, x, y):
        self.chamadas.append(("duplo", x, y))    

    def press(self, tecla, vezes=1, intervalo=0.02):
        self.chamadas.append(("press", tecla, vezes))

    def type_text(self, texto):
        self.chamadas.append(("digitar", texto))

    def focar_janela(self, titulo):
        self.chamadas.append(("focar", titulo))
        return self._focou

    def find_template(self, template, threshold=None):
        self.chamadas.append(("procurar", template))
        return None


class FakeEsperas:
    def __init__(self, apareceu=True, sumiu=True):
        self.apareceu = apareceu
        self.sumiu = sumiu
        self.esperou = []

    def esperar_janela_aparecer(self, titulo, timeout=None):
        self.esperou.append(("aparecer", titulo))
        return self.apareceu

    def esperar_janela_sumir(self, titulo, timeout=None):
        self.esperou.append(("sumir", titulo))
        return self.sumiu


def _acoes(runner=None, esperas=None, tela=TELA):
    runner = runner or FakeRunner()
    objetos = ObjectRepository(dict(OBJETOS), tela)
    return Acoes(objetos, runner,
                 Resolvedor(objetos, runner),
                 esperas or FakeEsperas(),
                 pausar=lambda _: None), runner


# ── receitas ─────────────────────────────────────────────────────────
def test_texto_clica_limpa_e_digita():
    acoes, runner = _acoes()
    acoes.preencher("nome", "MARIA")
    assert runner.chamadas == [
        ("click", 10, 20),
        ("press", "backspace", BACKSPACES),
        ("digitar", "MARIA"),
    ]


def test_data_usa_a_mesma_receita_do_texto():
    acoes, runner = _acoes()
    acoes.preencher("nascimento", "01011990")
    assert runner.chamadas == [
        ("click", 11, 21),
        ("press", "backspace", BACKSPACES),
        ("digitar", "01011990"),
    ]


def test_lov_fecha_com_tab_e_ok():
    acoes, runner = _acoes()
    acoes.preencher("sexo", "MASCULINO")
    assert runner.chamadas == [
        ("click", 12, 22),
        ("press", "backspace", BACKSPACES),
        ("digitar", "MASCULINO"),
        ("press", "tab", 1),
        ("click", 90, 91),
    ]


def test_lov_lista_faz_f9_localizar_enter_e_ok():
    acoes, runner = _acoes()
    acoes.preencher("cor_etnia", "BRANCA")
    assert runner.chamadas == [
        ("click", 13, 23),
        ("press", "f9", 1),
        ("click", 80, 81),
        ("press", "backspace", BACKSPACES),
        ("digitar", "BRANCA"),
        ("press", "enter", 1),
        ("click", 90, 91),
    ]


def test_lov_lista_nao_espera_janela_do_windows():
    """
    As LOVs do SI3 sao janelas INTERNAS do Forms — medido em 05/08 com a
    Lista de Pais aberta: o pygetwindow so enxerga 'Form_Pac0010'.
    Esperar por titulo aqui nunca poderia dar certo (regra 46), entao a
    receita nao consulta as esperas. Quem prova que a LOV abriu e a
    verificacao do valor, depois do preenchimento.
    """
    esperas = FakeEsperas()
    acoes, _ = _acoes(esperas=esperas)
    acoes.preencher("cor_etnia", "BRANCA")
    assert esperas.esperou == []


def test_limpeza_e_uma_chamada_so_com_n_repeticoes():
    acoes, runner = _acoes()
    acoes.preencher("nome", "MARIA")
    presses = [c for c in runner.chamadas if c[0] == "press"]
    assert presses == [("press", "backspace", BACKSPACES)]


# ── falhas ───────────────────────────────────────────────────────────
# Removidos em 05/08: test_lov_que_nao_abre_explode e
# test_lov_que_nao_fecha_explode. Provavam as duas esperas por titulo de
# janela do _receita_lov_lista, que sairam — a LOV do Forms nao tem
# janela no Windows. Baseline cai de 969 para 967 em tests/unit.


def test_tipo_botao_nao_se_preenche():
    acoes, _ = _acoes()
    with pytest.raises(StepError, match="nao se preenche"):
        acoes.preencher("btn_ok_lov", "X")


def test_campo_nao_declarado_explode():
    acoes, _ = _acoes()
    with pytest.raises(StepError, match="nao declarado"):
        acoes.preencher("fantasma", "X")


def test_elemento_sem_locator_e_inalcancavel():
    acoes, _ = _acoes()
    with pytest.raises(StepError, match="inalcancavel"):
        acoes.preencher("inalcancavel", "X")


def test_template_que_falha_cai_na_coordenada():
    acoes, runner = _acoes()
    acoes.preencher("so_template", "X")
    assert ("procurar", "t.png") in runner.chamadas
    assert ("click", 70, 71) in runner.chamadas


# ── salvar ───────────────────────────────────────────────────────────
def test_salvar_foca_a_janela_e_pressiona_f10():
    acoes, runner = _acoes()
    acoes.salvar("f10")
    assert runner.chamadas == [("focar", "Cadastro De Pacientes"),
                               ("press", "f10", 1)]


def test_salvar_sem_titulo_declarado_nao_foca_mas_pressiona():
    acoes, runner = _acoes(tela={})
    acoes.salvar("f10")
    assert runner.chamadas == [("press", "f10", 1)]


def test_mecanica_de_salvar_desconhecida_explode():
    acoes, _ = _acoes()
    with pytest.raises(StepError, match="desconhecida"):
        acoes.salvar("ctrl+s")


# ── as duas tabelas de tipo nao podem divergir ───────────────────────
def test_tipos_da_mecanica_sao_os_mesmos_da_validacao():
    acoes, _ = _acoes()
    assert set(acoes.tipos_preenchiveis()) == set(CHAVES_POR_TIPO)

# ── duplo clique ─────────────────────────────────────────────────────
def test_clicar_duas_vezes_usa_duplo_clique():
    acoes, runner = _acoes()
    acoes.clicar_duas_vezes("nome")
    assert runner.chamadas == [("duplo", 10, 20)]


def test_clicar_duas_vezes_em_elemento_inalcancavel_explode():
    acoes, _ = _acoes()
    with pytest.raises(StepError, match="inalcancavel"):
        acoes.clicar_duas_vezes("inalcancavel")    