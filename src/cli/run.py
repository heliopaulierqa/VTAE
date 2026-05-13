# src/cli/run.py
"""
CLI do VTAE — vtae run, vtae systems, vtae clean, vtae send.
v0.5.4 — caminhos atualizados após remoção da pasta vtae/
"""
import argparse
import subprocess
import sys
from pathlib import Path

from src.cli.summary import generate_summary
from src.cli.send import enviar_relatorio


MODULOS = {
    "sislab": [
        "tests/integration/sislab/test_cadastro_funcionario_sislab.py",
    ],
    "si3": [
        "tests/integration/si3/test_cadastro_paciente.py",
        "tests/integration/si3/test_admissao_internacao.py",
    ],
    "msi3": [
        "tests/integration/msi3/test_frequencia_aplicacao.py",
        "tests/integration/msi3/test_tipo_anestesia.py",
    ],
}

TESTES = {
    "login_si3":            "tests/integration/si3/test_login_real.py",
    "cadastro_paciente":    "tests/integration/si3/test_cadastro_paciente.py",
    "admissao_internacao":  "tests/integration/si3/test_admissao_internacao.py",
    "cadastro_funcionario": "tests/integration/sislab/test_cadastro_funcionario_sislab.py",
    "frequencia_aplicacao": "tests/integration/msi3/test_frequencia_aplicacao.py",
    "tipo_anestesia":       "tests/integration/msi3/test_tipo_anestesia.py",
}


def _rodar_pytest(arquivos, ambiente, retry):
    existentes = [a for a in arquivos if Path(a).exists()]
    ausentes   = [a for a in arquivos if not Path(a).exists()]

    if ausentes:
        print("[VTAE] Aviso — arquivos não encontrados (serão ignorados):")
        for a in ausentes:
            print(f"  ✗ {a}")

    if not existentes:
        print("[VTAE] Nenhum arquivo de teste encontrado.")
        return 1

    cmd = ["python", "-m", "pytest"] + existentes + ["-v", "--tb=short"]
    ultimo_rc = 0
    for i in range(retry + 1):
        if i > 0:
            print(f"\n[VTAE] Retry {i}/{retry}...")
        ultimo_rc = subprocess.run(cmd).returncode
        if ultimo_rc == 0:
            break
    return ultimo_rc


def cmd_run(args):
    ambiente = args.ambiente or "dev"
    print("\n" + "=" * 60)
    print("  VTAE — Visual Test Automation Engine")
    print("=" * 60)
    print(f"  Ambiente  : {ambiente}")

    if args.all:
        arquivos = [f for files in MODULOS.values() for f in files]
        label = "todos os sistemas"
    elif args.module:
        if args.module not in MODULOS:
            print(f"[VTAE] Módulo '{args.module}' não encontrado. Disponíveis: {list(MODULOS.keys())}")
            sys.exit(1)
        arquivos = MODULOS[args.module]
        label = f"módulo '{args.module}'"
    elif args.test:
        if args.test not in TESTES:
            print(f"[VTAE] Teste '{args.test}' não encontrado. Disponíveis: {list(TESTES.keys())}")
            sys.exit(1)
        arquivos = [TESTES[args.test]]
        label = f"teste '{args.test}'"
    else:
        print("[VTAE] Especifique --all, --module ou --test.")
        sys.exit(1)

    print(f"  Executando: {label}")
    print(f"  Testes    : {len(arquivos)} arquivo(s)")
    for a in arquivos:
        print(f"    → {a}")
    print("=" * 60 + "\n")

    rc = _rodar_pytest(arquivos, ambiente, args.retry)

    modulo = args.module or args.test or "all"
    try:
        from pathlib import Path as _P
        import glob as _glob
        from datetime import datetime as _dt
        hoje = _dt.now().strftime("%Y-%m-%d")
        json_paths = _glob.glob(f"evidence/{hoje}/**/execution.json", recursive=True)
        if json_paths:
            out = f"evidence/{hoje}/summary/{modulo}_{ambiente}.html"
            _P(out).parent.mkdir(parents=True, exist_ok=True)
            generate_summary(json_paths=json_paths, output_path=out,
                             titulo=f"{modulo} [{ambiente}]", ambiente=ambiente)
            print(f"\n📊 Relatório unificado: {out}")
    except Exception:
        pass

    if args.to:
        for dest in args.to:
            try:
                enviar_relatorio(modulo=modulo, ambiente=ambiente, destinatario=dest)
            except Exception as e:
                print(f"[VTAE] Erro ao enviar para {dest}: {e}")

    status = "✅ PASSOU" if rc == 0 else "❌ FALHOU"
    print(f"\n{'=' * 60}")
    print(f"  {status} — {label} [{ambiente}]")
    print("=" * 60 + "\n")
    sys.exit(rc)


def cmd_systems(args):
    from src.config import ConfigLoader
    base = Path("configs")
    if args.sistema:
        ambientes = ConfigLoader.listar_ambientes(args.sistema, configs_dir=base)
        print(f"\nAmbientes para '{args.sistema}':")
        for a in ambientes:
            print(f"  • {a}")
    else:
        sistemas = ConfigLoader.listar_sistemas(configs_dir=base)
        print("\nSistemas disponíveis:")
        for s in sistemas:
            print(f"  • {s}")
    print()


def cmd_clean(args):
    import shutil
    from datetime import datetime, timedelta
    base = Path("evidence")
    if not base.exists():
        print("[VTAE] Pasta evidence/ não encontrada.")
        return
    cutoff = datetime.now() - timedelta(days=args.days)
    removidos = 0
    for pasta in sorted(base.iterdir()):
        if not pasta.is_dir():
            continue
        try:
            data = datetime.strptime(pasta.name, "%Y-%m-%d")
        except ValueError:
            continue
        if data < cutoff:
            if args.dry_run:
                print(f"  [dry-run] removeria: {pasta}")
            else:
                shutil.rmtree(pasta)
                removidos += 1
    if not args.dry_run:
        print(f"\n[VTAE] {removidos} pasta(s) removida(s).")


def cmd_send(args):
    ambiente = args.ambiente or "dev"
    modulo = args.module or "all"
    if not args.to:
        print("[VTAE] Especifique --to.")
        sys.exit(1)
    for dest in args.to:
        try:
            enviar_relatorio(modulo=modulo, ambiente=ambiente, destinatario=dest)
            print(f"[VTAE] Relatório enviado para {dest}")
        except Exception as e:
            print(f"[VTAE] Erro: {e}")


def main():
    parser = argparse.ArgumentParser(prog="vtae")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run")
    p_run.add_argument("--module"); p_run.add_argument("--test")
    p_run.add_argument("--all", action="store_true")
    p_run.add_argument("--env", dest="ambiente", default="dev")
    p_run.add_argument("--retry", type=int, default=0)
    p_run.add_argument("--to", action="append")

    p_sys = sub.add_parser("systems")
    p_sys.add_argument("--sistema")

    p_clean = sub.add_parser("clean")
    p_clean.add_argument("--days", type=int, default=30)
    p_clean.add_argument("--dry-run", action="store_true")

    p_send = sub.add_parser("send")
    p_send.add_argument("--module"); p_send.add_argument("--all", action="store_true")
    p_send.add_argument("--to", action="append", required=True)
    p_send.add_argument("--env", dest="ambiente", default="dev")

    args = parser.parse_args()
    dispatch = {"run": cmd_run, "systems": cmd_systems, "clean": cmd_clean, "send": cmd_send}
    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()