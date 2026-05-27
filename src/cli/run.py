# src/cli/run.py
"""
CLI do VTAE — vtae run, vtae systems, vtae clean, vtae send, vtae flakiness.
v0.5.8c — cmd_jornada suporta --repeat N
"""
import argparse
import json
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
    "login_si3":                 "tests/integration/si3/test_login_real.py",
    "cadastro_paciente":         "tests/integration/si3/test_cadastro_paciente.py",
    "admissao_internacao":       "tests/integration/si3/test_admissao_internacao.py",
    "cadastro_funcionario":      "tests/integration/sislab/test_cadastro_funcionario_sislab.py",
    "frequencia_aplicacao":      "tests/integration/msi3/test_frequencia_aplicacao.py",
    "tipo_anestesia":            "tests/integration/msi3/test_tipo_anestesia.py",
    "cadastro_paciente_jornada": "tests/integration/jornadas/ambulatorio/test_01_cadastro_paciente.py",
    "admissao_ambulatorio_jornada": "tests/integration/jornadas/ambulatorio/test_02_admissao_ambulatorio.py",
     "agendamento_jornada": "tests/integration/jornadas/ambulatorio_agendamento/test_02_agendamento.py",
}

# Jornadas: sequencia ordenada de testes encadeados
JORNADAS = {
    "ambulatorio": [
        "tests/integration/jornadas/ambulatorio/test_01_cadastro_paciente.py",
        "tests/integration/jornadas/ambulatorio/test_02_admissao_ambulatorio.py",
    ],

     "ambulatorio_agendamento": [
        "tests/integration/jornadas/ambulatorio_agendamento/test_01_cadastro_paciente.py",
        "tests/integration/jornadas/ambulatorio_agendamento/test_02_agendamento.py",
    ],
}

# Mapa explicito: nome do teste -> sistema para o health check
_MAPA_TESTE_SISTEMA = {
    "login_si3":                 "si3",
    "cadastro_paciente":         "si3",
    "admissao_internacao":       "si3",
    "cadastro_paciente_jornada": "si3",
    "cadastro_funcionario":      "sislab",
    "frequencia_aplicacao":      "msi3",
    "tipo_anestesia":            "msi3",
}

_MAPA_JORNADA_SISTEMA = {
    "ambulatorio": "si3",
}


def _rodar_pytest(arquivos, ambiente, retry, repeat=1):
    existentes = [a for a in arquivos if Path(a).exists()]
    ausentes   = [a for a in arquivos if not Path(a).exists()]

    if ausentes:
        print("[VTAE] Aviso — arquivos nao encontrados (serao ignorados):")
        for a in ausentes:
            print(f"  x {a}")

    if not existentes:
        print("[VTAE] Nenhum arquivo de teste encontrado.")
        return 1

    cmd = ["python", "-m", "pytest"] + existentes + ["-v", "--tb=short", f"--count={repeat}"]
    ultimo_rc = 0
    for i in range(retry + 1):
        if i > 0:
            print(f"\n[VTAE] Retry {i}/{retry}...")
        ultimo_rc = subprocess.run(cmd).returncode
        if ultimo_rc == 0:
            break
    return ultimo_rc


def _health_check(sistemas_alvo):
    """Executa health check e imprime resultado. Nao bloqueia execucao."""
    if not sistemas_alvo:
        return
    from src.core.health_check import verificar
    ok, avisos = verificar(sistemas_alvo)
    if avisos:
        print("[VTAE] !!  Health check — atencao:")
        for a in avisos:
            print(a)
        print()
    else:
        print("[VTAE] OK Health check OK — sistemas detectados.\n")


