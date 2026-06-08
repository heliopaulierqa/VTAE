# src/vision/ocr_engine.py
"""
OcrEngine — facade centralizado de OCR para o VTAE.

Engine padrão: easyocr (pip puro, sem instalação no SO).
Tesseract removido na v0.5.11.

Controla qual engine OCR é usado via config.yaml:
    ocr_engine: easyocr     # padrão — pip puro, campos pequenos e grandes

Integração futura YOLO (Fase 6):
    ocr_engine: yolo+easyocr
    YOLO detecta a bounding box → EasyOCR lê o texto dentro dela.
    A troca será feita aqui, sem alterar nenhum flow.

Uso:
    # Via runner (recomendado — engine vem do config.yaml):
    ctx.runner.verify_lov(...)     # usa engine configurado automaticamente
    ctx.runner.verify_fill(...)    # idem

    # Direto (só se necessário fora dos runners):
    from src.vision.ocr_engine import OcrEngine
    engine = OcrEngine(engine="easyocr")
    texto = engine.ler_regiao(screenshot_path, regiao)
"""

import numpy as np
from PIL import Image


class OcrEngine:
    """
    Facade para motores OCR. Instanciado uma vez no runner e reutilizado.

    Args:
        engine: "easyocr" (unico engine suportado na v0.5.11+)
    """

    ENGINES_VALIDOS = ("easyocr",)  # tesseract removido na v0.5.11

    def __init__(self, engine: str = "easyocr"):
        engine = engine.lower().strip()
        if engine not in self.ENGINES_VALIDOS:
            raise ValueError(
                f"ocr_engine invalido: '{engine}'.\n"
                f"Valores aceitos: {self.ENGINES_VALIDOS}\n"
                f"Verifique o config.yaml da jornada.\n"
                f"Nota: tesseract foi removido na v0.5.11 — use easyocr."
            )
        self._engine = engine
        self._easyocr_reader = None  # lazy load — carrega na primeira leitura
        print(f"[OcrEngine] engine configurado: {engine}")

    # ------------------------------------------------------------------ #
    #  API publica                                                         #
    # ------------------------------------------------------------------ #

    def ler_regiao(self, screenshot_path: str, regiao: tuple) -> str:
        """
        Le o texto de uma regiao usando EasyOCR.

        Escala automatica baseada na altura do campo:
          < 20px  → 4x  (campos numericos Oracle Forms)
          < 35px  → 3x  (campos pequenos)
          < 60px  → 2x  (campos medios)
          >= 60px → 1x

        Args:
            screenshot_path: caminho do screenshot completo
            regiao: (x1, y1, x2, y2)

        Returns:
            Texto reconhecido em CAIXA ALTA.
        """
        return self._ler_easyocr(screenshot_path, regiao)

    def ler_tela_inteira(self, screenshot_path: str) -> str:
        """Le o texto da tela inteira usando EasyOCR."""
        return self._ler_easyocr_tela_inteira(screenshot_path)

    @property
    def engine_nome(self) -> str:
        return self._engine

    # ------------------------------------------------------------------ #
    #  EasyOCR                                                             #
    # ------------------------------------------------------------------ #

    def _get_reader(self):
        """Retorna instancia singleton EasyOCR (lazy load)."""
        if self._easyocr_reader is None:
            try:
                import easyocr
                print("[OcrEngine] Inicializando EasyOCR (primeira vez pode demorar ~30s)...")
                self._easyocr_reader = easyocr.Reader(["pt", "en"], gpu=False)
                print("[OcrEngine] EasyOCR pronto.")
            except ImportError:
                raise ImportError(
                    "EasyOCR nao instalado.\n"
                    "Execute no venv: pip install easyocr"
                )
        return self._easyocr_reader

    def _ler_easyocr(self, screenshot_path: str, regiao: tuple) -> str:
        img = Image.open(screenshot_path)
        recorte = img.crop(regiao)

        w, h = recorte.size
        if h < 20:
            escala = 4
        elif h < 35:
            escala = 3
        elif h < 60:
            escala = 2
        else:
            escala = 1

        if escala > 1:
            recorte = recorte.resize((w * escala, h * escala), Image.LANCZOS)

        arr = np.array(recorte)
        reader = self._get_reader()
        resultados = reader.readtext(arr, detail=0, paragraph=True)
        texto = " ".join(resultados).strip()
        return texto.upper()

    def _ler_easyocr_tela_inteira(self, screenshot_path: str) -> str:
        img = Image.open(screenshot_path)
        arr = np.array(img)
        reader = self._get_reader()
        resultados = reader.readtext(arr, detail=0, paragraph=True)
        return " ".join(resultados).strip().upper()