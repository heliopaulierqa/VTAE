"""
VTAE Report Generator — Fase 1
Gera relatório HTML profissional a partir do execution.json.
É chamado automaticamente pelo ExecutionObserver ao final de cada execução.

Melhorias Fase 1:
  - Fontes do sistema (sem dependência de internet)
  - Seção de alertas no topo (steps críticos em destaque)
  - Score de confiança visível nos steps que falharam por template
  - Tendência histórica lida do flakiness.json
"""

import base64
import json
import os
from datetime import datetime
from pathlib import Path


def _img_to_base64(path: str) -> str | None:
    """Converte imagem para base64 para embutir no HTML."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{data}"
    except Exception:
        return None


def _ler_flakiness() -> dict:
    """Le o flakiness.json para exibir tendencia historica."""
    path = Path("evidence/flakiness.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def generate(json_path: str, output_path: str | None = None) -> str:
    """
    Gera relatório HTML a partir do execution.json.

    Args:
        json_path: caminho para o execution.json
        output_path: caminho de saída do HTML (default: mesmo dir do json)

    Returns:
        Caminho do arquivo HTML gerado.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if output_path is None:
        output_path = str(Path(json_path).parent / "report.html")

    html = _build_html(data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _score_bar(score: float) -> str:
    """Gera barra visual de score de confiança."""
    pct = round(score * 100)
    if score >= 0.75:
        color = "#1D9E75"
    elif score >= 0.55:
        color = "#f59e0b"
    else:
        color = "#E24B4A"
    return (
        f'<span class="score-bar" title="Score: {score:.3f}">'
        f'<span class="score-fill" style="width:{pct}%;background:{color}"></span>'
        f'</span>'
        f'<span class="score-label" style="color:{color}">{score:.2f}</span>'
    )


def _build_html(data: dict) -> str:
    status    = data.get("status", "?")
    test_name = data.get("test_name", "Execução")
    started   = data.get("started_at", "")[:19].replace("T", " ")
    duration  = data.get("duration_seconds", 0)
    exec_id   = data.get("execution_id", "")[:8]
    summary   = data.get("summary", {})
    flows     = data.get("flows", [])
    flakiness = _ler_flakiness()

    status_color = "#1D9E75" if status == "PASSOU" else "#E24B4A"
    status_bg    = "#E1F5EE" if status == "PASSOU" else "#FCEBEB"
    status_icon  = "✅" if status == "PASSOU" else "❌"

    total  = summary.get("total_steps", 0)
    passed = summary.get("passed_steps", 0)
    failed = summary.get("failed_steps", 0)
    pct    = round((passed / total * 100) if total > 0 else 0)

    all_steps = [s for f in flows for s in f.get("steps", [])]
    validated_count   = sum(1 for s in all_steps if s.get("validated") is True)
    sem_validacao     = sum(1 for s in all_steps if s.get("success") and s.get("validated") is None)
    falha_integridade = sum(
        1 for s in all_steps
        if not s.get("success") and "observabilidade" in (s.get("error") or "").lower()
    )

    # ----------------------------------------------------------------
    # Seção de alertas — steps críticos em destaque no topo
    # ----------------------------------------------------------------
    alertas = []

    # Steps que falharam nesta execução
    for s in all_steps:
        if not s.get("success"):
            sid   = s.get("step_id", "")
            causa = s.get("causa_falha", "desconhecida")
            score = s.get("confidence_score")
            tpl   = s.get("template_path", "")
            fdata = flakiness.get(sid, {})
            fail_count  = fdata.get("fail_count", 0)
            total_exec  = fdata.get("pass_count", 0) + fail_count
            taxa        = round((fail_count / total_exec * 100) if total_exec > 0 else 0)
            score_txt   = f" · score {score:.3f}" if score is not None else ""
            hist_txt    = f" · {taxa}% de falha histórica ({fail_count}/{total_exec})" if total_exec > 0 else ""
            alertas.append((sid, causa, score_txt + hist_txt, tpl))

    # Steps com alta taxa de falha histórica que passaram hoje
    # (regressão silenciosa — pode quebrar na próxima execução)
    for sid, fdata in flakiness.items():
        fail_count = fdata.get("fail_count", 0)
        total_exec = fdata.get("pass_count", 0) + fail_count
        if total_exec < 3:
            continue
        taxa = (fail_count / total_exec) * 100
        if taxa >= 30:
            # verificar se passou nesta execução
            passou_agora = any(
                s.get("step_id") == sid and s.get("success")
                for s in all_steps
            )
            if passou_agora:
                alertas.append((
                    sid, "historico",
                    f"passou hoje mas taxa histórica: {taxa:.0f}% ({fail_count}/{total_exec})",
                    ""
                ))

    alertas_html = ""
    if alertas:
        items_html = ""
        for sid, causa, detalhe, tpl in alertas:
            cor = "#E24B4A" if causa != "historico" else "#f59e0b"
            bg  = "#fff8f8" if causa != "historico" else "#fffbeb"
            icone = "❌" if causa != "historico" else "⚠"
            tpl_html = f'<span class="alerta-tpl">{tpl}</span>' if tpl else ""
            items_html += f"""
            <div class="alerta-item" style="border-left:3px solid {cor};background:{bg};">
              <span class="alerta-icon">{icone}</span>
              <div class="alerta-body">
                <span class="alerta-step">{sid}</span>
                <span class="alerta-causa">{causa}</span>
                {tpl_html}
                <span class="alerta-detalhe">{detalhe}</span>
              </div>
            </div>"""
        alertas_html = f"""
  <div class="alertas-wrap">
    <div class="section-title">⚠ Atenção — {len(alertas)} ponto(s) crítico(s)</div>
    {items_html}
  </div>"""

    # ----------------------------------------------------------------
    # Flows e steps
    # ----------------------------------------------------------------
    flows_html = ""
    for flow in flows:
        flow_ok    = flow.get("success", False)
        flow_color = "#1D9E75" if flow_ok else "#E24B4A"
        flow_bg    = "#E1F5EE" if flow_ok else "#FCEBEB"
        flow_icon  = "✅" if flow_ok else "❌"
        flow_ms    = round(flow.get("total_duration_ms", 0))

        steps_html = ""
        for step in flow.get("steps", []):
            s_ok        = step.get("success", False)
            s_color     = "#1D9E75" if s_ok else "#E24B4A"
            s_bg        = "#f8fffe" if s_ok else "#fff8f8"
            s_icon      = "✅" if s_ok else "❌"
            s_id        = step.get("step_id", "")
            s_ms        = round(step.get("duration_ms", 0))
            s_err       = step.get("error") or ""
            s_ts        = step.get("timestamp", "")[:19].replace("T", " ")
            s_img       = _img_to_base64(step.get("screenshot"))
            s_validated = step.get("validated")
            s_score     = step.get("confidence_score")
            s_tpl       = step.get("template_path") or ""
            s_ocr_lido  = step.get("ocr_lido") or ""

            # Flakiness histórico do step
            fdata      = flakiness.get(s_id, {})
            fail_count = fdata.get("fail_count", 0)
            total_exec = fdata.get("pass_count", 0) + fail_count
            taxa_hist  = round((fail_count / total_exec * 100) if total_exec > 0 else 0)
            hist_badge = ""
            if total_exec >= 3 and taxa_hist >= 10:
                hist_color = "#E24B4A" if taxa_hist >= 30 else "#f59e0b"
                hist_badge = (
                    f'<span class="badge" style="background:#fff3e0;color:{hist_color};'
                    f'border:1px solid {hist_color};">'
                    f'↻ {taxa_hist}% histórico</span>'
                )

            # Série temporal — últimos 10 resultados (Obs-Fase2)
            # Visualiza se step começou a falhar recentemente ou sempre foi instável
            serie_html = ""
            last_10 = fdata.get("last_10_results", [])
            if len(last_10) >= 2:
                dots = ""
                for r in last_10:
                    cor = "#1D9E75" if r == 1 else "#E24B4A"
                    dots += f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{cor};margin:0 1px;" title="{"OK" if r==1 else "FALHOU"}"></span>'
                serie_html = (
                    f'<div class="step-serie" title="Últimas {len(last_10)} execuções">'
                    f'{dots}</div>'
                )

            # Badge de integridade
            # "sem validação" agora usa cor laranja para chamar mais atenção —
            # steps bem-sucedidos sem verify/confirm são observabilidade cosmética
            is_obs_falha = not s_ok and (
                "observabilidade" in s_err.lower() or
                "verify_fill" in s_err.lower() or
                "verify_lov" in s_err.lower()
            )
            if is_obs_falha:
                badge_html = '<span class="badge badge-integridade">⚠ FALHA DE INTEGRIDADE</span>'
            elif s_validated is True:
                badge_html = '<span class="badge badge-validado">✔ VALIDADO</span>'
            elif s_ok and s_validated is None:
                # Laranja pulsante — mais visível que cinza anterior
                badge_html = '<span class="badge badge-sem-validacao">~ sem validação</span>'
            else:
                badge_html = ""

            # OCR lido — exibe valor real lido pelo EasyOCR
            ocr_lido_html = ""
            if s_ocr_lido and s_validated is True:
                ocr_lido_html = f'''
                <div class="step-ocr-lido">
                  <span class="ocr-label">OCR leu:</span>
                  <span class="ocr-valor">{s_ocr_lido}</span>
                </div>'''

            # Score de confiança (Fase 1) — só exibe quando falhou por template
            score_html = ""
            if not s_ok and s_score is not None:
                score_html = f"""
                <div class="step-score">
                  <span class="score-label-txt">Confiança do template:</span>
                  {_score_bar(s_score)}
                  {f'<span class="score-tpl">{s_tpl}</span>' if s_tpl else ""}
                </div>"""

            img_html = ""
            if s_img:
                img_html = f"""
                <div class="step-screenshot">
                    <img src="{s_img}" alt="screenshot {s_id}" onclick="openImg(this)" />
                    <span class="img-hint">clique para ampliar</span>
                </div>"""

            err_html = ""
            if s_err:
                err_html = f'<div class="step-error">⚠ {s_err}</div>'

            steps_html += f"""
            <div class="step" style="border-left:3px solid {s_color};background:{s_bg};">
                <div class="step-header">
                    <span class="step-icon">{s_icon}</span>
                    <span class="step-id">{s_id}</span>
                    <span class="step-time">{s_ms}ms</span>
                    {badge_html}
                    {hist_badge}
                    {serie_html}
                    <span class="step-ts">{s_ts}</span>
                </div>
                {ocr_lido_html}
                {score_html}
                {err_html}
                {img_html}
            </div>"""

        flows_html += f"""
        <div class="flow-card">
            <div class="flow-header" style="background:{flow_bg};border-left:4px solid {flow_color};">
                <span class="flow-icon">{flow_icon}</span>
                <span class="flow-name">{flow.get("flow_name", "")}</span>
                <span class="flow-steps">{len([s for s in flow.get("steps",[]) if s.get("success")])}/{len(flow.get("steps",[]))} steps</span>
                <span class="flow-duration">{flow_ms}ms</span>
            </div>
            <div class="steps-container">
                {steps_html}
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VTAE — {test_name}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: #f4f3f0;
    --card: #ffffff;
    --border: #e2e0db;
    --text: #1a1a1a;
    --muted: #6b6966;
    --green: #1D9E75;
    --green-bg: #E1F5EE;
    --red: #E24B4A;
    --red-bg: #FCEBEB;
    --mono: 'Consolas', 'Courier New', monospace;
    --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
  }}

  body {{
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 2rem 1rem;
  }}

  .container {{ max-width: 960px; margin: 0 auto; }}

  /* HEADER */
  .header {{
    display: flex; align-items: flex-start;
    justify-content: space-between; flex-wrap: wrap;
    gap: 1rem; margin-bottom: 2rem;
  }}
  .header-left h1 {{
    font-size: 1.6rem; font-weight: 600; letter-spacing: -0.03em;
    font-family: var(--sans);
  }}
  .header-left p {{
    font-size: 0.82rem; color: var(--muted); margin-top: 4px;
    font-family: var(--mono);
  }}
  .status-badge {{
    padding: 6px 18px; border-radius: 99px;
    font-weight: 600; font-size: 0.9rem;
  }}

  /* ALERTAS */
  .alertas-wrap {{
    background: var(--card); border: 1px solid #fca5a5;
    border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 2rem;
  }}
  .alerta-item {{
    display: flex; align-items: flex-start; gap: 10px;
    padding: 8px 10px; border-radius: 6px; margin-top: 8px;
  }}
  .alerta-icon {{ font-size: 0.9rem; margin-top: 1px; flex-shrink: 0; }}
  .alerta-body {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 0.8rem; }}
  .alerta-step {{ font-family: var(--mono); font-weight: 600; font-size: 0.82rem; }}
  .alerta-causa {{
    background: #fee2e2; color: #991b1b;
    padding: 1px 7px; border-radius: 99px; font-size: 0.72rem; font-weight: 600;
  }}
  .alerta-tpl {{ font-family: var(--mono); font-size: 0.72rem; color: var(--muted); }}
  .alerta-detalhe {{ font-size: 0.78rem; color: var(--muted); }}

  /* METRICS */
  .metrics {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin-bottom: 2rem;
  }}
  .metric {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.25rem;
  }}
  .metric-label {{
    font-size: 0.72rem; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;
  }}
  .metric-value {{
    font-size: 1.8rem; font-weight: 600; letter-spacing: -0.03em;
    font-family: var(--mono);
  }}

  /* PROGRESS */
  .progress-wrap {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 2rem;
  }}
  .progress-label {{
    display: flex; justify-content: space-between;
    font-size: 0.8rem; color: var(--muted); margin-bottom: 8px;
  }}
  .progress-bar {{
    height: 8px; background: #eee; border-radius: 99px; overflow: hidden;
  }}
  .progress-fill {{
    height: 100%; border-radius: 99px;
    background: {status_color}; width: {pct}%;
  }}

  /* INTEGRIDADE */
  .integrity-summary {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 2rem;
  }}
  .integrity-row {{ display: flex; gap: 1.5rem; flex-wrap: wrap; }}
  .integrity-item {{
    display: flex; align-items: center; gap: 6px; font-size: 0.82rem;
  }}
  .integrity-dot {{ width: 10px; height: 10px; border-radius: 50%; }}

  /* FLOWS */
  .section-title {{
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 1rem;
  }}
  .flow-card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; margin-bottom: 1.25rem; overflow: hidden;
  }}
  .flow-header {{
    display: flex; align-items: center; gap: 10px;
    padding: 0.9rem 1.25rem; flex-wrap: wrap;
  }}
  .flow-name {{ font-weight: 600; font-size: 0.95rem; flex: 1; }}
  .flow-steps, .flow-duration {{
    font-size: 0.78rem; color: var(--muted); font-family: var(--mono);
  }}
  .steps-container {{ padding: 0.75rem 1rem; display: flex; flex-direction: column; gap: 8px; }}

  /* STEPS */
  .step {{ border-radius: 6px; padding: 0.6rem 0.9rem; }}
  .step-header {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
  .step-id {{ font-family: var(--mono); font-weight: 600; font-size: 0.8rem; min-width: 48px; }}
  .step-time {{ font-family: var(--mono); font-size: 0.78rem; color: var(--muted); min-width: 60px; }}
  .step-ts {{ font-size: 0.72rem; color: var(--muted); margin-left: auto; }}
  .step-error {{
    margin-top: 6px; font-size: 0.76rem; color: var(--red);
    font-family: var(--mono); line-height: 1.5;
    background: #fff0f0; padding: 6px 8px; border-radius: 4px; word-break: break-word;
  }}

  /* OCR LIDO — valor lido pelo EasyOCR no verify_fill / verify_lov */
  .step-ocr-lido {{
    display: inline-flex; align-items: center; gap: 6px;
    margin-top: 5px; font-size: 0.76rem;
  }}
  .ocr-label {{ color: var(--muted); white-space: nowrap; }}
  .ocr-valor {{
    font-family: var(--mono); font-weight: 600; color: #1D9E75;
    background: #E1F5EE; padding: 1px 8px; border-radius: 4px;
    border: 1px solid #a8e6cf; letter-spacing: 0.03em;
  }}

  /* SCORE DE CONFIANÇA (Fase 1) */
  .step-score {{
    display: flex; align-items: center; gap: 8px;
    margin-top: 6px; font-size: 0.76rem;
  }}
  .score-label-txt {{ color: var(--muted); white-space: nowrap; }}
  .score-bar {{
    display: inline-block; width: 80px; height: 6px;
    background: #eee; border-radius: 99px; overflow: hidden; vertical-align: middle;
  }}
  .score-fill {{ display: block; height: 100%; border-radius: 99px; }}
  .score-label {{ font-family: var(--mono); font-size: 0.76rem; font-weight: 600; }}
  .score-tpl {{ font-family: var(--mono); font-size: 0.7rem; color: var(--muted); word-break: break-all; }}

  /* SCREENSHOT */
  .step-screenshot {{ margin-top: 8px; }}
  .step-screenshot img {{
    max-width: 100%; max-height: 220px; border-radius: 6px;
    border: 1px solid var(--border); cursor: zoom-in;
  }}
  .img-hint {{ display: block; font-size: 0.7rem; color: var(--muted); margin-top: 3px; }}

  /* SÉRIE TEMPORAL — últimas N execuções */
  .step-serie {{
    display: inline-flex; align-items: center; gap: 2px;
    margin-left: 4px; padding: 2px 6px;
    background: #f5f4f0; border-radius: 99px;
    border: 1px solid var(--border);
  }}

  /* LIGHTBOX */
  .lightbox {{
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.85); z-index: 1000;
    align-items: center; justify-content: center; cursor: zoom-out;
  }}
  .lightbox.open {{ display: flex; }}
  .lightbox img {{
    max-width: 92vw; max-height: 92vh;
    border-radius: 8px; box-shadow: 0 20px 60px rgba(0,0,0,.5);
  }}

  /* BADGES */
  .badge {{
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.04em;
    padding: 2px 8px; border-radius: 99px; white-space: nowrap;
  }}
  .badge-validado {{ background: #E1F5EE; color: #1D9E75; border: 1px solid #a8e6cf; }}
  .badge-sem-validacao {{
    background: #fff3e0; color: #b45309; border: 1px solid #f59e0b;
    animation: pulse-badge 2s ease-in-out infinite;
  }}
  .badge-integridade {{
    background: #FFF3CD; color: #856404; border: 1px solid #ffc107;
    animation: pulse-badge 1.5s ease-in-out infinite;
  }}
  @keyframes pulse-badge {{ 0%,100%{{opacity:1}} 50%{{opacity:0.6}} }}

  /* FOOTER */
  .footer {{
    margin-top: 3rem; text-align: center;
    font-size: 0.72rem; color: var(--muted); font-family: var(--mono);
  }}
</style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <div class="header">
    <div class="header-left">
      <h1>VTAE — {test_name.replace("_", " ").title()}</h1>
      <p>{started} &nbsp;·&nbsp; {round(duration, 1)}s &nbsp;·&nbsp; id: {exec_id}</p>
    </div>
    <div class="status-badge" style="background:{status_bg};color:{status_color};">
      {status_icon} {status}
    </div>
  </div>

  <!-- ALERTAS -->
  {alertas_html}

  <!-- METRICS -->
  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Steps totais</div>
      <div class="metric-value" style="color:var(--text);">{total}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Passaram</div>
      <div class="metric-value" style="color:var(--green);">{passed}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Falharam</div>
      <div class="metric-value" style="color:{'var(--red)' if failed > 0 else 'var(--muted)'};">{failed}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Duração</div>
      <div class="metric-value" style="color:var(--text);">{round(duration, 1)}s</div>
    </div>
  </div>

  <!-- INTEGRIDADE -->
  <div class="integrity-summary">
    <div class="section-title">Integridade dos steps</div>
    <div class="integrity-row">
      <div class="integrity-item">
        <span class="integrity-dot" style="background:#1D9E75;"></span>
        <strong>{validated_count}</strong>&nbsp;validados
      </div>
      <div class="integrity-item">
        <span class="integrity-dot" style="background:#9b9590;"></span>
        <strong>{sem_validacao}</strong>&nbsp;sem validação
      </div>
      <div class="integrity-item">
        <span class="integrity-dot" style="background:#ffc107;"></span>
        <strong>{falha_integridade}</strong>&nbsp;falha de integridade
      </div>
    </div>
  </div>

  <!-- PROGRESS -->
  <div class="progress-wrap">
    <div class="progress-label">
      <span>Taxa de sucesso</span>
      <span>{pct}%</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill"></div>
    </div>
  </div>

  <!-- FLOWS -->
  <div class="section-title">Detalhamento por flow</div>
  {flows_html}

  <div class="footer">
    VTAE &nbsp;·&nbsp; {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} &nbsp;·&nbsp; execution_id: {data.get("execution_id", "")}
  </div>

</div>

<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img" src="" alt="screenshot ampliado" />
</div>

<script>
  function openImg(el) {{
    document.getElementById('lightbox-img').src = el.src;
    document.getElementById('lightbox').classList.add('open');
  }}
  function closeLightbox() {{
    document.getElementById('lightbox').classList.remove('open');
  }}
  document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeLightbox(); }});
</script>
</body>
</html>"""