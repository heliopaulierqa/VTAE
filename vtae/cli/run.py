"""
CLI do VTAE — Fase 6
Uso:
    vtae run --all
    vtae run --module admissao
    vtae run --test login
"""

import argparse
import sys


MODULES = {
    "admissao": "vtae.tests.unit.test_admissao_flow",
    "suprimentos": "vtae.tests.unit.test_suprimentos_flow",
    "login": "vtae.tests.unit.test_login_flow",
}


def main():
    parser = argparse.ArgumentParser(
        prog="vtae",
        description="VTAE — Visual Test Automation Engine",
    )
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Executa testes")
    group = run_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Executa todos os testes")
    group.add_argument("--module", choices=MODULES.keys(), help="Executa um módulo específico")
    group.add_argument("--test", help="Executa um teste pelo nome")

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        sys.exit(1)

    _run(args)


def _run(args):
    import subprocess

    base_cmd = [sys.executable, "-m", "pytest", "-v"]

    if args.all:
        cmd = base_cmd + ["vtae/tests/"]
    elif args.module:
        module_path = MODULES[args.module].replace(".", "/") + ".py"
        cmd = base_cmd + [module_path]
    elif args.test:
        cmd = base_cmd + ["-k", args.test]

    print(f"[VTAE CLI] Executando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
