"""
OpenCVRunner — runner desktop via visão computacional.
Usa OpenCV para template matching e PyAutoGUI para controle de mouse/teclado.
"""

import os
import time

import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab

from vtae.core.base_runner import BaseRunner


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
                        Use 0.6-0.7 para templates com variação de renderização.
                        Use 0.85-0.95 para templates muito específicos.
        """
        self.confidence = confidence

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
        pos = self._find_template(template, threshold or self.confidence)
        if pos:
            pyautogui.click(pos[0], pos[1])
            time.sleep(0.3)
            return True
        return False

    def type_text(self, text: str) -> None:
        """
        Digita texto no elemento atualmente focado.
        Usa interval para simular digitação humana.

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
            if self._find_template(template, threshold or self.confidence):
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

        Args:
            template: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.
            retries: número de tentativas antes de lançar erro.
            delay: espera em segundos entre tentativas.

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

        Args:
            template: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.
            retries: número de tentativas antes de lançar erro.
            delay: espera em segundos entre tentativas.

        Raises:
            RuntimeError: se o template não for encontrado após `retries` tentativas.
        """
        for attempt in range(1, retries + 1):
            pos = self._find_template(template, threshold or self.confidence)
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

    def find_template(
        self,
        template: str,
        threshold: float = None,
    ):
        """
        Encontra o template na tela e retorna as coordenadas do centro.
        Útil para casos onde você precisa das coordenadas antes de clicar.

        Args:
            template: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.

        Returns:
            Objeto com .x e .y do centro do template, ou None se não encontrou.
        """
        pos = self._find_template(template, threshold or self.confidence)
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
        Útil para validações dentro dos flows.

        Args:
            template: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.

        Returns:
            True se visível, False caso contrário.
        """
        return self._find_template(template, threshold or self.confidence) is not None

    def find_all(
        self,
        template: str,
        threshold: float = None,
    ) -> list:
        """
        Encontra todas as ocorrências do template na tela.
        Útil quando há múltiplos elementos iguais (ex: várias linhas de uma tabela).

        Args:
            template: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.

        Returns:
            Lista de tuplas (cx, cy) com as coordenadas de cada ocorrência.
        """
        screenshot = ImageGrab.grab()
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        tmpl = cv2.imread(template)

        if tmpl is None:
            raise FileNotFoundError(
                f"Arquivo de template não encontrado: '{template}'\n"
                f"Verifique se o recorte foi salvo na pasta correta."
            )

        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        h, w = tmpl.shape[:2]
        locations = np.where(result >= (threshold or self.confidence))

        points = []
        for pt in zip(*locations[::-1]):
            cx = pt[0] + w // 2
            cy = pt[1] + h // 2
            points.append((cx, cy))

        return points

    # ──────────────────────────────────────────────
    # _find_template — núcleo do runner
    # ──────────────────────────────────────────────

    def _find_template(
        self,
        template: str,
        threshold: float,
    ):
        """
        Captura a tela e busca o template usando matchTemplate do OpenCV.

        Args:
            template: caminho para a imagem PNG do template.
            threshold: similaridade mínima (0.0 a 1.0).

        Returns:
            Tupla (cx, cy) do centro do template encontrado, ou None.

        Raises:
            FileNotFoundError: se o arquivo de template não existir.
        """
        screenshot = ImageGrab.grab()
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        tmpl = cv2.imread(template)

        if tmpl is None:
            raise FileNotFoundError(
                f"Arquivo de template não encontrado: '{template}'\n"
                f"Verifique se o recorte foi salvo na pasta correta."
            )

        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = tmpl.shape[:2]
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            return cx, cy

        return None
