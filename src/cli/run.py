# src/cli/run.py
"""
CLI do VTAE — vtae run, vtae systems, vtae clean, vtae send,
              vtae flakiness, vtae summary, vtae metrics.

v0.5.10:
  - TESTES e JORNADAS atualizados com todas as jornadas novas
  - vtae summary — gera relatorio gerencial HTML offline (Onda 2)
  - vtae metrics  — dashboard de metricas e alertas offline (Onda 3)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.cli.send import enviar_relatorio


MODULOS = {
    "sislab": [
        "tests/integration/sislab/jornadas/cadastros/test_01_cadastro_funcionario.py",
    ],
    "si3": [
        "tests/integration/si3/test_login_real.py",
        "tests/integration/si3/jornadas/internacao/test_01_cadastro_paciente.py",
        "tests/integration/si3/jornadas/internacao/test_02_admissao_internacao.py",
        "tests/integration/si3/jornadas/ambulatorio/sem_agendamento/test_01_cadastro_paciente.py",
        "tests/integration/si3/jornadas/ambulatorio/sem_agendamento/test_02_admissao_ambulatorio.py",
    ],
    "msi3": [
        "tests/integration/msi3/jornadas/intra_operatorio/test_frequencia_aplicacao.py",
        "tests/integration/msi3/jornadas/intra_operatorio/test_tipo_anestesia.py",
    ],
}

TESTES = {
    # SI3 — testes individuais
    "login_si3":                          "tests/integration/si3/test_login_real.py",
    "cadastro_paciente_jornada":          "tests/integration/si3/jornadas/ambulatorio/sem_agendamento/test_01_cadastro_paciente.py",
    "admissao_ambulatorio_jornada":       "tests/integration/si3/jornadas/ambulatorio/sem_agendamento/test_02_admissao_ambulatorio.py",
    "agendamento_jornada":                "tests/integration/si3/jornadas/ambulatorio/com_agendamento/test_02_agendamento.py",
    "admissao_com_agendamento_jornada":   "tests/integration/si3/jornadas/ambulatorio/com_agendamento/test_03_admissao_com_agendamento.py",
    "cadastro_paciente_internacao_jornada": "tests/integration/si3/jornadas/internacao/test_01_cadastro_paciente.py",
    "admissao_internacao_jornada":        "tests/integration/si3/jornadas/internacao/test_02_admissao_internacao.py",
    # SisLab
    "cadastro_funcionario":               "tests/integration/sislab/jornadas/cadastros/test_01_cadastro_funcionario.py",
    # MSI3
    'tipo_anestesia':                      'tests/integration/msi3/jornadas/anestesia_pre_operatorio/test_tipo_anestesia.py',
}

# Jornadas: sequencia ordenada de testes encadeados
JORNADAS = {
    "ambulatorio": [
        "tests/integration/si3/jornadas/ambulatorio/sem_agendamento/test_01_cadastro_paciente.py",
        "tests/integration/si3/jornadas/ambulatorio/sem_agendamento/test_02_admissao_ambulatorio.py",
    ],
    "ambulatorio_com_agendamento": [
        "tests/integration/si3/jornadas/ambulatorio/com_agendamento/test_01_cadastro_paciente.py",
        "tests/integration/si3/jornadas/ambulatorio/com_agendamento/test_02_agendamento.py",
        "tests/integration/si3/jornadas/ambulatorio/com_agendamento/test_03_admissao_com_agendamento.py",
    ],
    "internacao": [
        "tests/integration/si3/jornadas/internacao/test_01_cadastro_paciente.py",
        "tests/integration/si3/jornadas/internacao/test_02_admissao_internacao.py",
    ],
}

_MAPA_TESTE_SISTEMA = {
    "login_si3":                            "si3",
    "cadastro_paciente_jornada":            "si3",
    "admissao_ambulatorio_jornada":         "si3",
    "agendamento_jornada":                  "si3",
    "admissao_com_agendamento_jornada":     "si3",
    "cadastro_paciente_internacao_jornada": "si3",
    "admissao_internacao_jornada":          "si3",
    "cadastro_funcionario":                 "sislab",
    "frequencia_aplicacao":                 "msi3",
    "tipo_anestesia":                       "msi3",
}

_MAPA_JORNADA_SISTEMA = {
    "ambulatorio":                 "si3",
    "ambulatorio_com_agendamento": "si3",
    "internacao":                  "si3",
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
    if not sistemas_alvo:
        return
    try:
        from src.core.health_check import verificar
        ok, avisos = verificar(sistemas_alvo)
        if avisos:
            print("[VTAE] !!  Health check — atencao:")
            for a in avisos:
                print(a)
            print()
        else:
            print("[VTAE] OK Health check OK — sistemas detectados.\n")
    except Exception:
        pass


def _gerar_summary(modulo, ambiente):
    """Gera relatorio gerencial HTML unificado com os execution.json do dia."""
    try:
        from src.core.summary_generator import SummaryGenerator
        from datetime import datetime as _dt
        hoje = _dt.now().strftime("%Y-%m-%d")
        out = SummaryGenerator.gerar(date_str=hoje)
        print(f"\nRelatorio gerencial: {out}")
    except FileNotFoundError:
        pass  # sem execucoes no dia — nao e erro
    except Exception as e:
        print(f"[VTAE] AVISO: nao foi possivel gerar summary: {e}")


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
    """
    jornada  = args.jornada
    ambiente = args.ambiente or "dev"

    if jornada not in JORNADAS:
        print(f"[VTAE] Jornada '{jornada}' nao encontrada. Disponiveis: {list(JORNADAS.keys())}")
        sys.exit(1)

    testes = JORNADAS[jornada]

    print("\n" + "=" * 60)
    print("  VTAE — Visual Test Automation Engine")
    print("=" * 60)
    print(f"  Ambiente  : {ambiente}")
    print(f"  Jornada   : {jornada}")
    print(f"  Testes    : {len(testes)} step(s)")
    for i, t in enumerate(testes, 1):
        print(f"    {i}. {t}")
    print("=" * 60 + "\n")

    sistema = _MAPA_JORNADA_SISTEMA.get(jornada)
    if sistema:
        _health_check([sistema])

    # Limpa estado UMA VEZ antes do primeiro step
    # Nunca limpar dentro do loop — o estado_jornada.json e o canal de
    # comunicacao entre steps (ex: paciente_id gravado pelo cadastro e
    # lido pela admissao)
    estado_path = Path("evidence/estado_jornada.json")
    estado_path.parent.mkdir(parents=True, exist_ok=True)
    estado_path.write_text("{}", encoding="utf-8")
    print("[VTAE] Estado da jornada limpo — pronto para o step 1.")

    resultados = []
    rc_final   = 0

    for i, arquivo in enumerate(testes, 1):
        label_step = Path(arquivo).stem
        print(f"\n[VTAE] >> Step {i}/{len(testes)}: {label_step}")
        print("-" * 60)

        if not Path(arquivo).exists():
            print(f"[VTAE] FALHOU Arquivo nao encontrado: {arquivo}")
            rc_final = 1
            resultados.append({"step": i, "teste": label_step, "status": "NAO_ENCONTRADO"})
            break

        cmd = ["python", "-m", "pytest", arquivo, "-v", "--tb=short"]
        rc  = subprocess.run(cmd).returncode

        status = "PASSOU" if rc == 0 else "FALHOU"
        resultados.append({"step": i, "teste": label_step, "status": status})

        if rc != 0:
            print(f"\n[VTAE] FALHOU Jornada interrompida no step {i}: {label_step}")
            rc_final = rc
            break

        try:
            estado = json.loads(estado_path.read_text(encoding="utf-8"))
            if estado:
                chaves = ", ".join(f"{k}={v}" for k, v in estado.items())
                print(f"[VTAE] Estado: {chaves}")
        except Exception:
            pass

    print("\n" + "=" * 60)
    print(f"  Jornada '{jornada}' — resumo")
    print("=" * 60)
    for r in resultados:
        icone = "OK" if r["status"] == "PASSOU" else "FALHOU"
        print(f"  {icone} Step {r['step']}: {r['teste']} — {r['status']}")

    pendentes = len(testes) - len(resultados)
    if pendentes > 0:
        print(f"  -- {pendentes} step(s) nao executado(s) — jornada interrompida")

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

    min_falhas = getattr(args, "min_falhas", 0)
    top        = getattr(args, "top", 999)

    linhas = []
    for sid, dados in historico.items():
        total = dados["pass_count"] + dados["fail_count"]
        if total == 0:
            continue
        fail = dados["fail_count"]
        if fail < min_falhas:
            continue
        taxa     = (fail / total) * 100
        avg_ms   = dados.get("avg_duration_ms", 0)
        max_ms   = dados.get("max_duration_ms", 0)
        ultima   = dados.get("last_failure") or "-"
        causa    = dados.get("last_causa_falha") or "-"
        desc     = dados.get("description", "")[:30]
        linhas.append((taxa, fail, total, avg_ms, max_ms, ultima, causa, sid, desc))

    linhas.sort(key=lambda x: (-x[0], -x[1]))
    linhas = linhas[:top]

    print("\n" + "=" * 80)
    print("  VTAE — Flakiness Report")
    print("=" * 80)
    print(f"  {'Step':<8} {'%Falha':<8} {'Falhas':<8} {'Total':<7} "
          f"{'Avg ms':<10} {'Max ms':<10} {'Causa':<22} {'Descricao'}")
    print("-" * 80)

    for taxa, fail, total, avg_ms, max_ms, ultima, causa, sid, desc in linhas:
        indicador = "!!" if taxa >= 30 else (" !" if taxa >= 10 else "  ")
        data_curta = ultima[:16] if ultima != "-" else "-"
        print(f"  {indicador} {sid:<6} {taxa:<8.1f} {fail:<8} {total:<7} "
              f"{avg_ms:<10.0f} {max_ms:<10.0f} {causa:<22} {desc}")

    print("-" * 80)

    total_steps     = len(historico)
    steps_com_falha = sum(1 for d in historico.values() if d["fail_count"] > 0)
    steps_flaky     = sum(
        1 for d in historico.values()
        if d["fail_count"] > 0 and d["pass_count"] > 0
    )
    print(f"\n  Total monitorados   : {total_steps}")
    print(f"  Com pelo menos 1 falha: {steps_com_falha}")
    print(f"  Flaky (falhou E passou): {steps_flaky}")
    print(f"\n  Arquivo: {flakiness_path.resolve()}")
    print(f"  Dica: vtae metrics --html  para dashboard visual completo")
    print("=" * 80 + "\n")


