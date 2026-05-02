"""
TemplateMatcher — núcleo de visão computacional do VTAE.

v0.3.3 — F2-A: Multi-scale template matching.
v0.3.4 — F2-B: Heurísticas de confiança visual.
    Quando multi-scale falha, tenta ajustes de pré-processamento
    (contraste, brilho, equalização, cinza) antes de concluir que não encontrou.
    Log detalhado mostra qual ajuste funcionou ou o score de cada tentativa.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from PIL import ImageGrab

from src.core.types import TemplateNotFoundError


@dataclass
class MatchResult:
    """
    Resultado de um match — posição, escala, score e ajuste usado.
    """
    x: int
    y: int
    score: float
    scale: float
    adjustment: str = "none"

    def __str__(self) -> str:
        adj = f", adj={self.adjustment}" if self.adjustment != "none" else ""
        return (f"MatchResult(pos=({self.x},{self.y}), "
                f"score={self.score:.3f}, scale={self.scale:.2f}x{adj})")


@dataclass
class DiagnosticReport:
    """
    Relatório de diagnóstico quando nenhuma estratégia encontra o template.
    """
    template_path: str
    threshold: float
    attempts: list = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Template não encontrado: '{self.template_path}'",
            f"Threshold: {self.threshold:.2f}",
            "Scores por estratégia:",
        ]
        for strategy, score in self.attempts:
            indicator = "✓" if score >= self.threshold else "✗"
            lines.append(f"  {indicator} {strategy:<25} score={score:.3f}")
        lines.append("Dicas:")
        lines.append("  - Reduza o confidence (ex: threshold=0.6)")
        lines.append("  - Recapture o template com o sistema no mesmo estado")
        lines.append("  - Verifique se a janela está maximizada")
        return "\n".join(lines)


class TemplateMatcher:
    """
    Template matching via OpenCV com multi-scale e heurísticas de confiança visual.

    Pipeline de matching:
        1. Multi-scale na tela original    (escalas: 1.0, 0.9, 1.1, 0.8, 1.2)
        2. Se falhar → contraste +30%
        3. Se falhar → brilho +20
        4. Se falhar → equalização de histograma
        5. Se falhar → escala de cinza
        6. Se tudo falhar → DiagnosticReport com score de cada tentativa

    Por que heurísticas:
        Oracle Forms e sistemas legados têm renderização inconsistente —
        o mesmo botão pode aparecer com contraste diferente dependendo do
        tema Windows, DPI, modo de compatibilidade ou estado de foco.
        Os ajustes compensam essas variações sem precisar recapturar o template.
    """

    DEFAULT_SCALES = (1.0, 0.9, 1.1, 0.8, 1.2)

    # Ajustes tentados em ordem — nome, (alpha, beta) ou None para equalize/gray
    _ADJUSTMENTS = [
        ("contrast",   dict(type="scale_abs", alpha=1.3, beta=0)),
        ("brightness", dict(type="scale_abs", alpha=1.0, beta=30)),
        ("equalize",   dict(type="equalize")),
        ("gray",       dict(type="gray")),
    ]

    def __init__(self, confidence: float = 0.8,
                 scales: tuple = None,
                 use_adjustments: bool = True):
        """
        Args:
            confidence: threshold mínimo de similaridade (0.0 a 1.0).
            scales: escalas para multi-scale. None = usa DEFAULT_SCALES.
            use_adjustments: False = desativa heurísticas (só multi-scale).
        """
        self.confidence = confidence
        self.scales = scales or self.DEFAULT_SCALES
        self.use_adjustments = use_adjustments

    # ──────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────

    def find(self, template_path: str,
             threshold: float = None) -> tuple[int, int]:
        """
        Retorna (x, y) do melhor match.
        Tenta multi-scale + heurísticas automaticamente.
        Lança TemplateNotFoundError com relatório de diagnóstico se falhar.
        """
        result = self.find_best(template_path, threshold)
        if result is None:
            report = self.diagnose(template_path, threshold)
            raise TemplateNotFoundError(f"\n{report.summary()}")
        return result.x, result.y

    def find_or_none(self, template_path: str,
                     threshold: float = None) -> tuple[int, int] | None:
        """Igual ao find(), mas retorna None em vez de lançar exceção."""
        result = self.find_best(template_path, threshold)
        return (result.x, result.y) if result else None

    def find_best(self, template_path: str,
                  threshold: float = None) -> MatchResult | None:
        """
        Retorna o MatchResult completo — score, escala e ajuste usado.
        Tenta todos os ajustes até encontrar ou esgotar as estratégias.
        """
        thr = threshold or self.confidence
        screen = self._capture_screen()
        tmpl = self._load_template(template_path)

        # Tentativa 1 — multi-scale sem ajuste
        result = self._try_multiscale(screen, tmpl, thr, "none")
        if result:
            return result

        if not self.use_adjustments:
            return None

        # Tentativas 2-5 — ajustes de pré-processamento
        for adj_name, adj_params in self._ADJUSTMENTS:
            s_adj = self._apply_adjustment(screen, adj_params)
            t_adj = self._apply_adjustment(tmpl, adj_params)
            result = self._try_multiscale(s_adj, t_adj, thr, adj_name)
            if result:
                print(f"[TemplateMatcher] match via '{adj_name}' "
                      f"(score={result.score:.3f}, scale={result.scale:.1f}x) "
                      f"— '{template_path}'")
                return result

        return None

    def find_best_score(self, template_path: str) -> float:
        """
        Retorna o melhor score encontrado em todas as escalas (sem threshold).
        Usado pelo diagnóstico do safe_click.
        """
        screen = self._capture_screen()
        tmpl = self._load_template(template_path)
        return max(
            self._match_single(screen, tmpl, s)[0]
            for s in self.scales
        )

    def diagnose(self, template_path: str,
                 threshold: float = None) -> DiagnosticReport:
        """
        Executa todas as estratégias e retorna relatório com score de cada uma.

        Exemplo:
            report = matcher.diagnose("templates/si3/btn_salvar.png")
            print(report.summary())
        """
        thr = threshold or self.confidence
        screen = self._capture_screen()
        tmpl = self._load_template(template_path)
        report = DiagnosticReport(template_path=template_path, threshold=thr)

        best_orig = max(
            self._match_single(screen, tmpl, s)[0] for s in self.scales
        )
        report.attempts.append(("original (multi-scale)", best_orig))

        if self.use_adjustments:
            for adj_name, adj_params in self._ADJUSTMENTS:
                s_adj = self._apply_adjustment(screen, adj_params)
                t_adj = self._apply_adjustment(tmpl, adj_params)
                best = max(
                    self._match_single(s_adj, t_adj, s)[0] for s in self.scales
                )
                report.attempts.append((adj_name, best))

        return report

    def is_visible(self, template_path: str,
                   threshold: float = None) -> bool:
        """Verifica se o template está visível na tela sem clicar."""
        return self.find_or_none(template_path, threshold) is not None

    def find_all(self, template_path: str,
                 threshold: float = None) -> list[tuple[int, int]]:
        """
        Encontra todas as ocorrências do template (escala 1.0).
        Útil para grades com múltiplos elementos iguais.
        """
        screen = self._capture_screen()
        tmpl = self._load_template(template_path)
        thr = threshold or self.confidence

        result = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        h, w = tmpl.shape[:2]
        locations = np.where(result >= thr)

        return [
            (int(pt[0] + w // 2), int(pt[1] + h // 2))
            for pt in zip(*locations[::-1])
        ]

    def find_anchor(self, anchor_path: str,
                    offset_x: int = 0,
                    offset_y: int = 0,
                    threshold: float = None) -> tuple[int, int]:
        """
        Encontra o template âncora e retorna posição deslocada pelo offset.
        Útil para Oracle Forms — encontra o label e calcula posição do campo.

        Raises:
            TemplateNotFoundError: se o âncora não for encontrado.

        Exemplo:
            # encontra label "Nome:" e clica 200px à direita (no campo)
            x, y = matcher.find_anchor("templates/si3/label_nome.png", offset_x=200)
        """
        ax, ay = self.find(anchor_path, threshold)
        return ax + offset_x, ay + offset_y

    # ──────────────────────────────────────────────
    # Internos — matching
    # ──────────────────────────────────────────────

    def _try_multiscale(self, screen: np.ndarray,
                        tmpl: np.ndarray,
                        threshold: float,
                        adjustment: str) -> MatchResult | None:
        """Testa todas as escalas e retorna o melhor MatchResult acima do threshold."""
        best: MatchResult | None = None

        for scale in self.scales:
            score, loc = self._match_single(screen, tmpl, scale)

            if score >= threshold:
                scaled_w = int(tmpl.shape[1] * scale)
                scaled_h = int(tmpl.shape[0] * scale)
                cx = int(loc[0] + scaled_w // 2)
                cy = int(loc[1] + scaled_h // 2)

                candidate = MatchResult(
                    x=cx, y=cy, score=score,
                    scale=scale, adjustment=adjustment
                )
                if best is None or score > best.score:
                    best = candidate

                # otimização: score muito alto sem ajuste em 1.0x → retorna já
                if scale == 1.0 and adjustment == "none" and score >= 0.9:
                    return best

        return best

    def _match_single(self, screen: np.ndarray,
                      tmpl: np.ndarray,
                      scale: float) -> tuple[float, tuple[int, int]]:
        """Executa matchTemplate para uma escala específica."""
        if scale != 1.0:
            new_w = max(1, int(tmpl.shape[1] * scale))
            new_h = max(1, int(tmpl.shape[0] * scale))
            tmpl_scaled = cv2.resize(
                tmpl, (new_w, new_h),
                interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
            )
        else:
            tmpl_scaled = tmpl

        if (tmpl_scaled.shape[0] > screen.shape[0] or
                tmpl_scaled.shape[1] > screen.shape[1]):
            return 0.0, (0, 0)

        result = cv2.matchTemplate(screen, tmpl_scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        return float(max_val), max_loc

    # ──────────────────────────────────────────────
    # Internos — pré-processamento
    # ──────────────────────────────────────────────

    def _apply_adjustment(self, img: np.ndarray, params: dict) -> np.ndarray:
        """Aplica o ajuste de pré-processamento conforme o tipo."""
        adj_type = params["type"]

        if adj_type == "scale_abs":
            return cv2.convertScaleAbs(img, alpha=params["alpha"], beta=params["beta"])

        if adj_type == "equalize":
            channels = cv2.split(img)
            return cv2.merge([cv2.equalizeHist(c) for c in channels])

        if adj_type == "gray":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        return img

    # ──────────────────────────────────────────────
    # Internos — captura e carregamento
    # ──────────────────────────────────────────────

    def _capture_screen(self) -> np.ndarray:
        """Captura a tela inteira e converte para BGR."""
        screenshot = ImageGrab.grab()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def _load_template(self, template_path: str) -> np.ndarray:
        """Carrega o template do disco. Lança FileNotFoundError se não existir."""
        tmpl = cv2.imread(template_path)
        if tmpl is None:
            raise FileNotFoundError(
                f"Arquivo de template não encontrado: '{template_path}'\n"
                f"Verifique se o recorte foi salvo na pasta correta."
            )
        return tmpl
