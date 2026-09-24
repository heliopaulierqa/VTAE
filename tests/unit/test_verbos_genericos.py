"""
Verbos genericos — decisao 26 (24/09/2026).

abrir, esperar, clicar, teclar + salvar por botao ou tecla + campo
sigiloso + prefixo {dado:X}. Nenhum teste aqui cita sistema algum: e a
prova de que estes verbos servem qualquer tela.
"""
import pytest

from vtae.core.exceptions import ConfigError
from vtae.core.motor.executor import Executor
from vtae.core.motor.interpolacao import Interpolador
from vtae.core.motor.plano import montar
from vtae.core.motor.validacao import validar
from vtae.core.object_repository import ObjectRepository

OBJETOS = {
    "tela_inicial": {"tipo": "botao", "template": "tela.png"},
    "usuario": {"tipo": "texto", "coordenada": {"x": 10, "y": 10},
                "regiao_ocr": {"x1": 0, "y1": 0, "x2": 5, "y2": 5}},
    "senha": {"tipo": "texto", "sigiloso": True, "coordenada": {"x": 20, "y": 20}},
    "btn_entrar": {"tipo": "botao", "coordenada": {"x": 30, "y": 30}},
    "sem_local": {"tipo": "botao"},
}
DADOS = {"usuario": "ana", "senha": "segredo", "programa": "app.exe"}


def _validar(*steps):
    plano = montar({"flow": "x", "objetos": "o.yaml", "steps": list(steps)})
    validar(plano, ObjectRepository(OBJETOS), {}, DADOS)


# ── validacao ────────────────────────────────────────────────────────
def test_roteiro_de_login_sem_python_e_valido():
    _validar({"abrir": "{dado:programa}"},
             {"esperar": "tela_inicial"},
             {"preencher": {"campo": "usuario", "valor": "{dado:usuario}"}},
             {"preencher": {"campo": "senha", "valor": "{dado:senha}"}},
             {"clicar": "btn_entrar"},
             {"teclar": "enter"})


def test_clicar_em_elemento_inexistente_explode():
    with pytest.raises(ConfigError, match="nao declarado"):
        _validar({"clicar": "fantasma"})


def test_clicar_sem_template_nem_coordenada_explode():
    with pytest.raises(ConfigError, match="nao ha como clicar"):
        _validar({"clicar": "sem_local"})


def test_esperar_sem_template_explode():
    with pytest.raises(ConfigError, match="precisa de"):
        _validar({"esperar": "btn_entrar"})


def test_dado_ausente_explode_antes_do_primeiro_clique():
    with pytest.raises(ConfigError, match="ausente"):
        _validar({"abrir": "{dado:nao_existe}"})


# ── interpolacao ─────────────────────────────────────────────────────
def test_prefixo_dado_devolve_o_valor_fixo():
    assert Interpolador(DADOS).resolver("{dado:usuario}") == "ana"


def test_prefixo_dado_recusa_lista():
    with pytest.raises(ConfigError, match="esperava texto"):
        Interpolador({"x": [1, 2]}).resolver("{dado:x}")


# ── execucao ponta a ponta com runner falso ──────────────────────────
class Achado:
    x, y = 99, 98


class FakeRunner:
    def __init__(self):
        self.chamadas = []

    def abrir_aplicacao(self, comando):
        self.chamadas.append(("abrir", comando))

    def wait_template(self, template, timeout=10):
        self.chamadas.append(("esperar", template))
        return True

    def find_template(self, template, threshold=None):
        return Achado()

    def click_xy(self, x, y):
        self.chamadas.append(("click", x, y))

    def press(self, tecla, vezes=1, intervalo=0.02):
        self.chamadas.append(("press", tecla, vezes))

    def teclar(self, partes):
        self.chamadas.append(("teclar", tuple(partes)))

    def type_text(self, texto):
        self.chamadas.append(("digitar", texto))
        self.digitado = texto

    def verify_lov(self, nome, region=None, timeout=3):
        # OCR falso: le exatamente o ultimo texto digitado
        return True, getattr(self, "digitado", "")

    def focar_janela(self, titulo):
        return True

    def screenshot(self, caminho):
        return caminho


class FakeConfig:
    DADOS = DADOS


class FakeCtx:
    def __init__(self, runner):
        self.runner = runner
        self.config = FakeConfig()
        self.evidence_dir = "evidence/"
        self.resultados = []

    def add_result(self, r):
        self.resultados.append(r)


class LeitorSempreIgual:
    """Camada exata falsa: le exatamente o que foi digitado."""
    def __init__(self):
        self.ultimo = None


def _roteiro(tmp_path, *linhas):
    import yaml
    obj = tmp_path / "objetos.yaml"
    obj.write_text(yaml.safe_dump({"objetos": OBJETOS}), encoding="utf-8")
    rot = tmp_path / "roteiro.yaml"
    rot.write_text(yaml.safe_dump({"flow": "login", "objetos": str(obj),
                                   "steps": list(linhas)}), encoding="utf-8")
    return str(rot)


def test_abrir_esperar_clicar_teclar_executam_na_ordem(tmp_path):
    runner = FakeRunner()
    caminho = _roteiro(tmp_path,
                       {"abrir": "{dado:programa}"},
                       {"esperar": "tela_inicial"},
                       {"clicar": "btn_entrar"},
                       {"teclar": "ctrl+s"})
    resultado = Executor(FakeCtx(runner), pausar=lambda s: None).executar(caminho)
    assert resultado.success, [s.error for s in resultado.steps]
    assert runner.chamadas == [("abrir", "app.exe"),
                               ("esperar", "tela.png"),
                               ("click", 30, 30),
                               ("teclar", ("ctrl", "s"))]


def test_campo_sigiloso_e_preenchido_sem_verificar_e_sem_expor(tmp_path):
    runner = FakeRunner()
    caminho = _roteiro(tmp_path,
                       {"preencher": {"campo": "senha", "valor": "{dado:senha}"}})
    resultado = Executor(FakeCtx(runner), pausar=lambda s: None).executar(caminho)
    passo = resultado.steps[0]
    assert resultado.success
    assert ("digitar", "segredo") in runner.chamadas
    assert "segredo" not in str(passo.__dict__)
    assert any("sigiloso" in a for a in passo.avisos)


def test_esperar_que_nao_chega_falha_alto(tmp_path):
    runner = FakeRunner()
    runner.wait_template = lambda template, timeout=10: False
    caminho = _roteiro(tmp_path, {"esperar": "tela_inicial"})
    resultado = Executor(FakeCtx(runner), pausar=lambda s: None).executar(caminho)
    assert not resultado.success
    assert "nao apareceu" in resultado.steps[0].error
