# scripts/testar_conexao_db.py
"""
Teste isolado de conexao ao Oracle via DatabaseRunner — v0.5.28.

NAO toca em nenhum flow. Objetivo unico: provar que credencial + DSN +
DatabaseRunner funcionam de ponta a ponta, antes de mapear o schema
completo das tabelas de dominio (unidades, provedores).

Usa o SELECT que ja se sabe que existe (adm_admissao / ADM_OACI_ID /
adm_st = 1) so como prova de acesso — nao e o SELECT definitivo de
nenhum step do flow.

Uso:
    python scripts/testar_conexao_db.py

Le as credenciais do .env de configs/si3/si3_ambulatorio/.env
(SI3_DB_USER, SI3_DB_PASS, SI3_DB_DSN opcional — default
CNPQDW:1521/DESENV), sem precisar do ConfigLoader completo.
"""

import os
import sys
from pathlib import Path

# Garante que 'src' esta no path mesmo rodando de scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _carregar_env_simples(env_path: Path) -> dict:
    """Parser minimo de .env — mesmo formato que o ConfigLoader usa."""
    valores = {}
    if not env_path.exists():
        return valores
    for linha in env_path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def main():
    env_path = Path("configs/si3/si3_ambulatorio/.env")
    env_vars = _carregar_env_simples(env_path)

    # os.environ tem prioridade, igual ao ConfigLoader
    user  = os.environ.get("SI3_DB_USER")  or env_vars.get("SI3_DB_USER")
    senha = os.environ.get("SI3_DB_PASS")  or env_vars.get("SI3_DB_PASS")
    dsn   = os.environ.get("SI3_DB_DSN")   or env_vars.get("SI3_DB_DSN") or "CNPQDW:1521/DESENV"

    if not user or not senha:
        print(f"[ERRO] SI3_DB_USER/SI3_DB_PASS nao encontrados.")
        print(f"Verificado em: os.environ e '{env_path}'")
        print("Defina no .env do sistema antes de rodar este script.")
        sys.exit(1)

    print(f"[teste] dsn='{dsn}' user='{user}'")

    from src.runners.database_runner import DatabaseRunner

    db = DatabaseRunner(dsn=dsn, user=user, password=senha)

    try:
        resultado = db.query(
            "SELECT * FROM adm_admissao WHERE adm_st = 1"
        )
        print(f"[OK] Conexao funcionou — {len(resultado)} registro(s) encontrado(s).")
        if resultado:
            print(f"[OK] Colunas disponiveis: {list(resultado[0].keys())}")
            print(f"[OK] Primeiro registro: {resultado[0]}")
        else:
            print("[AVISO] Query rodou mas retornou 0 linhas — verificar filtro adm_st=1.")
    except Exception as e:
        print(f"[FALHOU] Erro ao consultar: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()