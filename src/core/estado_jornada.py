# src/core/estado_jornada.py
"""
Helper para leitura e escrita do estado compartilhado entre testes da jornada.
Lanca AssertionError com CausaFalha.ESTADO_AUSENTE se chave nao encontrada.
"""
import json
import pathlib

from src.core.result import CausaFalha

_ESTADO_PATH = pathlib.Path("evidence/estado_jornada.json")


def ler(chave: str) -> str:
    """
    Le uma chave do estado_jornada.json.
    Lanca AssertionError com causa ESTADO_AUSENTE se nao encontrada.
    """
    if not _ESTADO_PATH.exists():
        raise AssertionError(
            f"[ESTADO_AUSENTE] estado_jornada.json nao encontrado. "
            f"Execute o test_01 antes de rodar este teste."
        )
    try:
        estado = json.loads(_ESTADO_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise AssertionError(
            f"[ESTADO_AUSENTE] Erro ao ler estado_jornada.json: {e}"
        )
    if chave not in estado or not estado[chave]:
        raise AssertionError(
            f"[ESTADO_AUSENTE] Chave '{chave}' nao encontrada no estado_jornada.json. "
            f"Chaves disponiveis: {list(estado.keys())}"
        )
    return estado[chave]


def salvar(chave: str, valor: str) -> None:
    """Salva ou atualiza uma chave no estado_jornada.json."""
    _ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
    estado = {}
    if _ESTADO_PATH.exists():
        try:
            estado = json.loads(_ESTADO_PATH.read_text(encoding="utf-8"))
        except Exception:
            estado = {}
    estado[chave] = valor
    _ESTADO_PATH.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[estado_jornada] {chave} = {valor} -> {_ESTADO_PATH}")