import os
import time

import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab

from vtae.core.base_runner import BaseRunner


class OpenCVRunner(BaseRunner):
    """
    Runner real usando visão computacional.
    Usa OpenCV para template matching e PyAutoGUI para controle de mouse/teclado.

    Uso:
        runner = OpenCVRunner(confidence=0.8)
        ctx = FlowContext(runner=runner, config=LoginConfigSisLab)
        LoginFlow().execute(ctx)
    """

    def __init__(self, confidence: float = 0.8):
        """
        Args:
            confidence: threshold padrão de similaridade (0.0 a 1.0).
                        Valores mais altos = mais exigente, menos falsos positivos.
                        Recomendado: 0.8 para a maioria dos casos.
        """
        self.confidence = confidence
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    # ──────────────────────────────────────────────
    # Métodos abstratos obrigatórios (BaseRunner)
    # ──────────────────────────────────────────────

    def click_template(self, template: str, threshold: float = None) -> bool:
        """
        Localiza o template na tela e clica no centro dele.

        Args:
            template: caminho para o arquivo .png do template.
            threshold: override do confidence padrão da instância.

        Returns:
            True se encontrou e clicou, False se não encontrou.
        """
        th = threshold if threshold is not None else self.confidence
        pos = self._find_template(template, th)
        if pos:
            pyautogui.click(pos[0], pos[1])
            time.sleep(0.3)
            return True
        return False

    def type_text(self, text: str) -> None:
        """
        Digita texto no elemento atualmente focado.
        Usa interval para simular digitação humana e evitar perda de caracteres.

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
        Aguarda o template aparecer na tela por até `timeout` segundos.
        Verifica a cada 0.5s.

        Args:
            template: caminho para o arquivo .png do template.
            timeout: tempo máximo de espera em segundos.
            threshold: override do confidence padrão da instância.

        Returns:
            True se o template apareceu dentro do timeout, False caso contrário.
        """
        th = threshold if threshold is not None else self.confidence
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._find_template(template, th):
                return True
            time.sleep(0.5)
        return False

    def screenshot(self, name: str) -> str:
        """
        Captura a tela inteira e salva no caminho especificado.
        Cria as pastas necessárias automaticamente.

        Args:
            name: caminho completo do arquivo de saída (ex: evidence/login/L01.png).

        Returns:
            O mesmo caminho recebido, para encadeamento.
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
            template: caminho para o arquivo .png do template.
            threshold: override do confidence padrão da instância.
            retries: número máximo de tentativas.
            delay: tempo de espera entre tentativas em segundos.

        Returns:
            True se clicou com sucesso.

        Raises:
            RuntimeError: se o elemento não for encontrado após `retries` tentativas.
        """
        th = threshold if threshold is not None else self.confidence
        for attempt in range(1, retries + 1):
            if self.click_template(template, th):
                return True
            print(
                f"[safe_click] tentativa {attempt}/{retries} falhou — '{template}'"
            )
            if attempt < retries:
                time.sleep(delay)

        raise RuntimeError(
            f"Elemento não encontrado após {retries} tentativas: '{template}'"
        )

    # ──────────────────────────────────────────────
    # Métodos auxiliares
    # ──────────────────────────────────────────────

    def _find_template(self, template: str, threshold: float):
        """
        Procura o template na tela atual usando matchTemplate do OpenCV.

        Retorna (cx, cy) com o centro do elemento encontrado,
        ou None se não encontrar acima do threshold.

        Args:
            template: caminho para o arquivo .png do template.
            threshold: score mínimo de similaridade (0.0 a 1.0).

        Raises:
            FileNotFoundError: se o arquivo de template não existir.
        """
        if not os.path.exists(template):
            raise FileNotFoundError(
                f"Arquivo de template não encontrado: '{template}'\n"
                f"Verifique se o recorte foi salvo na pasta correta."
            )

        screenshot = ImageGrab.grab()
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        tmpl = cv2.imread(template)
        if tmpl is None:
            raise ValueError(
                f"Não foi possível carregar o template: '{template}'\n"
                f"Verifique se o arquivo é uma imagem válida (.png, .jpg)."
            )

        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = tmpl.shape[:2]
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            return cx, cy

        return None

    def find_all(self, template: str, threshold: float = None) -> list[tuple]:
        """
        Encontra TODAS as ocorrências do template na tela.
        Útil quando o mesmo elemento aparece mais de uma vez.

        Args:
            template: caminho para o arquivo .png do template.
            threshold: override do confidence padrão da instância.

        Returns:
            Lista de tuplas (cx, cy) com o centro de cada ocorrência encontrada.
        """
        th = threshold if threshold is not None else self.confidence

        if not os.path.exists(template):
            raise FileNotFoundError(f"Template não encontrado: '{template}'")

        screenshot = ImageGrab.grab()
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        tmpl = cv2.imread(template)

        if tmpl is None:
            raise ValueError(f"Não foi possível carregar o template: '{template}'")

        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        h, w = tmpl.shape[:2]

        locations = np.where(result >= th)
        positions = []

        for pt in zip(*locations[::-1]):
            cx = pt[0] + w // 2
            cy = pt[1] + h // 2
            positions.append((cx, cy))

        return self._deduplicate(positions, min_distance=10)

    def is_visible(self, template: str, threshold: float = None) -> bool:
        """
        Verifica se o template está visível na tela sem clicar.
        Útil para asserções e condicionais nos flows.

        Args:
            template: caminho para o arquivo .png do template.
            threshold: override do confidence padrão da instância.

        Returns:
            True se o template estiver visível, False caso contrário.
        """
        th = threshold if threshold is not None else self.confidence
        return self._find_template(template, th) is not None

    # ──────────────────────────────────────────────
    # Utilitários internos
    # ──────────────────────────────────────────────

    @staticmethod
    def _deduplicate(
        positions: list[tuple], min_distance: int = 10
    ) -> list[tuple]:
        """
        Remove posições duplicadas que estejam muito próximas entre si.
        Evita múltiplos cliques no mesmo elemento por pequenas variações de pixel.
        """
        unique = []
        for pos in positions:
            if all(
                abs(pos[0] - u[0]) > min_distance
                or abs(pos[1] - u[1]) > min_distance
                for u in unique
            ):
                unique.append(pos)
        return unique