"""
Smoke tests do OpenCVRunner — vtae/runners/opencv_runner.py

Estratégia: nunca toca em tela real. TemplateMatcher e OcrEngine são
substituídos por MagicMock via object.__new__ (pula o __init__ real,
que carregaria EasyOCR e criaria um TemplateMatcher de verdade — caro
e não determinístico em CI). pyautogui/pyperclip são mockados nos
pontos de uso. Cobre a lógica de retry/verificação — não o
comportamento real de clique/digitação, que só é validado no gate
visual (vtae run).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vtae.core.exceptions import TemplateNotFoundError
from vtae.runners.opencv_runner import OpenCVRunner


def _novo_runner(confidence=0.8):
    """OpenCVRunner sem __init__ real — matcher e ocr_engine mockados."""
    runner = object.__new__(OpenCVRunner)
    runner.confidence = confidence
    runner._matcher = MagicMock()
    runner._logger = None
    runner._ocr_engine = MagicMock()
    return runner


def _match(x=100, y=200, scale=1.0, score=0.9):
    return SimpleNamespace(x=x, y=y, scale=scale, score=score)


class TestClickTemplate:

    def test_clica_quando_encontra(self):
        runner = _novo_runner()
        runner._matcher.find_best.return_value = _match()
        with patch("vtae.runners.opencv_runner.pyautogui") as pag:
            with patch("vtae.runners.opencv_runner.time.sleep"):
                ok = runner.click_template("tpl.png")
        assert ok is True
        pag.click.assert_called_once_with(100, 200)

    def test_retorna_false_quando_nao_encontra(self):
        runner = _novo_runner()
        runner._matcher.find_best.return_value = None
        with patch("vtae.runners.opencv_runner.pyautogui") as pag:
            ok = runner.click_template("tpl.png")
        assert ok is False
        pag.click.assert_not_called()


class TestWaitTemplate:

    def test_retorna_true_quando_visivel(self):
        runner = _novo_runner()
        runner._matcher.is_visible.return_value = True
        with patch("vtae.runners.opencv_runner.time.sleep"):
            ok = runner.wait_template("tpl.png", timeout=1.0)
        assert ok is True

    def test_retorna_false_apos_timeout(self):
        runner = _novo_runner()
        runner._matcher.is_visible.return_value = False
        ok = runner.wait_template("tpl.png", timeout=0.01)
        assert ok is False


class TestSafeClick:

    def test_sucesso_na_primeira_tentativa(self):
        runner = _novo_runner()
        runner._matcher.find_best.return_value = _match()
        with patch("vtae.runners.opencv_runner.pyautogui") as pag:
            with patch("vtae.runners.opencv_runner.time.sleep"):
                ok = runner.safe_click("tpl.png")
        assert ok is True
        pag.click.assert_called_once()

    def test_lanca_apos_esgotar_retries(self):
        runner = _novo_runner()
        runner._matcher.find_best.return_value = None
        runner._matcher.find_best_score.return_value = 0.3
        with patch("vtae.runners.opencv_runner.pyautogui"):
            with patch("vtae.runners.opencv_runner.time.sleep"):
                with pytest.raises(TemplateNotFoundError):
                    runner.safe_click("tpl.png", retries=2)
        assert runner._matcher.find_best.call_count == 2

    def test_usa_confidence_como_threshold_default(self):
        runner = _novo_runner(confidence=0.65)
        runner._matcher.find_best.return_value = _match()
        with patch("vtae.runners.opencv_runner.pyautogui"):
            with patch("vtae.runners.opencv_runner.time.sleep"):
                runner.safe_click("tpl.png")
        runner._matcher.find_best.assert_called_with("tpl.png", 0.65)


class TestDoubleClick:

    def test_sucesso(self):
        runner = _novo_runner()
        runner._matcher.find_best.return_value = _match()
        with patch("vtae.runners.opencv_runner.pyautogui") as pag:
            with patch("vtae.runners.opencv_runner.time.sleep"):
                ok = runner.double_click("tpl.png")
        assert ok is True
        pag.doubleClick.assert_called_once_with(100, 200)

    def test_lanca_apos_esgotar_retries(self):
        runner = _novo_runner()
        runner._matcher.find_best.return_value = None
        runner._matcher.find_best_score.return_value = 0.1
        with patch("vtae.runners.opencv_runner.pyautogui"):
            with patch("vtae.runners.opencv_runner.time.sleep"):
                with pytest.raises(TemplateNotFoundError):
                    runner.double_click("tpl.png", retries=1)


class TestVerifyFillClipboard:

    def test_ok_quando_clipboard_contem_valor(self):
        runner = _novo_runner()
        with patch("vtae.runners.opencv_runner.pyperclip") as pc, \
             patch("vtae.runners.opencv_runner.pyautogui"), \
             patch("vtae.runners.opencv_runner.time.sleep"):
            pc.paste.return_value = "MARIA SILVA"
            ok, lido = runner.verify_fill_clipboard("maria silva")
        assert ok is True
        assert lido == "MARIA SILVA"

    def test_falha_quando_clipboard_nao_contem_valor(self):
        runner = _novo_runner()
        with patch("vtae.runners.opencv_runner.pyperclip") as pc, \
             patch("vtae.runners.opencv_runner.pyautogui"), \
             patch("vtae.runners.opencv_runner.time.sleep"):
            pc.paste.return_value = "OUTRO VALOR"
            ok, lido = runner.verify_fill_clipboard("maria silva")
        assert ok is False
        assert lido == "OUTRO VALOR"

    def test_retorna_false_em_excecao(self):
        runner = _novo_runner()
        with patch("vtae.runners.opencv_runner.pyperclip") as pc, \
             patch("vtae.runners.opencv_runner.pyautogui"):
            pc.copy.side_effect = Exception("clipboard indisponivel")
            ok, lido = runner.verify_fill_clipboard("qualquer")
        assert ok is False
        assert lido == ""


class TestVerifyFill:

    def test_ok_quando_ocr_encontra_valor(self):
        runner = _novo_runner()
        runner._ocr_engine.ler_regiao.return_value = "MARIA SILVA"
        with patch.object(runner, "screenshot", return_value="fake.png"):
            ok, lido = runner.verify_fill("maria silva", (0, 0, 10, 10), timeout=1.0)
        assert ok is True
        assert lido == "MARIA SILVA"

    def test_falha_apos_timeout(self):
        runner = _novo_runner()
        runner._ocr_engine.ler_regiao.return_value = "valor errado"
        with patch.object(runner, "screenshot", return_value="fake.png"):
            ok, lido = runner.verify_fill("esperado", (0, 0, 10, 10), timeout=0.05)
        assert ok is False
        assert lido == ""


class TestVerifyLov:

    def test_ok_quando_campo_nao_vazio(self):
        runner = _novo_runner()
        runner._ocr_engine.ler_regiao.return_value = "PALMEIRAS"
        with patch.object(runner, "screenshot", return_value="fake.png"):
            ok, lido = runner.verify_lov("provedor", (0, 0, 10, 10), timeout=1.0)
        assert ok is True
        assert lido == "PALMEIRAS"

    def test_falha_quando_campo_vazio(self):
        runner = _novo_runner()
        runner._ocr_engine.ler_regiao.return_value = ""
        with patch.object(runner, "screenshot", return_value="fake.png"):
            ok, lido = runner.verify_lov("provedor", (0, 0, 10, 10), timeout=0.05)
        assert ok is False


class TestClickNear:

    def test_clica_na_posicao_da_ancora(self):
        runner = _novo_runner()
        runner._matcher.find_anchor.return_value = (150, 250)
        with patch("vtae.runners.opencv_runner.pyautogui") as pag, \
             patch("vtae.runners.opencv_runner.time.sleep"):
            ok = runner.click_near("label.png", offset_x=250)
        assert ok is True
        pag.click.assert_called_once_with(150, 250)

    def test_relanca_com_mensagem_de_ancora_quando_nao_encontra(self):
        runner = _novo_runner()
        runner._matcher.find_anchor.side_effect = TemplateNotFoundError(
            "nao encontrado", template="label.png", score=0.2, threshold=0.8, tentativas=1,
        )
        runner._matcher.find_best_score.return_value = 0.2
        with pytest.raises(TemplateNotFoundError, match="Ancora nao encontrada"):
            runner.click_near("label.png")
