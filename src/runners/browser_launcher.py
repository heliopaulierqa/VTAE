# src/runners/browser_launcher.py
import subprocess
import time


def abrir_si3_navegador(url: str) -> None:
    """
    Abre o Edge normalmente (sem Playwright) e navega ate a URL do SI3.
    Playwright nao pode ser usado aqui — o SI3 detecta depuracao remota
    e bloqueia o carregamento do Oracle Forms.
    """
    # Caminho padrao do Edge no Windows
    edge_path = (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    )

    subprocess.Popen([edge_path, url])

    # Sleep justificado: Edge acabou de abrir, Oracle Forms ainda
    # esta inicializando a janela nativa — nao ha template para confirmar.
    time.sleep(12)