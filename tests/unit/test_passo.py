"""
Unitarios do passo — peca 4 do motor.

Fakes, nao MagicMock (regra 42): o que interessa e o que o StepResult
carrega e em que ordem o observer e avisado — nao a forma das chamadas.
"""
from vtae.core.motor.passo import Coleta, executar
from vtae.core.result import CausaFalha


class FakeObserver:
    def __init__(self):
        self.eventos = []

    def log_step_start(self, step_id, descricao):
        self.eventos.append(("start", step_id))

    def log_step_result(self, passo):
        self.eventos.append(("result", passo.step_id, passo.success))


class FakeRunner:
    def __init__(self, explode=False):
        self.explode = explode
        self.screenshots = []

    def screenshot(self, caminho):
        if self.explode:
            raise OSError("disco cheio")
        self.screenshots.append(caminho)
        return caminho


class FakeCtx:
    def __init__(self, runner=None):
        self.runner = runner or FakeRunner()
        self.evidence_dir = "evidence/"


def _explodir(erro):
    def fn():
        raise erro
    return fn


# ── sucesso ──────────────────────────────────────────────────────────
def test_sucesso_devolve_o_screenshot_do_fn():
    passo = executar("S01", "preencher nome", lambda: "evidence/S01.png")
    assert passo.success is True
    assert passo.screenshot_path == "evidence/S01.png"
    assert passo.description == "preencher nome"


def test_sucesso_propaga_a_coleta():
    coleta = Coleta(ocr_lido="MARIA", jab_lido="MARIA", validated=True)
    coleta.avisos.append("campo cego")
    passo = executar("S01", "x", lambda: None, coleta=coleta)
    assert (passo.ocr_lido, passo.jab_lido, passo.validated) == ("MARIA", "MARIA", True)
    assert passo.avisos == ["campo cego"]


def test_sem_coleta_usa_os_defaults():
    passo = executar("S01", "x", lambda: None)
    assert passo.avisos == []
    assert passo.ocr_lido is None
    assert passo.validated is None


def test_duracao_e_registrada():
    assert executar("S01", "x", lambda: None).duration_ms >= 0


# ── a lista de avisos nao vaza entre steps ───────────────────────────
def test_avisos_sao_copiados_para_o_resultado():
    coleta = Coleta()
    coleta.avisos.append("primeiro")
    passo = executar("S01", "x", lambda: None, coleta=coleta)
    coleta.avisos.append("segundo")
    assert passo.avisos == ["primeiro"]


def test_duas_coletas_nao_dividem_a_mesma_lista():
    a, b = Coleta(), Coleta()
    a.avisos.append("so da A")
    assert b.avisos == []


# ── observer ─────────────────────────────────────────────────────────
def test_observer_recebe_start_e_result_em_ordem():
    obs = FakeObserver()
    executar("S01", "x", lambda: None, observer=obs)
    assert obs.eventos == [("start", "S01"), ("result", "S01", True)]


def test_observer_recebe_o_result_mesmo_na_falha():
    obs = FakeObserver()
    executar("S01", "x", _explodir(RuntimeError("boom")), observer=obs)
    assert obs.eventos == [("start", "S01"), ("result", "S01", False)]


def test_sem_observer_nao_explode():
    assert executar("S01", "x", lambda: None).success is True


# ── falha ────────────────────────────────────────────────────────────
def test_falha_marca_o_step_e_guarda_a_mensagem():
    passo = executar("S01", "x", _explodir(AssertionError("valor incorreto")))
    assert passo.success is False
    assert passo.validated is False
    assert "valor incorreto" in passo.error


def test_falha_usa_a_causa_que_o_motor_informou():
    coleta = Coleta(causa=CausaFalha.OCR_REGIAO)
    passo = executar("S01", "x", _explodir(RuntimeError("qualquer coisa")),
                     coleta=coleta)
    assert passo.causa_falha is CausaFalha.OCR_REGIAO


def test_sem_causa_informada_assertion_error_vira_sistema():
    passo = executar("S01", "x", _explodir(AssertionError("valor incorreto")))
    assert passo.causa_falha is CausaFalha.SISTEMA


def test_sem_causa_informada_fareja_a_mensagem():
    passo = executar("S01", "x", _explodir(RuntimeError("template nao encontrado")))
    assert passo.causa_falha is CausaFalha.TEMPLATE_NAO_ENCONTRADO


def test_falha_propaga_o_que_a_coleta_ja_tinha_lido():
    coleta = Coleta(ocr_lido="PALMEIRAS")
    passo = executar("S01", "x", _explodir(AssertionError("divergente")),
                     coleta=coleta)
    assert passo.ocr_lido == "PALMEIRAS"


# ── screenshot de diagnostico ────────────────────────────────────────
def test_falha_tira_screenshot_de_diagnostico():
    ctx = FakeCtx()
    executar("S01", "x", _explodir(RuntimeError("boom")), ctx=ctx)
    assert ctx.runner.screenshots == ["evidence/S01_auto_diag_001.png"]


def test_sucesso_nao_tira_screenshot_de_diagnostico():
    ctx = FakeCtx()
    executar("S01", "x", lambda: "evidence/S01.png", ctx=ctx)
    assert ctx.runner.screenshots == []


def test_diagnostico_que_explode_nao_mascara_o_erro_real():
    ctx = FakeCtx(FakeRunner(explode=True))
    passo = executar("S01", "x", _explodir(RuntimeError("boom")), ctx=ctx)
    assert "boom" in passo.error


def test_falha_sem_ctx_nao_explode():
    assert executar("S01", "x", _explodir(RuntimeError("boom"))).success is False