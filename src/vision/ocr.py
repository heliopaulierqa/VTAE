# src/vision/ocr.py
"""
Helper centralizado de OCR para o VTAE.

Engine padrão: EasyOCR (pip puro, sem dependência de instalação no SO).
Tesseract removido na v0.5.11 — EasyOCR é mais preciso em campos pequenos,
não requer instalação separada e é compatível com pipeline YOLO (Fase 6).

Uso recomendado (via OcrEngine — runners usam automaticamente):
    ocr_engine: easyocr  # em config.yaml — zero código no flow

Uso direto (quando necessário fora dos runners):
    from src.vision.ocr import OcrHelper
    texto = OcrHelper.ler_regiao(screenshot_path, regiao)
"""

import numpy as np
from PIL import Image
from pathlib import Path

# Singleton EasyOCR — lazy load na primeira chamada
_easyocr_reader = None


def _get_easyocr_reader():
    """Retorna instancia singleton do EasyOCR (lazy load)."""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            print("[OCR] Inicializando EasyOCR (primeira vez pode demorar ~30s)...")
            _easyocr_reader = easyocr.Reader(["pt", "en"], gpu=False)
            print("[OCR] EasyOCR pronto.")
        except ImportError:
            raise ImportError(
                "EasyOCR nao instalado.\n"
                "Execute: pip install easyocr\n"
                "Ou dentro do venv: .venv\\Scripts\\pip install easyocr"
            )
    return _easyocr_reader


class OcrHelper:
    """
    Helper centralizado de OCR — EasyOCR como engine unico.

    Todos os metodos retornam texto em CAIXA ALTA para comparacoes.
    Usado internamente pelo OcrEngine e pelos runners.
    """

    # ------------------------------------------------------------------ #
    #  Leitura principal                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ler_regiao(screenshot_path: str, regiao: tuple) -> str:
        """
        Le o texto de uma regiao usando EasyOCR.

        Escala automatica baseada na altura do campo:
          < 20px → 4x  (campos muito pequenos Oracle Forms)
          < 35px → 3x
          < 60px → 2x
          >= 60px → 1x (sem escala)

        Args:
            screenshot_path: caminho do screenshot completo
            regiao: (x1, y1, x2, y2)

        Returns:
            Texto reconhecido em CAIXA ALTA.
        """
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
        reader = _get_easyocr_reader()
        resultados = reader.readtext(arr, detail=0, paragraph=True)
        texto = " ".join(resultados).strip()
        return texto.upper()

    @staticmethod
    def ler_tela_inteira(screenshot_path: str) -> str:
        """Le o texto da tela inteira. Util para debug."""
        img = Image.open(screenshot_path)
        arr = np.array(img)
        reader = _get_easyocr_reader()
        resultados = reader.readtext(arr, detail=0, paragraph=True)
        return " ".join(resultados).strip().upper()

    # ------------------------------------------------------------------ #
    #  Verificacoes                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def contem_texto(screenshot_path: str, texto_esperado: str,
                     regiao: tuple = None) -> bool:
        """Verifica se um texto aparece na tela ou regiao. Case-insensitive."""
        if regiao:
            texto_tela = OcrHelper.ler_regiao(screenshot_path, regiao)
        else:
            texto_tela = OcrHelper.ler_tela_inteira(screenshot_path)
        return texto_esperado.upper() in texto_tela

    @staticmethod
    def contem_qualquer_token(screenshot_path: str, tokens: list,
                              regiao: tuple = None,
                              tamanho_minimo: int = 4):
        """
        Verifica se qualquer token de uma lista aparece na tela.
        Ignora tokens com tamanho <= tamanho_minimo.

        Returns:
            (encontrado: bool, token_encontrado: str)
        """
        if regiao:
            texto_tela = OcrHelper.ler_regiao(screenshot_path, regiao)
        else:
            texto_tela = OcrHelper.ler_tela_inteira(screenshot_path)

        tokens_validos = [t.upper() for t in tokens if len(t) > tamanho_minimo]
        for token in tokens_validos:
            if token in texto_tela:
                return True, token
        return False, ""

    # ------------------------------------------------------------------ #
    #  Aliases para retrocompatibilidade                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ler_regiao_easyocr(screenshot_path: str, regiao: tuple) -> str:
        """Alias de ler_regiao() — retrocompatibilidade."""
        return OcrHelper.ler_regiao(screenshot_path, regiao)

    @staticmethod
    def contem_texto_easyocr(screenshot_path: str, texto_esperado: str,
                              regiao: tuple = None) -> bool:
        """Alias de contem_texto() — retrocompatibilidade."""
        return OcrHelper.contem_texto(screenshot_path, texto_esperado, regiao)

    # ------------------------------------------------------------------ #
    #  Debug                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def salvar_debug(screenshot_path: str, regiao: tuple,
                     output_path: str = None) -> str:
        """
        Salva o recorte da regiao para inspecao visual.
        Util quando o OCR nao encontra o texto esperado.
        """
        img = Image.open(screenshot_path)
        recorte = img.crop(regiao)

        if output_path is None:
            p = Path(screenshot_path)
            output_path = str(p.parent / f"{p.stem}_ocr_debug.png")

        recorte.save(output_path)
        print(f"[OCR debug] recorte salvo em: {output_path}")
        return output_path

    @staticmethod
    def verificar_instalacao() -> bool:
        """
        Verifica se o EasyOCR esta instalado e funcional.

        Uso:
            python -c "from src.vision.ocr import OcrHelper; OcrHelper.verificar_instalacao()"
        """
        try:
            _get_easyocr_reader()
            print("[OCR] EasyOCR OK — pronto para uso.")
            return True
        except ImportError as e:
            print(f"[OCR] EasyOCR nao disponivel: {e}")
            return False