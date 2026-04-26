# vtae/core/ocr_helper.py
"""
Helper centralizado de OCR para o VTAE.

Uso em qualquer flow:
    from vtae.core.ocr_helper import OcrHelper
    texto = OcrHelper.ler_regiao(screenshot_path, regiao=(x1, y1, x2, y2))
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
from pathlib import Path

# Caminho do executável Tesseract no Windows
# Ajuste se instalou em diretório diferente
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


class OcrHelper:
    """
    Métodos estáticos de OCR reutilizáveis por qualquer flow do VTAE.
    Todos os métodos retornam texto em CAIXA ALTA para facilitar comparações.
    """

    # ------------------------------------------------------------------ #
    #  Pré-processamento                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def preprocessar(img: Image.Image) -> Image.Image:
        """
        Prepara a imagem para melhor leitura pelo Tesseract:
          1. Converte para escala de cinza
          2. Escala 2x (Tesseract performa melhor com imagens maiores)
          3. Threshold adaptativo — lida com variações de contraste
             comuns em interfaces Oracle Forms
        """
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        scaled = cv2.resize(gray, None, fx=2, fy=2,
                            interpolation=cv2.INTER_CUBIC)
        processed = cv2.adaptiveThreshold(
            scaled, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2,
        )
        return Image.fromarray(processed)

    # ------------------------------------------------------------------ #
    #  Leitura                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ler_regiao(screenshot_path: str, regiao: tuple,
                   lang: str = "por") -> str:
        """
        Lê o texto de uma região específica de um screenshot.

        Args:
            screenshot_path: caminho do screenshot completo (salvo pelo runner)
            regiao: (x1, y1, x2, y2) — coordenadas do recorte na tela
            lang: idioma do Tesseract (padrão: "por" para português)

        Returns:
            Texto reconhecido em CAIXA ALTA.

        Exemplo:
            texto = OcrHelper.ler_regiao(
                "evidence/CF09.png",
                regiao=(0, 320, 950, 620),
            )
        """
        img = Image.open(screenshot_path)
        recorte = img.crop(regiao)
        recorte_processado = OcrHelper.preprocessar(recorte)
        texto = pytesseract.image_to_string(recorte_processado, lang=lang)
        return texto.upper()

    @staticmethod
    def ler_tela_inteira(screenshot_path: str, lang: str = "por") -> str:
        """
        Lê o texto da tela inteira.
        Útil para debug ou quando a região ainda não foi mapeada.

        Returns:
            Texto reconhecido em CAIXA ALTA.
        """
        img = Image.open(screenshot_path)
        processado = OcrHelper.preprocessar(img)
        texto = pytesseract.image_to_string(processado, lang=lang)
        return texto.upper()

    # ------------------------------------------------------------------ #
    #  Verificações                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def contem_texto(screenshot_path: str, texto_esperado: str,
                     regiao: tuple = None, lang: str = "por") -> bool:
        """
        Verifica se um texto aparece na tela (ou numa região).
        Comparação case-insensitive.

        Args:
            screenshot_path: caminho do screenshot
            texto_esperado: texto a procurar
            regiao: (x1, y1, x2, y2) opcional — restringe a busca

        Returns:
            True se encontrado, False caso contrário.

        Exemplo:
            # verificar mensagem de sucesso após salvar
            ok = OcrHelper.contem_texto("CF08.png", "REGISTRO SALVO")
        """
        if regiao:
            texto_tela = OcrHelper.ler_regiao(screenshot_path, regiao, lang)
        else:
            texto_tela = OcrHelper.ler_tela_inteira(screenshot_path, lang)
        return texto_esperado.upper() in texto_tela

    @staticmethod
    def contem_qualquer_token(screenshot_path: str, tokens: list,
                              regiao: tuple = None,
                              tamanho_minimo: int = 4,
                              lang: str = "por"):
        """
        Verifica se qualquer token de uma lista aparece na tela.
        Ignora tokens com tamanho <= tamanho_minimo (partículas, artigos).

        Útil para validar nomes gerados pelo Faker, onde o Tesseract
        pode errar um caractere mas dificilmente erra o token inteiro.

        Args:
            tokens: lista de strings a procurar (ex: nome.split())
            tamanho_minimo: tokens com len <= esse valor são ignorados
            regiao: (x1, y1, x2, y2) opcional

        Returns:
            (encontrado: bool, token_encontrado: str)

        Exemplo:
            nome = "MARIA JOSE DA SILVA"
            encontrado, token = OcrHelper.contem_qualquer_token(
                "CF09.png",
                tokens=nome.split(),
                regiao=(0, 320, 950, 620),
            )
            assert encontrado, f"Nome não encontrado. Token testado: {token}"
        """
        if regiao:
            texto_tela = OcrHelper.ler_regiao(screenshot_path, regiao, lang)
        else:
            texto_tela = OcrHelper.ler_tela_inteira(screenshot_path, lang)

        tokens_validos = [t.upper() for t in tokens if len(t) > tamanho_minimo]
        for token in tokens_validos:
            if token in texto_tela:
                return True, token

        return False, ""

    # ------------------------------------------------------------------ #
    #  Debug                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def salvar_debug(screenshot_path: str, regiao: tuple,
                     output_path: str = None) -> str:
        """
        Salva a imagem pré-processada para inspecionar visualmente
        o que o Tesseract está lendo.

        Útil quando o OCR não encontra o texto esperado.

        Args:
            output_path: onde salvar (padrão: mesmo dir do screenshot)

        Returns:
            Caminho da imagem de debug salva.

        Exemplo:
            # rode isso no _step_verificar e abra a imagem para ver
            OcrHelper.salvar_debug("evidence/CF09.png", (0, 320, 950, 620))
        """
        img = Image.open(screenshot_path)
        recorte = img.crop(regiao)
        processado = OcrHelper.preprocessar(recorte)

        if output_path is None:
            p = Path(screenshot_path)
            output_path = str(p.parent / f"{p.stem}_ocr_debug.png")

        processado.save(output_path)
        print(f"[OCR debug] imagem salva em: {output_path}")
        return output_path

    @staticmethod
    def verificar_instalacao() -> bool:
        """
        Verifica se o Tesseract está instalado e acessível.
        Rode isso uma vez para confirmar o ambiente.

        Uso:
            python -c "from vtae.core.ocr_helper import OcrHelper; OcrHelper.verificar_instalacao()"
        """
        try:
            versao = pytesseract.get_tesseract_version()
            print(f"[OCR] Tesseract encontrado: v{versao}")
            return True
        except Exception as e:
            print(f"[OCR] Tesseract NÃO encontrado: {e}")
            print(f"[OCR] Verifique o caminho: {pytesseract.pytesseract.tesseract_cmd}")
            return False