def _gerar_summary(modulo, ambiente):
    """Gera relatorio HTML unificado com os execution.json do dia."""
    try:
        import glob as _glob
        from datetime import datetime as _dt
        hoje = _dt.now().strftime("%Y-%m-%d")
        json_paths = _glob.glob(f"evidence/{hoje}/**/execution.json", recursive=True)
        if json_paths:
            out = f"evidence/{hoje}/summary/{modulo}_{ambiente}.html"
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            generate_summary(json_paths=json_paths, output_path=out,
                             titulo=f"{modulo} [{ambiente}]", ambiente=ambiente)
            print(f"\nRelatorio unificado: {out}")
    except Exception:
        pass


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
            print(f"[VTAE] Modulo '{args.module}' nao encontrado. Disponiveis: {list(MODULOS.keys())}")
            sys.exit(1)
        arquivos = MODULOS[args.module]
        label = f"modulo '{args.module}'"
    elif args.test:
        if args.test not in TESTES:
            print(f"[VTAE] Teste '{args.test}' nao encontrado. Disponiveis: {list(TESTES.keys())}")
            sys.exit(1)
        arquivos = [TESTES[args.test]]
        label = f"teste '{args.test}'"
    elif args.jornada:
        cmd_jornada(args)
        return
    else:
        print("[VTAE] Especifique --all, --module, --test ou --jornada.")
        sys.exit(1)

    repeat_label = f" x {args.repeat}" if args.repeat > 1 else ""
    print(f"  Executando: {label}{repeat_label}")
    print(f"  Testes    : {len(arquivos)} arquivo(s)")
    for a in arquivos:
        print(f"    -> {a}")
    print("=" * 60 + "\n")

    # health check
    sistemas_alvo = []
    if args.all:
        sistemas_alvo = list(MODULOS.keys())
    elif args.module:
        sistemas_alvo = [args.module]
    elif args.test:
        s = _MAPA_TESTE_SISTEMA.get(args.test)
        if s:
            sistemas_alvo = [s]

    _health_check(sistemas_alvo)

    rc = _rodar_pytest(arquivos, ambiente, args.retry, args.repeat)

    modulo = args.module or args.test or "all"
    _gerar_summary(modulo, ambiente)

    if args.to:
        for dest in args.to:
            try:
                enviar_relatorio(modulo=modulo, ambiente=ambiente, destinatario=dest)
            except Exception as e:
                print(f"[VTAE] Erro ao enviar para {dest}: {e}")

    status = "PASSOU" if rc == 0 else "FALHOU"
    print(f"\n{'=' * 60}")
    print(f"  {status} — {label} [{ambiente}]")
    print("=" * 60 + "\n")
    sys.exit(rc)


