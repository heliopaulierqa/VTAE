"""
PlaywrightRunner — runner para sistemas web.
Usa Playwright para controle de browser no lugar do OpenCV.

Instalação:
    pip install playwright
    playwright install chromium
"""

import os
import time

from playwright.sync_api import sync_playwright, Page, Browser, Playwright

from vtae.core.base_runner import BaseRunner


class PlaywrightRunner(BaseRunner):
    """
    Runner real para sistemas web usando Playwright.
    Implementa o mesmo contrato do BaseRunner — todos os flows
    existentes funcionam sem nenhuma alteração.

    Uso:
        runner = PlaywrightRunner(url="http://sistema.interno/login")
        ctx = FlowContext(runner=runner, config=LoginConfigSistemaWeb)
        LoginFlow().execute(ctx, observer=observer)

    Nota sobre templates:
        No PlaywrightRunner, o parâmetro `template` dos métodos
        click_template/wait_template é um SELETOR CSS ou XPath,
        não um caminho de imagem como no OpenCVRunner.

        Exemplos de seletores:
            "#input-usuario"           → campo com id
            "input[name='username']"   → campo pelo atributo name
            "button[type='submit']"    → botão de submit
            "text=Entrar"              → elemento pelo texto visível
    """

    def __init__(
        self,
        url: str,
        headless: bool = False,
        timeout: float = 10.0,
        slow_mo: int = 100,
    ):
        """
        Args:
            url: URL inicial do sistema a ser testado.
            headless: False = abre o browser visível (recomendado para debug).
            timeout: timeout padrão em segundos para esperas.
            slow_mo: delay em ms entre ações (simula uso humano, evita bloqueios).
        """
        self.url = url
        self.headless = headless
        self.default_timeout = timeout * 1000
        self.slow_mo = slow_mo

        self._pw: Playwright = sync_playwright().start()
        self._browser: Browser = self._pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=["--start-maximized"],
        )

        # cria página com tamanho de tela completo
        self._page: Page = self._browser.new_page(
            viewport=None,  # None = usa o tamanho real da janela maximizada
            no_viewport=True,
        )
        self._page.set_default_timeout(self.default_timeout)
        self._page.goto(url)

        # garante que a janela está maximizada
        self._page.evaluate("() => { window.moveTo(0,0); window.resizeTo(screen.availWidth, screen.availHeight); }")
        time.sleep(0.5)

    # ──────────────────────────────────────────────
    # Métodos abstratos obrigatórios (BaseRunner)
    # ──────────────────────────────────────────────

    def click_template(self, template: str, threshold: float = 0.8) -> bool:
        """
        Clica no elemento identificado pelo seletor CSS/XPath.

        Args:
            template: seletor CSS ou XPath do elemento.

        Returns:
            True se encontrou e clicou, False se não encontrou.
        """
        try:
            self._page.click(template, timeout=3000)
            return True
        except Exception:
            return False

    def type_text(self, text: str) -> None:
        """
        Digita texto no elemento atualmente focado.

        Args:
            text: texto a digitar.
        """
        self._page.keyboard.type(text, delay=50)

    def wait_template(
        self,
        template: str,
        timeout: float = 10.0,
        threshold: float = 0.8,
    ) -> bool:
        """
        Aguarda o elemento aparecer na página.

        Args:
            template: seletor CSS ou XPath do elemento.
            timeout: tempo máximo de espera em segundos.

        Returns:
            True se o elemento apareceu, False caso contrário.
        """
        try:
            self._page.wait_for_selector(template, timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def screenshot(self, name: str) -> str:
        """
        Captura screenshot da página atual e salva no caminho especificado.

        Args:
            name: caminho completo do arquivo de saída.

        Returns:
            O mesmo caminho recebido.
        """
        folder = os.path.dirname(name)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self._page.screenshot(path=name, full_page=False)
        return name

    # ──────────────────────────────────────────────
    # safe_click com retry e exceção
    # ──────────────────────────────────────────────

    def safe_click(
        self,
        template: str,
        threshold: float = 0.8,
        retries: int = 3,
        delay: float = 0.5,
    ) -> bool:
        """
        Clica no elemento com retry automático.
        Lança RuntimeError se não encontrar após todas as tentativas.

        Raises:
            RuntimeError: se o elemento não for encontrado após `retries` tentativas.
        """
        for attempt in range(1, retries + 1):
            if self.click_template(template):
                return True
            print(f"[safe_click] tentativa {attempt}/{retries} falhou — '{template}'")
            if attempt < retries:
                time.sleep(delay)

        raise RuntimeError(
            f"Elemento não encontrado após {retries} tentativas: '{template}'"
        )

    # ──────────────────────────────────────────────
    # Métodos extras específicos para web
    # ──────────────────────────────────────────────

    def fill(self, selector: str, text: str) -> None:
        """
        Limpa o campo e preenche com o texto.
        Mais confiável que type_text para inputs complexos.

        Args:
            selector: seletor CSS/XPath do campo.
            text: texto a preencher.
        """
        self._page.fill(selector, text)

    def is_visible(self, selector: str) -> bool:
        """
        Verifica se o elemento está visível na página sem interagir.

        Args:
            selector: seletor CSS/XPath do elemento.

        Returns:
            True se visível, False caso contrário.
        """
        try:
            return self._page.is_visible(selector)
        except Exception:
            return False

    def get_text(self, selector: str) -> str:
        """
        Retorna o texto visível de um elemento.
        Útil para validações dentro dos flows.

        Args:
            selector: seletor CSS/XPath do elemento.

        Returns:
            Texto do elemento ou string vazia se não encontrado.
        """
        try:
            return self._page.inner_text(selector)
        except Exception:
            return ""

    def navigate(self, url: str) -> None:
        """
        Navega para uma URL diferente.

        Args:
            url: URL de destino.
        """
        self._page.goto(url)
        self._page.wait_for_load_state("networkidle")

    def maximize(self) -> None:
        """Maximiza a janela do browser."""
        self._page.evaluate(
            "() => { window.moveTo(0,0); window.resizeTo(screen.availWidth, screen.availHeight); }"
        )
        time.sleep(0.5)

    # ──────────────────────────────────────────────
    # Gerenciamento do browser
    # ──────────────────────────────────────────────

    def close(self) -> None:
        """Fecha o browser e encerra o Playwright. Chame ao final dos testes."""
        self._browser.close()
        self._pw.stop()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
