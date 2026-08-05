"""
Unitarios do executor — peca 4 do motor.

Os dois YAMLs sao escritos em tmp_path pelo proprio teste: o motor le
arquivo de verdade, com o plano, o ObjectRepository, a validacao, as
acoes e o verificador de verdade. So o runner e falso — e o unico que
tocaria a tela.
"""
import pytest

from vtae.core.exceptions import ConfigError
from vtae.core.motor.executor import Executor

DADOS = {"nome": "MARIA DA SILVA"}

OBJETOS_YAML = """
tela:
  titulo_janela: "Janela De Teste"
objetos:
  nome:
    tipo: texto
    coordenada: { x: 10, y: 20 }
    regiao_ocr: { x1: 1, y1: 2, x2: 3, y2: 4 }
  hora:
    tipo: data
    coordenada: { x: 30, y: 40 }
  matricula:
    tipo: resultado
    regiao_ocr: { x1: 5, y1: 6, x2: 7, y2: 8 }
"""


class FakeRunner:
    """
    leituras: nome -> fila de valores devolvidos pelo OCR. O ultimo
    valor da fila se repete, o que permite simular polling.
    """

    def __init__(self, leituras=None):
        self.chamadas = []
        self.leituras = {k: list(v) for k, v in (leituras or {}).items()}

    def click_xy(self, x, y):
        self.chamadas.append(("click", x, y))

    def press(self, tecla, vezes=1, intervalo=0.02):
        self.chamadas.append(("press", tecla, vezes))

    def type_text(self, texto):
        self.chamadas.append(("digitar", texto))

    def focar_janela(self, titulo):
        self.chamadas.append(("focar", titulo))
        return True

    def find_template(self, template, threshold=None):
        return None

    def screenshot(self, caminho):
        self.chamadas.append(("screenshot", caminho))
        return caminho

    def verify_lov(self, campo_nome, region=None, timeout=None):
        fila = self.leituras.get(campo_nome)
        if not fila:
            return False, ""
        lido = fila.pop(0) if len(fila) > 1 else fila[0]
        return bool(lido), lido


class FakeConfig:
    def __init__(self, dados):
        self.DADOS = dados


class FakeCtx:
    def __init__(self, runner, dados=None):
        self.runner = runner
        self.config = FakeConfig(dados if dados is not None else dict(DADOS))
        self.evidence_dir = "evidence/"
        self.resultados = []

    def add_result(self, resultado):
        self.resultados.append(resultado)


class FakeObserver:
    def __init__(self):
        self.flows = []

    def log_step_start(self, step_id, descricao):
        pass

    def log_step_result(self, passo):
        pass

    def log_flow_result(self, resultado):
        self.flows.append(resultado)


def _yaml(tmp_path, *steps, steps_python=None):
    objetos = tmp_path / "objetos.yaml"
    objetos.write_text(OBJETOS_YAML, encoding="utf-8")
    caminho_objetos = str(objetos).replace("\\", "/")

    linhas = ["flow: teste", f"objetos: {caminho_objetos}"]
    if steps_python:
        linhas.append(f"steps_python: {steps_python}")
    linhas.append("steps:")
    linhas += [f"  - {s}" for s in steps]

    flow = tmp_path / "flow.yaml"
    flow.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return str(flow)


def _executor(ctx, **kwargs):
    return Executor(ctx, pausar=lambda _: None, **kwargs)


PREENCHER_NOME = 'preencher: { campo: nome, valor: "{faker:nome}" }'
VERIFICAR_NOME = 'verificar: { campo: nome, valor: "{faker:nome}" }'


# ── caminho feliz ────────────────────────────────────────────────────
def test_flow_feliz_passa_todos_os_steps(tmp_path):
    runner = FakeRunner({"nome": ["MARIA DA SILVA"], "matricula": ["123456"]})
    ctx = FakeCtx(runner)
    caminho = _yaml(tmp_path, PREENCHER_NOME, "salvar: f10",
                    "ler_resultado: matricula")

    resultado = _executor(ctx).executar(caminho)

    assert resultado.success is True
    assert [s.step_id for s in resultado.steps] == ["S01", "S02", "S03"]