def cmd_jornada(args):
    """
    Executa jornada encadeada: test_01 -> test_02 -> ... -> test_N.
    Para imediatamente se qualquer teste falhar.
    Estado compartilhado via evidence/estado_jornada.json.
    Suporta --repeat N para repetir a jornada completa N vezes.
    Se qualquer repeticao falhar, interrompe e reporta quantas passaram.
    """
    jornada = args.jornada
    ambiente = args.ambiente or "dev"
    repeat   = getattr(args, "repeat", 1) or 1

    if jornada not in JORNADAS:
        print(f"[VTAE] Jornada '{jornada}' nao encontrada. Disponiveis: {list(JORNADAS.keys())}")
        sys.exit(1)

    testes = JORNADAS[jornada]
    repeat_label = f" x {repeat}" if repeat > 1 else ""

    print("\n" + "=" * 60)
    print("  VTAE — Visual Test Automation Engine")
    print("=" * 60)
    print(f"  Ambiente  : {ambiente}")
    print(f"  Jornada   : {jornada}{repeat_label}")
    print(f"  Testes    : {len(testes)} step(s)")
    for i, t in enumerate(testes, 1):
        print(f"    {i}. {t}")
    print("=" * 60 + "\n")

    sistema = _MAPA_JORNADA_SISTEMA.get(jornada)
    if sistema:
        _health_check([sistema])

    estado_path = Path("evidence/estado_jornada.json")
    estado_path.parent.mkdir(parents=True, exist_ok=True)

    rc_final = 0
    resumo_repeticoes = []

    for rep in range(1, repeat + 1):
        if repeat > 1:
            print(f"\n{'=' * 60}")
            print(f"  Repeticao {rep}/{repeat}")
            print("=" * 60)

        # limpa estado anterior da jornada a cada repeticao
        estado_path.write_text("{}", encoding="utf-8")

        resultados = []
        rc_rep = 0

        for i, arquivo in enumerate(testes, 1):
            label_step = Path(arquivo).stem
            print(f"\n[VTAE] >> Step {i}/{len(testes)}: {label_step}")
            print("-" * 60)

            if not Path(arquivo).exists():
                print(f"[VTAE] FALHOU Arquivo nao encontrado: {arquivo}")
                rc_rep = 1
                resultados.append({"step": i, "teste": label_step, "status": "NAO_ENCONTRADO"})
                break

            cmd = ["python", "-m", "pytest", arquivo, "-v", "--tb=short"]
            rc = subprocess.run(cmd).returncode

            status = "PASSOU" if rc == 0 else "FALHOU"
            resultados.append({"step": i, "teste": label_step, "status": status})

            if rc != 0:
                print(f"\n[VTAE] FALHOU Jornada interrompida no step {i}: {label_step}")
                rc_rep = rc
                break

            # le estado apos cada step (para log)
            try:
                estado = json.loads(estado_path.read_text(encoding="utf-8"))
                if estado:
                    chaves = ", ".join(f"{k}={v}" for k, v in estado.items())
                    print(f"[VTAE] Estado: {chaves}")
            except Exception:
                pass

        # sumario da repeticao atual
        print("\n" + "=" * 60)
        if repeat > 1:
            print(f"  Jornada '{jornada}' — repeticao {rep}/{repeat}")
        else:
            print(f"  Jornada '{jornada}' — resumo")
        print("=" * 60)
        for r in resultados:
            icone = "OK" if r["status"] == "PASSOU" else "FALHOU"
            print(f"  {icone} Step {r['step']}: {r['teste']} — {r['status']}")

        pendentes = len(testes) - len(resultados)
        if pendentes > 0:
            print(f"  -- {pendentes} step(s) nao executado(s) — jornada interrompida")

        status_rep = "PASSOU" if rc_rep == 0 else "FALHOU"
        resumo_repeticoes.append({"rep": rep, "status": status_rep})

        if rc_rep != 0:
            rc_final = rc_rep
            if repeat > 1:
                print(f"\n[VTAE] Repeticao {rep} FALHOU — interrompendo --repeat")
            break

    # sumario global de todas as repeticoes (so exibe se repeat > 1)
    if repeat > 1:
        print("\n" + "=" * 60)
        print(f"  Jornada '{jornada}' — resumo das {repeat} repeticoes")
        print("=" * 60)
        for r in resumo_repeticoes:
            icone = "OK" if r["status"] == "PASSOU" else "FALHOU"
            print(f"  {icone} Repeticao {r['rep']}: {r['status']}")
        passou = sum(1 for r in resumo_repeticoes if r["status"] == "PASSOU")
        print(f"\n  {passou}/{repeat} repeticoes passaram")

    _gerar_summary(f"jornada_{jornada}", ambiente)

    status_final = "PASSOU" if rc_final == 0 else "FALHOU"
    print(f"\n  {status_final} — jornada '{jornada}' [{ambiente}]")
    print("=" * 60 + "\n")
    sys.exit(rc_final)


