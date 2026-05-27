"""
OpenCVRunner — runner desktop via visão computacional.

v0.5.9 — Obs-Fase1b: evidências reais
  - verify_fill: screenshot tirado DENTRO do loop (não antes), reflete estado real
  - verify_lov: novo método — confirma via OCR que campo LOV não ficou vazio
  - screenshot de debug salvo com timestamp e path explícito
  - _log unificado: todos os prints chegam ao execution.log quando logger injetado
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

    v0.5.9 — verify_fill e verify_lov com evidências reais:
      O screenshot de validação é tirado DENTRO do loop de tentativas,
      garantindo que a imagem reflita o estado da tela no momento exato
      em que o OCR leu o valor — não um frame anterior à digitação.
    """

    def __init__(self, confidence: float = 0.8, scales: tuple = None):
        self.confidence = confidence
        self._matcher   = TemplateMatcher(confidence=confidence, scales=scales)
        self._logger: logging.Logger | None = None

    def set_logger(self, logger: logging.Logger) -> None:
        """Injeta o logger do Observer. Chamado pelo FlowContext após instanciar."""
        self._logger = logger

    def _log(self, msg: str, level: str = "debug") -> None:
        if self._logger:
            getattr(self._logger, level)(msg)
        else:
            print(msg)

    # ──────────────────────────────────────────────
    # Métodos abstratos obrigatórios (BaseRunner)
    # ──────────────────────────────────────────────

    def click_template(self, template: str, threshold: float = None) -> bool:
        result = self._matcher.find_best(template, threshold)
        if result:
            pyautogui.click(result.x, result.y)
            time.sleep(0.3)
            return True
        return False

    def type_text(self, text: str) -> None:
        pyautogui.write(text, interval=0.05)

    def wait_template(self, template: str,
                      timeout: float = 10.0,
                      threshold: float = None) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._matcher.is_visible(template, threshold):
                return True
            time.sleep(0.5)
        return False

    def screenshot(self, name: str) -> str:
        folder = os.path.dirname(name)
        if folder:
            os.makedirs(folder, exist_ok=True)
        pyautogui.screenshot(name)
        return name

    # ──────────────────────────────────────────────
    # safe_click
    # ──────────────────────────────────────────────

    def safe_click(self, template: str,
                   threshold: float = None,
                   retries: int = 3,
                   delay: float = 0.5) -> bool:
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
            template=template, score=final_score, threshold=thr, tentativas=retries,
        )

    # ──────────────────────────────────────────────
    # double_click
    # ──────────────────────────────────────────────

    def double_click(self, template: str,
                     threshold: float = None,
                     retries: int = 3,
                     delay: float = 0.5) -> bool:
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
            template=template, score=final_score, threshold=thr, tentativas=retries,
        )

    # ──────────────────────────────────────────────
    # Utilitários
    # ──────────────────────────────────────────────

    def find_template(self, template: str, threshold: float = None):
        return self._matcher.find_best(template, threshold)

    def is_visible(self, template: str, threshold: float = None) -> bool:
        return self._matcher.is_visible(template, threshold)

    def find_all(self, template: str, threshold: float = None) -> list:
        return self._matcher.find_all(template, threshold)

    # ──────────────────────────────────────────────
    # verify_fill — validação pós-digitação (Obs-Fase1)
    # ──────────────────────────────────────────────

    def verify_fill(self, expected_value: str,
                    region: tuple,
                    timeout: float = 3.0,
                    debug_path: str = None) -> bool:
        """
        Verifica via OCR se o valor esperado está presente na região após digitação.

        CORREÇÃO v0.5.9: o screenshot é tirado DENTRO do loop de tentativas.
        A versão anterior capturava o screenshot ANTES do loop — sempre lia
        o estado anterior à digitação, gerando falsos negativos intermitentes.

        Args:
            expected_value: texto esperado (comparação case-insensitive).
            region: (x1, y1, x2, y2) — área do campo na tela.
            timeout: tempo máximo de espera em segundos.
            debug_path: caminho para screenshot de debug se falhar.
                        Se None, salva em /tmp/verify_fill_debug_<timestamp>.png
                        para não sobrescrever debug de steps anteriores.

        Returns:
            True se encontrou o valor na região dentro do timeout.
            False se expirou — o caller decide se lança StepError.
        """
        deadline = time.monotonic() + timeout
        attempt  = 0

        while time.monotonic() < deadline:
            attempt += 1
            # Screenshot tirado aqui — dentro do loop — reflete estado atual da tela
            ts  = int(time.monotonic() * 1000)
            tmp = f"/tmp/verify_fill_attempt_{ts}.png"
            self.screenshot(tmp)
            texto = OcrHelper.ler_regiao(tmp, region)

            self._log(
                f"[verify_fill] tentativa {attempt} — "
                f"esperado: '{expected_value}' | OCR leu: '{texto.strip()}'"
            )

            if expected_value.upper() in texto.upper():
                self._log(f"[verify_fill] OK na tentativa {attempt}")
                return True

            time.sleep(0.5)

        # Falhou — salvar screenshot de diagnóstico com timestamp único
        ts_fail = int(time.time())
        path_debug = debug_path or f"/tmp/verify_fill_debug_{ts_fail}.png"
        self.screenshot(path_debug)
        self._log(
            f"[verify_fill] FALHOU após {attempt} tentativas — "
            f"valor esperado: '{expected_value}' | região: {region} | "
            f"debug: {path_debug}",
            level="warning"
        )
        return False

    # ──────────────────────────────────────────────
    # verify_lov — validação pós-seleção de LOV (Obs-Fase1b)
    # ──────────────────────────────────────────────

    def verify_lov(self, campo_nome: str,
                   region: tuple,
                   timeout: float = 3.0,
                   debug_path: str = None) -> bool:
        """
        Verifica via OCR se um campo foi preenchido após seleção via LOV.

        Diferente do verify_fill (que verifica um valor exato), o verify_lov
        verifica apenas se o campo NÃO está vazio — qualquer texto vale.
        Isso é necessário porque o conteúdo selecionado na LOV pode ser
        formatado de forma diferente do termo de busca original.

        PROBLEMA RESOLVIDO: AG07 (Executante), AB11 (Médico), AB12 (Procedimentos)
        retornavam sucesso com campo vazio porque não havia validação pós-LOV.
        Com verify_lov, o step falha imediatamente se o campo ficou vazio,
        expondo o problema real (lista vazia, termo errado, popup não fechou).

        Args:
            campo_nome: nome do campo para mensagem de diagnóstico (ex: "Executante").
            region: (x1, y1, x2, y2) — área do campo na tela.
            timeout: tempo máximo de espera (padrão 3s — LOV fecha rápido).
            debug_path: caminho para screenshot de debug se falhar.

        Returns:
            True se o campo tem qualquer conteúdo após a LOV fechar.
            False se o campo ficou vazio — indica falha real na seleção.

        Uso obrigatório após qualquer LOV:
            self._selecionar_via_lov(ctx, coords, ...)
            if not ctx.runner.verify_lov("Executante",
                                          region=ctx.config.regioes_ocr["campo_executante_ag"]):
                raise AssertionError(
                    "Falha de Observabilidade: campo Executante ficou vazio apos LOV. "
                    "Verifique se o item foi selecionado — lista pode ter ficado vazia "
                    "ou o popup nao fechou corretamente."
                )
        """
        deadline = time.monotonic() + timeout
        attempt  = 0

        while time.monotonic() < deadline:
            attempt += 1
            ts  = int(time.monotonic() * 1000)
            tmp = f"/tmp/verify_lov_attempt_{ts}.png"
            self.screenshot(tmp)
            texto = OcrHelper.ler_regiao(tmp, region).strip()

            self._log(
                f"[verify_lov] campo '{campo_nome}' — "
                f"tentativa {attempt} — OCR leu: '{texto}'"
            )

            if texto:
                self._log(f"[verify_lov] OK — campo '{campo_nome}' preenchido: '{texto}'")
                return True

            time.sleep(0.5)

        # Campo ficou vazio — salvar evidência de diagnóstico
        ts_fail = int(time.time())
        path_debug = debug_path or f"/tmp/verify_lov_debug_{campo_nome}_{ts_fail}.png"
        self.screenshot(path_debug)
        self._log(
            f"[verify_lov] FALHOU — campo '{campo_nome}' ficou VAZIO após {attempt} tentativas | "
            f"região: {region} | debug: {path_debug}",
            level="warning"
        )
        return False

    # ──────────────────────────────────────────────
    # click_near — anchor-based clicking (F2-C)
    # ──────────────────────────────────────────────

    def click_near(self, template: str,
                   offset_x: int = 0,
                   offset_y: int = 0,
                   threshold: float = None) -> bool:
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
                template=template, score=final_score,
                threshold=threshold or self.confidence, tentativas=1,
            )