def test_valor_interpolado_chega_na_tela(tmp_path):
    runner = FakeRunner({"nome": ["MARIA DA SILVA"]})
    _executor(FakeCtx(runner)).executar(_yaml(tmp_path, PREENCHER_NOME))
    assert ("digitar", "MARIA DA SILVA") in runner.chamadas


def test_ocr_lido_chega_ao_step_result(tmp_path):
    runner = FakeRunner({"nome": ["MARIA DA SILVA"]})
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, PREENCHER_NOME))
    assert resultado.steps[0].ocr_lido == "MARIA DA SILVA"
    assert resultado.steps[0].validated is True


def test_tira_screenshot_de_cada_step(tmp_path):
    runner = FakeRunner({"nome": ["MARIA DA SILVA"]})
    _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, PREENCHER_NOME, "salvar: f10"))
    tirados = [c[1] for c in runner.chamadas if c[0] == "screenshot"]
    assert tirados == ["evidence/S01_preencher.png", "evidence/S02_salvar.png"]


def test_salvar_foca_e_pressiona_f10(tmp_path):
    runner = FakeRunner()
    _executor(FakeCtx(runner)).executar(_yaml(tmp_path, "salvar: f10"))
    assert ("focar", "Janela De Teste") in runner.chamadas
    assert ("press", "f10", 1) in runner.chamadas


def test_resultado_vai_para_o_ctx_e_para_o_observer(tmp_path):
    runner = FakeRunner()
    ctx = FakeCtx(runner)
    observer = FakeObserver()
    resultado = _executor(ctx, observer=observer).executar(
        _yaml(tmp_path, "salvar: f10"))
    assert ctx.resultados == [resultado]
    assert observer.flows == [resultado]


# ── vereditos ────────────────────────────────────────────────────────
def test_campo_cego_passa_com_aviso(tmp_path):
    runner = FakeRunner()
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, 'preencher: { campo: hora, valor: "0000" }'))
    assert resultado.steps[0].success is True
    assert "nao verificavel" in resultado.steps[0].avisos[0]


def test_valor_divergente_falha_o_step(tmp_path):
    runner = FakeRunner({"nome": ["OUTRA COISA QUALQUER"]})
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, PREENCHER_NOME))
    assert resultado.steps[0].success is False
    assert "MARIA DA SILVA" in resultado.steps[0].error


def test_falha_aborta_os_steps_seguintes(tmp_path):
    runner = FakeRunner({"nome": ["OUTRA COISA QUALQUER"]})
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, PREENCHER_NOME, "salvar: f10"))
    assert [s.step_id for s in resultado.steps] == ["S01"]
    assert ("press", "f10", 1) not in runner.chamadas


# ── ler_resultado ────────────────────────────────────────────────────
def test_ler_resultado_faz_polling_ate_vir_valor(tmp_path):
    runner = FakeRunner({"matricula": ["", "", "123456"]})
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, "ler_resultado: matricula"))
    assert resultado.steps[0].success is True
    assert resultado.steps[0].ocr_lido == "123456"


def test_ler_resultado_que_nunca_vem_falha(tmp_path):
    runner = FakeRunner({"matricula": [""]})
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, "ler_resultado: matricula"))
    assert resultado.steps[0].success is False


# ── validacao antecipada ─────────────────────────────────────────────
def test_yaml_invalido_explode_antes_de_qualquer_clique(tmp_path):
    runner = FakeRunner()
    caminho = _yaml(tmp_path, 'preencher: { campo: fantasma, valor: "X" }')
    with pytest.raises(ConfigError, match="nao declarado"):
        _executor(FakeCtx(runner)).executar(caminho)
    assert runner.chamadas == []


