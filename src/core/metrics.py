# src/core/metrics.py
"""
Metrics — Onda 3
Metricas e alertas de regressao a partir do flakiness.json existente.

Ponto central: nao precisa rodar nenhum teste.
Lê flakiness.json (gravado automaticamente pelo observer) e calcula:

  - Taxa de falha por step
  - Steps criticos (>= threshold, default 30%)
  - Cobertura de validacao (% validated=True) — via execution.json
  - Steps mais lentos (avg e max duration)
  - Alerta automatico quando step cruza threshold

Uso:
    vtae metrics                      # analisa flakiness.json atual
    vtae metrics --threshold 20       # alerta a partir de 20% de falha
    vtae metrics --top 10             # mostra top 10 steps mais flaky
    vtae metrics --date 2026-05-30    # analisa execucoes de uma data
    vtae metrics --html               # gera dashboard HTML

Uso programatico:
    from src.core.metrics import MetricsAnalyzer

    relatorio = MetricsAnalyzer.analisar()
    alertas   = MetricsAnalyzer.alertas(threshold=30)
    html      = MetricsAnalyzer.gerar_dashboard()
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime
from pathlib import Path


class MetricsAnalyzer:
    """
    Analisa metricas de qualidade a partir dos arquivos de historico.
    Todos os metodos sao offline — nenhum teste e executado.
    """

    DEFAULT_THRESHOLD  = 30   # % de falha para disparar alerta
    FLAKINESS_PATH     = "evidence/flakiness.json"
    EVIDENCE_BASE      = "evidence"

    # ----------------------------------------------------------------
    # API publica
    # ----------------------------------------------------------------

    @staticmethod
    def analisar(
        flakiness_path: str = FLAKINESS_PATH,
        threshold: int = DEFAULT_THRESHOLD,
        top: int = 999,
    ) -> dict:
        """
        Analisa flakiness.json e retorna relatorio estruturado.

        Returns:
            {
                "gerado_em": str,
                "total_steps": int,
                "steps_com_falha": int,
                "steps_criticos": list,   # taxa >= threshold
                "steps_flaky": list,      # falhou E passou
                "steps_estáveis": int,
                "top_flaky": list,        # top N por taxa
                "top_lentos": list,       # top N por avg_duration_ms
                "alertas": list[str],     # mensagens de alerta
            }
        """
        historico = MetricsAnalyzer._ler_flakiness(flakiness_path)
        if not historico:
            return {"erro": f"flakiness.json vazio ou nao encontrado: {flakiness_path}"}

        steps_criticos = []
        steps_flaky    = []
        steps_lentos   = []
        alertas        = []

        for sid, dados in historico.items():
            total = dados.get("pass_count", 0) + dados.get("fail_count", 0)
            if total == 0:
                continue

            fail  = dados.get("fail_count", 0)
            taxa  = round((fail / total) * 100, 1)
            avg   = dados.get("avg_duration_ms", 0)
            maxi  = dados.get("max_duration_ms", 0)
            desc  = dados.get("description", "")
            causa = dados.get("last_causa_falha", "")
            ult   = dados.get("last_failure", "")

            entrada = {
                "step_id":          sid,
                "description":      desc,
                "taxa_falha_pct":   taxa,
                "fail_count":       fail,
                "pass_count":       dados.get("pass_count", 0),
                "total_execucoes":  total,
                "avg_duration_ms":  round(avg, 1),
                "max_duration_ms":  round(maxi, 1),
                "last_causa_falha": causa,
                "last_failure":     ult[:16] if ult else None,
            }

            if taxa >= threshold:
                steps_criticos.append(entrada)
                alertas.append(
                    f"ALERTA [{sid}] taxa de falha {taxa:.0f}% >= {threshold}% "
                    f"({fail}/{total} execucoes)"
                    + (f" | causa: {causa}" if causa else "")
                    + (f" | {desc}" if desc else "")
                )

            if fail > 0 and dados.get("pass_count", 0) > 0:
                steps_flaky.append(entrada)

            steps_lentos.append(entrada)

        # ordena
        steps_criticos.sort(key=lambda x: -x["taxa_falha_pct"])
        steps_flaky.sort(key=lambda x: -x["taxa_falha_pct"])
        steps_lentos.sort(key=lambda x: -x["avg_duration_ms"])

        total_steps     = len(historico)
        steps_com_falha = sum(1 for d in historico.values() if d.get("fail_count", 0) > 0)
        steps_estaveis  = total_steps - steps_com_falha

        return {
            "gerado_em":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "flakiness_path":  flakiness_path,
            "threshold_pct":   threshold,
            "total_steps":     total_steps,
            "steps_com_falha": steps_com_falha,
            "steps_estaveis":  steps_estaveis,
            "steps_criticos":  steps_criticos[:top],
            "steps_flaky":     steps_flaky[:top],
            "top_flaky":       steps_flaky[:top],
            "top_lentos":      steps_lentos[:10],
            "alertas":         alertas,
        }

    @staticmethod
    def alertas(
        threshold: int = DEFAULT_THRESHOLD,
        flakiness_path: str = FLAKINESS_PATH,
    ) -> list[str]:
        """
        Retorna lista de mensagens de alerta para steps acima do threshold.
        Lista vazia = nenhum alerta.
        """
        rel = MetricsAnalyzer.analisar(flakiness_path, threshold=threshold)
        return rel.get("alertas", [])

    @staticmethod
    def cobertura_validacao(
        date_str: str | None = None,
        evidence_dir: str = EVIDENCE_BASE,
    ) -> dict:
        """
        Calcula cobertura de validacao (% validated=True) a partir dos
        execution.json de uma data. Nao precisa rodar testes.

        Returns:
            {
                "date_str": str,
                "total_steps": int,
                "validated_steps": int,
                "cobertura_pct": int,
                "por_flow": { flow_name: {"total": int, "validated": int, "pct": int} }
                "steps_sem_validacao": [{"step_id", "description", "flow"}]
            }
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        pattern  = os.path.join(evidence_dir, date_str, "**", "execution.json")
        paths    = sorted(glob.glob(pattern, recursive=True))

        total_steps = 0
        val_steps   = 0
        por_flow: dict[str, dict] = {}
        sem_validacao = []

        for path in paths:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            for flow in data.get("flows", []):
                flow_name = flow.get("flow_name", "?")
                if flow_name not in por_flow:
                    por_flow[flow_name] = {"total": 0, "validated": 0}

                for step in flow.get("steps", []):
                    if not step.get("success", False):
                        continue  # ignora steps que falharam
                    total_steps += 1
                    por_flow[flow_name]["total"] += 1

                    if step.get("validated") is True:
                        val_steps += 1
                        por_flow[flow_name]["validated"] += 1
                    else:
                        sem_validacao.append({
                            "step_id":     step.get("step_id", "?"),
                            "description": step.get("description", ""),
                            "flow":        flow_name,
                            "test":        data.get("test_name", "?"),
                        })

        # calcula percentuais
        for fname, d in por_flow.items():
            d["pct"] = round(d["validated"] / d["total"] * 100) if d["total"] else 0

        cobertura_pct = round(val_steps / total_steps * 100) if total_steps else 0

        return {
            "date_str":           date_str,
            "total_steps":        total_steps,
            "validated_steps":    val_steps,
            "cobertura_pct":      cobertura_pct,
            "por_flow":           por_flow,
            "steps_sem_validacao": sem_validacao,
        }

    @staticmethod
    def gerar_dashboard(
        date_str: str | None = None,
        threshold: int = DEFAULT_THRESHOLD,
        evidence_dir: str = EVIDENCE_BASE,
        flakiness_path: str = FLAKINESS_PATH,
    ) -> str:
        """
        Gera dashboard HTML de metricas. Pode ser executado a qualquer
        momento sem rodar testes.

        Returns:
            Caminho do HTML gerado.
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        relatorio  = MetricsAnalyzer.analisar(flakiness_path, threshold=threshold)
        cobertura  = MetricsAnalyzer.cobertura_validacao(date_str, evidence_dir)

        out_dir  = Path(evidence_dir) / date_str / "summary"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"metrics_{date_str}.html"

        html = MetricsAnalyzer._renderizar_dashboard(relatorio, cobertura, threshold)
        out_path.write_text(html, encoding="utf-8")
        print(f"[MetricsAnalyzer] Dashboard de metricas: {out_path}")
        return str(out_path)

    # ----------------------------------------------------------------
    # Internos
    # ----------------------------------------------------------------

    @staticmethod
    def _ler_flakiness(path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _renderizar_dashboard(
        rel: dict,
        cob: dict,
        threshold: int,
    ) -> str:
        hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        date_str = cob.get("date_str", hora[:10])

        alertas     = rel.get("alertas", [])
        criticos    = rel.get("steps_criticos", [])
        flaky       = rel.get("steps_flaky", [])
        lentos      = rel.get("top_lentos", [])
        cob_pct     = cob.get("cobertura_pct", 0)
        total_steps = rel.get("total_steps", 0)
        sem_val     = cob.get("steps_sem_validacao", [])
        por_flow    = cob.get("por_flow", {})

        # cores
        def cor_taxa(t):
            if t >= 30: return "#E24B4A"
            if t >= 10: return "#EF9F27"
            return "#1D9E75"

        def cor_cob(p):
            if p >= 80: return "#1D9E75"
            if p >= 50: return "#EF9F27"
            return "#E24B4A"

        # HTML de alertas
        alertas_html = ""
        if alertas:
            for a in alertas:
                alertas_html += f'<div class="alerta">{a}</div>'
        else:
            alertas_html = '<div class="ok-box">Nenhum alerta — todos os steps abaixo do threshold de {threshold}%</div>'

        # tabela de steps criticos
        def tabela_steps(steps, titulo, id_tab):
            if not steps:
                return f'<div class="section"><div class="section-title">{titulo}</div><div class="vazio">Nenhum step nesta categoria.</div></div>'
            rows = ""
            for s in steps:
                t = s["taxa_falha_pct"]
                rows += f"""<tr>
                  <td><b>{s['step_id']}</b></td>
                  <td style="color:#555;font-size:12px">{s.get('description','')[:60]}</td>
                  <td style="color:{cor_taxa(t)};font-weight:600">{t:.1f}%</td>
                  <td>{s['fail_count']}</td>
                  <td>{s['total_execucoes']}</td>
                  <td>{s['avg_duration_ms']:.0f}ms</td>
                  <td style="font-size:11px;color:#888">{s.get('last_causa_falha','') or '-'}</td>
                  <td style="font-size:11px;color:#888">{s.get('last_failure','') or '-'}</td>
                </tr>"""
            return f"""<div class="section">
              <div class="section-title">{titulo}</div>
              <table id="{id_tab}">
                <thead><tr>
                  <th>Step</th><th>Descricao</th><th>Taxa Falha</th>
                  <th>Falhas</th><th>Total</th><th>Avg Dur</th>
                  <th>Ultima Causa</th><th>Ultima Falha</th>
                </tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>"""

        # tabela cobertura por flow
        flow_rows = ""
        for fname, d in sorted(por_flow.items()):
            p = d["pct"]
            flow_rows += f"""<tr>
              <td>{fname}</td>
              <td>{d['total']}</td>
              <td>{d['validated']}</td>
              <td style="color:{cor_cob(p)};font-weight:600">{p}%</td>
            </tr>"""

        # steps sem validacao
        sem_val_rows = ""
        for s in sem_val[:30]:
            sem_val_rows += f"""<tr>
              <td><b>{s['step_id']}</b></td>
              <td style="color:#555;font-size:12px">{s.get('description','')[:60]}</td>
              <td style="font-size:12px;color:#888">{s.get('flow','')}</td>
            </tr>"""

        sem_val_html = ""
        if sem_val:
            sem_val_html = f"""<div class="section">
              <div class="section-title">Steps sem validacao — adicionar confirm_template ou verify_fill</div>
              <table>
                <thead><tr><th>Step</th><th>Descricao</th><th>Flow</th></tr></thead>
                <tbody>{sem_val_rows}</tbody>
              </table>
            </div>"""

        # tabela lentos
        lentos_rows = ""
        for s in lentos:
            lentos_rows += f"""<tr>
              <td><b>{s['step_id']}</b></td>
              <td style="color:#555;font-size:12px">{s.get('description','')[:60]}</td>
              <td style="color:#EF9F27;font-weight:600">{s['avg_duration_ms']:.0f}ms</td>
              <td>{s['max_duration_ms']:.0f}ms</td>
              <td>{s['total_execucoes']}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>VTAE — Metricas {date_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #F5F7FA;
          color: #1A1A2E; font-size: 14px; }}
  .header {{ background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 100%);
             color: white; padding: 28px 40px; }}
  .header h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
  .header .sub {{ font-size: 13px; opacity: 0.8; }}
  .stats {{ display: flex; gap: 16px; padding: 24px 40px; flex-wrap: wrap; }}
  .stat {{ background: white; border-radius: 10px; padding: 16px 22px;
           min-width: 130px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .stat .num {{ font-size: 26px; font-weight: 600; }}
  .stat .lbl {{ font-size: 11px; color: #888; margin-top: 2px;
                text-transform: uppercase; letter-spacing: 0.05em; }}
  .section {{ padding: 0 40px 28px; }}
  .section-title {{ font-size: 12px; font-weight: 500; color: #888;
                    text-transform: uppercase; letter-spacing: 0.08em;
                    margin-bottom: 10px; }}
  table {{ width: 100%; border-collapse: collapse; background: white;
           border-radius: 10px; overflow: hidden;
           box-shadow: 0 1px 4px rgba(0,0,0,0.07); }}
  th {{ background: #1F4E79; color: white; padding: 10px 14px;
        font-size: 11px; text-align: left; font-weight: 500; }}
  td {{ padding: 9px 14px; border-bottom: 1px solid #F0F0F0; font-size: 13px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #F8FAFC; }}
  .alerta {{ background: #FCE4E4; border-left: 4px solid #E24B4A;
             padding: 10px 16px; margin-bottom: 8px; border-radius: 6px;
             font-size: 13px; color: #A32D2D; }}
  .ok-box {{ background: #E1F5EE; border-left: 4px solid #1D9E75;
             padding: 10px 16px; border-radius: 6px; color: #0F6E56; }}
  .vazio {{ color: #AAA; font-size: 13px; padding: 12px 0; }}
  .footer {{ text-align: center; padding: 24px; font-size: 11px; color: #AAA; }}
</style>
</head>
<body>

<div class="header">
  <h1>VTAE — Dashboard de Métricas</h1>
  <div class="sub">InCor · Automação de Testes · {date_str} · Gerado em {hora}</div>
</div>

<div class="stats">
  <div class="stat">
    <div class="num">{total_steps}</div>
    <div class="lbl">Steps monitorados</div>
  </div>
  <div class="stat">
    <div class="num" style="color:{cor_cob(cob_pct)}">{cob_pct}%</div>
    <div class="lbl">Cobertura validação</div>
  </div>
  <div class="stat">
    <div class="num" style="color:#E24B4A">{len(criticos)}</div>
    <div class="lbl">Steps críticos (≥{threshold}%)</div>
  </div>
  <div class="stat">
    <div class="num" style="color:#EF9F27">{len(flaky)}</div>
    <div class="lbl">Steps flaky</div>
  </div>
  <div class="stat">
    <div class="num" style="color:#1D9E75">{rel.get('steps_estaveis',0)}</div>
    <div class="lbl">Steps estáveis</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Alertas (threshold {threshold}%)</div>
  {alertas_html}
</div>

{tabela_steps(criticos, f"Steps criticos — taxa de falha >= {threshold}%", "tab-criticos")}
{tabela_steps(flaky,    "Steps flaky — falharam E passaram", "tab-flaky")}

<div class="section">
  <div class="section-title">Cobertura de validacao por flow (data: {date_str})</div>
  <table>
    <thead><tr><th>Flow</th><th>Total Steps</th><th>Validados</th><th>Cobertura</th></tr></thead>
    <tbody>{flow_rows if flow_rows else '<tr><td colspan="4" style="color:#AAA">Sem execucoes na data informada.</td></tr>'}</tbody>
  </table>
</div>

{sem_val_html}

<div class="section">
  <div class="section-title">Top 10 steps mais lentos (historico)</div>
  <table>
    <thead><tr><th>Step</th><th>Descricao</th><th>Avg Dur</th><th>Max Dur</th><th>Execucoes</th></tr></thead>
    <tbody>{lentos_rows if lentos_rows else '<tr><td colspan="5" style="color:#AAA">Sem dados.</td></tr>'}</tbody>
  </table>
</div>

<div class="footer">
  VTAE v0.5.10 · InCor — Automação de Testes · threshold configurado: {threshold}% · {hora}
</div>

</body>
</html>"""