def cmd_summary(args):
    """
    Gera relatorio gerencial HTML offline.
    Nao precisa rodar testes — le evidence/*.json existentes.

    Uso:
        vtae summary
        vtae summary --date 2026-05-30
        vtae summary --jornada internacao
    """
    from src.core.summary_generator import SummaryGenerator

    date_str = getattr(args, "date", None)
    jornada  = getattr(args, "jornada", None)

    print("\n[VTAE] Gerando relatorio gerencial...")
    try:
        html_path = SummaryGenerator.gerar(
            date_str=date_str,
            jornada_filtro=jornada,
        )
        print(f"[VTAE] OK Relatorio gerencial: {html_path}\n")
    except FileNotFoundError as e:
        print(f"[VTAE] {e}")
        sys.exit(1)


def cmd_metrics(args):
    """
    Analisa metricas e alertas offline.
    Nao precisa rodar testes — le flakiness.json e execution.json existentes.

    Uso:
        vtae metrics
        vtae metrics --threshold 20
        vtae metrics --top 10
        vtae metrics --date 2026-05-30
        vtae metrics --html
    """
    from src.core.metrics import MetricsAnalyzer

    threshold = getattr(args, "threshold", MetricsAnalyzer.DEFAULT_THRESHOLD)
    top       = getattr(args, "top", 999)
    date_str  = getattr(args, "date", None)
    gerar_html = getattr(args, "html", False)

    # analise de flakiness
    print("\n[VTAE] Analisando metricas...")
    relatorio = MetricsAnalyzer.analisar(threshold=threshold, top=top)

    if "erro" in relatorio:
        print(f"[VTAE] {relatorio['erro']}")
        sys.exit(1)

    # alertas
    alertas = relatorio.get("alertas", [])
    if alertas:
        print(f"\n[VTAE] !! {len(alertas)} alerta(s) — threshold {threshold}%:")
        for a in alertas:
            print(f"  {a}")
    else:
        print(f"\n[VTAE] OK Nenhum alerta — todos os steps abaixo de {threshold}%")

    # cobertura de validacao
    try:
        cob = MetricsAnalyzer.cobertura_validacao(date_str)
        print(f"\n[VTAE] Cobertura de validacao ({cob['date_str']}): "
              f"{cob['cobertura_pct']}% "
              f"({cob['validated_steps']}/{cob['total_steps']} steps validados)")
        sem_val = cob.get("steps_sem_validacao", [])
        if sem_val:
            print(f"  Steps sem validacao: {len(sem_val)}")
            for s in sem_val[:5]:
                print(f"    {s['step_id']} — {s.get('description','')} [{s['flow']}]")
            if len(sem_val) > 5:
                print(f"    ... e mais {len(sem_val) - 5}. Use --html para lista completa.")
    except Exception:
        pass

    # resumo
    print(f"\n[VTAE] Resumo:")
    print(f"  Steps monitorados : {relatorio['total_steps']}")
    print(f"  Steps criticos    : {len(relatorio['steps_criticos'])} (>= {threshold}%)")
    print(f"  Steps flaky       : {len(relatorio['steps_flaky'])}")
    print(f"  Steps estaveis    : {relatorio['steps_estaveis']}")

    if gerar_html:
        try:
            html_path = MetricsAnalyzer.gerar_dashboard(
                date_str=date_str,
                threshold=threshold,
            )
            print(f"\n[VTAE] Dashboard HTML: {html_path}")
        except Exception as e:
            print(f"[VTAE] AVISO: nao foi possivel gerar dashboard: {e}")

    print()


