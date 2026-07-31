# tests/unit/test_admissao_internacao_flow.py
"""
Testes unitarios do AdmissaoInternacaoFlow — 20 steps (AI01-AI19, ordem real
de execucao coloca AI19 ANTES de AI18 — ver execute(), preservado verbatim
na migracao).
Migracao src/flows/si3/ -> vtae/flows/si3/admissao/

REGRAS (mesmo padrao das outras suites desta migracao):
  - mock_sleep autouse (conftest.py) elimina todos os time.sleep reais
  - regioes_ocr vazio = bootstrap, toda verificacao OCR/verify_fill/verify_lov
    e pulada silenciosamente ou com AVISO nao-bloqueante
  - os.path.exists patchado False -> todo _tpl_existe() e confirm_template
    tolerante caem no caminho de AVISO (nao existe / template ausente)
  - _ler_estado (paciente_id) e patchado — evita depender de
    evidence/estado_jornada.json no disco durante o teste
  - Esta classe define _dado/_coord/_step PROPRIOS (nao herda de BaseFlow —
    drift ja documentado, status "Reorganizar" no estado dos flows). Os
    testes de TestHelpersLocais cobrem esse comportamento duplicado
    isoladamente, sem alterar a logica.
"""

from unittest.mock import MagicMock, patch

import pytest

from vtae.flows.si3.admissao.admissao_internacao_flow import AdmissaoInternacaoFlow
from vtae.core.result import FlowResult, CausaFalha


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _config():
    coordenadas = {
        "campo_localizar_menu":       {"x": 300, "y": 195},
        "campo_identificador":        {"x": 300, "y": 176},
        "campo_unidade_funcional":    {"x": 300, "y": 200},
        "campo_provedor":             {"x": 300, "y": 220},
        "campo_plano":                {"x": 300, "y": 240},
        "campo_carteirinha":          {"x": 300, "y": 260},
        "campo_validade_carteirinha": {"x": 300, "y": 280},
        "campo_declarante":           {"x": 200, "y": 300},
        "campo_especialidade":        {"x": 400, "y": 300},
        "campo_obs":                  {"x": 200, "y": 340},
        "campo_origem_tipo":          {"x": 200, "y": 360},
        "dropdown_origem_solicitacao": {"x": 400, "y": 360},
        "btn_lov_medico_responsavel": {"x": 500, "y": 380},
        "btn_ok_medico_resp":         {"x": 500, "y": 400},
        "campo_numero_compl":         {"x": 300, "y": 420},
        "campo_busca_medico_compl":   {"x": 300, "y": 440},
        "btn_localizar_medico_compl": {"x": 400, "y": 440},
        "btn_retornar_compl":         {"x": 400, "y": 460},
        "btn_alocar_leito":           {"x": 300, "y": 480},
        "btn_consultar_leito":        {"x": 400, "y": 480},
        "campo_busca_unidade_leito":  {"x": 300, "y": 500},
        "btn_localizar_unidade_leito": {"x": 400, "y": 500},
        "btn_ok_unidade_leito":       {"x": 400, "y": 520},
        "primeira_linha_leitos":      {"x": 300, "y": 540},
        "btn_selecionar_leito":       {"x": 400, "y": 540},
        "btn_ok_alocar":              {"x": 400, "y": 560},
        "btn_sair_alocar":            {"x": 400, "y": 580},
        "btn_sair_menu":              {"x": 10, "y": 300},
    }
    config = MagicMock()
    config.coordenadas = coordenadas
    config.regioes_ocr = {}  # bootstrap — toda verificacao OCR pulada
    config.confidence = 0.75
    return config


