# tests/unit/test_admissao_com_agendamento_flow.py
"""
Testes unitarios do AdmissaoComAgendamentoFlow — subclasse de
AdmissaoAmbulatorioFlow que sobrescreve 5 dos 16 steps (AB03, AB05,
AB06, AB07, AB11). Migracao src/flows/si3/ -> vtae/flows/si3/admissao/

REGRAS (mesmo padrao de test_admissao_ambulatorio_flow.py):
  - mock_sleep autouse (conftest.py) elimina todos os time.sleep reais
  - _titulo_janela_contem (guard do AB05) e testado ISOLADO (classe
    TestTituloJanelaContem, com pygetwindow falso injetado via
    sys.modules) e tambem mockado via patch.object nos testes de
    execute() completo — evita busy-loop de ate 10s reais de wall-clock
    (time.monotonic() NAO e mockado pelo mock_sleep autouse; so o
    time.sleep vira no-op, entao um guard que nao encontra o titulo
    ficaria girando ate o deadline real passar).
  - Os 11 steps herdados (AB01, AB02, AB04, AB08-AB10, AB12-AB16) usam
    a implementacao do AdmissaoAmbulatorioFlow, ja cobertos em
    test_admissao_ambulatorio_flow.py — aqui testamos apenas que o
    flow completo (16 steps) roda com sucesso herdando-os, e focamos
    os testes detalhados nos 5 steps sobrescritos.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from vtae.flows.si3.admissao.admissao_com_agendamento_flow import AdmissaoComAgendamentoFlow
from vtae.core.result import FlowResult


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _config():
    coordenadas = {
        "campo_localizar_menu":        {"x": 300, "y": 195},
        "campo_identificador_amb":     {"x": 300, "y": 176},
        "campo_tipo_endereco_amb":     {"x": 143, "y": 378},
        "primeira_linha_grade_ag":     {"x": 250, "y": 210},
        "campo_nome_medico_ab":        {"x": 350, "y": 410},
        "campo_declarante":            {"x": 200, "y": 300},
        "campo_especialidade":         {"x": 400, "y": 300},
        "campo_obs_amb":               {"x": 200, "y": 340},
        "campo_origem_tipo":           {"x": 200, "y": 360},
        "btn_lov_codigo_proc":         {"x": 500, "y": 200},
        "campo_localizar_proc":        {"x": 300, "y": 220},
        "btn_localizar_proc":          {"x": 400, "y": 220},
        "btn_ok_proc":                 {"x": 400, "y": 240},
        "campo_localizar_area":        {"x": 300, "y": 260},
        "btn_localizar_area":          {"x": 400, "y": 260},
        "btn_ok_area_executora":       {"x": 400, "y": 280},
        "btn_lov_complemento":         {"x": 500, "y": 300},
        "campo_localizar_complemento": {"x": 300, "y": 320},
        "btn_localizar_complemento":   {"x": 400, "y": 320},
        "btn_ok_complemento":          {"x": 400, "y": 340},
        "btn_lov_profissional_proc":   {"x": 500, "y": 360},
        "campo_localizar_profissional": {"x": 300, "y": 380},
        "btn_localizar_profissional":  {"x": 400, "y": 380},
        "btn_ok_profissional":         {"x": 400, "y": 400},
    }
    config = MagicMock()
    config.coordenadas = coordenadas
    config.regioes_ocr = {}  # bootstrap — toda verificacao OCR pulada
    config.DADOS = {
        "termo_menu_amb": "AMBULATORIO",
        "nome_medico_ab": "DR TESTE AUTOMACAO",
    }
    config.PACIENTE_ID = "1000123"  # evita depender de estado_jornada.json
    config.confidence = 0.75
    return config


def _dados():
    return {
        "provedor": "SUS",
        "plano": "BASICO",
        "unidade_funcional": "CLINICA DE CARDIOPATIA GERAL",
        "origem_tipo": "RESIDENCIA",
        "procedimentos": [{"codigo": "12345", "profissional": "MEDICO"}],
    }


def _runner_ok():
    runner = MagicMock()
    runner.screenshot.return_value = "evidence/step.png"
    runner.wait_template.return_value = True
    runner.is_visible.return_value = False
    runner.safe_click.return_value = True
    runner.double_click.return_value = True
    runner.click_near.return_value = True
    runner.type_text.return_value = None
    return runner


def _ctx(runner=None):
    ctx = MagicMock()
    ctx.runner = runner or _runner_ok()
    ctx.config = _config()
    ctx.evidence_dir = "evidence/"
    ctx.jab = None
    ctx.db = None
    return ctx


def _run(runner=None, dados=None, titulo_ok=True):
    """
    Roda o flow completo com o guard de titulo de janela (AB05) mockado —
    titulo_ok=True simula tela AMBULATORIO confirmada de primeira, sem
    depender de pygetwindow real nem de espera de wall-clock.
    """
    with patch("os.path.exists", return_value=False), \
         patch.object(AdmissaoComAgendamentoFlow, "_titulo_janela_contem",
                      return_value=titulo_ok):
        return AdmissaoComAgendamentoFlow().execute(
            _ctx(runner), dados=dados or _dados()
        )


# ──────────────────────────────────────────────────────────────────────────────
# _titulo_janela_contem — helper estatico isolado
# ──────────────────────────────────────────────────────────────────────────────

class TestTituloJanelaContem:

    def test_encontra_titulo_de_primeira(self):
        fake_gw = MagicMock()
        fake_gw.getAllTitles.return_value = ["SI3 - AMBULATORIO - Admissao"]
        with patch.dict(sys.modules, {"pygetwindow": fake_gw}):
            assert AdmissaoComAgendamentoFlow._titulo_janela_contem(
                "AMBULAT", timeout=1.0
            ) is True

    def test_nao_encontra_retorna_false_apos_timeout(self):
        fake_gw = MagicMock()
        fake_gw.getAllTitles.return_value = ["SI3 - Verificar Agendamento"]
        with patch.dict(sys.modules, {"pygetwindow": fake_gw}):
            # timeout curto — o guard NAO acha "AMBULAT", entao espera o
            # timeout todo. 0.05s mantem o teste rapido.
            assert AdmissaoComAgendamentoFlow._titulo_janela_contem(
                "AMBULAT", timeout=0.05
            ) is False

    def test_exclui_titulo_quando_excluir_fornecido(self):
        fake_gw = MagicMock()
        # titulo contem "AMBULAT" mas TAMBEM contem "VERIFICAR" — deve ser
        # excluido (Oracle Forms as vezes renderiza os 2 titulos juntos)
        fake_gw.getAllTitles.return_value = ["VERIFICAR AGENDAMENTO - AMBULATORIO"]
        with patch.dict(sys.modules, {"pygetwindow": fake_gw}):
            assert AdmissaoComAgendamentoFlow._titulo_janela_contem(
                "AMBULAT", excluir="VERIFICAR", timeout=0.05
            ) is False

    def test_tolera_excecao_do_pygetwindow_e_retorna_false(self):
        fake_gw = MagicMock()
        fake_gw.getAllTitles.side_effect = Exception("sem acesso a janelas")
        with patch.dict(sys.modules, {"pygetwindow": fake_gw}):
            assert AdmissaoComAgendamentoFlow._titulo_janela_contem(
                "AMBULAT", timeout=0.05
            ) is False


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow — 16 steps herdados de AdmissaoAmbulatorioFlow.execute()
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert AdmissaoComAgendamentoFlow.FLOW_NAME == "AdmissaoComAgendamentoFlow"

    def test_execute_retorna_flow_result(self):
        assert isinstance(_run(), FlowResult)

    def test_execute_tem_16_steps(self):
        assert len(_run().steps) == 16

    def test_ids_corretos(self):
        ids = [s.step_id for s in _run().steps]
        assert ids == [f"AB{i:02d}" for i in range(1, 17)]

    def test_todos_steps_passam_com_runner_ok(self):
        falhos = [s for s in _run().steps if not s.success]
        assert falhos == [], [f"{s.step_id}: {s.error}" for s in falhos]

    def test_flow_sucesso(self):
        assert _run().success is True

    def test_execute_chama_add_result(self):
        ctx = _ctx()
        with patch("os.path.exists", return_value=False), \
             patch.object(AdmissaoComAgendamentoFlow, "_titulo_janela_contem",
                          return_value=True):
            AdmissaoComAgendamentoFlow().execute(ctx, dados=_dados())
        ctx.add_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# AB03 — Pesquisar (override)
# ──────────────────────────────────────────────────────────────────────────────

class TestAb03Override:

    def test_sucesso(self):
        assert _run().steps[2].success is True

    def test_step_id(self):
        assert _run().steps[2].step_id == "AB03"

    def test_clica_btn_pesquisar(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_ambulatorio/btn_pesquisar.png", threshold=0.7
        )

    def test_falha_se_admitir_paciente_nao_aparece(self):
        runner = _runner_ok()

        def _wait_template(tpl, *args, **kwargs):
            return "btn_admitir_paciente.png" not in tpl

        runner.wait_template.side_effect = _wait_template
        result = _run(runner)
        ab03 = result.steps[2]
        assert ab03.success is False
        assert "nao apareceu apos pesquisa" in ab03.error
        assert len(result.steps) == 3


# ──────────────────────────────────────────────────────────────────────────────
# AB05 — Admitir Paciente — 3 telas (override)
# ──────────────────────────────────────────────────────────────────────────────

class TestAb05Override:

    def test_sucesso_quando_guard_confirma_ambulatorio(self):
        result = _run(titulo_ok=True)
        assert result.steps[4].success is True

    def test_clica_primeira_linha_da_grade_de_agendamento(self):
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch.object(AdmissaoComAgendamentoFlow, "_titulo_janela_contem",
                          return_value=True), \
             patch("pyautogui.click") as mock_click:
            AdmissaoComAgendamentoFlow().execute(_ctx(runner), dados=_dados())
        # primeira_linha_grade_ag = (250, 210)
        assert (250, 210) in [c.args for c in mock_click.call_args_list]

    def test_clica_btn_admitir_verificar_ag(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_ambulatorio/btn_admitir_verificar_ag.png",
            threshold=0.7,
        )

    def test_fecha_popup_convenio_quando_aparece(self):
        runner = _runner_ok()
        # 1a chamada de wait_template no AB05 (popup convenio) = True, depois False
        chamadas = {"n": 0}

        def _wait_template(tpl, *args, **kwargs):
            if "btn_ok_convenio.png" in tpl:
                chamadas["n"] += 1
                return chamadas["n"] == 1
            return True

        runner.wait_template.side_effect = _wait_template
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_ambulatorio/btn_ok_convenio.png", threshold=0.7
        )

    def test_falha_quando_guard_nao_confirma_ambulatorio(self):
        result = _run(titulo_ok=False)
        ab05 = result.steps[4]
        assert ab05.success is False
        assert "formulario de admissao" in ab05.error
        assert len(result.steps) == 5


# ──────────────────────────────────────────────────────────────────────────────
# AB06 — Unidade Funcional (override — sem OCR, sem banco)
# ──────────────────────────────────────────────────────────────────────────────

class TestAb06Override:

    def test_sucesso(self):
        assert _run().steps[5].success is True

    def test_digita_unidade_funcional_do_yaml(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("CLINICA DE CARDIOPATIA GERAL" in c for c in chamadas)

    def test_confirma_campo_provedor_visivel(self):
        runner = _runner_ok()
        _run(runner)
        runner.wait_template.assert_any_call(
            "templates/si3/admissao_ambulatorio/campo_provedor.png",
            timeout=8, threshold=0.65,
        )

    def test_falha_se_campo_provedor_nao_aparece(self):
        runner = _runner_ok()

        def _wait_template(tpl, *args, **kwargs):
            return "campo_provedor.png" not in tpl

        runner.wait_template.side_effect = _wait_template
        result = _run(runner)
        ab06 = result.steps[5]
        assert ab06.success is False
        assert "campo_provedor nao visivel" in ab06.error

    def test_validated_true_via_confirm_template(self):
        # nao roda OCR (sem _verify_campo_obrigatorio), mas o proprio
        # confirm_template="campo_provedor.png" passado ao _step() ja
        # marca validated=True automaticamente (ver BaseFlow._step()).
        assert _run().steps[5].validated is True


# ──────────────────────────────────────────────────────────────────────────────
# AB07 — Provedor/Plano (override — ja preenchido, so fecha popups)
# ──────────────────────────────────────────────────────────────────────────────

class TestAb07Override:
    """
    Testado chamando _step_provedor_plano() diretamente (isolado do
    execute() completo) — o AB05 desta mesma subclasse tambem consome
    wait_template("btn_ok_convenio.png") no proprio loop de popup, entao
    rodar via _run() contaminaria a contagem de chamadas do AB07 com as
    do AB05. Chamada direta do metodo elimina essa interferencia (mesmo
    padrao ja usado em TestFecharPopupsConvenio do modulo 2, que testa
    flow._fechar_popups_convenio(ctx) isolado do execute()).
    """

    def test_sucesso_via_execute_completo(self):
        assert _run().steps[6].success is True

    def test_nao_digita_provedor_nem_plano(self):
        flow = AdmissaoComAgendamentoFlow()
        ctx = _ctx()
        step = flow._step_provedor_plano(ctx, _dados(), observer=None)
        assert step.success is True
        ctx.runner.type_text.assert_not_called()

    def test_fecha_popup_quando_aparece_uma_vez(self):
        flow = AdmissaoComAgendamentoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.side_effect = [True, False]
        step = flow._step_provedor_plano(ctx, _dados(), observer=None)
        assert step.success is True
        ctx.runner.safe_click.assert_called_once_with(
            "templates/si3/admissao_ambulatorio/btn_ok_convenio.png", threshold=0.7
        )

    def test_nao_clica_quando_popup_nao_aparece(self):
        flow = AdmissaoComAgendamentoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = False
        flow._step_provedor_plano(ctx, _dados(), observer=None)
        ctx.runner.safe_click.assert_not_called()

    def test_nao_e_marcado_como_validated(self):
        assert _run().steps[6].validated is None


# ──────────────────────────────────────────────────────────────────────────────
# AB11 — Medico Responsavel — digitacao direta (override — sem LOV)
# ──────────────────────────────────────────────────────────────────────────────

class TestAb11Override:

    def test_sucesso(self):
        assert _run().steps[10].success is True

    def test_step_id(self):
        assert _run().steps[10].step_id == "AB11"

    def test_digita_nome_medico_do_yaml(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("DR TESTE AUTOMACAO" in c for c in chamadas)

    def test_clica_campo_nome_medico_ab(self):
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch.object(AdmissaoComAgendamentoFlow, "_titulo_janela_contem",
                          return_value=True), \
             patch("pyautogui.click") as mock_click:
            AdmissaoComAgendamentoFlow().execute(_ctx(runner), dados=_dados())
        # campo_nome_medico_ab = (350, 410)
        assert (350, 410) in [c.args for c in mock_click.call_args_list]

    def test_nao_e_marcado_como_validated(self):
        # ao contrario do AB11 herdado (LOV + _verify_campo_obrigatorio),
        # esta versao nao roda verificacao OCR.
        assert _run().steps[10].validated is None


# ──────────────────────────────────────────────────────────────────────────────
# Abort on failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_ab03_nao_executa_ab04(self):
        runner = _runner_ok()

        def _wait_template(tpl, *args, **kwargs):
            return "btn_admitir_paciente.png" not in tpl

        runner.wait_template.side_effect = _wait_template
        result = _run(runner)
        ids = [s.step_id for s in result.steps]
        assert ids == ["AB01", "AB02", "AB03"]

    def test_falha_ab05_nao_executa_ab06(self):
        result = _run(titulo_ok=False)
        ids = [s.step_id for s in result.steps]
        assert "AB06" not in ids
        assert ids[-1] == "AB05"

    def test_observer_notificado_para_todos_steps_ok(self):
        observer = MagicMock()
        with patch("os.path.exists", return_value=False), \
             patch.object(AdmissaoComAgendamentoFlow, "_titulo_janela_contem",
                          return_value=True):
            AdmissaoComAgendamentoFlow().execute(_ctx(), dados=_dados(), observer=observer)
        assert observer.log_step_start.call_count == 16
        observer.log_flow_result.assert_called_once()
