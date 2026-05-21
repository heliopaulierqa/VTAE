# tests/unit/test_cadastro_paciente_flow.py
"""
Testes unitários do CadastroPacienteFlow — 27 steps (CP01–CP27)
Fase 5a — v0.5.6

REGRAS:
  - mock_sleep autouse (conftest.py) elimina todos os time.sleep reais
  - Config sempre via _config() com coordenadas e regioes_ocr mockadas
  - side_effect de mocks SEMPRE seletivo por template/campo
  - Os 27 steps são testados individualmente
"""

import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from src.flows.si3.cadastro_paciente_flow import CadastroPacienteFlow
from src.core.result import FlowResult, StepResult


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _config():
    coordenadas = {
        "campo_pesquisa_nome":              {"x": 300, "y": 195},
        "campo_nome_social":                {"x": 160, "y": 176},
        "campo_data_nascimento":            {"x": 355, "y": 176},
        "campo_hora":                       {"x": 425, "y": 176},
        "campo_sexo":                       {"x": 484, "y": 176},
        "campo_nacionalidade":              {"x": 600, "y": 176},
        "campo_mae":                        {"x": 70,  "y": 212},
        "campo_pai":                        {"x": 215, "y": 212},
        "campo_conjuge":                    {"x": 404, "y": 212},
        "campo_responsavel":                {"x": 600, "y": 212},
        "campo_cor_etnia":                  {"x": 80,  "y": 250},
        "campo_religiao":                   {"x": 255, "y": 250},
        "campo_estado_civil":               {"x": 395, "y": 250},
        "campo_ocupacao":                   {"x": 600, "y": 250},
        "campo_situacao_familiar":          {"x": 105, "y": 287},
        "campo_tipo_deficiencia":           {"x": 310, "y": 287},
        "campo_escolaridade":               {"x": 550, "y": 287},
        "campo_frequenta_escola":           {"x": 795, "y": 287},
        "campo_rg":                         {"x": 280, "y": 340},
        "campo_cpf":                        {"x": 280, "y": 358},
        "campo_cns":                        {"x": 280, "y": 376},
        "campo_cep":                        {"x": 68,  "y": 378},
        "campo_tipo_endereco":              {"x": 143, "y": 378},
        "campo_logradouro":                 {"x": 345, "y": 378},
        "campo_numero_endereco":            {"x": 500, "y": 378},
        "campo_complemento_endereco":       {"x": 584, "y": 378},
        "campo_uf_endereco":                {"x": 220, "y": 415},
        "campo_municipio_endereco":         {"x": 445, "y": 415},
        "campo_bairro":                     {"x": 150, "y": 452},
        "campo_referencia_endereco":        {"x": 620, "y": 452},
        "campo_comunicacao_prioridade_l1":  {"x": 55,  "y": 430},
        "campo_comunicacao_lov_l1":         {"x": 175, "y": 430},
        "campo_comunicacao_numero_l1":      {"x": 310, "y": 430},
        "campo_comunicacao_prioridade_l2":  {"x": 55,  "y": 448},
        "campo_comunicacao_lov_l2":         {"x": 175, "y": 448},
        "campo_comunicacao_numero_l2":      {"x": 310, "y": 448},
    }
    regioes_ocr = {k: {"x1": 0, "y1": 0, "x2": 0, "y2": 0} for k in [
        "nome", "data_nascimento", "hora", "sexo", "cor_etnia",
        "nacionalidade", "nome_mae", "frequenta_escola", "rg", "cpf",
        "cns", "celular", "email", "matricula",
    ]}
    config = MagicMock()
    config.coordenadas = coordenadas
    config.regioes_ocr = regioes_ocr
    config.confidence = 0.75
    return config