def _dados():
    return {
        "termo_menu_int": "INTERNACAO",
        "unidade_funcional": "UNIDADE TESTE",
        "cenario_provedor": "convenio_teste",
        "cenarios_provedor": {
            "convenio_teste": {"provedor": "SUS", "plano": "BASICO"},
        },
        "declarante": "TESTE AUTOMATIZADO",
        "especialidade": "CLINICA GERAL",
        "obs": "ADMISSAO DE TESTE",
        "origem_tipo": "RESIDENCIA",
        "origem_solicitacao": "AMBULATORIO",
        "termo_medico_compl": "%medico",
        "termo_unidade_leito": "UNIDADE TESTE",
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
    runner.verify_fill.return_value = (True, "ok")
    runner.verify_lov.return_value = (True, "12345")
    return runner


def _ctx(runner=None):
    ctx = MagicMock()
    ctx.runner = runner or _runner_ok()
    ctx.config = _config()
    ctx.evidence_dir = "evidence/"
    ctx.jab = None
    ctx.db = None
    return ctx


def _run(runner=None, dados=None, paciente_id="1000123"):
    with patch("os.path.exists", return_value=False), \
         patch(
             "vtae.flows.si3.admissao.admissao_internacao_flow._ler_estado",
             return_value=paciente_id,
         ):
        return AdmissaoInternacaoFlow().execute(
            _ctx(runner), dados=dados or _dados()
        )


# ordem real de execucao definida em execute() — AI19 roda ANTES de AI18
_IDS_ESPERADOS = [
    "AI01", "AI02", "AI03", "AI04", "AI05", "AI06", "AI07", "AI08", "AI08b",
    "AI09", "AI10", "AI11", "AI12", "AI13", "AI14", "AI15", "AI16", "AI17",
    "AI19", "AI18",
]


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert AdmissaoInternacaoFlow.FLOW_NAME == "AdmissaoInternacaoFlow"

    def test_execute_retorna_flow_result(self):
        assert isinstance(_run(), FlowResult)

    def test_execute_tem_20_steps(self):
        assert len(_run().steps) == 20

    def test_ids_corretos_e_ordem_ai19_antes_de_ai18(self):
        ids = [s.step_id for s in _run().steps]
        assert ids == _IDS_ESPERADOS

    def test_todos_steps_passam_com_runner_ok(self):
        falhos = [s for s in _run().steps if not s.success]
        assert falhos == [], [f"{s.step_id}: {s.error}" for s in falhos]

    def test_flow_sucesso(self):
        assert _run().success is True

    def test_execute_chama_add_result(self):
        ctx = _ctx()
        with patch("os.path.exists", return_value=False), \
             patch(
                 "vtae.flows.si3.admissao.admissao_internacao_flow._ler_estado",
                 return_value="1000123",
             ):
            AdmissaoInternacaoFlow().execute(ctx, dados=_dados())
        ctx.add_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# AI01 — Abrir modulo Internacao
# ──────────────────────────────────────────────────────────────────────────────

class TestAi01:

    def test_sucesso(self):
        assert _run().steps[0].success is True

    def test_step_id(self):
        assert _run().steps[0].step_id == "AI01"

    def test_digita_termo_menu(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("INTERNACAO" in c for c in chamadas)

    def test_falha_se_termo_menu_int_ausente(self):
        dados = _dados()
        del dados["termo_menu_int"]
        result = _run(dados=dados)
        assert result.steps[0].success is False
        assert len(result.steps) == 1


# ──────────────────────────────────────────────────────────────────────────────
# AI02 — Informar paciente
# ──────────────────────────────────────────────────────────────────────────────

class TestAi02:

    def test_sucesso(self):
        assert _run().steps[1].success is True

    def test_digita_paciente_id(self):
        runner = _runner_ok()
        _run(runner, paciente_id="999888")
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("999888" in c for c in chamadas)

    def test_falha_se_paciente_id_vazio(self):
        result = _run(paciente_id="")
        assert result.steps[1].success is False
        assert len(result.steps) == 2


# ──────────────────────────────────────────────────────────────────────────────
# AI03 — Pesquisar
# ──────────────────────────────────────────────────────────────────────────────

class TestAi03:

    def test_sucesso(self):
        assert _run().steps[2].success is True

    def test_clica_btn_pesquisar(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_internacao/btn_pesquisar.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AI04 — Aba Endereco
# ──────────────────────────────────────────────────────────────────────────────

class TestAi04:

    def test_sucesso(self):
        assert _run().steps[3].success is True

    def test_clica_aba_endereco(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_internacao/aba_endereco.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AI05 — Tipo Endereco condicional
# ──────────────────────────────────────────────────────────────────────────────

class TestAi05:

    def test_sucesso_bootstrap_preenche_rua(self):
        runner = _runner_ok()
        result = _run(runner)
        assert result.steps[4].success is True
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("RUA" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AI06 — Admitir Paciente
# ──────────────────────────────────────────────────────────────────────────────

class TestAi06:

    def test_sucesso(self):
        assert _run().steps[5].success is True

    def test_clica_btn_admitir(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_internacao/btn_admitir_paciente.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AI07 — Unidade Funcional
# ──────────────────────────────────────────────────────────────────────────────

class TestAi07:

    def test_sucesso(self):
        assert _run().steps[6].success is True

    def test_digita_unidade(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("UNIDADE TESTE" in c for c in chamadas)

    def test_falha_se_unidade_funcional_ausente(self):
        dados = _dados()
        del dados["unidade_funcional"]
        result = _run(dados=dados)
        assert result.steps[6].success is False


# ──────────────────────────────────────────────────────────────────────────────
# AI08 — Provedor / Plano (via cenarios_provedor)
# ──────────────────────────────────────────────────────────────────────────────

class TestAi08:

    def test_sucesso(self):
        assert _run().steps[7].success is True

    def test_digita_provedor_e_plano_do_cenario(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("SUS" in c for c in chamadas)
        assert any("BASICO" in c for c in chamadas)

    def test_falha_se_cenario_nao_encontrado(self):
        dados = _dados()
        dados["cenario_provedor"] = "inexistente"
        result = _run(dados=dados)
        ai08 = result.steps[7]
        assert ai08.success is False
        assert "nao encontrado em cenarios_provedor" in ai08.error

    def test_carteirinha_e_validade_digitadas_quando_presentes(self):
        dados = _dados()
        dados["cenarios_provedor"]["convenio_teste"]["carteirinha"] = "1234567890"
        dados["cenarios_provedor"]["convenio_teste"]["validade"] = "12/2030"
        runner = _runner_ok()
        result = _run(runner, dados=dados)
        assert result.steps[7].success is True
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("1234567890" in c for c in chamadas)
        assert any("12/2030" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AI08b — Declarante / Especialidade
# ──────────────────────────────────────────────────────────────────────────────

class TestAi08b:

    def test_sucesso(self):
        assert _run().steps[8].success is True

    def test_step_id(self):
        assert _run().steps[8].step_id == "AI08b"

    def test_falha_se_declarante_ausente(self):
        dados = _dados()
        del dados["declarante"]
        result = _run(dados=dados)
        assert result.steps[8].success is False


# ──────────────────────────────────────────────────────────────────────────────
# AI09 — Obs
# ──────────────────────────────────────────────────────────────────────────────

class TestAi09:

    def test_sucesso(self):
        assert _run().steps[9].success is True

    def test_digita_obs(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("ADMISSAO DE TESTE" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AI10 — Origem do Paciente
# ──────────────────────────────────────────────────────────────────────────────

class TestAi10:

    def test_sucesso(self):
        assert _run().steps[10].success is True

    def test_digita_origem_tipo(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("RESIDENCIA" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AI11 — Origem da Solicitacao
# ──────────────────────────────────────────────────────────────────────────────

class TestAi11:

    def test_sucesso(self):
        assert _run().steps[11].success is True

    def test_sem_template_de_opcao_cai_no_fallback_de_seta_e_passa(self):
        # os.path.exists patchado False -> _tpl_existe(opcao_*.png) False ->
        # cai no fallback (seta baixo + enter) em vez de clicar template.
        result = _run()
        assert result.steps[11].success is True


# ──────────────────────────────────────────────────────────────────────────────
# AI12 — Medico Responsavel via LOV
# ──────────────────────────────────────────────────────────────────────────────

class TestAi12:

    def test_sucesso(self):
        assert _run().steps[12].success is True

    def test_step_id(self):
        assert _run().steps[12].step_id == "AI12"


# ──────────────────────────────────────────────────────────────────────────────
# AI13 — Info. Compl. de Internacao
# ──────────────────────────────────────────────────────────────────────────────

class TestAi13:

    def test_sucesso(self):
        assert _run().steps[13].success is True

    def test_clica_btn_info_compl(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_internacao/btn_info_compl.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AI14 — Medico Complementar
# ──────────────────────────────────────────────────────────────────────────────

class TestAi14:

    def test_sucesso(self):
        assert _run().steps[14].success is True

    def test_digita_termo_medico(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("%medico" in c for c in chamadas)

    def test_falha_se_termo_medico_compl_ausente(self):
        dados = _dados()
        del dados["termo_medico_compl"]
        result = _run(dados=dados)
        assert result.steps[14].success is False


# ──────────────────────────────────────────────────────────────────────────────
# AI15 — Botao LEITO
# ──────────────────────────────────────────────────────────────────────────────

class TestAi15:

    def test_sucesso(self):
        assert _run().steps[15].success is True

    def test_clica_btn_leito(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_internacao/btn_leito.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AI16 — Alocar Leito
# ──────────────────────────────────────────────────────────────────────────────

class TestAi16:

    def test_sucesso(self):
        assert _run().steps[16].success is True

    def test_digita_termo_unidade_leito(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("UNIDADE TESTE" in c for c in chamadas)

    def test_falha_se_termo_unidade_leito_ausente(self):
        dados = _dados()
        del dados["termo_unidade_leito"]
        result = _run(dados=dados)
        assert result.steps[16].success is False


# ──────────────────────────────────────────────────────────────────────────────
# AI17 — Selecionar Leito
# ──────────────────────────────────────────────────────────────────────────────

class TestAi17:

    def test_sucesso(self):
        assert _run().steps[17].success is True

    def test_ocr_lido_propaga_numero_do_leito_quando_regiao_calibrada(self):
        config = _config()
        config.regioes_ocr = {"numero_leito": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        runner = _runner_ok()
        runner.verify_lov.return_value = (True, "12345")
        ctx = _ctx(runner)
        ctx.config = config
        with patch("os.path.exists", return_value=False), \
             patch(
                 "vtae.flows.si3.admissao.admissao_internacao_flow._ler_estado",
                 return_value="1000123",
             ):
            result = AdmissaoInternacaoFlow().execute(ctx, dados=_dados())
        step = result.steps[17]
        assert step.success is True
        assert step.ocr_lido == "12345"

    def test_falha_quando_verify_lov_retorna_vazio(self):
        config = _config()
        config.regioes_ocr = {"numero_leito": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        runner = _runner_ok()
        runner.verify_lov.return_value = (False, "")
        ctx = _ctx(runner)
        ctx.config = config
        with patch("os.path.exists", return_value=False), \
             patch(
                 "vtae.flows.si3.admissao.admissao_internacao_flow._ler_estado",
                 return_value="1000123",
             ):
            result = AdmissaoInternacaoFlow().execute(ctx, dados=_dados())
        ai17 = result.steps[17]
        assert ai17.success is False
        assert "Leito nao foi alocado" in ai17.error


# ──────────────────────────────────────────────────────────────────────────────
# AI19 — Validar Nr Admissao (executa antes de AI18, ver execute())
# ──────────────────────────────────────────────────────────────────────────────

class TestAi19:

    def test_sucesso_modo_bootstrap(self):
        assert _run().steps[18].success is True

    def test_step_id(self):
        assert _run().steps[18].step_id == "AI19"

    def test_lanca_quando_regiao_calibrada_sem_numero(self):
        config = _config()
        config.regioes_ocr = {"nr_admissao": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch(
                 "vtae.flows.si3.admissao.admissao_internacao_flow._ler_estado",
                 return_value="1000123",
             ), \
             patch("vtae.flows.si3.admissao.admissao_internacao_flow.OcrHelper") as mock_ocr:
            mock_ocr.ler_regiao.return_value = ""
            ctx = _ctx(runner)
            ctx.config = config
            result = AdmissaoInternacaoFlow().execute(ctx, dados=_dados())
        ai19 = result.steps[18]
        assert ai19.success is False
        assert "Nr Admissao nao encontrado" in ai19.error


# ──────────────────────────────────────────────────────────────────────────────
# AI18 — Sair (ultimo na ordem real de execucao)
# ──────────────────────────────────────────────────────────────────────────────

class TestAi18:

    def test_sucesso(self):
        assert _run().steps[19].success is True

    def test_step_id(self):
        assert _run().steps[19].step_id == "AI18"

    def test_falha_quando_login_nao_confirma(self):
        runner = _runner_ok()

        def _wait_template(tpl, *args, **kwargs):
            return "btn_entrar.png" not in tpl

        runner.wait_template.side_effect = _wait_template
        result = _run(runner)
        ai18 = result.steps[19]
        assert ai18.success is False
        assert "sair-3" in ai18.error


# ──────────────────────────────────────────────────────────────────────────────
# Abort on failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_ai01_nao_executa_ai02(self):
        dados = _dados()
        del dados["termo_menu_int"]
        result = _run(dados=dados)
        ids = [s.step_id for s in result.steps]
        assert ids == ["AI01"]

    def test_observer_notificado_para_todos_steps_ok(self):
        observer = MagicMock()
        with patch("os.path.exists", return_value=False), \
             patch(
                 "vtae.flows.si3.admissao.admissao_internacao_flow._ler_estado",
                 return_value="1000123",
             ):
            AdmissaoInternacaoFlow().execute(_ctx(), dados=_dados(), observer=observer)
        assert observer.log_step_start.call_count == 20
        observer.log_flow_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers locais (_dado / _coord / _step) — duplicados de BaseFlow, drift
# ja documentado (status "Reorganizar"). Testados isoladamente para garantir
# que o comportamento duplicado nao mudou na migracao.
# ──────────────────────────────────────────────────────────────────────────────

class TestDadoLocal:

    def test_retorna_valor_quando_chave_existe(self):
        flow = AdmissaoInternacaoFlow()
        assert flow._dado({"x": "1"}, "x", "AI01") == "1"

    def test_lanca_assertion_error_quando_chave_ausente(self):
        flow = AdmissaoInternacaoFlow()
        with pytest.raises(AssertionError, match="ausente no config"):
            flow._dado({}, "x", "AI01")


class TestCoordLocal:

    def test_retorna_tupla_xy(self):
        flow = AdmissaoInternacaoFlow()
        assert flow._coord({"campo": {"x": 1, "y": 2}}, "campo") == (1, 2)

    def test_lanca_assertion_error_quando_ausente(self):
        flow = AdmissaoInternacaoFlow()
        with pytest.raises(AssertionError, match="nao encontrada em coordenadas"):
            flow._coord({}, "campo_ausente")


class TestStepLocal:

    def test_sucesso_sem_confirm_template(self):
        flow = AdmissaoInternacaoFlow()
        step = flow._step("AI01", "abrir", lambda: "shot.png", None)
        assert step.success is True
        assert step.screenshot_path == "shot.png"

    def test_excecao_generica_classifica_desconhecida(self):
        flow = AdmissaoInternacaoFlow()

        def fn():
            raise RuntimeError("erro qualquer")

        step = flow._step("AI01", "abrir", fn, None)
        assert step.success is False
        assert step.causa_falha == CausaFalha.DESCONHECIDA