# ── steps nomeados ───────────────────────────────────────────────────
def test_step_nomeado_recebe_ctx_motor_e_argumento_interpolado(tmp_path):
    recebidos = []
    registro = {"abrir_modulo": lambda ctx, motor, arg:
                recebidos.append((ctx, motor, arg))}
    runner = FakeRunner()
    ctx = FakeCtx(runner)
    executor = _executor(ctx, registro=registro)

    executor.executar(_yaml(tmp_path, 'abrir_modulo: "{faker:nome}"'))

    assert recebidos == [(ctx, executor, "MARIA DA SILVA")]


def test_steps_python_e_importado_de_verdade(tmp_path, monkeypatch):
    (tmp_path / "steps_de_mentira.py").write_text(
        "CHAMADAS = []\n"
        "def _abrir(ctx, motor, argumento):\n"
        "    CHAMADAS.append(argumento)\n"
        "STEPS = {'abrir_modulo': _abrir}\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    caminho = _yaml(tmp_path, "abrir_modulo: CADASTRO DE PACIENTE",
                    steps_python="steps_de_mentira")
    resultado = _executor(FakeCtx(FakeRunner())).executar(caminho)

    import steps_de_mentira
    assert steps_de_mentira.CHAMADAS == ["CADASTRO DE PACIENTE"]
    assert resultado.success is True


def test_steps_python_inexistente_explode(tmp_path):
    caminho = _yaml(tmp_path, "salvar: f10", steps_python="nao.existe.modulo")
    with pytest.raises(ConfigError, match="nao pode ser importado"):
        _executor(FakeCtx(FakeRunner())).executar(caminho)


def test_modulo_sem_dicionario_steps_explode(tmp_path, monkeypatch):
    (tmp_path / "steps_vazios.py").write_text("X = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    caminho = _yaml(tmp_path, "salvar: f10", steps_python="steps_vazios")
    with pytest.raises(ConfigError, match="STEPS"):
        _executor(FakeCtx(FakeRunner())).executar(caminho)


# ── verbo verificar ──────────────────────────────────────────────────
def test_verificar_confere_sem_tocar_no_campo(tmp_path):
    """
    O Nome do cadastro chega pre-preenchido da tela de pesquisa: o teste
    prova o valor e nao clica, nao apaga, nao digita.
    """
    runner = FakeRunner({"nome": ["MARIA DA SILVA"]})
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, VERIFICAR_NOME))
    assert resultado.steps[0].success is True
    assert resultado.steps[0].ocr_lido == "MARIA DA SILVA"
    assert runner.chamadas == [("screenshot", "evidence/S01_verificar.png")]


def test_verificar_falha_quando_a_tela_diverge(tmp_path):
    runner = FakeRunner({"nome": ["OUTRA COISA QUALQUER"]})
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, VERIFICAR_NOME))
    assert resultado.steps[0].success is False


def test_campo_cego_falha_quando_a_verificacao_e_explicita(tmp_path):
    """Mesmo campo que passa com aviso no preencher (tabela do §6)."""
    runner = FakeRunner()
    resultado = _executor(FakeCtx(runner)).executar(
        _yaml(tmp_path, 'verificar: { campo: hora, valor: "0000" }'))
    assert resultado.steps[0].success is False
    assert "nao e verificavel" in resultado.steps[0].error


def test_step_nomeado_registra_veredito_pelo_motor(tmp_path):
    def _conferir(ctx, motor, argumento):
        motor.verificar("nome", argumento)

    runner = FakeRunner({"nome": ["MARIA DA SILVA"]})
    resultado = _executor(FakeCtx(runner),
                          registro={"conferir": _conferir}).executar(
        _yaml(tmp_path, 'conferir: "{faker:nome}"'))
    assert resultado.steps[0].success is True
    assert resultado.steps[0].ocr_lido == "MARIA DA SILVA"


def test_step_nomeado_que_verifica_errado_falha(tmp_path):
    def _conferir(ctx, motor, argumento):
        motor.verificar("nome", "VALOR ERRADO")

    runner = FakeRunner({"nome": ["MARIA DA SILVA"]})
    resultado = _executor(FakeCtx(runner),
                          registro={"conferir": _conferir}).executar(
        _yaml(tmp_path, "conferir: x"))
    assert resultado.steps[0].success is False