def _dados():
    return {
        "nome":              "MARIA SILVA TESTE",
        "nome_social":       "MARI",
        "nome_pai":          "JOSE SILVA",
        "nome_mae":          "ANA SILVA",
        "data_nascimento":   "15/06/1985",
        "hora":              "00:00",
        "sexo":              "F",
        "cor_etnia":         "PARDA",
        "nacionalidade":     "BRASILEIRA",
        "religiao":          "CATOLICO",
        "estado_civil":      "SOLTEIRO",
        "ocupacao":          "PROFESSOR DE ENSINO PRE ESCOLAR",
        "situacao_familiar": "VIVE SO",
        "tipo_deficiencia":  "",
        "escolaridade":      "SUPERIOR COMPLETO",
        "frequenta_escola":  "Sim",
        "cpf":               "12345678900",
        "rg":                "",
        "cns":               "",
        "celular":           "11999990000",
        "email":             "maria@teste.com",
        "conjuge":           "",
        "responsavel":       "",
        "endereco": {
            "cep":         "01310100",
            "tipo":        "AVENIDA",
            "logradouro":  "DR ENEAS CARVALHO DE AGUIAR",
            "numero":      "44",
            "complemento": "Cadastro de Teste",
            "uf":          "SP",
            "municipio":   "SAO PAULO",
            "bairro":      "CERQUEIRA CESAR",
            "referencia":  "Proximo ao centro",
        },
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
    return ctx


def _run(runner=None, dados=None):
    with patch("os.path.exists", return_value=False):
        return CadastroPacienteFlow().execute(
            _ctx(runner), dados=dados or _dados()
        )


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura do flow
# ──────────────────────────────────────────────────────────────────────────────

class TestEstrutura:

    def test_flow_name_correto(self):
        assert CadastroPacienteFlow.FLOW_NAME == "CadastroPacienteFlow"

    def test_execute_retorna_flow_result(self):
        assert isinstance(_run(), FlowResult)

    def test_execute_tem_27_steps(self):
        assert len(_run().steps) == 27

    def test_ids_corretos(self):
        ids = [s.step_id for s in _run().steps]
        assert ids == [f"CP{i:02d}" for i in range(1, 28)]

    def test_todos_steps_passam_com_runner_ok(self):
        falhos = [s for s in _run().steps if not s.success]
        assert falhos == [], [f"{s.step_id}: {s.error}" for s in falhos]

    def test_flow_sucesso(self):
        assert _run().success is True

    def test_execute_chama_add_result(self):
        ctx = _ctx()
        with patch("os.path.exists", return_value=False):
            CadastroPacienteFlow().execute(ctx, dados=_dados())
        ctx.add_result.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# CP01 — Abrir módulo
# ──────────────────────────────────────────────────────────────────────────────

class TestCp01:

    def test_sucesso(self):
        assert _run().steps[0].success is True

    def test_step_id(self):
        assert _run().steps[0].step_id == "CP01"

    def test_chama_double_click_menu(self):
        runner = _runner_ok()
        _run(runner)
        runner.double_click.assert_any_call(
            "templates/si3/cadastro_paciente/menu_cadastro_paciente.png",
            threshold=0.7
        )

    def test_aguarda_label_pesquisa(self):
        runner = _runner_ok()
        _run(runner)
        runner.wait_template.assert_any_call(
            "templates/si3/cadastro_paciente/label_pesquisa_paciente.png",
            timeout=20.0
        )

    def test_falha_se_double_click_lanca_excecao(self):
        runner = _runner_ok()
        runner.double_click.side_effect = Exception("template nao encontrado")
        result = _run(runner)
        assert result.steps[0].success is False
        assert len(result.steps) == 1

    def test_tira_screenshot(self):
        runner = _runner_ok()
        _run(runner)
        runner.screenshot.assert_called()


# ──────────────────────────────────────────────────────────────────────────────
# CP02 — Pesquisar
# ──────────────────────────────────────────────────────────────────────────────

class TestCp02:

    def test_sucesso(self):
        assert _run().steps[1].success is True

    def test_digita_nome_no_campo_pesquisa(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("MARIA SILVA TESTE" in c for c in chamadas)

    def test_clica_btn_pesquisar(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/cadastro_paciente/btn_pesquisar.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# CP03 — Novo
# ──────────────────────────────────────────────────────────────────────────────

class TestCp03:

    def test_sucesso(self):
        assert _run().steps[2].success is True

    def test_clica_btn_novo(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/cadastro_paciente/btn_novo_resultado.png", threshold=0.7
        )

    def test_aguarda_label_cadastro(self):
        runner = _runner_ok()
        _run(runner)
        runner.wait_template.assert_any_call(
            "templates/si3/cadastro_paciente/label_cadastro_pacientes.png",
            timeout=15.0
        )

    def test_falha_se_label_cadastro_nao_aparece(self):
        runner = _runner_ok()
        def wt(tpl, **kw):
            if "label_cadastro_pacientes" in tpl:
                raise Exception("tela de cadastro nao abriu")
            return True
        runner.wait_template.side_effect = wt
        result = _run(runner)
        cp03 = next(s for s in result.steps if s.step_id == "CP03")
        assert cp03.success is False


# ──────────────────────────────────────────────────────────────────────────────
# CP04 — Nome
# ──────────────────────────────────────────────────────────────────────────────

class TestCp04:

    def test_sucesso(self):
        assert _run().steps[3].success is True

    def test_clica_label_nome(self):
        runner = _runner_ok()
        _run(runner)
        runner.click_near.assert_any_call(
            "templates/si3/cadastro_paciente/label_nome_cadastro.png", offset_x=250
        )

    def test_digita_nome(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("MARIA SILVA TESTE" in c for c in chamadas)

    def test_falha_se_click_near_lanca_excecao(self):
        runner = _runner_ok()
        def cn(tpl, **kw):
            if "label_nome_cadastro" in tpl:
                raise Exception("template nao encontrado")
        runner.click_near.side_effect = cn
        result = _run(runner)
        cp04 = next(s for s in result.steps if s.step_id == "CP04")
        assert cp04.success is False


# ──────────────────────────────────────────────────────────────────────────────
# CP05 — Nome Social
# ──────────────────────────────────────────────────────────────────────────────

class TestCp05:

    def test_sucesso(self):
        assert _run().steps[4].success is True

    def test_digita_nome_social(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("MARI" in c for c in chamadas)

    def test_nao_digita_se_nome_social_vazio(self):
        runner = _runner_ok()
        dados = _dados()
        dados["nome_social"] = ""
        with patch("os.path.exists", return_value=False):
            result = CadastroPacienteFlow().execute(_ctx(runner), dados=dados)
        assert result.steps[4].success is True


# ──────────────────────────────────────────────────────────────────────────────
# CP06 — Data de Nascimento
# ──────────────────────────────────────────────────────────────────────────────

class TestCp06:

    def test_sucesso(self):
        assert _run().steps[5].success is True

    def test_digita_data(self):
        runner = _runner_ok()
        dados = _dados()
        dados["data_nascimento"] = "01/01/1990"
        with patch("os.path.exists", return_value=False):
            CadastroPacienteFlow().execute(_ctx(runner), dados=dados)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("01/01/1990" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# CP07 — Hora
# ──────────────────────────────────────────────────────────────────────────────

class TestCp07:

    def test_sucesso(self):
        assert _run().steps[6].success is True

    def test_digita_hora(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("00:00" in c for c in chamadas)

    def test_default_hora_quando_ausente(self):
        runner = _runner_ok()
        dados = _dados()
        del dados["hora"]
        with patch("os.path.exists", return_value=False):
            CadastroPacienteFlow().execute(_ctx(runner), dados=dados)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("00:00" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# CP08 — Sexo
# ──────────────────────────────────────────────────────────────────────────────

class TestCp08:

    def test_sucesso(self):
        assert _run().steps[7].success is True

    def test_digita_sexo_f(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("'F'" in c for c in chamadas)

    def test_default_m_quando_ausente(self):
        runner = _runner_ok()
        dados = _dados()
        del dados["sexo"]
        with patch("os.path.exists", return_value=False):
            CadastroPacienteFlow().execute(_ctx(runner), dados=dados)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("'M'" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# CP09 — Nacionalidade (LOV)
# ──────────────────────────────────────────────────────────────────────────────

class TestCp09:

    def test_sucesso(self):
        assert _run().steps[8].success is True

    def test_digita_brasileira(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("BRASILEIRA" in c for c in chamadas)

    def test_clica_btn_ok_popup(self):
        runner = _runner_ok()
        _run(runner)
        chamadas_ok = [c for c in runner.safe_click.call_args_list if "btn_ok_popup" in str(c)]
        assert len(chamadas_ok) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# CP10 — Mãe
# ──────────────────────────────────────────────────────────────────────────────

class TestCp10:

    def test_sucesso(self):
        assert _run().steps[9].success is True

    def test_digita_nome_mae(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("ANA SILVA" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# CP11 — Pai
# ──────────────────────────────────────────────────────────────────────────────

class TestCp11:

    def test_sucesso(self):
        assert _run().steps[10].success is True

    def test_step_id(self):
        assert _run().steps[10].step_id == "CP11"

    def test_digita_nome_pai(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("JOSE SILVA" in c for c in chamadas)

    def test_nao_digita_se_pai_vazio(self):
        runner = _runner_ok()
        dados = _dados()
        dados["nome_pai"] = ""
        with patch("os.path.exists", return_value=False):
            result = CadastroPacienteFlow().execute(_ctx(runner), dados=dados)
        assert result.steps[10].success is True


# ──────────────────────────────────────────────────────────────────────────────
# CP12 e CP13 — Cônjuge e Responsável (opcionais)
# ──────────────────────────────────────────────────────────────────────────────

class TestCp12Cp13:

    def test_cp12_sucesso_vazio(self):
        assert _run().steps[11].success is True

    def test_cp12_step_id(self):
        assert _run().steps[11].step_id == "CP12"

    def test_cp13_sucesso_vazio(self):
        assert _run().steps[12].success is True

    def test_cp13_step_id(self):
        assert _run().steps[12].step_id == "CP13"


# ──────────────────────────────────────────────────────────────────────────────
# CP14–CP20 — Dropdowns
# ──────────────────────────────────────────────────────────────────────────────

class TestDropdowns:

    @pytest.mark.parametrize("idx,step_id", [
        (13, "CP14"),
        (14, "CP15"),
        (15, "CP16"),
        (16, "CP17"),
        (17, "CP18"),
        (18, "CP19"),
        (19, "CP20"),
    ])
    def test_sucesso(self, idx, step_id):
        result = _run()
        assert result.steps[idx].step_id == step_id
        assert result.steps[idx].success is True

    def test_cp20_frequenta_escola_sim(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("'S'" in c for c in chamadas)

    def test_cp19_skip_quando_deficiencia_vazia(self):
        runner = _runner_ok()
        result = _run(runner)
        assert result.steps[18].success is True


# ──────────────────────────────────────────────────────────────────────────────
# CP21 — Aba Documentos
# ──────────────────────────────────────────────────────────────────────────────

class TestCp21:

    def test_sucesso(self):
        assert _run().steps[20].success is True

    def test_step_id(self):
        assert _run().steps[20].step_id == "CP21"

    def test_clica_aba_documentos(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/cadastro_paciente/aba_documentos.png", threshold=0.7
        )

    def test_aguarda_label_documentos(self):
        runner = _runner_ok()
        _run(runner)
        runner.wait_template.assert_any_call(
            "templates/si3/cadastro_paciente/label_documentos_paciente.png",
            timeout=10.0
        )

    def test_digita_cpf_sem_pontuacao(self):
        runner = _runner_ok()
        dados = _dados()
        dados["cpf"] = "123.456.789-00"
        with patch("os.path.exists", return_value=False):
            CadastroPacienteFlow().execute(_ctx(runner), dados=dados)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("12345678900" in c for c in chamadas)
        assert not any("123.456.789-00" in c for c in chamadas)

    def test_falha_se_aba_nao_abre(self):
        runner = _runner_ok()
        def wt(tpl, **kw):
            if "label_documentos_paciente" in tpl:
                raise Exception("aba nao abriu")
            return True
        runner.wait_template.side_effect = wt
        result = _run(runner)
        cp21 = next(s for s in result.steps if s.step_id == "CP21")
        assert cp21.success is False
        assert "CP22" not in [s.step_id for s in result.steps]


# ──────────────────────────────────────────────────────────────────────────────
# CP22 — Aba Endereços
# ──────────────────────────────────────────────────────────────────────────────

class TestCp22:

    def test_sucesso(self):
        assert _run().steps[21].success is True

    def test_step_id(self):
        assert _run().steps[21].step_id == "CP22"

    def test_clica_aba_enderecos(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/cadastro_paciente/aba_enderecos.png", threshold=0.7
        )

    def test_aguarda_label_enderecos(self):
        runner = _runner_ok()
        _run(runner)
        runner.wait_template.assert_any_call(
            "templates/si3/cadastro_paciente/label_enderecos_paciente.png",
            timeout=10.0
        )

    def test_digita_cep(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("01310100" in c for c in chamadas)

    def test_digita_numero(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("'44'" in c for c in chamadas)

    def test_falha_se_aba_nao_abre(self):
        runner = _runner_ok()
        def wt(tpl, **kw):
            if "label_enderecos_paciente" in tpl:
                raise Exception("aba nao abriu")
            return True
        runner.wait_template.side_effect = wt
        result = _run(runner)
        cp22 = next(s for s in result.steps if s.step_id == "CP22")
        assert cp22.success is False


# ──────────────────────────────────────────────────────────────────────────────
# CP23 — Aba Comunicação (LOV)
# ──────────────────────────────────────────────────────────────────────────────

class TestCp23:

    def test_sucesso(self):
        assert _run().steps[22].success is True

    def test_step_id(self):
        assert _run().steps[22].step_id == "CP23"

    def test_clica_aba_comunicacao(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/cadastro_paciente/aba_comunicacao.png", threshold=0.7
        )

    def test_aguarda_label_comunicacao(self):
        runner = _runner_ok()
        _run(runner)
        runner.wait_template.assert_any_call(
            "templates/si3/cadastro_paciente/label_comunicacao_paciente.png",
            timeout=10.0
        )

    def test_digita_prioridade_1_para_celular(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("'1'" in c for c in chamadas)

    def test_seleciona_celular_no_popup(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.safe_click.call_args_list]
        assert any("popup_opcao_celular" in c for c in chamadas)

    def test_seleciona_email_no_popup(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.safe_click.call_args_list]
        assert any("popup_opcao_email" in c for c in chamadas)

    def test_btn_ok_clicado_2_vezes(self):
        runner = _runner_ok()
        _run(runner)
        chamadas_ok = [c for c in runner.safe_click.call_args_list if "btn_ok_popup" in str(c)]
        assert len(chamadas_ok) >= 2

    def test_digita_numero_celular(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("11999990000" in c for c in chamadas)

    def test_digita_email(self):
        runner = _runner_ok()
        _run(runner)
        chamadas = [str(c) for c in runner.type_text.call_args_list]
        assert any("maria@teste.com" in c for c in chamadas)


# ──────────────────────────────────────────────────────────────────────────────
# CP24 — Gerar CNS
# ──────────────────────────────────────────────────────────────────────────────

class TestCp24:

    def test_sucesso(self):
        assert _run().steps[23].success is True

    def test_step_id(self):
        assert _run().steps[23].step_id == "CP24"

    def test_clica_btn_gerar_cns(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/cadastro_paciente/btn_gerar_cns.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# CP25 — Gerar Matrícula + OCR
# ──────────────────────────────────────────────────────────────────────────────

class TestCp25:

    def test_sucesso_regiao_zerada(self):
        assert _run().steps[24].success is True

    def test_step_id(self):
        assert _run().steps[24].step_id == "CP25"

    def test_clica_btn_gerar_matricula(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/cadastro_paciente/btn_gerar_matricula.png", threshold=0.7
        )

    def test_ocr_salva_estado_quando_calibrado(self, tmp_path):
        runner = _runner_ok()
        ctx = _ctx(runner)
        ctx.config.regioes_ocr["matricula"] = {"x1": 10, "y1": 100, "x2": 320, "y2": 160}
        estado_path = tmp_path / "estado_jornada.json"
        with patch("os.path.exists", return_value=False), \
             patch("src.flows.si3.cadastro_paciente_flow._ESTADO_PATH", estado_path), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value="Matricula: 34567"):
            result = CadastroPacienteFlow().execute(ctx, dados=_dados())
        assert result.steps[24].success is True
        assert json.loads(estado_path.read_text())["paciente_id"] == "34567"

    def test_falha_se_ocr_calibrado_nao_retorna_numero(self):
        runner = _runner_ok()
        ctx = _ctx(runner)
        ctx.config.regioes_ocr["matricula"] = {"x1": 10, "y1": 100, "x2": 320, "y2": 160}
        with patch("os.path.exists", return_value=False), \
             patch("src.vision.ocr.OcrHelper.ler_regiao", return_value=""), \
             patch("src.vision.ocr.OcrHelper.salvar_debug"):
            result = CadastroPacienteFlow().execute(ctx, dados=_dados())
        assert result.steps[24].success is False


# ──────────────────────────────────────────────────────────────────────────────
# CP26 — Salvar
# ──────────────────────────────────────────────────────────────────────────────

class TestCp26:

    def test_sucesso(self):
        assert _run().steps[25].success is True

    def test_step_id(self):
        assert _run().steps[25].step_id == "CP26"

    def test_clica_btn_salvar_toolbar(self):
        runner = _runner_ok()
        _run(runner)
        runner.safe_click.assert_any_call(
            "templates/si3/cadastro_paciente/btn_salvar_toolbar.png", threshold=0.7
        )


# ──────────────────────────────────────────────────────────────────────────────
# CP27 — Sair
# ──────────────────────────────────────────────────────────────────────────────

class TestCp27:

    def test_sucesso(self):
        assert _run().steps[26].success is True

    def test_step_id(self):
        assert _run().steps[26].step_id == "CP27"

    def test_clica_btn_sair(self):
        runner = _runner_ok()
        _run(runner)
        chamadas_sair = [c for c in runner.safe_click.call_args_list if "btn_sair" in str(c)]
        assert len(chamadas_sair) >= 1

    def test_tira_screenshot(self):
        runner = _runner_ok()
        _run(runner)
        runner.screenshot.assert_called()


# ──────────────────────────────────────────────────────────────────────────────
# Abort-on-failure
# ──────────────────────────────────────────────────────────────────────────────

class TestAbortOnFailure:

    def test_falha_cp01_aborta_no_step_1(self):
        runner = _runner_ok()
        runner.double_click.side_effect = Exception("menu nao encontrado")
        result = _run(runner)
        assert len(result.steps) == 1
        assert result.steps[0].success is False

    def test_falha_cp03_nao_executa_cp04(self):
        runner = _runner_ok()
        def wt(tpl, **kw):
            if "label_cadastro_pacientes" in tpl:
                raise Exception("tela nao abriu")
            return True
        runner.wait_template.side_effect = wt
        result = _run(runner)
        ids = [s.step_id for s in result.steps]
        assert "CP03" in ids
        assert "CP04" not in ids

    def test_falha_cp21_nao_executa_cp22(self):
        runner = _runner_ok()
        def wt(tpl, **kw):
            if "label_documentos_paciente" in tpl:
                raise Exception("aba nao abriu")
            return True
        runner.wait_template.side_effect = wt
        result = _run(runner)
        ids = [s.step_id for s in result.steps]
        assert "CP21" in ids
        assert "CP22" not in ids
        assert result.success is False

    def test_flow_falso_quando_step_falha(self):
        runner = _runner_ok()
        runner.safe_click.side_effect = Exception("clique falhou")
        result = _run(runner)
        assert result.success is False

    def test_observer_notificado_para_todos_steps(self):
        observer = MagicMock()
        with patch("os.path.exists", return_value=False):
            result = CadastroPacienteFlow().execute(_ctx(), dados=_dados(), observer=observer)
        assert observer.log_step_start.call_count == 27
        assert observer.log_step_result.call_count == 27
        observer.log_flow_result.assert_called_once()