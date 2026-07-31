# tests/unit/test_agendamento_flow.py
"""
Testes unitarios do AgendamentoFlow — 13 steps (AG01-AG13)
Migracao src/flows/si3/agendamento_flow.py -> vtae/flows/si3/agendamento/

Historicamente esta e a flow onde o _step() canonico do BaseFlow nasceu
(v0.5.9) — nenhum teste unitario existia ate esta migracao.

REGRAS (mesmo padrao dos demais flows migrados):
  - mock_sleep autouse (conftest.py) elimina todos os time.sleep reais
  - os.path.exists=False forca todos os _tpl_existe() do AG08/AG09/AG11
    para o caminho de bootstrap/fallback (deterministic, sem depender
    de templates reais no disco)
  - _ler_estado/_salvar_estado (AG10/AG11) patchados no modulo do flow —
    evita depender de evidence/estado_jornada.json real
  - regioes_ocr = {} (bootstrap) — AG07 pula verify_lov com AVISO
  - AG08 nao lanca nenhuma excecao (100% tolerante) — sem teste de falha
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from vtae.flows.si3.agendamento.agendamento_flow import AgendamentoFlow
from vtae.core.result import FlowResult


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _config():
    coordenadas = {
        "campo_localizar_menu":       {"x": 624, "y": 578},
        "campo_provedor_ag":          {"x": 39,  "y": 145},
        "campo_plano_ag":             {"x": 526, "y": 145},
        "campo_codigo_proc_ag":       {"x": 30,  "y": 213},
        "campo_complemento_ag":       {"x": 392, "y": 213},
        "campo_busca_area_ag":        {"x": 748, "y": 212},
        "btn_ok_area_ag":             {"x": 1055, "y": 574},
        "btn_lov_executante_ag":      {"x": 306, "y": 387},
        "campo_busca_executante_ag":  {"x": 85,  "y": 458},
        "item_medico_executante_ag":  {"x": 91,  "y": 518},
        "btn_agendar_ag":             {"x": 888, "y": 656},
        "btn_fechar_info_ag":         {"x": 737, "y": 621},
        "btn_ok_recursos_ag":         {"x": 1095, "y": 586},
        "item_recurso_ag":            {"x": 200, "y": 300},
        "btn_ok_recurso_ag":          {"x": 400, "y": 300},
        "campo_data_ag":              {"x": 738, "y": 334},
        "campo_hora_ag":              {"x": 851, "y": 335},
        "btn_ok_horario_ag":          {"x": 820, "y": 505},
        "campo_id_paciente_ag":       {"x": 34,  "y": 151},
        "btn_confirmar_ag":           {"x": 833, "y": 617},
    }
    config = MagicMock()
    config.coordenadas = coordenadas
    config.regioes_ocr = {}  # bootstrap — AG07 verify_lov pulado
    return config


def _dados():
    return {
        "termo_menu_ag": "AGENDAR",
        "provedor_ag": "SUS",
        "plano_ag": "SUS",
        "codigo_proc_ag": "CARDIO",
        "complemento_ag": "SEGUIMENTO",
        "area_executora_ag": "UNGRA",
        "termo_executante_ag": "1208.2",
        "horas_offset_ag": 3,
    }


def _runner_ok():
    runner = MagicMock()
    runner.screenshot.return_value = "evidence/step.png"
    runner.wait_template.return_value = True
    runner.safe_click.return_value = True
    runner.double_click.return_value = True
    runner.type_text.return_value = None
    runner.verify_lov.return_value = True
    return runner


def _ctx(runner=None):
    ctx = MagicMock()
    ctx.runner = runner or _runner_ok()
    ctx.config = _config()
    ctx.evidence_dir = "evidence/"
    return ctx


def _run(runner=None, dados=None, paciente_id="1000123"):
    with patch("os.path.exists", return_value=False), \
         patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
               return_value=paciente_id), \
         patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado"):
        return AgendamentoFlow().execute(_ctx(runner), dados=dados or _dados())


def _wait_template_falha_em(*templates_que_falham):
    """
    Retorna um side_effect para runner.wait_template que retorna False
    apenas para templates cujo nome contenha um dos textos informados —
    True para qualquer outro (mesmo padrao ja usado no fix de TestAb03
    do modulo de admissao_ambulatorio).
    """
    def _wt(tpl, *args, **kwargs):
        return not any(t in tpl for t in templates_que_falham)
    return _wt


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert AgendamentoFlow.FLOW_NAME == "AgendamentoFlow"

    def test_execute_retorna_flow_result(self):
        assert isinstance(_run(), FlowResult)

    def test_execute_tem_13_steps(self):
        assert len(_run().steps) == 13

    def test_ids_corretos(self):
        ids = [s.step_id for s in _run().steps]
        assert ids == [f"AG{i:02d}" for i in range(1, 14)]

    def test_todos_steps_passam_com_runner_ok(self):
        falhos = [s for s in _run().steps if not s.success]
        assert falhos == [], [f"{s.step_id}: {s.error}" for s in falhos]

    def test_flow_sucesso(self):
        assert _run().success is True

    def test_execute_chama_add_result(self):
        ctx = _ctx()
        with patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado"):
            AgendamentoFlow().execute(ctx, dados=_dados())
        ctx.add_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# AG01 — Abrir modulo Agendar
# ──────────────────────────────────────────────────────────────────────────────

class TestAg01:

    def test_sucesso(self):
        assert _run().steps[0].success is True

    def test_digita_termo_menu(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("AGENDAR" in c for c in chamadas)

    def test_falha_se_popup_continuar_busca_nao_aparece(self):
        runner = _runner_ok()
        runner.wait_template.side_effect = _wait_template_falha_em("btn_nao_popup.png")
        result = _run(runner)
        ag01 = result.steps[0]
        assert ag01.success is False
        assert "Continuar Busca" in ag01.error
        assert len(result.steps) == 1

    def test_falha_se_tela_agendar_nao_abre(self):
        runner = _runner_ok()
        runner.wait_template.side_effect = _wait_template_falha_em("tela_agendar.png")
        result = _run(runner)
        ag01 = result.steps[0]
        assert ag01.success is False
        assert "Tela de Agendar nao abriu" in ag01.error


# ──────────────────────────────────────────────────────────────────────────────
# AG02 — Provedor
# ──────────────────────────────────────────────────────────────────────────────

class TestAg02:

    def test_sucesso(self):
        assert _run().steps[1].success is True

    def test_digita_provedor(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("SUS" in c for c in chamadas)

    def test_fecha_popup_ok_quando_aparece(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/agendamento/btn_ok_popup_ag.png", threshold=0.7
        )

    def test_nao_fecha_popup_quando_nao_aparece(self):
        # escopado so ao popup do AG02 — wait_template=False global quebraria
        # o proprio AG01 (btn_nao_popup.png/tela_agendar.png precisam de True)
        runner = _runner_ok()

        def _wt(tpl, *args, **kwargs):
            return "btn_ok_popup_ag.png" not in tpl

        runner.wait_template.side_effect = _wt
        _run(runner)
        chamadas_popup = [
            c for c in runner.safe_click.call_args_list
            if "btn_ok_popup_ag.png" in str(c)
        ]
        assert chamadas_popup == []


# ──────────────────────────────────────────────────────────────────────────────
# AG03 — Plano
# ──────────────────────────────────────────────────────────────────────────────

class TestAg03:

    def test_sucesso(self):
        assert _run().steps[2].success is True

    def test_digita_plano(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("SUS" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AG04 — Codigo do procedimento
# ──────────────────────────────────────────────────────────────────────────────

class TestAg04:

    def test_sucesso(self):
        assert _run().steps[3].success is True

    def test_digita_codigo(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("CARDIO" in c for c in chamadas)

    def test_falha_se_codigo_ausente_no_dados(self):
        dados = _dados()
        del dados["codigo_proc_ag"]
        result = _run(dados=dados)
        assert result.steps[3].success is False


# ──────────────────────────────────────────────────────────────────────────────
# AG05 — Complemento
# ──────────────────────────────────────────────────────────────────────────────

class TestAg05:

    def test_sucesso(self):
        assert _run().steps[4].success is True

    def test_digita_complemento(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("SEGUIMENTO" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AG06 — Area Executora
# ──────────────────────────────────────────────────────────────────────────────

class TestAg06:

    def test_sucesso(self):
        assert _run().steps[5].success is True

    def test_digita_area_executora(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("UNGRA" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AG07 — Executante via LOV
# ──────────────────────────────────────────────────────────────────────────────

class TestAg07:

    def test_sucesso(self):
        assert _run().steps[6].success is True

    def test_validated_true(self):
        assert _run().steps[6].validated is True

    def test_digita_termo_executante(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("1208.2" in c for c in chamadas)

    def test_pula_verify_lov_quando_regiao_nao_calibrada(self):
        # regioes_ocr={} (bootstrap) -> verify_lov nunca chamado
        runner = _runner_ok()
        _run(runner)
        runner.verify_lov.assert_not_called()

    def test_falha_quando_regiao_calibrada_e_verify_lov_retorna_false(self):
        config = _config()
        config.regioes_ocr = {
            "campo_executante_ag": {"x1": 15, "y1": 379, "x2": 233, "y2": 395}
        }
        runner = _runner_ok()
        runner.verify_lov.return_value = False
        ctx = _ctx(runner)
        ctx.config = config
        with patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado"):
            result = AgendamentoFlow().execute(ctx, dados=_dados())
        ag07 = result.steps[6]
        assert ag07.success is False
        assert "campo Executante ficou VAZIO" in ag07.error

    def test_sucesso_quando_regiao_calibrada_e_verify_lov_retorna_true(self):
        config = _config()
        config.regioes_ocr = {
            "campo_executante_ag": {"x1": 15, "y1": 379, "x2": 233, "y2": 395}
        }
        runner = _runner_ok()
        runner.verify_lov.return_value = True
        ctx = _ctx(runner)
        ctx.config = config
        with patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado"):
            result = AgendamentoFlow().execute(ctx, dados=_dados())
        assert result.steps[6].success is True
        runner.verify_lov.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# AG08 — Clicar Agendar + fechar popups (100% tolerante — nunca lanca excecao)
# ──────────────────────────────────────────────────────────────────────────────

class TestAg08:

    def test_sucesso(self):
        assert _run().steps[7].success is True

    def test_clica_btn_agendar(self):
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado"), \
             patch("pyautogui.click") as mock_click:
            AgendamentoFlow().execute(_ctx(runner), dados=_dados())
        assert (888, 656) in [c.args for c in mock_click.call_args_list]

    def test_fecha_info_profissional_por_coordenada_quando_template_ausente(self):
        # os.path.exists=False -> _tpl_existe(tela_info_profissional_ag) = False
        # -> cai no else: fecha por coordenada, sem depender do template.
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado"), \
             patch("pyautogui.click") as mock_click:
            AgendamentoFlow().execute(_ctx(runner), dados=_dados())
        assert (737, 621) in [c.args for c in mock_click.call_args_list]


# ──────────────────────────────────────────────────────────────────────────────
# AG09 — Tela Recursos disponiveis — tolerante
# ──────────────────────────────────────────────────────────────────────────────

class TestAg09:

    def test_sucesso_quando_tela_recursos_nao_aparece(self):
        # os.path.exists=False -> _tpl_existe(tela_recursos_ag) = False ->
        # na_tela_recursos fica False -> nenhum clique extra
        assert _run().steps[8].success is True

    def test_nao_clica_recursos_quando_tela_nao_existe(self):
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado"):
            AgendamentoFlow().execute(_ctx(runner), dados=_dados())
        chamadas_recursos = [
            c for c in runner.safe_click.call_args_list
            if "btn_ok_recursos_ag" in str(c)
        ]
        assert chamadas_recursos == []


# ──────────────────────────────────────────────────────────────────────────────
# AG10 — Data + Hora Inicial
# ──────────────────────────────────────────────────────────────────────────────

class TestAg10:

    def test_sucesso(self):
        assert _run().steps[9].success is True

    def test_salva_data_e_hora_no_estado(self):
        runner = _runner_ok()
        with patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado") as mock_salvar:
            AgendamentoFlow().execute(_ctx(runner), dados=_dados())
        chaves_salvas = [c.args[0] for c in mock_salvar.call_args_list]
        assert "hora_agendamento" in chaves_salvas
        assert "data_agendamento" in chaves_salvas

    def test_falha_se_horas_offset_ausente(self):
        dados = _dados()
        del dados["horas_offset_ag"]
        result = _run(dados=dados)
        assert result.steps[9].success is False


# ──────────────────────────────────────────────────────────────────────────────
# AG11 — Confirmar Paciente
# ──────────────────────────────────────────────────────────────────────────────

class TestAg11:

    def test_sucesso_modo_bootstrap_sem_template(self):
        # os.path.exists=False -> _tpl_existe(tela_conclusao_ag) = False ->
        # cai no fallback (AVISO + timeout fixo), sem lancar excecao.
        assert _run().steps[10].success is True

    def test_le_paciente_id_do_estado(self):
        runner = _runner_ok()
        _run(runner, paciente_id="9999999")
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("9999999" in c for c in chamadas)

    def test_falha_quando_tela_conclusao_nao_confirma_com_template_calibrado(self):
        # chamada direta do metodo do step — isola do execute() completo,
        # que quebraria em AG01/AG08/AG09 se os.path.exists=True e
        # wait_template=False fossem aplicados globalmente ao flow inteiro
        # (mesmo cuidado ja adotado em TestAb07Override do modulo de
        # admissao_com_agendamento).
        flow = AgendamentoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = False
        with patch("os.path.exists", return_value=True), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"):
            step = flow._step_confirmar_paciente(ctx, ctx.config.coordenadas, observer=None)
        assert step.success is False
        assert "tela Conclusao nao apareceu" in step.error


# ──────────────────────────────────────────────────────────────────────────────
# AG12 — Fechar tela de Conclusao
# ──────────────────────────────────────────────────────────────────────────────

class TestAg12:

    def test_sucesso(self):
        assert _run().steps[11].success is True

    def test_clica_btn_fechar(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/agendamento/btn_fechar_ag.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AG13 — Sair
# ──────────────────────────────────────────────────────────────────────────────

class TestAg13:

    def test_sucesso(self):
        assert _run().steps[12].success is True

    def test_clica_btn_sair_duas_vezes(self):
        runner = _runner_ok()
        _run(runner)
        chamadas_sair = [
            c for c in runner.safe_click.call_args_list
            if "btn_sair_ag.png" in str(c)
        ]
        assert len(chamadas_sair) == 2


# ──────────────────────────────────────────────────────────────────────────────
# Abort on failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_ag01_nao_executa_ag02(self):
        runner = _runner_ok()
        runner.wait_template.side_effect = _wait_template_falha_em("btn_nao_popup.png")
        result = _run(runner)
        ids = [s.step_id for s in result.steps]
        assert ids == ["AG01"]

    def test_falha_ag04_nao_executa_ag05(self):
        dados = _dados()
        del dados["codigo_proc_ag"]
        result = _run(dados=dados)
        ids = [s.step_id for s in result.steps]
        assert ids == ["AG01", "AG02", "AG03", "AG04"]

    def test_observer_notificado_para_todos_steps_ok(self):
        observer = MagicMock()
        with patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._ler_estado",
                   return_value="1000123"), \
             patch("vtae.flows.si3.agendamento.agendamento_flow._salvar_estado"):
            AgendamentoFlow().execute(_ctx(), dados=_dados(), observer=observer)
        assert observer.log_step_start.call_count == 13
        observer.log_flow_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# _fechar_popup_ok — helper privado
# ──────────────────────────────────────────────────────────────────────────────

class TestFecharPopupOk:

    def test_retorna_true_e_clica_quando_popup_aparece(self):
        flow = AgendamentoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = True
        assert flow._fechar_popup_ok(ctx, "templates/x.png") is True
        ctx.runner.safe_click.assert_called_once_with("templates/x.png", threshold=0.7)

    def test_retorna_false_quando_popup_nao_aparece(self):
        flow = AgendamentoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = False
        assert flow._fechar_popup_ok(ctx, "templates/x.png") is False
        ctx.runner.safe_click.assert_not_called()
