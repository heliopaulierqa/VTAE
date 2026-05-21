# src/core/health_check.py
"""
Health check pré-run do VTAE.
Verifica se os sistemas necessários estão abertos antes de iniciar os testes.
"""
import subprocess


_PROCESSOS_SISTEMA = {
    "si3":    ["jp2launcher.exe", "iexplore.exe", "java.exe"],
    "sislab": ["jp2launcher.exe", "iexplore.exe", "java.exe"],
    "msi3":   ["chrome.exe", "msedge.exe", "firefox.exe"],
}


def _processos_ativos() -> list[str]:
    """Retorna lista de nomes de processos em execução (Windows)."""
    try:
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True, text=True, timeout=10
        )
        return [
            line.split(",")[0].strip('"').lower()
            for line in result.stdout.splitlines()
            if line
        ]
    except Exception:
        return []


def verificar(sistemas: list[str]) -> tuple[bool, list[str]]:
    """
    Verifica se os processos esperados estão rodando para cada sistema.

    Retorna:
        (ok, avisos) — ok=True se tudo encontrado, avisos com detalhes do que faltou.
    """
    ativos = _processos_ativos()
    avisos = []

    for sistema in sistemas:
        esperados = _PROCESSOS_SISTEMA.get(sistema.lower(), [])
        if not esperados:
            continue
        encontrado = any(p.lower() in ativos for p in esperados)
        if not encontrado:
            avisos.append(
                f"  ⚠  Sistema '{sistema}' — nenhum processo encontrado: {esperados}"
            )

    ok = len(avisos) == 0
    return ok, avisos