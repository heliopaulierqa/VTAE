"""
VTAE CLI — Visual Test Automation Engine

Uso:
    vtae run --module sislab
    vtae run --module sislab --env homologacao
    vtae run --test cadastro_funcionario
    vtae run --test cadastro_funcionario --env producao
    vtae run --all
    vtae run --all --env homologacao
    vtae systems
    vtae systems --sistema sislab

O ambiente padrão é sempre "dev" se não especificado.
O ambiente é passado via variável de ambiente VTAE_ENV para os testes,
que o ConfigLoader lê automaticamente.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────────────
# Mapa de módulos → arquivos de teste
# Atualizar ao adicionar novos sistemas ou flows.
# ──────────────────────────────────────────────────────────────────────────────

MODULOS: dict[str, list[str]] = {
    "sislab": [
        "vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py",
    ],
    "si3": [
        "vtae/tests/integration/si3/test_cadastro_paciente_si3.py",
    ],
    "msi3": [
        "vtae/tests/integration/msi3/test_login_msi3.py",
        "vtae/tests/integration/msi3/test_frequencia_aplicacao.py",
        "vtae/tests/integration/msi3/test_tipo_anestesia.py",
    ],
}

# Mapa de nome curto → arquivo de teste (para --test)
TESTES: dict[str, str] = {
    "cadastro_funcionario":  "vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py",
    "cadastro_paciente":     "vtae/tests/integration/si3/test_cadastro_paciente_si3.py",
    "login_msi3":            "vtae/tests/integration/msi3/test_login_msi3.py",
    "frequencia_aplicacao":  "vtae/tests/integration/msi3/test_frequencia_aplicacao.py",
    "tipo_anestesia":        "vtae/tests/integration/msi3/test_tipo_anestesia.py",
}

AMBIENTES_VALIDOS = {"dev", "homologacao", "producao"}


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="vtae",
        description="VTAE — Visual Test Automation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  vtae run --module sislab
  vtae run --module sislab --env homologacao
  vtae run --test cadastro_funcionario
  vtae run --all --env producao
  vtae systems
  vtae systems --sistema sislab
        """,
    )

    sub = parser.add_subparsers(dest="command", metavar="comando")

    # ── vtae run ──────────────────────────────────────────────────────────────
    run_parser = sub.add_parser("run", help="Executa testes de integração")
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument(
        "--all",
        action="store_true",
        help="Executa todos os testes de integração",
    )
    run_group.add_argument(
        "--module",
        choices=MODULOS.keys(),
        metavar="SISTEMA",
        help=f"Executa todos os testes de um sistema. Opções: {', '.join(MODULOS.keys())}",
    )
    run_group.add_argument(
        "--test",
        choices=TESTES.keys(),
        metavar="TESTE",
        help=f"Executa um teste específico. Opções: {', '.join(TESTES.keys())}",
    )
    run_parser.add_argument(
        "--env",
        choices=AMBIENTES_VALIDOS,
        default="dev",
        metavar="AMBIENTE",
        help="Ambiente de execução: dev (padrão), homologacao, producao",
    )
    run_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Saída detalhada (padrão: ativado)",
    )

    # ── vtae systems ──────────────────────────────────────────────────────────
    sys_parser = sub.add_parser("systems", help="Lista sistemas e ambientes disponíveis")
    sys_parser.add_argument(
        "--sistema",
        choices=MODULOS.keys(),
        metavar="SISTEMA",
        help="Lista ambientes de um sistema específico",
    )

    # ── parse ─────────────────────────────────────────────────────────────────
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "systems":
        _cmd_systems(args)


# ──────────────────────────────────────────────────────────────────────────────
# Comandos
# ──────────────────────────────────────────────────────────────────────────────

def _cmd_run(args):
    """Executa testes via pytest, injetando VTAE_ENV no ambiente."""

    env = args.env

    # monta lista de arquivos de teste
    if args.all:
        arquivos = [f for files in MODULOS.values() for f in files]
        descricao = f"todos os módulos"
    elif args.module:
        arquivos = MODULOS[args.module]
        descricao = f"módulo '{args.module}'"
    else:
        arquivos = [TESTES[args.test]]
        descricao = f"teste '{args.test}'"

    # filtra só os arquivos que existem
    existentes = [f for f in arquivos if Path(f).exists()]
    faltando = [f for f in arquivos if not Path(f).exists()]

    if faltando:
        print(f"[VTAE] Aviso — arquivos não encontrados (serão ignorados):")
        for f in faltando:
            print(f"  ✗ {f}")

    if not existentes:
        print(f"[VTAE] Nenhum arquivo de teste encontrado para {descricao}.")
        sys.exit(1)

    # monta o comando pytest
    cmd = [sys.executable, "-m", "pytest", "-v", "-s"] + existentes

    # injeta o ambiente via variável de ambiente
    processo_env = os.environ.copy()
    processo_env["VTAE_ENV"] = env

    print(f"\n{'='*60}")
    print(f"  VTAE — Visual Test Automation Engine")
    print(f"{'='*60}")
    print(f"  Ambiente : {env}")
    print(f"  Executando: {descricao}")
    print(f"  Testes   : {len(existentes)} arquivo(s)")
    for f in existentes:
        print(f"    → {f}")
    print(f"{'='*60}\n")

    resultado = subprocess.run(cmd, env=processo_env)

    print(f"\n{'='*60}")
    if resultado.returncode == 0:
        print(f"  ✅ PASSOU — {descricao} [{env}]")
    else:
        print(f"  ❌ FALHOU — {descricao} [{env}]")
    print(f"{'='*60}\n")

    sys.exit(resultado.returncode)


def _cmd_systems(args):
    """Lista sistemas e ambientes disponíveis."""

    if args.sistema:
        # lista ambientes de um sistema específico
        try:
            from src.config import ConfigLoader
            ambientes = ConfigLoader.listar_ambientes(
                args.sistema,
                configs_dir=Path("vtae/configs")
            )
            print(f"\nSistema '{args.sistema}' — ambientes disponíveis:")
            for amb in ambientes:
                marker = "← padrão" if amb == "dev" else ""
                print(f"  • {amb} {marker}")
            print()
        except Exception as e:
            print(f"[VTAE] Erro ao listar ambientes de '{args.sistema}': {e}")
            sys.exit(1)
    else:
        # lista todos os sistemas
        try:
            from src.config import ConfigLoader
            sistemas = ConfigLoader.listar_sistemas(
                configs_dir=Path("vtae/configs")
            )
        except Exception:
            sistemas = list(MODULOS.keys())

        print(f"\nSistemas disponíveis ({len(sistemas)}):")
        for s in sistemas:
            testes_do_sistema = MODULOS.get(s, [])
            existentes = sum(1 for f in testes_do_sistema if Path(f).exists())
            print(f"  • {s:<12} — {existentes}/{len(testes_do_sistema)} testes")
        print()
        print("Use 'vtae systems --sistema <nome>' para ver os ambientes.")
        print()
     

if __name__ == "__main__":
    main()