def cmd_systems(args):
    from src.config.loader import ConfigLoader
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
    cutoff   = datetime.now() - timedelta(days=args.days)
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
    modulo   = args.module or "all"
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
    # Garante working directory correto independente de onde vtae for chamado
    # src/cli/run.py -> src/cli -> src -> VTAE/
    import os
    _raiz = Path(__file__).resolve().parent.parent.parent
    if not (_raiz / "src").exists():
        print(f"[VTAE] ERRO: estrutura do projeto nao encontrada a partir de {_raiz}")
        print(f"  Verifique se o pacote foi instalado corretamente com: pip install -e .")
        sys.exit(1)
    os.chdir(_raiz)

    parser = argparse.ArgumentParser(prog="vtae")
    sub    = parser.add_subparsers(dest="command")

    # vtae run
    p_run = sub.add_parser("run", help="Executar testes ou jornadas")
    p_run.add_argument("--module");  p_run.add_argument("--test")
    p_run.add_argument("--all", action="store_true")
    p_run.add_argument("--jornada")
    p_run.add_argument("--env", dest="ambiente", default="dev")
    p_run.add_argument("--retry",  type=int, default=0)
    p_run.add_argument("--repeat", type=int, default=1)
    p_run.add_argument("--to", action="append")

    # vtae systems
    p_sys = sub.add_parser("systems", help="Listar sistemas disponiveis")
    p_sys.add_argument("--sistema")

    # vtae clean
    p_clean = sub.add_parser("clean", help="Remover evidencias antigas")
    p_clean.add_argument("--days",    type=int, default=30)
    p_clean.add_argument("--dry-run", action="store_true")

    # vtae send
    p_send = sub.add_parser("send", help="Enviar relatorio por email")
    p_send.add_argument("--module"); p_send.add_argument("--all", action="store_true")
    p_send.add_argument("--to",  action="append", required=True)
    p_send.add_argument("--env", dest="ambiente", default="dev")

    # vtae flakiness
    p_flak = sub.add_parser("flakiness", help="Ranking de steps instáveis")
    p_flak.add_argument("--min-falhas", type=int, default=0,
                        help="Mostrar apenas steps com pelo menos N falhas")
    p_flak.add_argument("--top", type=int, default=999,
                        help="Mostrar apenas os N steps mais instáveis")

    # vtae summary — Onda 2
    p_sum = sub.add_parser("summary", help="Gerar relatorio gerencial HTML (offline)")
    p_sum.add_argument("--date",    default=None, help="Data YYYY-MM-DD (default: hoje)")
    p_sum.add_argument("--jornada", default=None, help="Filtrar por jornada")

    # vtae metrics — Onda 3
    p_met = sub.add_parser("metrics", help="Dashboard de metricas e alertas (offline)")
    p_met.add_argument("--threshold", type=int, default=30,
                       help="% de falha para disparar alerta (default: 30)")
    p_met.add_argument("--top",  type=int, default=999,
                       help="Mostrar os N steps mais flaky")
    p_met.add_argument("--date", default=None,
                       help="Data YYYY-MM-DD para cobertura de validacao (default: hoje)")
    p_met.add_argument("--html", action="store_true",
                       help="Gerar dashboard HTML alem do output no terminal")

    args = parser.parse_args()
    dispatch = {
        "run":       cmd_run,
        "systems":   cmd_systems,
        "clean":     cmd_clean,
        "send":      cmd_send,
        "flakiness": cmd_flakiness,
        "summary":   cmd_summary,
        "metrics":   cmd_metrics,
    }
    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()