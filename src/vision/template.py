"""
TemplateMatcher — núcleo de visão computacional do VTAE.
Extraído do OpenCVRunner para permitir reutilização independente
(ex: YOLO poderá ser adicionado aqui como segundo matcher na Fase 2 final).
"""

import cv2
import numpy as np
from PIL import ImageGrab

from src.core.types import TemplateNotFoundError


class TemplateMatcher:
    """
    Template matching via OpenCV.
    Usado internamente pelo OpenCVRunner — pode ser instanciado
    diretamente quando apenas a detecção é necessária (sem controle de mouse).
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

    def find(self, template_path: str, threshold: float = None) -> tuple[int, int]:
        """
        Captura a tela e retorna (x, y) do centro do template.

        Args:
            template_path: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.

        Returns:
            Tupla (cx, cy) do centro do template encontrado.

        Raises:
            TemplateNotFoundError: se o template não for encontrado na tela.
            FileNotFoundError: se o arquivo de template não existir.
        """
        pos = self._match(template_path, threshold or self.confidence)
        if pos is None:
            raise TemplateNotFoundError(
                f"Template não encontrado na tela: '{template_path}'\n"
                f"Verifique se o recorte está na pasta correta e a janela está maximizada."
            )
        return pos

    def find_or_none(self, template_path: str, threshold: float = None) -> tuple[int, int] | None:
        """
        Igual ao find(), mas retorna None em vez de lançar exceção.
        Use quando a ausência do template é um caso esperado.
        """
        return self._match(template_path, threshold or self.confidence)

    def is_visible(self, template_path: str, threshold: float = None) -> bool:
        """
        Verifica se o template está visível na tela sem clicar.

        Args:
            template_path: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.

        Returns:
            True se visível, False caso contrário.
        """
        return self._match(template_path, threshold or self.confidence) is not None

    def find_all(self, template_path: str, threshold: float = None) -> list[tuple[int, int]]:
        """
        Encontra todas as ocorrências do template na tela.
        Útil quando há múltiplos elementos iguais (ex: várias linhas de uma tabela).

        Args:
            template_path: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.

        Returns:
            Lista de tuplas (cx, cy) com as coordenadas de cada ocorrência.
        """
        screen = self._capture_screen()
        tmpl = self._load_template(template_path)
        thr = threshold or self.confidence

        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        h, w = tmpl.shape[:2]
        locations = np.where(result >= thr)

        return [
            (pt[0] + w // 2, pt[1] + h // 2)
            for pt in zip(*locations[::-1])
        ]

    # ──────────────────────────────────────────────
    # Internos
    # ──────────────────────────────────────────────

    def _match(self, template_path: str, threshold: float) -> tuple[int, int] | None:
        """
        Núcleo do matching — captura tela e busca o template.

        Returns:
            Tupla (cx, cy) se encontrado, None caso contrário.
        """
        screen = self._capture_screen()
        tmpl = self._load_template(template_path)

        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = tmpl.shape[:2]
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            return cx, cy

        return None

    def _capture_screen(self) -> np.ndarray:
        """Captura a tela inteira e converte para BGR (formato OpenCV)."""
        screenshot = ImageGrab.grab()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def _load_template(self, template_path: str) -> np.ndarray:
        """
        Carrega o template do disco.

        Raises:
            FileNotFoundError: se o arquivo não existir.
        """
        tmpl = cv2.imread(template_path)
        if tmpl is None:
            raise FileNotFoundError(
                f"Arquivo de template não encontrado: '{template_path}'\n"
                f"Verifique se o recorte foi salvo na pasta correta."
            )
        return tmpl
