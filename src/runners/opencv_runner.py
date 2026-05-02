"""
OpenCVRunner — runner desktop via visão computacional.

v0.3.3 — F2-A: usa TemplateMatcher com multi-scale matching.
Log de diagnóstico mostra score máximo quando template não é encontrado.
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

    v0.3.3 — Multi-scale template matching:
        O TemplateMatcher agora testa o template em múltiplas escalas
        (0.8x, 0.9x, 1.0x, 1.1x, 1.2x) antes de concluir que não encontrou.
        Resolve falhas causadas por diferença de zoom/DPI entre a captura
        do template e a execução do teste.

    Uso:
        runner = OpenCVRunner(confidence=0.8)
        ctx = FlowContext(runner=runner, config=LoginConfigSisLab)
        LoginFlow().execute(ctx, observer=observer)
    """

    def __init__(self, confidence: float = 0.8,
                 scales: tuple = None):
        """
        Args:
            confidence: threshold de similaridade (0.0 a 1.0).
                        0.8 = 80% de similaridade mínima.
                        Use 0.6–0.7 para templates com variação de renderização.
                        Use 0.85–0.95 para templates muito específicos.
            scales: escalas para multi-scale matching.
                    None = usa padrão (1.0, 0.9, 1.1, 0.8, 1.2).
                    Passe (1.0,) para desativar multi-scale.
        """
        self.confidence = confidence
        self._matcher = TemplateMatcher(confidence=confidence, scales=scales)

    # ──────────────────────────────────────────────
    # Métodos abstratos obrigatórios (BaseRunner)
    # ──────────────────────────────────────────────

    def click_template(self, template: str, threshold: float = None) -> bool:
        """
        Clica no centro do melhor match do template na tela.
        Testa múltiplas escalas automaticamente.

        Args:
            template: caminho para a imagem PNG do template.
            threshold: override do confidence padrão.

        Returns:
            True se encontrou e clicou, False se não encontrou.
        """
        result = self._matcher.find_best(template, threshold)
        if result:
            pyautogui.click(result.x, result.y)
            time.sleep(0.3)
            return True
        return False

    def type_text(self, text: str) -> None:
        """
        Digita texto no elemento atualmente focado.
        Usa pyautogui.write — suporta unicode e acentos no Windows.
        """
        pyautogui.write(text, interval=0.05)

    def wait_template(self, template: str,
                      timeout: float = 10.0,
                      threshold: float = None) -> bool:
        """
        Aguarda o template aparecer na tela (multi-scale).
        Verifica a cada 0.5s por até `timeout` segundos.

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

        Returns:
            O mesmo caminho recebido.
        """
        folder = os.path.dirname(name)
        if folder:
            os.makedirs(folder, exist_ok=True)
        pyautogui.screenshot(name)
        return name

    # ──────────────────────────────────────────────
    # safe_click com retry, diagnóstico e exceção
    # ──────────────────────────────────────────────

    def safe_click(self, template: str,
                   threshold: float = None,
                   retries: int = 3,
                   delay: float = 0.5) -> bool:
        """
        Clica no template com retry automático e log de diagnóstico.

        Se todas as tentativas falharem, loga o score máximo encontrado
        para facilitar o diagnóstico (ex: "score máximo: 0.63, threshold: 0.70").

        Raises:
            RuntimeError: se o template não for encontrado após `retries` tentativas.
        """
        thr = threshold or self.confidence

        for attempt in range(1, retries + 1):
            result = self._matcher.find_best(template, thr)
            if result:
                pyautogui.click(result.x, result.y)
                time.sleep(0.3)
                if result.scale != 1.0:
                    print(f"[safe_click] match em escala {result.scale:.1f}x "
                          f"(score={result.score:.3f}) — '{template}'")
                return True

            # diagnóstico — mostra o melhor score encontrado
            best_score = self._matcher.find_best_score(template)
            print(f"[safe_click] tentativa {attempt}/{retries} falhou — "
                  f"score máximo: {best_score:.3f} (threshold: {thr:.2f}) — '{template}'")

            if attempt < retries:
                time.sleep(delay)

        raise RuntimeError(
            f"Template não encontrado após {retries} tentativas: '{template}'\n"
            f"Score máximo encontrado: {self._matcher.find_best_score(template):.3f} "
            f"(threshold: {thr:.2f})\n"
            f"Dicas: reduza o confidence, recapture o template ou verifique "
            f"se a janela está maximizada."
        )

    # ──────────────────────────────────────────────
    # double_click — para menus Oracle Forms
    # ──────────────────────────────────────────────

    def double_click(self, template: str,
                     threshold: float = None,
                     retries: int = 3,
                     delay: float = 0.5) -> bool:
        """
        Duplo clique no centro do melhor match do template.
        Necessário para menus do Oracle Forms.

        Raises:
            RuntimeError: se o template não for encontrado após `retries` tentativas.
        """
        thr = threshold or self.confidence

        for attempt in range(1, retries + 1):
            result = self._matcher.find_best(template, thr)
            if result:
                pyautogui.doubleClick(result.x, result.y)
                time.sleep(0.3)
                return True

            best_score = self._matcher.find_best_score(template)
            print(f"[double_click] tentativa {attempt}/{retries} falhou — "
                  f"score máximo: {best_score:.3f} (threshold: {thr:.2f}) — '{template}'")

            if attempt < retries:
                time.sleep(delay)

        raise RuntimeError(
            f"Template não encontrado para duplo clique após {retries} tentativas: '{template}'\n"
            f"Score máximo: {self._matcher.find_best_score(template):.3f} "
            f"(threshold: {thr:.2f})"
        )

    # ──────────────────────────────────────────────
    # find_template — retorna coordenadas
    # ──────────────────────────────────────────────

    def find_template(self, template: str, threshold: float = None):
        """
        Encontra o template e retorna objeto com .x e .y do centro.
        Inclui .score e .scale para diagnóstico.

        Returns:
            MatchResult com .x, .y, .score, .scale — ou None.
        """
        return self._matcher.find_best(template, threshold)

    # ──────────────────────────────────────────────
    # is_visible — sem clicar
    # ──────────────────────────────────────────────

    def is_visible(self, template: str, threshold: float = None) -> bool:
        """Verifica se o template está visível na tela sem clicar."""
        return self._matcher.is_visible(template, threshold)

    def find_all(self, template: str,
                 threshold: float = None) -> list:
        """
        Encontra todas as ocorrências do template na tela.
        Usa escala 1.0 — útil para grades com múltiplas linhas iguais.
        """
        return self._matcher.find_all(template, threshold)

    # ──────────────────────────────────────────────
    # click_near — anchor-based clicking (F2-C)
    # ──────────────────────────────────────────────

    def click_near(self, template: str,
                   offset_x: int = 0,
                   offset_y: int = 0,
                   threshold: float = None) -> bool:
        """
        Encontra o template como âncora e clica na posição deslocada.
        Útil para Oracle Forms onde o label é estável mas o campo fica
        a uma distância fixa do label.

        Args:
            template: caminho para o template âncora.
            offset_x: pixels à direita do centro do âncora.
            offset_y: pixels abaixo do centro do âncora.
            threshold: override do confidence padrão.

        Returns:
            True se o âncora foi encontrado e o clique executado.

        Raises:
            RuntimeError: se o âncora não for encontrado.

        Exemplo:
            # encontra label "Nome:" e clica 200px à direita (no campo)
            runner.click_near("templates/si3/label_nome.png", offset_x=200)
        """
        try:
            x, y = self._matcher.find_anchor(template, offset_x, offset_y, threshold)
            pyautogui.click(x, y)
            time.sleep(0.3)
            return True
        except TemplateNotFoundError:
            best_score = self._matcher.find_best_score(template)
            raise RuntimeError(
                f"Âncora não encontrada: '{template}'\n"
                f"Score máximo: {best_score:.3f} "
                f"(threshold: {threshold or self.confidence:.2f})"
            )
