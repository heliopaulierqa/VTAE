"""
OpenCVRunner — runner desktop via visão computacional.
Usa TemplateMatcher (src/vision/template.py) para detecção
e PyAutoGUI para controle de mouse/teclado.
"""

import os
import time

import pyautogui

from src.runners.base_runner import BaseRunner
from src.vision.template import TemplateMatcher
from src.core.types import TemplateNotFoundError


class OpenCVRunner(BaseRunner):
    """
    Runner real para sistemas desktop usando visão computacional.
    Implementa o mesmo contrato do BaseRunner — todos os flows
    existentes funcionam sem nenhuma alteração.

    Uso:
        runner = OpenCVRunner(confidence=0.8)
        ctx = FlowContext(runner=runner, config=LoginConfigSisLab)
        LoginFlow().execute(ctx, observer=observer)
    """

    def __init__(self, confidence: float = 0.8):
        """
        Args:
            confidence: threshold de similaridade (0.0 a 1.0).
                        0.8 = 80% de similaridade mínima.
                        Use 0.6–0.7 para templates com variação de renderização.
                        Use 0.85–0.95 para templates muito específicos.
        """
        self.confidence = confidence
        self._matcher = TemplateMatcher(confidence=confidence)

    # ──────────────────────────────────────────────
    # Métodos abstratos obrigatórios (BaseRunner)
    # ──────────────────────────────────────────────

    def click_template(self, template: str, threshold: float = None) -> bool:
        """
        Clica no centro do template encontrado na tela.

        Args:
            template: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.

        Returns:
            True se encontrou e clicou, False se não encontrou.
        """
        pos = self._matcher.find_or_none(template, threshold)
        if pos:
            pyautogui.click(pos[0], pos[1])
            time.sleep(0.3)
            return True
        return False

    def type_text(self, text: str) -> None:
        """
        Digita texto no elemento atualmente focado.
        Usa pyautogui.write — suporta unicode e acentos no Windows.

        Args:
            text: texto a digitar.
        """
        pyautogui.write(text, interval=0.05)

    def wait_template(
        self,
        template: str,
        timeout: float = 10.0,
        threshold: float = None,
    ) -> bool:
        """
        Aguarda o template aparecer na tela.
        Verifica a cada 0.5s por até `timeout` segundos.

        Args:
            template: caminho para a imagem PNG do template.
            timeout: tempo máximo de espera em segundos.
            threshold: override do confidence padrão.

        Returns:
            True se apareceu, False se expirou o timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._matcher.is_visible(template, threshold):
                return True
            time.sleep(0.5)
        return False

    def screenshot(self, name: str) -> str:
        """
        Captura screenshot da tela inteira e salva no caminho especificado.

        Args:
            name: caminho completo do arquivo de saída (ex: evidence/L01.png).

        Returns:
            O mesmo caminho recebido.
        """
        folder = os.path.dirname(name)
        if folder:
            os.makedirs(folder, exist_ok=True)
        pyautogui.screenshot(name)
        return name

    # ──────────────────────────────────────────────
    # safe_click com retry e exceção
    # ──────────────────────────────────────────────

    def safe_click(
        self,
        template: str,
        threshold: float = None,
        retries: int = 3,
        delay: float = 0.5,
    ) -> bool:
        """
        Clica no template com retry automático.
        Lança RuntimeError se não encontrar após todas as tentativas.

        Raises:
            RuntimeError: se o template não for encontrado após `retries` tentativas.
        """
        for attempt in range(1, retries + 1):
            if self.click_template(template, threshold):
                return True
            print(f"[safe_click] tentativa {attempt}/{retries} falhou — '{template}'")
            if attempt < retries:
                time.sleep(delay)

        raise RuntimeError(
            f"Elemento não encontrado após {retries} tentativas: '{template}'\n"
            f"Verifique se o recorte foi salvo na pasta correta."
        )

    # ──────────────────────────────────────────────
    # double_click — para menus Oracle Forms
    # ──────────────────────────────────────────────

    def double_click(
        self,
        template: str,
        threshold: float = None,
        retries: int = 3,
        delay: float = 0.5,
    ) -> bool:
        """
        Duplo clique no centro do template encontrado na tela.
        Necessário para menus do Oracle Forms.

        Raises:
            RuntimeError: se o template não for encontrado após `retries` tentativas.
        """
        for attempt in range(1, retries + 1):
            pos = self._matcher.find_or_none(template, threshold)
            if pos:
                pyautogui.doubleClick(pos[0], pos[1])
                time.sleep(0.3)
                return True
            print(f"[double_click] tentativa {attempt}/{retries} falhou — '{template}'")
            if attempt < retries:
                time.sleep(delay)

        raise RuntimeError(
            f"Elemento não encontrado para duplo clique após {retries} tentativas: '{template}'\n"
            f"Verifique se o recorte foi salvo na pasta correta."
        )

    # ──────────────────────────────────────────────
    # find_template — retorna coordenadas
    # ──────────────────────────────────────────────

    def find_template(self, template: str, threshold: float = None):
        """
        Encontra o template na tela e retorna objeto com .x e .y do centro.
        Útil quando as coordenadas são necessárias antes do clique.

        Returns:
            Objeto com .x e .y, ou None se não encontrou.
        """
        pos = self._matcher.find_or_none(template, threshold)
        if pos:
            class Location:
                def __init__(self, x, y):
                    self.x = x
                    self.y = y
            return Location(pos[0], pos[1])
        return None

    # ──────────────────────────────────────────────
    # is_visible — sem clicar
    # ──────────────────────────────────────────────

    def is_visible(self, template: str, threshold: float = None) -> bool:
        """
        Verifica se o template está visível na tela sem clicar.

        Returns:
            True se visível, False caso contrário.
        """
        return self._matcher.is_visible(template, threshold)

    def find_all(self, template: str, threshold: float = None) -> list:
        """
        Encontra todas as ocorrências do template na tela.
        Útil quando há múltiplos elementos iguais (ex: várias linhas de uma tabela).

        Returns:
            Lista de tuplas (cx, cy) com as coordenadas de cada ocorrência.
        """
        return self._matcher.find_all(template, threshold)
