"""
Smoke tests do BaseFlow — vtae/flows/base_flow.py

Estratégia: BaseFlow nao tem __init__ proprio (classe simples), entao
instanciar direto (BaseFlow()) e seguro — nenhum I/O real acontece na
construcao. ctx e um SimpleNamespace com os atributos minimos que cada
metodo le (runner, config, evidence_dir, jab, db), sempre MagicMock nos
pontos de I/O (runner.wait_template, runner.verify_lov, runner.screenshot,
ctx.jab.find_elements_by_name). pygetwindow e mockado via sys.modules
(import local dentro dos metodos _focar_*) — nunca toca em janela real.
Cobre o contrato de cada helper, nao o comportamento real de tela/OCR/
Access Bridge, que so e validado no gate visual (vtae run).
"""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vtae.core.result import CausaFalha
from vtae.flows.base_flow import BaseFlow, _normalizar, _similar


def _ctx(**overrides):
    base = SimpleNamespace(
        runner=MagicMock(),
        config=SimpleNamespace(
            regioes_ocr={},
            coordenadas={},
            DADOS={},
        ),
        evidence_dir="evidence/",
        jab=None,
        db=None,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


# ----------------------------------------------------------------
# _normalizar / _similar — funcoes de modulo
# ----------------------------------------------------------------

class TestNormalizar:

    def test_remove_acentos(self):
        assert _normalizar("CÂMARA") == "CAMARA"

    def test_remove_separadores_de_data(self):
        assert _normalizar("04/11/2023") == "04112023"

    def test_maiusculo_e_strip(self):
        assert _normalizar("  bruna  ") == "BRUNA"


class TestSimilar:

    def test_containment_direto(self):
        assert _similar("MARIA SILVA", "MARIA") is True

    def test_aceita_ruido_de_ocr_dentro_da_tolerancia(self):
        assert _similar("3RUNA", "BRUNA") is True

    def test_rejeita_valor_muito_diferente(self):
        assert _similar("TESTE ERRO", "BRUNA") is False

    def test_falso_quando_algum_lado_vazio(self):
        assert _similar("", "BRUNA") is False
        assert _similar("BRUNA", "") is False


# ----------------------------------------------------------------
# _dado() / _coord() / _tpl_existe()
# ----------------------------------------------------------------

class TestDado:

    def test_retorna_valor_quando_chave_existe(self):
        flow = BaseFlow()
        assert flow._dado({"nome": "MARIA"}, "nome", "CM04") == "MARIA"

    def test_lanca_assertion_error_quando_chave_ausente(self):
        flow = BaseFlow()
        with pytest.raises(AssertionError, match="ausente no config"):
            flow._dado({}, "nome", "CM04")


class TestCoord:

    def test_retorna_tupla_xy(self):
        flow = BaseFlow()
        coords = {"campo_nome": {"x": 100, "y": 200}}
        assert flow._coord(coords, "campo_nome") == (100, 200)

    def test_lanca_key_error_quando_nao_configurada(self):
        flow = BaseFlow()
        with pytest.raises(KeyError):
            flow._coord({}, "campo_ausente")


class TestTplExiste:

    def test_true_quando_existe(self):
        with patch("vtae.flows.base_flow.os.path.exists", return_value=True):
            assert BaseFlow._tpl_existe("templates/x.png") is True

    def test_false_quando_nao_existe(self):
        with patch("vtae.flows.base_flow.os.path.exists", return_value=False):
            assert BaseFlow._tpl_existe("templates/x.png") is False


# ----------------------------------------------------------------
# _step() — wrapper canonico
# ----------------------------------------------------------------

class TestStep:

    def test_sucesso_simples_sem_confirm_template(self):
        flow = BaseFlow()
        observer = MagicMock()
        step = flow._step("L01", "clicar usuario", lambda: "shot.png", observer)
        assert step.success is True
        assert step.description == "clicar usuario"
        assert step.screenshot_path == "shot.png"
        observer.log_step_start.assert_called_once_with("L01", "clicar usuario")
        observer.log_step_result.assert_called_once_with(step)

    def test_confirm_template_encontrado_marca_validated(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = True
        step = flow._step(
            "L02", "confirmar tela", lambda: "shot.png", None,
            confirm_template="templates/tela.png", ctx=ctx,
        )
        assert step.success is True
        assert step.validated is True

    def test_confirm_template_nao_encontrado_falha_com_causa_template(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = False
        step = flow._step(
            "L02", "confirmar tela", lambda: "shot.png", None,
            confirm_template="templates/tela.png", ctx=ctx,
        )
        assert step.success is False
        assert step.causa_falha == CausaFalha.TEMPLATE_NAO_ENCONTRADO
        ctx.runner.screenshot.assert_called_once()

    def test_assertion_error_com_config_ausente_classifica_configuracao(self):
        flow = BaseFlow()

        def fn():
            raise AssertionError("Dado obrigatorio ausente no config.yaml: 'nome'")

        step = flow._step("CM04", "preencher nome", fn, None)
        assert step.success is False
        assert step.causa_falha == CausaFalha.CONFIGURACAO

    def test_key_error_classifica_coordenada(self):
        flow = BaseFlow()

        def fn():
            raise KeyError("campo_nome")

        step = flow._step("CM04", "preencher nome", fn, None)
        assert step.success is False
        assert step.causa_falha == CausaFalha.COORDENADA

    def test_excecao_generica_classifica_desconhecida(self):
        flow = BaseFlow()

        def fn():
            raise RuntimeError("algo inesperado")

        step = flow._step("CM04", "preencher nome", fn, None)
        assert step.success is False
        assert step.causa_falha == CausaFalha.DESCONHECIDA

    def test_falha_tenta_screenshot_de_diagnostico_e_tolera_erro(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.runner.screenshot.side_effect = Exception("sem tela")

        def fn():
            raise RuntimeError("falhou")

        step = flow._step("CM04", "preencher nome", fn, None, ctx=ctx)
        assert step.success is False
        ctx.runner.screenshot.assert_called_once()


# ----------------------------------------------------------------
# _clicar_aguardar()
# ----------------------------------------------------------------

class TestClicarAguardar:

    def test_fallback_quando_template_de_confirmacao_nao_existe(self):
        flow = BaseFlow()
        ctx = _ctx()
        acao = MagicMock()
        with patch("vtae.flows.base_flow.os.path.exists", return_value=False), \
             patch("vtae.flows.base_flow.time.sleep"):
            ok = flow._clicar_aguardar(ctx, acao, "templates/ausente.png")
        assert ok is True
        acao.assert_called_once()

    def test_confirma_na_primeira_tentativa(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = True
        acao = MagicMock()
        with patch("vtae.flows.base_flow.os.path.exists", return_value=True):
            ok = flow._clicar_aguardar(ctx, acao, "templates/destino.png")
        assert ok is True
        acao.assert_called_once()

    def test_esgota_retries_e_lanca_assertion_error(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = False
        acao = MagicMock()
        with patch("vtae.flows.base_flow.os.path.exists", return_value=True), \
             patch("vtae.flows.base_flow.time.sleep"):
            with pytest.raises(AssertionError, match="Tela nao confirmada"):
                flow._clicar_aguardar(ctx, acao, "templates/destino.png", retries=1)
        assert acao.call_count == 2


# ----------------------------------------------------------------
# _verify_campo_obrigatorio() / _verify_campo_opcional()
# ----------------------------------------------------------------

class TestVerifyCampoObrigatorio:

    def test_regiao_nao_calibrada_pula_verificacao(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.config.regioes_ocr = {"campo_nome": {"x1": 0, "y1": 0, "x2": 0, "y2": 0}}
        flow._verify_campo_obrigatorio(ctx, "Nome", "MARIA", "CM04", "campo_nome", [None])
        ctx.runner.verify_lov.assert_not_called()

    def test_ok_quando_valor_confere(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.config.regioes_ocr = {"campo_nome": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        ctx.runner.verify_lov.return_value = (True, "MARIA SILVA")
        holder = [None]
        flow._verify_campo_obrigatorio(ctx, "Nome", "MARIA SILVA", "CM04", "campo_nome", holder)
        assert holder[0] == "MARIA SILVA"

    def test_lanca_quando_campo_vazio(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.config.regioes_ocr = {"campo_nome": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        ctx.runner.verify_lov.return_value = (False, "")
        with pytest.raises(AssertionError, match="ficou vazio"):
            flow._verify_campo_obrigatorio(ctx, "Nome", "MARIA", "CM04", "campo_nome", [None])

    def test_lanca_quando_valor_incorreto(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.config.regioes_ocr = {"campo_nome": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        ctx.runner.verify_lov.return_value = (True, "TESTE ERRO")
        with pytest.raises(AssertionError, match="valor INCORRETO"):
            flow._verify_campo_obrigatorio(ctx, "Nome", "MARIA SILVA", "CM04", "campo_nome", [None])


class TestVerifyCampoOpcional:

    def test_nunca_lanca_mesmo_com_campo_vazio(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.config.regioes_ocr = {"campo_obs": {"x1": 1, "y1": 1, "x2": 50, "y2": 20}}
        ctx.runner.verify_lov.return_value = (False, "")
        holder = [None]
        flow._verify_campo_opcional(ctx, "Obs", "esperado", "CM04", "campo_obs", holder)
        assert holder[0] == ""

    def test_regiao_nao_calibrada_nao_faz_nada(self):
        flow = BaseFlow()
        ctx = _ctx()
        ctx.config.regioes_ocr = {"campo_obs": {"x1": 0, "y1": 0, "x2": 0, "y2": 0}}
        flow._verify_campo_opcional(ctx, "Obs", "esperado", "CM04", "campo_obs", [None])
        ctx.runner.verify_lov.assert_not_called()


# ----------------------------------------------------------------
# _verify_campo_via_jab()
# ----------------------------------------------------------------

class TestVerifyCampoViaJab:

    def test_jab_nao_conectado_pula_verificacao(self):
        flow = BaseFlow()
        ctx = _ctx(jab=None)
        flow._verify_campo_via_jab(ctx, "Descricao do provedor.", "PALMEIRAS", "AB07", [None])

    def test_ok_quando_valor_confere_exatamente(self):
        flow = BaseFlow()
        elemento = SimpleNamespace(text="PALMEIRAS")
        ctx = _ctx(jab=MagicMock())
        ctx.jab.find_elements_by_name.return_value = [elemento]
        holder = [None]
        flow._verify_campo_via_jab(ctx, "Descricao do provedor.", "PALMEIRAS", "AB07", holder)
        assert holder[0] == "PALMEIRAS"

    def test_lanca_quando_campo_nao_encontrado(self):
        flow = BaseFlow()
        ctx = _ctx(jab=MagicMock())
        ctx.jab.find_elements_by_name.return_value = []
        with pytest.raises(AssertionError, match="nao encontrado via pyjab"):
            flow._verify_campo_via_jab(ctx, "Descricao do provedor.", "PALMEIRAS", "AB07", [None])

    def test_lanca_quando_valor_diferente_sem_tolerancia(self):
        flow = BaseFlow()
        elemento = SimpleNamespace(text="3ALMEIRAS")  # 1 char de ruido — pyjab NAO tolera
        ctx = _ctx(jab=MagicMock())
        ctx.jab.find_elements_by_name.return_value = [elemento]
        with pytest.raises(AssertionError, match="valor INCORRETO"):
            flow._verify_campo_via_jab(ctx, "Descricao do provedor.", "PALMEIRAS", "AB07", [None])


# ----------------------------------------------------------------
# _conectar_db() / _obter_via_banco_ou_yaml()
# Congelado (database_runner.py) — testado aqui so o CONTRATO do
# fallback, nunca uma conexao real.
# ----------------------------------------------------------------

class TestConectarDb:

    def test_nao_reconecta_se_ja_tem_ctx_db(self):
        flow = BaseFlow()
        db_existente = MagicMock()
        ctx = _ctx(db=db_existente)
        flow._conectar_db(ctx)
        assert ctx.db is db_existente

    def test_falha_de_conexao_deixa_ctx_db_none(self):
        flow = BaseFlow()
        ctx = _ctx(db=None)
        # Forca a falha explicitamente — o construtor real do
        # DatabaseRunner (congelado) e lazy e nao valida dsn/user/senha
        # None no __init__, entao nao da pra confiar nisso pra testar o
        # fallback. _conectar_db tolera qualquer excecao na construcao
        # e mantem ctx.db = None (regra 34 — nunca silencioso, so avisa).
        with patch(
            "vtae.runners.database_runner.DatabaseRunner",
            side_effect=Exception("sem DSN configurado"),
        ):
            flow._conectar_db(ctx)
        assert ctx.db is None


class TestObterViaBancoOuYaml:

    def test_fallback_yaml_quando_banco_indisponivel(self):
        flow = BaseFlow()
        ctx = _ctx(db=None)
        dados = {"unidades_validas": ["SC AMBULATORIO", "SC INTERNACAO"]}
        valores = flow._obter_via_banco_ou_yaml(
            ctx, dados, "AB06", "SELECT ...", "UNI_NOME", "unidades_validas",
        )
        assert valores == ["SC AMBULATORIO", "SC INTERNACAO"]

    def test_usa_banco_quando_disponivel(self):
        flow = BaseFlow()
        db_mock = MagicMock()
        db_mock.query.return_value = [{"UNI_NOME": "SC AMBULATORIO"}, {"UNI_NOME": "SC INTERNACAO"}]
        ctx = _ctx(db=db_mock)
        dados = {"unidades_validas": ["FALLBACK"]}
        valores = flow._obter_via_banco_ou_yaml(
            ctx, dados, "AB06", "SELECT ...", "UNI_NOME", "unidades_validas",
        )
        assert valores == ["SC AMBULATORIO", "SC INTERNACAO"]

    def test_fallback_yaml_quando_banco_retorna_vazio(self):
        flow = BaseFlow()
        db_mock = MagicMock()
        db_mock.query.return_value = []
        ctx = _ctx(db=db_mock)
        dados = {"unidades_validas": ["FALLBACK"]}
        valores = flow._obter_via_banco_ou_yaml(
            ctx, dados, "AB06", "SELECT ...", "UNI_NOME", "unidades_validas",
        )
        assert valores == ["FALLBACK"]


# ----------------------------------------------------------------
# _focar_si3() / _focar_navegador_sislab()
# pygetwindow mockado via sys.modules — import e local ao metodo.
# ----------------------------------------------------------------

class TestFocarSi3:

    def test_retorna_true_quando_janela_encontrada(self):
        janela = MagicMock(isMinimized=False)
        gw_mock = MagicMock()
        gw_mock.getWindowsWithTitle.return_value = [janela]
        with patch.dict(sys.modules, {"pygetwindow": gw_mock}), \
             patch("time.sleep"):
            assert BaseFlow._focar_si3() is True
        janela.activate.assert_called_once()

    def test_retorna_false_quando_nenhuma_janela_encontrada(self):
        gw_mock = MagicMock()
        gw_mock.getWindowsWithTitle.return_value = []
        with patch.dict(sys.modules, {"pygetwindow": gw_mock}):
            assert BaseFlow._focar_si3() is False


class TestFocarNavegadorSislab:

    def test_retorna_true_quando_titulo_contem_substring(self):
        janela = MagicMock(isMinimized=False)
        gw_mock = MagicMock()
        gw_mock.getAllTitles.return_value = ["SisLab - Modulo Funcionario"]
        gw_mock.getWindowsWithTitle.return_value = [janela]
        with patch.dict(sys.modules, {"pygetwindow": gw_mock}), \
             patch("time.sleep"):
            assert BaseFlow._focar_navegador_sislab("SisLab") is True

    def test_retorna_false_quando_titulo_nao_encontrado(self):
        gw_mock = MagicMock()
        gw_mock.getAllTitles.return_value = ["Outra janela qualquer"]
        with patch.dict(sys.modules, {"pygetwindow": gw_mock}):
            assert BaseFlow._focar_navegador_sislab("SisLab") is False
