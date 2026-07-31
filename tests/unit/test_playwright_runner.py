"""
Smoke tests do PlaywrightRunner — vtae/runners/playwright_runner.py

Estratégia: nunca abre browser real. __init__ é pulado via
object.__new__ (evita sync_playwright().start() + launch de verdade —
caro e não roda em CI sem browser instalado). Page é substituída por
MagicMock. Cobre a lógica de retry/verificação — não o comportamento
real de navegação, que só é validado no gate visual (vtae run).
"""

from unittest.mock import MagicMock

import pytest

from vtae.core.exceptions import RunnerError
from vtae.runners.playwright_runner import PlaywrightRunner


def _novo_runner():
    """PlaywrightRunner sem __init__ real — page mockada."""
    runner = object.__new__(PlaywrightRunner)
    runner._page = MagicMock()
    runner._logger = None
    runner._ocr_engine = MagicMock()
    return runner


class TestClickTemplate:

    def test_retorna_true_quando_clica(self):
        runner = _novo_runner()
        ok = runner.click_template("#botao")
        assert ok is True
        runner._page.click.assert_called_once_with("#botao", timeout=3000)

    def test_retorna_false_quando_excecao(self):
        runner = _novo_runner()
        runner._page.click.side_effect = Exception("elemento nao encontrado")
        ok = runner.click_template("#botao")
        assert ok is False


class TestTypeText:

    def test_digita_via_keyboard(self):
        runner = _novo_runner()
        runner.type_text("MARIA SILVA")
        runner._page.keyboard.type.assert_called_once_with("MARIA SILVA", delay=50)


class TestWaitTemplate:

    def test_retorna_true_quando_seletor_aparece(self):
        runner = _novo_runner()
        ok = runner.wait_template("#campo", timeout=5.0)
        assert ok is True
        runner._page.wait_for_selector.assert_called_once_with("#campo", timeout=5000)

    def test_retorna_false_quando_timeout(self):
        runner = _novo_runner()
        runner._page.wait_for_selector.side_effect = Exception("timeout")
        ok = runner.wait_template("#campo")
        assert ok is False


class TestScreenshot:

    def test_cria_pasta_e_chama_page_screenshot(self, tmp_path):
        runner = _novo_runner()
        path = str(tmp_path / "sub" / "evidencia.png")
        resultado = runner.screenshot(path)
        assert resultado == path
        runner._page.screenshot.assert_called_once_with(path=path, full_page=False)
        assert (tmp_path / "sub").is_dir()


class TestSafeClick:

    def test_sucesso_na_primeira_tentativa(self):
        runner = _novo_runner()
        ok = runner.safe_click("#botao")
        assert ok is True

    def test_lanca_runner_error_apos_esgotar_retries(self):
        runner = _novo_runner()
        runner._page.click.side_effect = Exception("nao encontrado")
        with pytest.raises(RunnerError):
            runner.safe_click("#botao", retries=2, delay=0)


class TestVerifyFillWeb:

    def test_ok_quando_dom_contem_valor(self):
        runner = _novo_runner()
        runner._page.input_value.return_value = "MARIA SILVA"
        ok = runner.verify_fill_web("#nome", "maria silva", timeout=1.0)
        assert ok is True

    def test_falha_apos_timeout(self):
        runner = _novo_runner()
        runner._page.input_value.return_value = "valor errado"
        ok = runner.verify_fill_web("#nome", "esperado", timeout=0.05)
        assert ok is False

    def test_continua_tentando_quando_input_value_lanca_excecao(self):
        runner = _novo_runner()
        runner._page.input_value.side_effect = Exception("elemento sumiu")
        ok = runner.verify_fill_web("#nome", "esperado", timeout=0.05)
        assert ok is False


class TestMetodosWeb:

    def test_fill_delega_para_page(self):
        runner = _novo_runner()
        runner.fill("#nome", "MARIA")
        runner._page.fill.assert_called_once_with("#nome", "MARIA")

    def test_is_visible_true(self):
        runner = _novo_runner()
        runner._page.is_visible.return_value = True
        assert runner.is_visible("#campo") is True

    def test_is_visible_retorna_false_em_excecao(self):
        runner = _novo_runner()
        runner._page.is_visible.side_effect = Exception("erro")
        assert runner.is_visible("#campo") is False

    def test_get_text_retorna_texto(self):
        runner = _novo_runner()
        runner._page.inner_text.return_value = "texto do elemento"
        assert runner.get_text("#campo") == "texto do elemento"

    def test_get_text_retorna_vazio_em_excecao(self):
        runner = _novo_runner()
        runner._page.inner_text.side_effect = Exception("erro")
        assert runner.get_text("#campo") == ""

    def test_navigate_chama_goto_e_espera_networkidle(self):
        runner = _novo_runner()
        runner.navigate("https://exemplo.com")
        runner._page.goto.assert_called_once_with("https://exemplo.com")
        runner._page.wait_for_load_state.assert_called_once_with("networkidle")


class TestVerifyFillScreenshot:

    def test_ok_quando_ocr_encontra_valor(self):
        runner = _novo_runner()
        runner._ocr_engine.ler_regiao.return_value = "MARIA SILVA"
        ok = runner.verify_fill_screenshot("maria silva", (0, 0, 10, 10), timeout=1.0)
        assert ok is True

    def test_falha_apos_timeout(self):
        runner = _novo_runner()
        runner._ocr_engine.ler_regiao.return_value = "valor errado"
        ok = runner.verify_fill_screenshot("esperado", (0, 0, 10, 10), timeout=0.05)
        assert ok is False


class TestCloseContextManager:

    def test_close_fecha_browser_e_playwright(self):
        runner = _novo_runner()
        runner._browser = MagicMock()
        runner._pw = MagicMock()
        runner.close()
        runner._browser.close.assert_called_once()
        runner._pw.stop.assert_called_once()

    def test_context_manager_chama_close_no_exit(self):
        runner = _novo_runner()
        runner._browser = MagicMock()
        runner._pw = MagicMock()
        with runner as r:
            assert r is runner
        runner._browser.close.assert_called_once()
