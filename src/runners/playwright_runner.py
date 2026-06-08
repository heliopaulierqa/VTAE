"""
PlaywrightRunner — runner para sistemas web.

v0.5.9 — Obs-Fase1b:
  - set_logger implementado (estava ausente — logs MSI3 nunca chegavam ao execution.log)
  - _log unificado: todos os prints roteiam pelo logger quando injetado
  - verify_fill_web: valida preenchimento via DOM (não OCR) após fill()
"""

import logging
import os
import time

from playwright.sync_api import sync_playwright, Page, Browser, Playwright

from src.runners.base_runner import BaseRunner
from src.core.types import RunnerError
from src.vision.ocr import OcrHelper
from src.vision.ocr_engine import OcrEngine


class PlaywrightRunner(BaseRunner):
    """
    Runner real para sistemas web usando Playwright.

    v0.5.9 — set_logger implementado:
      Antes desta versão, todos os prints do PlaywrightRunner iam para o console
      e nunca apareciam no execution.log. Agora o Observer pode injetar o logger
      via set_logger() e todos os _log() chegam ao execution.log com o mesmo
      execution_id da execução.

    Nota sobre templates:
      No PlaywrightRunner, o parâmetro `template` dos métodos
      click_template/wait_template é um SELETOR CSS ou XPath,
      não um caminho de imagem como no OpenCVRunner.
    """

    def __init__(self, url: str, headless: bool = False,
                 timeout: float = 10.0, slow_mo: int = 100,
                 ocr_engine: str = "tesseract"):
        self.url = url
        self.headless = headless
        self.default_timeout = timeout * 1000
        self.slow_mo = slow_mo
        self._logger: logging.Logger | None = None  # Obs-Fase1b
        self._ocr_engine = OcrEngine(engine=ocr_engine)

        self._pw: Playwright = sync_playwright().start()
        self._browser: Browser = self._pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=["--start-maximized"],
        )
        self._page: Page = self._browser.new_page(
            viewport=None,
            no_viewport=True,
        )
        self._page.set_default_timeout(self.default_timeout)
        self._page.goto(url)
        self._page.evaluate(
            "() => { window.moveTo(0,0); window.resizeTo(screen.availWidth, screen.availHeight); }"
        )
        time.sleep(0.5)

    # ──────────────────────────────────────────────
    # Logger — Obs-Fase1b (estava ausente)
    # ──────────────────────────────────────────────

    def set_logger(self, logger: logging.Logger) -> None:
        """
        Injeta o logger do Observer no runner.

        CORREÇÃO v0.5.9: método ausente na versão anterior — todos os prints
        do PlaywrightRunner iam para o console e nunca apareciam no execution.log.
        Agora o Observer.inject_logger() funciona para runners web também.
        """
        self._logger = logger
        self._log("[PlaywrightRunner] logger injetado — logs web chegam ao execution.log")

    def _log(self, msg: str, level: str = "debug") -> None:
        """Roteia log para o logger (quando injetado) ou para print()."""
        if self._logger:
            getattr(self._logger, level)(msg)
        else:
            print(msg)

    # ──────────────────────────────────────────────
    # Métodos abstratos obrigatórios (BaseRunner)
    # ──────────────────────────────────────────────

    def click_template(self, template: str, threshold: float = 0.8) -> bool:
        try:
            self._page.click(template, timeout=3000)
            return True
        except Exception:
            return False

    def type_text(self, text: str) -> None:
        self._page.keyboard.type(text, delay=50)

    def wait_template(self, template: str,
                      timeout: float = 10.0,
                      threshold: float = 0.8) -> bool:
        try:
            self._page.wait_for_selector(template, timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def screenshot(self, name: str) -> str:
        folder = os.path.dirname(name)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self._page.screenshot(path=name, full_page=False)
        return name

    # ──────────────────────────────────────────────
    # safe_click com log via _log()
    # ──────────────────────────────────────────────

    def safe_click(self, template: str,
                   threshold: float = 0.8,
                   retries: int = 3,
                   delay: float = 0.5) -> bool:
        for attempt in range(1, retries + 1):
            if self.click_template(template):
                return True
            self._log(f"[safe_click] tentativa {attempt}/{retries} falhou — '{template}'")
            if attempt < retries:
                time.sleep(delay)

        raise RunnerError(
            f"Elemento não encontrado após {retries} tentativas: '{template}'"
        )

    # ──────────────────────────────────────────────
    # verify_fill_web — validação pós-fill via DOM
    # ──────────────────────────────────────────────

    def verify_fill_web(self, selector: str,
                        expected_value: str,
                        timeout: float = 3.0) -> bool:
        """
        Verifica via DOM se o campo foi preenchido com o valor esperado.

        Para sistemas web (APEX/MSI3) a validação via DOM é mais confiável
        que OCR — não depende de rendering, zoom ou fonte da tela.

        Args:
            selector: seletor CSS/XPath do campo input.
            expected_value: valor esperado (comparação case-insensitive).
            timeout: tempo máximo de espera.

        Returns:
            True se o campo contém o valor esperado.
            False caso contrário — caller decide se lança StepError.

        Uso:
            runner.fill("#P10_NOME", "JOAO DA SILVA")
            if not runner.verify_fill_web("#P10_NOME", "JOAO DA SILVA"):
                raise StepError("Falha de Observabilidade: campo Nome nao preenchido")
        """
        deadline = time.monotonic() + timeout
        attempt  = 0

        while time.monotonic() < deadline:
            attempt += 1
            try:
                valor_dom = self._page.input_value(selector)
                self._log(
                    f"[verify_fill_web] tentativa {attempt} — "
                    f"selector: '{selector}' | esperado: '{expected_value}' | DOM: '{valor_dom}'"
                )
                if expected_value.upper() in (valor_dom or "").upper():
                    self._log(f"[verify_fill_web] OK na tentativa {attempt}")
                    return True
            except Exception as e:
                self._log(f"[verify_fill_web] erro ao ler DOM: {e}")
            time.sleep(0.5)

        self._log(
            f"[verify_fill_web] FALHOU — selector: '{selector}' | "
            f"esperado: '{expected_value}' | após {attempt} tentativas",
            level="warning"
        )
        return False

    # ──────────────────────────────────────────────
    # Métodos extras específicos para web
    # ──────────────────────────────────────────────

    def fill(self, selector: str, text: str) -> None:
        self._page.fill(selector, text)

    def is_visible(self, selector: str) -> bool:
        try:
            return self._page.is_visible(selector)
        except Exception:
            return False

    def get_text(self, selector: str) -> str:
        try:
            return self._page.inner_text(selector)
        except Exception:
            return ""

    def navigate(self, url: str) -> None:
        self._page.goto(url)
        self._page.wait_for_load_state("networkidle")

    def maximize(self) -> None:
        self._page.evaluate(
            "() => { window.moveTo(0,0); window.resizeTo(screen.availWidth, screen.availHeight); }"
        )
        time.sleep(0.5)


    def verify_fill_screenshot(self, expected_value: str,
                                region: tuple,
                                timeout: float = 3.0,
                                debug_path: str = None) -> bool:
        """
        Verifica via screenshot + OCR se o valor esperado esta visivel na regiao.
        Usar quando o campo nao tem seletor CSS acessivel (ex: componentes APEX custom).
        O engine OCR usado depende do ocr_engine configurado (tesseract ou easyocr).

        Args:
            expected_value: texto esperado (comparacao case-insensitive).
            region: (x1, y1, x2, y2) — area do campo na tela.
            timeout: tempo maximo de espera.
            debug_path: caminho para screenshot de debug se falhar.

        Returns:
            True se encontrou o valor na regiao dentro do timeout.
        """
        deadline = time.monotonic() + timeout
        attempt  = 0

        while time.monotonic() < deadline:
            attempt += 1
            ts  = int(time.monotonic() * 1000)
            tmp = f"/tmp/verify_fill_web_attempt_{ts}.png"
            self.screenshot(tmp)
            texto = self._ocr_engine.ler_regiao(tmp, region)

            self._log(
                f"[verify_fill_screenshot] tentativa {attempt} — "
                f"esperado: \'{expected_value}\' | OCR leu: \'{texto.strip()}\'"
            )

            if expected_value.upper() in texto.upper():
                self._log(f"[verify_fill_screenshot] OK na tentativa {attempt}")
                return True

            time.sleep(0.5)

        ts_fail = int(time.time())
        path_debug = debug_path or f"/tmp/verify_fill_web_debug_{ts_fail}.png"
        self.screenshot(path_debug)
        self._log(
            f"[verify_fill_screenshot] FALHOU apos {attempt} tentativas — "
            f"valor esperado: \'{expected_value}\' | regiao: {region} | "
            f"debug: {path_debug}",
            level="warning"
        )
        return False

    def close(self) -> None:
        self._browser.close()
        self._pw.stop()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()