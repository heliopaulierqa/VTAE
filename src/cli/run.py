"""
VTAE CLI — Visual Test Automation Engine

Uso:
    vtae run --module sislab
    vtae run --module sislab --env homologacao
    vtae run --module sislab --retry 2
    vtae run --test cadastro_funcionario
    vtae run --all
    vtae run --all --env homologacao
    vtae systems
    vtae systems --sistema sislab
    vtae clean --days 7
    vtae send --module sislab --to gestor@incor.org.br
    vtae send --all --to a@x.com --to b@x.com
    vtae send --module sislab --date 2026-05-03 --to fulano@incor.org.br
"""

import argparse
import os
import sys
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path


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

TESTES: dict[str, str] = {
    "cadastro_funcionario":  "vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py",
    "cadastro_paciente":     "vtae/tests/integration/si3/test_cadastro_paciente_si3.py",
    "login_msi3":            "vtae/tests/integration/msi3/test_login_msi3.py",
    "frequencia_aplicacao":  "vtae/tests/integration/msi3/test_frequencia_aplicacao.py",
    "tipo_anestesia":        "vtae/tests/integration/msi3/test_tipo_anestesia.py",
}

AMBIENTES_VALIDOS = {"dev", "homologacao", "producao"}


def main():
    parser = argparse.ArgumentParser(
        prog="vtae",
        description="VTAE — Visual Test Automation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  vtae run --module sislab
  vtae run --module sislab --env homologacao
  vtae run --module sislab --retry 2
  vtae run --test cadastro_funcionario
  vtae run --all --env producao
  vtae systems
  vtae systems --sistema sislab
  vtae clean --days 7
  vtae send --module sislab --to gestor@incor.org.br
  vtae send --all --to a@x.com --to b@x.com
        """,
    )

    sub = parser.add_subparsers(dest="command", metavar="comando")

    # ── vtae run ──────────────────────────────────────────────────────────────
    run_parser = sub.add_parser("run", help="Executa testes de integração")
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--all", action="store_true", help="Executa todos os testes")
    run_group.add_argument("--module", choices=MODULOS.keys(), metavar="SISTEMA")
    run_group.add_argument("--test", choices=TESTES.keys(), metavar="TESTE")
    run_parser.add_argument(
        "--env", choices=AMBIENTES_VALIDOS, default="dev", metavar="AMBIENTE"
    )
    run_parser.add_argument(
        "--retry", type=int, default=0, metavar="N",
        help="Re-executa testes que falharam até N vezes extras (ex: --retry 2)"
    )

    # ── vtae systems ──────────────────────────────────────────────────────────
    sys_parser = sub.add_parser("systems", help="Lista sistemas e ambientes disponíveis")
    sys_parser.add_argument("--sistema", choices=MODULOS.keys(), metavar="SISTEMA")

    # ── vtae clean ────────────────────────────────────────────────────────────
    clean_parser = sub.add_parser("clean", help="Remove evidências antigas")
    clean_parser.add_argument(
        "--days", type=int, default=7, metavar="N",
        help="Remove evidências com mais de N dias (padrão: 7)"
    )
    clean_parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostra o que seria removido sem apagar"
    )

    # ── vtae send ─────────────────────────────────────────────────────────────
    send_parser = sub.add_parser("send", help="Envia relatório por e-mail")
    send_group = send_parser.add_mutually_exclusive_group(required=True)
    send_group.add_argument("--all", action="store_true", help="Envia relatório de todos os módulos")
    send_group.add_argument("--module", choices=MODULOS.keys(), metavar="SISTEMA")
    send_parser.add_argument(
        "--to", action="append", dest="destinatarios", metavar="EMAIL",
        required=True, help="Destinatário (pode repetir: --to a@x.com --to b@x.com)"
    )
    send_parser.add_argument(
        "--env", choices=AMBIENTES_VALIDOS, default="dev", metavar="AMBIENTE"
    )
    send_parser.add_argument(
        "--date", default=None, metavar="YYYY-MM-DD",
        help="Data da execução a enviar (padrão: hoje)"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "systems":
        _cmd_systems(args)
    elif args.command == "clean":
        _cmd_clean(args)
    elif args.command == "send":
        _cmd_send(args)


# ──────────────────────────────────────────────────────────────────────────────
# vtae run
# ──────────────────────────────────────────────────────────────────────────────

def _cmd_run(args):
    env    = args.env
    retry  = args.retry

    if args.all:
        arquivos  = [f for files in MODULOS.values() for f in files]
        descricao = "todos os módulos"
        titulo    = "Execução Completa"
    elif args.module:
        arquivos  = MODULOS[args.module]
        descricao = f"módulo '{args.module}'"
        titulo    = f"Módulo {args.module.upper()}"
    else:
        arquivos  = [TESTES[args.test]]
        descricao = f"teste '{args.test}'"
        titulo    = args.test.replace("_", " ").title()

    existentes = [f for f in arquivos if Path(f).exists()]
    faltando   = [f for f in arquivos if not Path(f).exists()]

    if faltando:
        print("[VTAE] Aviso — arquivos não encontrados (serão ignorados):")
        for f in faltando:
            print(f"  ✗ {f}")

    if not existentes:
        print(f"[VTAE] Nenhum arquivo de teste encontrado para {descricao}.")
        sys.exit(1)

    processo_env = os.environ.copy()
    processo_env["VTAE_ENV"] = env

    _print_header(env, descricao, existentes, retry)

    # ── execução com retry ────────────────────────────────────────────────────
    tentativa      = 0
    max_tentativas = 1 + retry
    returncode     = 1
    arquivos_pendentes = list(existentes)

    while tentativa < max_tentativas and arquivos_pendentes:
        if tentativa > 0:
            print(f"\n{'─'*60}")
            print(f"  🔄 RETRY {tentativa}/{retry} — re-executando testes que falharam")
            print(f"{'─'*60}\n")
            time.sleep(2)  # pausa antes do retry

        cmd = [sys.executable, "-m", "pytest", "-v", "-s"] + arquivos_pendentes
        resultado = subprocess.run(cmd, env=processo_env)
        returncode = resultado.returncode

        if returncode == 0:
            break

        # identifica quais testes falharam para re-executar só eles
        if tentativa < max_tentativas - 1:
            arquivos_pendentes = _identificar_falhos(arquivos_pendentes)
            if not arquivos_pendentes:
                break

        tentativa += 1

    # ── relatório unificado ───────────────────────────────────────────────────
    _gerar_summary(existentes, env, titulo, returncode)

    # ── resultado final ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if returncode == 0:
        if tentativa > 0:
            print(f"  ✅ PASSOU (após {tentativa} retry) — {descricao} [{env}]")
        else:
            print(f"  ✅ PASSOU — {descricao} [{env}]")
    else:
        tentativas_str = f" após {tentativa} retries" if retry > 0 else ""
        print(f"  ❌ FALHOU{tentativas_str} — {descricao} [{env}]")
    print(f"{'='*60}\n")

    sys.exit(returncode)


def _print_header(env, descricao, existentes, retry):
    print(f"\n{'='*60}")
    print(f"  VTAE — Visual Test Automation Engine")
    print(f"{'='*60}")
    print(f"  Ambiente  : {env}")
    print(f"  Executando: {descricao}")
    print(f"  Testes    : {len(existentes)} arquivo(s)")
    for f in existentes:
        print(f"    → {f}")
    if retry > 0:
        print(f"  Retry     : até {retry}x em caso de falha")
    print(f"{'='*60}\n")


def _identificar_falhos(arquivos: list[str]) -> list[str]:
    """
    Identifica quais testes falharam na última execução lendo os execution.json.
    Retorna apenas os arquivos de testes que falharam para re-executar.
    """
    hoje = datetime.now().strftime("%Y-%m-%d")
    falhos = []

    for arq in arquivos:
        test_name = Path(arq).stem
        json_path = Path(f"evidence/{hoje}/{test_name}/execution.json")
        if json_path.exists():
            try:
                import json
                with open(json_path) as f:
                    data = json.load(f)
                if data.get("status") != "PASSOU":
                    falhos.append(arq)
            except Exception:
                falhos.append(arq)  # na dúvida, re-executa
        else:
            falhos.append(arq)

    return falhos


def _gerar_summary(arquivos: list[str], env: str,
                   titulo: str, returncode: int):
    """Coleta os execution.json e produz o summary.html."""
    try:
        from src.cli.summary import generate_summary

        hoje      = datetime.now().strftime("%Y-%m-%d")
        json_paths = []

        for arq in arquivos:
            test_name = Path(arq).stem
            json_path = Path(f"evidence/{hoje}/{test_name}/execution.json")
            if json_path.exists():
                json_paths.append(str(json_path))

        if not json_paths:
            return

        summary_dir  = f"evidence/{hoje}/summary"
        summary_path = f"{summary_dir}/{titulo.lower().replace(' ', '_')}_{env}.html"

        path = generate_summary(
            json_paths=json_paths,
            output_path=summary_path,
            titulo=titulo,
            ambiente=env,
        )

        if path:
            print(f"\n📊 Relatório unificado: {path}")

        # envio automático se configurado no YAML
        try:
            from src.cli.send import enviar_automatico
            if args.all:
                enviar_automatico("all", env)
            elif hasattr(args, 'module') and args.module:
                enviar_automatico(args.module, env)
        except Exception:
            pass  # envio automático nunca bloqueia a execução

    except Exception as e:
        print(f"[VTAE] Aviso — não foi possível gerar relatório unificado: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# vtae systems
# ──────────────────────────────────────────────────────────────────────────────

def _cmd_systems(args):
    if args.sistema:
        try:
            from src.config import ConfigLoader
            ambientes = ConfigLoader.listar_ambientes(
                args.sistema, configs_dir=Path("vtae/configs")
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
        try:
            from src.config import ConfigLoader
            sistemas = ConfigLoader.listar_sistemas(configs_dir=Path("vtae/configs"))
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


# ──────────────────────────────────────────────────────────────────────────────
# vtae clean
# ──────────────────────────────────────────────────────────────────────────────

def _cmd_clean(args):
    """Remove pastas de evidências com mais de N dias."""
    days     = args.days
    dry_run  = args.dry_run
    base_dir = Path("evidence")

    if not base_dir.exists():
        print("[VTAE] Pasta evidence/ não encontrada.")
        return

    cutoff = datetime.now() - timedelta(days=days)
    removidos = []
    tamanho_total = 0

    for pasta in sorted(base_dir.iterdir()):
        if not pasta.is_dir():
            continue
        # nome da pasta é YYYY-MM-DD
        try:
            data_pasta = datetime.strptime(pasta.name, "%Y-%m-%d")
        except ValueError:
            continue

        if data_pasta < cutoff:
            # calcula tamanho
            size = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file())
            tamanho_total += size
            removidos.append((pasta, size))

    if not removidos:
        print(f"[VTAE] Nenhuma evidência com mais de {days} dias encontrada.")
        return

    print(f"\n{'='*60}")
    print(f"  vtae clean — evidências com mais de {days} dias")
    print(f"{'='*60}")
    if dry_run:
        print(f"  Modo: DRY RUN (nenhum arquivo será apagado)")
    print(f"  Pastas encontradas: {len(removidos)}")
    print(f"  Espaço a liberar: {tamanho_total / 1024 / 1024:.1f} MB")
    print(f"{'─'*60}")

    for pasta, size in removidos:
        print(f"  {'[dry-run] ' if dry_run else ''}🗑  {pasta.name}  ({size/1024:.0f} KB)")
        if not dry_run:
            import shutil
            shutil.rmtree(pasta)

    print(f"{'='*60}")
    if dry_run:
        print(f"  Execute sem --dry-run para apagar.")
    else:
        print(f"  ✅ {len(removidos)} pasta(s) removida(s) — {tamanho_total/1024/1024:.1f} MB liberados.")
    print(f"{'='*60}\n")


# ──────────────────────────────────────────────────────────────────────────────
# vtae send
# ──────────────────────────────────────────────────────────────────────────────

def _cmd_send(args):
    """Envia o relatório de uma execução por e-mail."""
    from src.cli.send import enviar_relatorio

    modulo = "all" if args.all else args.module

    print(f"\n{'='*60}")
    print(f"  VTAE — Envio de relatório")
    print(f"{'='*60}")
    print(f"  Módulo : {modulo}")
    print(f"  Para   : {', '.join(args.destinatarios)}")
    print(f"  Data   : {args.date or 'hoje'}")
    print(f"{'='*60}\n")

    ok = enviar_relatorio(
        modulo=modulo,
        destinatarios=args.destinatarios,
        ambiente=args.env,
        data=args.date,
    )

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
