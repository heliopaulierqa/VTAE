import cv2
from vtae.vision.template import TemplateMatcher


def diagnose_contra_arquivo(template_path: str, screenshot_path: str) -> str:
    """
    Mesma logica de TemplateMatcher.diagnose(), mas compara o template
    contra um arquivo de screenshot salvo em disco, nao contra a tela
    ao vivo (bug do diagnose() original: sempre usa ImageGrab.grab()).
    """
    matcher = TemplateMatcher()
    imagem_screenshot = cv2.imread(screenshot_path)
    if imagem_screenshot is None:
        return f"ERRO: nao foi possivel abrir '{screenshot_path}'"

    matcher._capture_screen = lambda: imagem_screenshot
    report = matcher.diagnose(template_path)
    return report


def capturar_screenshot() -> str:
    """
    Tira um screenshot da tela ao vivo (pyautogui.screenshot(), regra 18)
    e salva com timestamp em evidence/diagnose_manual/. Retorna o caminho.
    """
    import datetime
    import pathlib
    import pyautogui

    pasta = pathlib.Path("evidence/diagnose_manual")
    pasta.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destino = str(pasta / f"{timestamp}.png")

    pyautogui.screenshot().save(destino)
    return destino


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(
        description="Mede o score de um template contra um screenshot. "
                     "Se 'screenshot' for omitido, tira um print ao vivo antes de medir."
    )
    parser.add_argument("template", help="Caminho do template (.png)")
    parser.add_argument("screenshot", nargs="?", default=None,
                         help="Caminho do screenshot (.png). Se omitido, captura a tela ao vivo.")
    args = parser.parse_args()

    caminho = args.screenshot
    if caminho is None:
        print("Sem screenshot informado — capturando tela ao vivo em 3s. Deixe a tela certa em foco.")
        time.sleep(3)
        caminho = capturar_screenshot()
        print(f"Screenshot salvo em: {caminho}")

    print(diagnose_contra_arquivo(args.template, caminho))