def cmd_flakiness(args):
    """
    Exibe ranking de steps instáveis a partir do flakiness.json.
    Uso: vtae flakiness
         vtae flakiness --min-falhas 2
         vtae flakiness --top 10
    """
    flakiness_path = Path("evidence/flakiness.json")

    if not flakiness_path.exists():
        print("[VTAE] flakiness.json nao encontrado. Execute pelo menos um teste primeiro.")
        sys.exit(1)

    try:
        historico = json.loads(flakiness_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[VTAE] Erro ao ler flakiness.json: {e}")
        sys.exit(1)

    if not historico:
        print("[VTAE] flakiness.json vazio — nenhum historico ainda.")
        sys.exit(0)

    min_falhas = args.min_falhas if hasattr(args, "min_falhas") else 0
    top = args.top if hasattr(args, "top") else 999

    # calcula taxa de flakiness e ordena
    linhas = []
    for sid, dados in historico.items():
        total = dados["pass_count"] + dados["fail_count"]
        if total == 0:
            continue
        fail = dados["fail_count"]
        if fail < min_falhas:
            continue
        taxa = (fail / total) * 100
        avg_ms = dados.get("avg_duration_ms", 0)
        max_ms = dados.get("max_duration_ms", 0)
        ultima = dados.get("last_failure") or "-"
        causa = dados.get("last_causa_falha") or "-"
        linhas.append((taxa, fail, total, avg_ms, max_ms, ultima, causa, sid))

    # ordena por taxa desc, depois por fail_count desc
    linhas.sort(key=lambda x: (-x[0], -x[1]))
    linhas = linhas[:top]

    print("\n" + "=" * 70)
    print("  VTAE — Flakiness Report")
    print("=" * 70)
    print(f"  {'Step':<10} {'Falhas':<8} {'Total':<8} {'Taxa%':<8} "
          f"{'Avg ms':<10} {'Max ms':<10} {'Ultima Causa':<20} {'Ultima Falha'}")
    print("-" * 70)

    for taxa, fail, total, avg_ms, max_ms, ultima, causa, sid in linhas:
        if taxa >= 30:
            indicador = "!!"
        elif taxa >= 10:
            indicador = " !"
        else:
            indicador = "  "

        data_curta = ultima[:16] if ultima != "-" else "-"

        print(f"  {indicador} {sid:<8} {fail:<8} {total:<8} {taxa:<8.1f} "
              f"{avg_ms:<10.0f} {max_ms:<10.0f} {causa:<20} {data_curta}")

    print("-" * 70)

    total_steps = len(historico)
    steps_com_falha = sum(1 for d in historico.values() if d["fail_count"] > 0)
    steps_flaky = sum(
        1 for d in historico.values()
        if d["fail_count"] > 0 and d["pass_count"] > 0
    )
    print(f"\n  Total de steps monitorados : {total_steps}")
    print(f"  Steps com pelo menos 1 falha: {steps_com_falha}")
    print(f"  Steps flaky (falhou E passou): {steps_flaky}")
    print(f"\n  Arquivo: {flakiness_path.resolve()}")
    print("=" * 70 + "\n")


def cmd_systems(args):
    from src.config import ConfigLoader
    base = Path("configs")
    if args.sistema:
        ambientes = ConfigLoader.listar_ambientes(args.sistema, configs_dir=base)
        print(f"\nAmbientes para '{args.sistema}':")
        for a in ambientes:
            print(f"  . {a}")
    else:
        sistemas = ConfigLoader.listar_sistemas(configs_dir=base)
        print("\nSistemas disponiveis:")
        for s in sistemas:
            print(f"  . {s}")
    print()


def cmd_clean(args):
    import shutil
    from datetime import datetime, timedelta
    base = Path("evidence")
    if not base.exists():
        print("[VTAE] Pasta evidence/ nao encontrada.")
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
            print(f"[VTAE] Relatorio enviado para {dest}")
        except Exception as e:
            print(f"[VTAE] Erro: {e}")


def main():
    parser = argparse.ArgumentParser(prog="vtae")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run")
    p_run.add_argument("--module"); p_run.add_argument("--test")
    p_run.add_argument("--all", action="store_true")
    p_run.add_argument("--jornada")
    p_run.add_argument("--env", dest="ambiente", default="dev")
    p_run.add_argument("--retry", type=int, default=0)
    p_run.add_argument("--repeat", type=int, default=1)
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

    p_flak = sub.add_parser("flakiness")
    p_flak.add_argument("--min-falhas", type=int, default=0,
                        help="Mostrar apenas steps com pelo menos N falhas")
    p_flak.add_argument("--top", type=int, default=999,
                        help="Mostrar apenas os N steps mais instáveis")

    args = parser.parse_args()
    dispatch = {
        "run":       cmd_run,
        "systems":   cmd_systems,
        "clean":     cmd_clean,
        "send":      cmd_send,
        "flakiness": cmd_flakiness,
    }
    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()