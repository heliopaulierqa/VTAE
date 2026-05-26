"""
OpenCVRunner — runner desktop via visão computacional.

v0.3.3 — F2-A: usa TemplateMatcher com multi-scale matching.
Log de diagnóstico mostra score máximo quando template não é encontrado.
"""

import logging
import os
import time

import pyautogui

from src.runners.base_runner import BaseRunner
from src.vision.template import TemplateMatcher
from src.core.types import TemplateNotFoundError
from src.vision.ocr import OcrHelper


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
                        0.8 = 80% de similaridade minima.
                        Use 0.6-0.7 para templates com variacao de renderizacao.
                        Use 0.85-0.95 para templates muito especificos.
            scales: escalas para multi-scale matching.
                    None = usa padrao (1.0, 0.9, 1.1, 0.8, 1.2).
                    Passe (1.0,) para desativar multi-scale.
        """
        self.confidence = confidence
        self._matcher   = TemplateMatcher(confidence=confidence, scales=scales)
        self._logger: logging.Logger | None = None  # Fase 1 — injetado pelo Observer

    def set_logger(self, logger: logging.Logger) -> None:
        """
        Injeta o logger do Observer no runner.
        Chamado pelo FlowContext apos instanciar o runner.
        Quando presente, substitui print() por logger.debug() — os logs
        chegam ao execution.log com o mesmo execution_id da execucao.
        """
        self._logger = logger

    def _log(self, msg: str, level: str = "debug") -> None:
        """
        Rota o log para o logger (quando injetado) ou para print().
        Todos os prints do runner passam por aqui — assim chegam ao
        execution.log quando o Observer estiver presente.
        """
        if self._logger:
            getattr(self._logger, level)(msg)
        else:
            print(msg)

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
                    self._log(f"[safe_click] match em escala {result.scale:.1f}x "
                              f"(score={result.score:.3f}) — '{template}'")
                return True

            best_score = self._matcher.find_best_score(template)
            self._log(f"[safe_click] tentativa {attempt}/{retries} falhou — "
                      f"score: {best_score:.3f} (threshold: {thr:.2f}) — '{template}'")

            if attempt < retries:
                time.sleep(delay)

        final_score = self._matcher.find_best_score(template)
        raise TemplateNotFoundError(
            f"Template nao encontrado apos {retries} tentativas: '{template}'\n"
            f"Score maximo encontrado: {final_score:.3f} (threshold: {thr:.2f})\n"
            f"Dicas: reduza o confidence, recapture o template ou verifique "
            f"se a janela esta maximizada.",
            template=template,
            score=final_score,
            threshold=thr,
            tentativas=retries,
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
            self._log(f"[double_click] tentativa {attempt}/{retries} falhou — "
                      f"score: {best_score:.3f} (threshold: {thr:.2f}) — '{template}'")

            if attempt < retries:
                time.sleep(delay)

        final_score = self._matcher.find_best_score(template)
        raise TemplateNotFoundError(
            f"Template nao encontrado para duplo clique apos {retries} tentativas: '{template}'\n"
            f"Score maximo: {final_score:.3f} (threshold: {thr:.2f})",
            template=template,
            score=final_score,
            threshold=thr,
            tentativas=retries,
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
    # verify_fill — validação pós-digitação (Fase A)
    # ──────────────────────────────────────────────

    def verify_fill(self, expected_value: str,
                    region: tuple,
                    timeout: float = 3.0,
                    debug_path: str = None) -> bool:
        """
        Verifica via OCR se o valor esperado está presente na região após digitação.
        Realiza múltiplas tentativas dentro do timeout para acomodar latência da UI.

        Args:
            expected_value: texto esperado no campo (comparação case-insensitive).
            region: tupla (x1, y1, x2, y2) da área do campo na tela.
            timeout: tempo máximo de espera em segundos (padrão 3s).
            debug_path: caminho para salvar screenshot de debug se falhar.
                        None = salva em /tmp/verify_fill_debug.png.

        Returns:
            True se o valor foi encontrado na região dentro do timeout.
            False caso contrário — o caller decide se isso é StepError.

        Exemplo:
            if not ctx.runner.verify_fill("JOAO DA SILVA", region=(100, 200, 400, 220)):
                raise StepError("Falha de Observabilidade: campo Nome nao contém o valor esperado")
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            tmp = debug_path or "/tmp/verify_fill_debug.png"
            screenshot = self.screenshot(tmp)
            texto = OcrHelper.ler_regiao(screenshot, region)
            if expected_value.upper() in texto.upper():
                return True
            time.sleep(0.5)

        if debug_path:
            self.screenshot(debug_path)
            self._log(f"[verify_fill] FALHOU — valor esperado: '{expected_value}' | "
                      f"debug salvo em: {debug_path}")
        else:
            self._log(f"[verify_fill] FALHOU — valor esperado: '{expected_value}' | "
                      f"regiao: {region}")
        return False

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
            final_score = self._matcher.find_best_score(template)
            raise TemplateNotFoundError(
                f"Ancora nao encontrada: '{template}'\n"
                f"Score maximo: {final_score:.3f} "
                f"(threshold: {threshold or self.confidence:.2f})",
                template=template,
                score=final_score,
                threshold=threshold or self.confidence,
                tentativas=1,
            )