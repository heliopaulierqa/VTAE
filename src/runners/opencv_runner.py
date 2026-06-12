"""
OpenCVRunner — runner desktop via visão computacional.

v0.5.12 — verify_fill_clipboard
  - verify_fill_clipboard: validacao via clipboard (Ctrl+A + Ctrl+C)
    mais confiavel que OCR para campos de texto livre Oracle Forms
  - _verify_campo detecta metodo automaticamente via config.yaml:
      metodo: clipboard -> verify_fill_clipboard
      x1/y1/x2/y2      -> verify_fill (EasyOCR)

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
import pyperclip

from src.runners.base_runner import BaseRunner
from src.vision.template import TemplateMatcher
from src.core.types import TemplateNotFoundError
from src.vision.ocr import OcrHelper
from src.vision.ocr_engine import OcrEngine


class OpenCVRunner(BaseRunner):
    """
    Runner real para sistemas desktop usando visão computacional.

    v0.5.12 — verify_fill_clipboard:
      Metodo alternativo ao OCR para campos de texto livre Oracle Forms.
      Usa Ctrl+A + Ctrl+C para ler o valor do campo via clipboard.
      Mais confiavel que OCR em campos com fonte bitmap pequena.

    v0.5.9 — verify_fill e verify_lov com evidências reais:
      O screenshot de validação é tirado DENTRO do loop de tentativas,
      garantindo que a imagem reflita o estado da tela no momento exato
      em que o OCR leu o valor — não um frame anterior à digitação.
    """

    def __init__(self, confidence: float = 0.8, scales: tuple = None,
                 ocr_engine: str = "easyocr"):
        self.confidence = confidence
        self._matcher   = TemplateMatcher(confidence=confidence, scales=scales)
        self._logger: logging.Logger | None = None
        self._ocr_engine = OcrEngine(engine=ocr_engine)

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
    # verify_fill — validação pós-digitação via OCR (Obs-Fase1)
    # ──────────────────────────────────────────────

    def verify_fill(self, expected_value: str,
                    region: tuple,
                    timeout: float = 3.0,
                    debug_path: str = None) -> tuple[bool, str]:
        """
        Verifica via OCR (EasyOCR) se o valor esperado esta na regiao apos digitacao.
        Ideal para campos numericos e campos com regioes bem delimitadas.

        Para campos de texto livre Oracle Forms (nome, data, sexo),
        prefira verify_fill_clipboard que e mais confiavel.

        Returns:
            (True, valor_lido) se encontrou o valor na regiao.
            (False, "") se expirou sem encontrar.
        """
        deadline = time.monotonic() + timeout
        attempt  = 0

        while time.monotonic() < deadline:
            attempt += 1
            ts  = int(time.monotonic() * 1000)
            tmp = f"/tmp/verify_fill_attempt_{ts}.png"
            self.screenshot(tmp)
            texto = self._ocr_engine.ler_regiao(tmp, region)

            self._log(
                f"[verify_fill] tentativa {attempt} — "
                f"esperado: '{expected_value}' | OCR leu: '{texto.strip()}'"
            )

            if expected_value.upper() in texto.upper():
                self._log(f"[verify_fill] OK na tentativa {attempt}")
                return True, texto.strip()

            time.sleep(0.5)

        ts_fail = int(time.time())
        path_debug = debug_path or f"/tmp/verify_fill_debug_{ts_fail}.png"
        # Salva o RECORTE da regiao — nao a tela inteira — para diagnostico preciso
        tmp_full = f"/tmp/verify_fill_full_{ts_fail}.png"
        self.screenshot(tmp_full)
        try:
            import cv2
            img = cv2.imread(tmp_full)
            x1, y1, x2, y2 = region
            recorte = img[y1:y2, x1:x2]
            folder = os.path.dirname(path_debug)
            if folder:
                os.makedirs(folder, exist_ok=True)
            cv2.imwrite(path_debug, recorte)
        except Exception:
            self.screenshot(path_debug)
        self._log(
            f"[verify_fill] FALHOU após {attempt} tentativas — "
            f"valor esperado: '{expected_value}' | região: {region} | "
            f"debug: {path_debug}",
            level="warning"
        )
        return False, ""

    # ──────────────────────────────────────────────
    # verify_fill_clipboard — validação via clipboard (v0.5.12)
    # ──────────────────────────────────────────────

    def verify_fill_clipboard(self, expected_value: str,
                               coord: tuple = None,
                               debug_path: str = None) -> tuple[bool, str]:
        """
        Verifica preenchimento via clipboard (Ctrl+A + Ctrl+C).

        Mais confiavel que OCR para campos de texto livre Oracle Forms.
        NAO clica no campo — assume que o campo ja esta focado apos digitacao.
        Isso evita o failsafe do PyAutoGUI por coordenadas fora da tela.

        Args:
            expected_value: texto esperado (comparacao case-insensitive).
            coord: ignorado — mantido para compatibilidade futura.
            debug_path: ignorado — mantido para compatibilidade de assinatura.

        Returns:
            (True, valor_lido) se campo contem o valor esperado.
            (False, valor_lido) caso contrario.
        """
        try:
            pyperclip.copy("")          # limpa clipboard anterior
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.2)
            valor_lido = pyperclip.paste().strip()
        except Exception as e:
            self._log(
                f"[verify_fill_clipboard] erro ao ler clipboard: {e}",
                level="warning"
            )
            return False, ""

        self._log(
            f"[verify_fill_clipboard] esperado: '{expected_value}' | "
            f"clipboard leu: '{valor_lido}'"
        )

        ok = expected_value.upper() in valor_lido.upper()
        if not ok:
            self._log(
                f"[verify_fill_clipboard] FALHOU — "
                f"esperado: '{expected_value}' | lido: '{valor_lido}'",
                level="warning"
            )
        else:
            self._log(f"[verify_fill_clipboard] OK — '{valor_lido}'")

        return ok, valor_lido

    # ──────────────────────────────────────────────
    # verify_lov — validação pós-seleção de LOV (Obs-Fase1b)
    # ──────────────────────────────────────────────

    def verify_lov(self, campo_nome: str,
                   region: tuple,
                   timeout: float = 3.0,
                   debug_path: str = None) -> tuple[bool, str]:
        """
        Verifica via OCR se campo LOV foi preenchido apos selecao.
        Verifica apenas se NAO esta vazio — qualquer texto vale.

        Returns:
            (True, valor_lido) se campo tem conteudo.
            (False, "") se campo ficou vazio.
        """
        deadline = time.monotonic() + timeout
        attempt  = 0

        while time.monotonic() < deadline:
            attempt += 1
            ts  = int(time.monotonic() * 1000)
            tmp = f"/tmp/verify_lov_attempt_{ts}.png"
            self.screenshot(tmp)
            texto = self._ocr_engine.ler_regiao(tmp, region).strip()

            self._log(
                f"[verify_lov] campo '{campo_nome}' — "
                f"tentativa {attempt} — OCR leu: '{texto}'"
            )

            if texto:
                self._log(f"[verify_lov] OK — campo '{campo_nome}' preenchido: '{texto}'")
                return True, texto

            time.sleep(0.5)

        ts_fail = int(time.time())
        path_debug = debug_path or f"/tmp/verify_lov_debug_{campo_nome}_{ts_fail}.png"
        self.screenshot(path_debug)
        self._log(
            f"[verify_lov] FALHOU — campo '{campo_nome}' ficou VAZIO após {attempt} tentativas | "
            f"região: {region} | debug: {path_debug}",
            level="warning"
        )
        return False, ""

    # ──────────────────────────────────────────────
    # find_anchor_region — OCR baseado em template de label (v0.5.13)
    # ──────────────────────────────────────────────

    def find_anchor_region(self, anchor_template: str,
                            offset_x: int = 0,
                            offset_y: int = 2,
                            largura: int = 280,
                            altura: int = 14,
                            threshold: float = None) -> tuple | None:
        """
        Localiza o template do label na tela e calcula a regiao do campo ao lado.

        Mais robusto que coordenadas absolutas — funciona mesmo se a janela
        mudar de posicao ou resolucao.

        Args:
            anchor_template: caminho para o PNG do label do campo
            offset_x:        deslocamento horizontal a partir do lado direito do label
            offset_y:        deslocamento vertical a partir do topo do label
            largura:         largura da regiao a ler
            altura:          altura da regiao a ler
            threshold:       threshold do template matching

        Returns:
            (x1, y1, x2, y2) da regiao do campo, ou None se label nao encontrado.
        """
        result = self._matcher.find_best(anchor_template, threshold)
        if not result:
            self._log(
                f"[find_anchor_region] label nao encontrado: '{anchor_template}'",
                level="warning"
            )
            return None
        # result.x, result.y = centro do template
        # Estimar largura do template para calcular borda direita
        import cv2 as _cv2
        try:
            tpl = _cv2.imread(anchor_template)
            tpl_w = tpl.shape[1] if tpl is not None else 0
        except Exception:
            tpl_w = 0
        x1 = result.x - tpl_w // 2 + tpl_w + offset_x
        y1 = result.y - altura // 2 + offset_y
        x2 = x1 + largura
        y2 = y1 + altura
        self._log(
            f"[find_anchor_region] label '{anchor_template}' encontrado em "
            f"({result.x},{result.y}) -> regiao ({x1},{y1},{x2},{y2})"
        )
        return (x1, y1, x2, y2)

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
