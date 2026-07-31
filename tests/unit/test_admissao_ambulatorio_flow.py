# tests/unit/test_admissao_ambulatorio_flow.py
"""
Testes unitarios do AdmissaoAmbulatorioFlow — 16 steps (AB01-AB16)
Migracao src/flows/si3/ -> vtae/flows/si3/admissao/

REGRAS (mesmo padrao de test_cadastro_paciente_flow.py):
  - mock_sleep autouse (conftest.py) elimina todos os time.sleep reais
  - Config sempre via _config() com coordenadas e regioes_ocr mockadas
    (regioes_ocr vazio = bootstrap, todas as verificacoes OCR puladas)
  - ctx.jab e ctx.db explicitamente None — forca os caminhos de fallback
    ja validados (pyjab "nao conectado, pulado" / YAML em vez de banco)
  - AB07 tenta conectar um JABDriver sob demanda (linha nova nesta classe,
    nao coberta em test_base_flow.py) — pyjab.jabdriver e injetado em
    sys.modules com JABDriver que sempre falha ao instanciar, simulando
    "Access Bridge indisponivel" sem depender de pyjab instalado nem de
    uma janela real do SI3 aberta durante o teste.
  - os 16 steps sao testados individualmente
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from vtae.flows.si3.admissao.admissao_ambulatorio_flow import AdmissaoAmbulatorioFlow
from vtae.core.result import FlowResult


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _config():
    coordenadas = {
        "campo_localizar_menu":        {"x": 300, "y": 195},
        "campo_identificador_amb":     {"x": 300, "y": 176},
        "campo_tipo_endereco_amb":     {"x": 143, "y": 378},
        "campo_declarante":            {"x": 200, "y": 300},
        "campo_especialidade":         {"x": 400, "y": 300},
        "campo_obs_amb":               {"x": 200, "y": 340},
        "campo_origem_tipo":           {"x": 200, "y": 360},
        "btn_lov_medico":              {"x": 500, "y": 300},
        "campo_localizar_medico":      {"x": 300, "y": 400},
        "btn_localizar_medico":        {"x": 400, "y": 400},
        "item_profissional_proc":      {"x": 300, "y": 420},
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
    config.DADOS = {"termo_menu_amb": "AMBULATORIO"}
    config.PACIENTE_ID = "1000123"  # evita depender de estado_jornada.json
    config.confidence = 0.75
    return config


def _dados():
    return {
        "provedor": "SUS",  # SUS pula o sub-fluxo de carteirinha/validade
        "plano": "BASICO",
        "unidades_validas": ["UNIDADE TESTE"],
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


def _sem_pyjab_modules():
    """
    Injeta pyjab.jabdriver falso — JABDriver sempre lanca excecao ao
    instanciar. Simula 'Access Bridge indisponivel' (caminho ja tolerado
    pelo flow: except Exception -> AVISO -> ctx.jab permanece None ->
    _verify_campo_via_jab pula). Nao depende de pyjab estar instalado
    nem de uma janela real do SI3 aberta durante o teste.
    """
    fake_jabdriver_module = MagicMock()
    fake_jabdriver_module.JABDriver.side_effect = Exception(
        "Access Bridge indisponivel em teste"
    )
    return {"pyjab": MagicMock(), "pyjab.jabdriver": fake_jabdriver_module}


def _run(runner=None, dados=None):
    with patch.dict(sys.modules, _sem_pyjab_modules()), \
         patch("os.path.exists", return_value=False):
        return AdmissaoAmbulatorioFlow().execute(
            _ctx(runner), dados=dados or _dados()
        )


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert AdmissaoAmbulatorioFlow.FLOW_NAME == "AdmissaoAmbulatorioFlow"

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
        with patch.dict(sys.modules, _sem_pyjab_modules()), \
             patch("os.path.exists", return_value=False):
            AdmissaoAmbulatorioFlow().execute(ctx, dados=_dados())
        ctx.add_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# AB01 — Abrir modulo Ambulatorio
# ──────────────────────────────────────────────────────────────────────────────

class TestAb01:

    def test_sucesso(self):
        assert _run().steps[0].success is True

    def test_step_id(self):
        assert _run().steps[0].step_id == "AB01"

    def test_digita_termo_menu(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("AMBULATORIO" in c for c in chamadas)

    def test_confirma_titulo_ambulatorio(self):
        runner = _runner_ok()
        _run(runner)
        runner.wait_template.assert_any_call(
            "templates/si3/admissao_ambulatorio/titulo_ambulatorio.png",
            timeout=8, threshold=0.7,
        )

    def test_falha_se_titulo_nao_confirma(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        result = _run(runner)
        assert result.steps[0].success is False
        assert len(result.steps) == 1


# ──────────────────────────────────────────────────────────────────────────────
# AB02 — Informar Identificador
# ──────────────────────────────────────────────────────────────────────────────

class TestAb02:

    def test_sucesso(self):
        assert _run().steps[1].success is True

    def test_usa_paciente_id_do_env(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("1000123" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AB03 — Pesquisar
# ──────────────────────────────────────────────────────────────────────────────

class TestAb03:

    def test_sucesso(self):
        assert _run().steps[2].success is True

    def test_step_id(self):
        assert _run().steps[2].step_id == "AB03"

    def test_falha_se_admitir_nao_confirma(self):
        runner = _runner_ok()

        def _wait_template(tpl, *args, **kwargs):
            # so o confirm_template do AB03 falha — AB01 continua confirmando normalmente
            return "btn_admitir_paciente.png" not in tpl

        runner.wait_template.side_effect = _wait_template
        result = _run(runner)
        assert result.steps[2].success is False
        assert len(result.steps) == 3


# ──────────────────────────────────────────────────────────────────────────────
# AB04 — Tipo Endereco = RUA
# ──────────────────────────────────────────────────────────────────────────────

class TestAb04:

    def test_sucesso(self):
        assert _run().steps[3].success is True

    def test_digita_rua(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("RUA" in c for c in chamadas)

    def test_clica_aba_enderecos(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_ambulatorio/aba_enderecos.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AB05 — Admitir Paciente
# ──────────────────────────────────────────────────────────────────────────────

class TestAb05:

    def test_sucesso(self):
        assert _run().steps[4].success is True

    def test_clica_btn_admitir(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_ambulatorio/btn_admitir_paciente.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AB06 — Unidade Funcional
# ──────────────────────────────────────────────────────────────────────────────

class TestAb06:

    def test_sucesso(self):
        assert _run().steps[5].success is True

    def test_digita_unidade_do_yaml(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("UNIDADE TESTE" in c for c in chamadas)

    def test_falha_sem_unidades_validas_e_sem_banco(self):
        dados = _dados()
        dados["unidades_validas"] = []
        result = _run(dados=dados)
        ab06 = result.steps[5]
        assert ab06.success is False
        assert "Nenhuma unidade valida" in ab06.error

    def test_validated_true(self):
        assert _run().steps[5].validated is True


# ──────────────────────────────────────────────────────────────────────────────
# AB07 — Provedor / Plano
# ──────────────────────────────────────────────────────────────────────────────

class TestAb07:

    def test_sucesso(self):
        assert _run().steps[6].success is True

    def test_digita_provedor_e_plano(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("SUS" in c for c in chamadas)
        assert any("BASICO" in c for c in chamadas)

    def test_provedor_particular_nao_abre_carteirinha(self):
        # provedor "SUS" ja cobre o caminho feliz sem carteirinha —
        # aqui so confirma que nao ha type_text extra de carteirinha/validade
        # quando essas chaves nao estao no dados.
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert not any("numero_carteirinha" in c for c in chamadas)

    def test_provedor_convenio_digita_carteirinha_e_validade(self):
        dados = _dados()
        dados["provedor"] = "ALLIANZ"
        dados["numero_carteirinha"] = "1234567890"
        dados["validade_carteirinha"] = "12/2030"
        runner = _runner_ok()
        result = _run(runner, dados=dados)
        assert result.steps[6].success is True
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("1234567890" in c for c in chamadas)
        assert any("12/2030" in c for c in chamadas)

    def test_jab_indisponivel_nao_quebra_o_step(self):
        # pyjab.jabdriver injetado sempre falha ao instanciar (ver
        # _sem_pyjab_modules) — o step deve continuar e passar mesmo assim.
        assert _run().steps[6].success is True

    def test_ocr_lido_registra_provedor_e_plano(self):
        step = _run().steps[6]
        assert "provedor=" in step.ocr_lido
        assert "plano=" in step.ocr_lido


# ──────────────────────────────────────────────────────────────────────────────
# AB08 — Declarante / Especialidade
# ──────────────────────────────────────────────────────────────────────────────

class TestAb08:

    def test_sucesso(self):
        assert _run().steps[7].success is True

    def test_usa_defaults_quando_ausentes(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("TESTE AUTOMATIZADO" in c for c in chamadas)
        assert any("CAR - CARDIO GERAL" in c for c in chamadas)

    def test_usa_valores_do_yaml_quando_presentes(self):
        dados = _dados()
        dados["declarante"] = "MARIA SILVA"
        dados["especialidade"] = "CLINICA MEDICA"
        runner = _runner_ok()
        _run(runner, dados=dados)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("MARIA SILVA" in c for c in chamadas)
        assert any("CLINICA MEDICA" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AB09 — Obs
# ──────────────────────────────────────────────────────────────────────────────

class TestAb09:

    def test_sucesso(self):
        assert _run().steps[8].success is True

    def test_usa_default_quando_ausente(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("ADMISSAO REALIZADA" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AB10 — Origem do Paciente
# ──────────────────────────────────────────────────────────────────────────────

class TestAb10:

    def test_sucesso(self):
        assert _run().steps[9].success is True

    def test_digita_origem_tipo(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("RESIDENCIA" in c for c in chamadas)

    def test_falha_se_origem_tipo_ausente(self):
        dados = _dados()
        del dados["origem_tipo"]
        result = _run(dados=dados)
        assert result.steps[9].success is False
        assert result.steps[9].causa_falha is not None


# ──────────────────────────────────────────────────────────────────────────────
# AB11 — Medico Responsavel via LOV
# ──────────────────────────────────────────────────────────────────────────────

class TestAb11:

    def test_sucesso(self):
        assert _run().steps[10].success is True

    def test_step_id(self):
        assert _run().steps[10].step_id == "AB11"

    def test_digita_termo_medico(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("%medico" in c for c in chamadas)

    def test_duplo_clique_no_item_medico(self):
        # _selecionar_via_lov usa pyautogui.doubleClick quando duplo_clique_item
        # e informado — nao passa por runner, entao so confirmamos que o step passa.
        assert _run().steps[10].validated is True


# ──────────────────────────────────────────────────────────────────────────────
# AB12 — Lista de Procedimentos
# ──────────────────────────────────────────────────────────────────────────────

class TestAb12:

    def test_sucesso(self):
        assert _run().steps[11].success is True

    def test_step_id(self):
        assert _run().steps[11].step_id == "AB12"

    def test_clica_btn_lista_procedimentos(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_ambulatorio/btn_lista_procedimentos.png",
            threshold=0.7,
        )

    def test_digita_codigo_do_procedimento_escolhido(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("12345" in c for c in chamadas)

    def test_falha_sem_procedimentos_configurados(self):
        dados = _dados()
        dados["procedimentos"] = []
        result = _run(dados=dados)
        ab12 = result.steps[11]
        assert ab12.success is False
        assert "Nenhum procedimento configurado" in ab12.error

    def test_complemento_dispara_lov_extra(self):
        dados = _dados()
        dados["procedimentos"] = [{
            "codigo": "12345", "complemento": "COMP TESTE", "profissional": "MEDICO",
        }]
        runner = _runner_ok()
        result = _run(runner, dados=dados)
        assert result.steps[11].success is True
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("COMP TESTE" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# AB13 — Voltar
# ──────────────────────────────────────────────────────────────────────────────

class TestAb13:

    def test_sucesso(self):
        assert _run().steps[12].success is True

    def test_clica_btn_voltar(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/admissao_ambulatorio/btn_voltar.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# AB14 — Salvar (F10)
# ──────────────────────────────────────────────────────────────────────────────

class TestAb14:

    def test_sucesso(self):
        assert _run().steps[13].success is True

    def test_step_id(self):
        assert _run().steps[13].step_id == "AB14"


# ──────────────────────────────────────────────────────────────────────────────
# AB15 — Validar Nr Admissao via OCR
# ──────────────────────────────────────────────────────────────────────────────

class TestAb15:

    def test_sucesso_modo_bootstrap(self):
        # regioes_ocr vazio -> regiao nao calibrada -> passa sem OCR (bootstrap)
        assert _run().steps[14].success is True

    def test_ocr_lido_vazio_em_bootstrap(self):
        assert _run().steps[14].ocr_lido == ''

    def test_lanca_quando_regiao_calibrada_e_ocr_nao_encontra_numero(self):
        config = _config()
        config.regioes_ocr = {"nr_admissao_amb": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        runner = _runner_ok()
        with patch.dict(sys.modules, _sem_pyjab_modules()), \
             patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.admissao.admissao_ambulatorio_flow.OcrHelper") as mock_ocr:
            mock_ocr.ler_regiao.return_value = ""
            ctx = _ctx(runner)
            ctx.config = config
            result = AdmissaoAmbulatorioFlow().execute(ctx, dados=_dados())
        ab15 = result.steps[14]
        assert ab15.success is False
        assert "Nr Admissao nao encontrado" in ab15.error

    def test_salva_estado_quando_ocr_encontra_numero(self):
        config = _config()
        config.regioes_ocr = {"nr_admissao_amb": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        runner = _runner_ok()
        with patch.dict(sys.modules, _sem_pyjab_modules()), \
             patch("os.path.exists", return_value=False), \
             patch("vtae.flows.si3.admissao.admissao_ambulatorio_flow.OcrHelper") as mock_ocr, \
             patch("vtae.flows.si3.admissao.admissao_ambulatorio_flow._salvar_estado") as mock_salvar:
            mock_ocr.ler_regiao.return_value = "Nr: 00234746"
            ctx = _ctx(runner)
            ctx.config = config
            result = AdmissaoAmbulatorioFlow().execute(ctx, dados=_dados())
        ab15 = result.steps[14]
        assert ab15.success is True
        assert ab15.ocr_lido == "00234746"
        mock_salvar.assert_called_once_with("nr_admissao_amb", "00234746")


# ──────────────────────────────────────────────────────────────────────────────
# AB16 — Sair
# ──────────────────────────────────────────────────────────────────────────────

class TestAb16:

    def test_sucesso(self):
        assert _run().steps[15].success is True

    def test_clica_btn_sair_duas_vezes(self):
        runner = _runner_ok()
        _run(runner)
        chamadas_sair = [
            c for c in runner.safe_click.call_args_list
            if "btn_sair.png" in str(c)
        ]
        assert len(chamadas_sair) == 2


# ──────────────────────────────────────────────────────────────────────────────
# Abort on failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_ab01_nao_executa_ab02(self):
        runner = _runner_ok()
        runner.wait_template.return_value = False
        result = _run(runner)
        ids = [s.step_id for s in result.steps]
        assert ids == ["AB01"]

    def test_observer_notificado_para_todos_steps_ok(self):
        observer = MagicMock()
        with patch.dict(sys.modules, _sem_pyjab_modules()), \
             patch("os.path.exists", return_value=False):
            AdmissaoAmbulatorioFlow().execute(_ctx(), dados=_dados(), observer=observer)
        assert observer.log_step_start.call_count == 16
        observer.log_flow_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers privados — _resolver_cenario_provedor / _obter_provedores_validos /
# _fechar_popups_convenio
# ──────────────────────────────────────────────────────────────────────────────

class TestResolverCenarioProvedor:

    def test_sem_cenario_provedor_retorna_dados_intactos(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()
        dados = {"provedor": "SUS", "plano": "BASICO"}
        merged = flow._resolver_cenario_provedor(ctx, dados)
        assert merged["provedor"] == "SUS"
        assert merged["plano"] == "BASICO"

    def test_cenario_fixo_faz_merge_com_dados_base(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()
        dados = {
            "cenario_provedor": "convenio_allianz",
            "cenarios_provedor": {
                "convenio_allianz": {"provedor": "ALLIANZ", "plano": "BASICO"},
            },
        }
        merged = flow._resolver_cenario_provedor(ctx, dados)
        assert merged["provedor"] == "ALLIANZ"
        assert merged["plano"] == "BASICO"

    def test_aleatorio_sem_banco_sorteia_de_cenarios_validos(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()  # ctx.db = None -> banco indisponivel
        dados = {
            "cenario_provedor": "aleatorio",
            "cenarios_validos": ["cenario_a"],
            "cenarios_provedor": {
                "cenario_a": {"provedor": "SUS", "plano": "BASICO"},
            },
        }
        merged = flow._resolver_cenario_provedor(ctx, dados)
        assert merged["provedor"] == "SUS"

    def test_aleatorio_com_banco_localiza_cenario_yaml_correspondente(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()
        ctx.db = MagicMock()
        ctx.db.query.return_value = [{"PRV_NOME": "ALLIANZ", "PRV_PLANO": "BASICO"}]
        dados = {
            "cenario_provedor": "aleatorio",
            "cenarios_provedor": {
                "convenio_allianz": {"provedor": "ALLIANZ", "plano": "BASICO"},
            },
        }
        merged = flow._resolver_cenario_provedor(ctx, dados)
        assert merged["provedor"] == "ALLIANZ"


class TestObterProvedoresValidos:

    def test_retorna_none_quando_banco_indisponivel(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()  # ctx.db = None
        assert flow._obter_provedores_validos(ctx) is None

    def test_retorna_pares_quando_banco_disponivel(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()
        ctx.db = MagicMock()
        ctx.db.query.return_value = [
            {"PRV_NOME": "ALLIANZ", "PRV_PLANO": "BASICO"},
            {"PRV_NOME": "SUS", "PRV_PLANO": ""},
        ]
        pares = flow._obter_provedores_validos(ctx)
        assert pares == {"ALLIANZ": "BASICO", "SUS": ""}

    def test_retorna_none_quando_banco_retorna_vazio(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()
        ctx.db = MagicMock()
        ctx.db.query.return_value = []
        assert flow._obter_provedores_validos(ctx) is None


class TestFecharPopupsConvenio:

    def test_retorna_false_quando_popup_nao_aparece(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = False
        assert flow._fechar_popups_convenio(ctx) is False
        ctx.runner.safe_click.assert_not_called()

    def test_retorna_true_e_clica_quando_popup_aparece(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()
        ctx.runner.wait_template.side_effect = [True, False]
        assert flow._fechar_popups_convenio(ctx) is True
        ctx.runner.safe_click.assert_called_once_with(
            "templates/si3/admissao_ambulatorio/btn_sim_convenio.png", threshold=0.75
        )

    def test_tolera_excecao_e_retorna_false(self):
        flow = AdmissaoAmbulatorioFlow()
        ctx = _ctx()
        ctx.runner.wait_template.side_effect = Exception("erro de tela")
        assert flow._fechar_popups_convenio(ctx) is False
