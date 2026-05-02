"""
VTAE Summary Report Generator
Gera relatório HTML unificado agregando múltiplos execution.json.
Chamado automaticamente pela CLI ao final de vtae run --all ou --module.
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


def generate_summary(json_paths: list[str],
                     output_path: str,
                     titulo: str = "Execução Completa",
                     ambiente: str = "dev") -> str:
    """
    Gera relatório HTML unificado a partir de múltiplos execution.json.

    Args:
        json_paths: lista de caminhos para execution.json de cada teste
        output_path: caminho de saída do summary.html
        titulo: título do relatório
        ambiente: ambiente de execução (dev, homologacao, producao)

    Returns:
        Caminho do arquivo HTML gerado.
    """
    execucoes = []
    for path in json_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    execucoes.append(json.load(f))
            except Exception:
                pass

    if not execucoes:
        return ""

    html = _build_summary_html(execucoes, titulo, ambiente)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _build_summary_html(execucoes: list[dict],
                         titulo: str,
                         ambiente: str) -> str:
    """Constrói o HTML do relatório unificado."""

    # ── métricas globais ──────────────────────────────────────────────────────
    total_testes  = len(execucoes)
    testes_ok     = sum(1 for e in execucoes if e.get("status") == "PASSOU")
    testes_falhou = total_testes - testes_ok

    total_steps  = sum(e.get("summary", {}).get("total_steps", 0) for e in execucoes)
    passed_steps = sum(e.get("summary", {}).get("passed_steps", 0) for e in execucoes)
    failed_steps = total_steps - passed_steps
    duracao_total = sum(e.get("duration_seconds", 0) for e in execucoes)

    pct = round((passed_steps / total_steps * 100) if total_steps > 0 else 0)
    status_global = "PASSOU" if testes_falhou == 0 else "FALHOU"
    status_color  = "#1D9E75" if status_global == "PASSOU" else "#E24B4A"
    status_bg     = "#E1F5EE" if status_global == "PASSOU" else "#FCEBEB"
    status_icon   = "✅" if status_global == "PASSOU" else "❌"

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # ── tabela de resumo ──────────────────────────────────────────────────────
    rows_html = ""
    for e in execucoes:
        e_status = e.get("status", "?")
        e_color  = "#1D9E75" if e_status == "PASSOU" else "#E24B4A"
        e_bg     = "#E1F5EE" if e_status == "PASSOU" else "#FCEBEB"
        e_icon   = "✅" if e_status == "PASSOU" else "❌"
        e_name   = e.get("test_name", "").replace("_", " ").title()
        e_total  = e.get("summary", {}).get("total_steps", 0)
        e_passed = e.get("summary", {}).get("passed_steps", 0)
        e_dur    = round(e.get("duration_seconds", 0), 1)
        e_report = e.get("report_path", "")

        link = ""
        if e_report and os.path.exists(e_report):
            rel = os.path.relpath(e_report, os.path.dirname(e_report))
            link = f'<a href="{e_report}" target="_blank" style="font-size:0.75rem;color:#2563eb;">ver detalhes →</a>'

        rows_html += f"""
        <tr>
            <td>
                <span class="badge" style="background:{e_bg};color:{e_color};">
                    {e_icon} {e_status}
                </span>
            </td>
            <td style="font-weight:500;">{e_name}</td>
            <td style="font-family:'DM Mono',monospace;font-size:0.85rem;">
                {e_passed}/{e_total}
            </td>
            <td style="font-family:'DM Mono',monospace;font-size:0.85rem;">{e_dur}s</td>
            <td>{link}</td>
        </tr>"""

    # ── detalhes dos flows com erros ──────────────────────────────────────────
    erros_html = ""
    for e in execucoes:
        if e.get("status") == "PASSOU":
            continue
        e_name = e.get("test_name", "").replace("_", " ").title()
        for flow in e.get("flows", []):
            if flow.get("success"):
                continue
            for step in flow.get("steps", []):
                if step.get("success"):
                    continue
                s_id  = step.get("step_id", "")
                s_err = step.get("error", "")
                s_img = _img_to_base64(step.get("screenshot"))

                img_html = ""
                if s_img:
                    img_html = f"""
                    <div style="margin-top:8px;">
                        <img src="{s_img}" style="max-width:100%;max-height:200px;
                             border-radius:6px;border:1px solid #e2e0db;cursor:zoom-in;"
                             onclick="openImg(this)" />
                    </div>"""

                erros_html += f"""
                <div class="error-card">
                    <div class="error-header">
                        <span style="font-weight:600;">{e_name}</span>
                        <span style="font-family:'DM Mono',monospace;font-size:0.8rem;
                              background:#fff0f0;color:#E24B4A;padding:2px 8px;
                              border-radius:99px;">
                            {flow.get("flow_name","")} › {s_id}
                        </span>
                    </div>
                    <div class="error-msg">{s_err}</div>
                    {img_html}
                </div>"""

    erros_section = ""
    if erros_html:
        erros_section = f"""
        <div class="section-title" style="margin-top:2rem;">Erros encontrados</div>
        {erros_html}"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VTAE — {titulo}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #f4f3f0; --card: #ffffff; --border: #e2e0db;
    --text: #1a1a1a; --muted: #6b6966;
    --green: #1D9E75; --green-bg: #E1F5EE;
    --red: #E24B4A; --red-bg: #FCEBEB;
  }}
  body {{
    font-family: 'DM Sans', sans-serif;
    background: var(--bg); color: var(--text);
    min-height: 100vh; padding: 2rem 1rem;
  }}
  .container {{ max-width: 960px; margin: 0 auto; }}

  .header {{
    display: flex; align-items: flex-start;
    justify-content: space-between; flex-wrap: wrap;
    gap: 1rem; margin-bottom: 2rem;
  }}
  .header-left h1 {{
    font-size: 1.6rem; font-weight: 600; letter-spacing: -0.03em;
  }}
  .header-left p {{
    font-size: 0.85rem; color: var(--muted); margin-top: 4px;
    font-family: 'DM Mono', monospace;
  }}
  .status-badge {{
    padding: 6px 18px; border-radius: 99px;
    font-weight: 600; font-size: 0.9rem;
  }}

  .metrics {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
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
    font-size: 1.7rem; font-weight: 600;
    font-family: 'DM Mono', monospace;
  }}

  .progress-wrap {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 2rem;
  }}
  .progress-label {{
    display: flex; justify-content: space-between;
    font-size: 0.8rem; color: var(--muted); margin-bottom: 8px;
  }}
  .progress-bar {{
    height: 8px; background: #eee;
    border-radius: 99px; overflow: hidden;
  }}
  .progress-fill {{
    height: 100%; border-radius: 99px;
    background: {status_color}; width: {pct}%;
  }}

  .section-title {{
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 1rem;
  }}

  table {{
    width: 100%; border-collapse: collapse;
    background: var(--card); border-radius: 10px;
    overflow: hidden; border: 1px solid var(--border);
    margin-bottom: 2rem;
  }}
  th {{
    text-align: left; padding: 10px 16px;
    font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--muted); background: #fafaf8;
    border-bottom: 1px solid var(--border);
  }}
  td {{
    padding: 12px 16px; border-bottom: 1px solid #f0eeea;
    font-size: 0.88rem; vertical-align: middle;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #fafaf8; }}

  .badge {{
    padding: 3px 10px; border-radius: 99px;
    font-size: 0.78rem; font-weight: 600;
  }}

  .error-card {{
    background: var(--card); border: 1px solid var(--border);
    border-left: 4px solid var(--red);
    border-radius: 10px; padding: 1rem 1.25rem;
    margin-bottom: 1rem;
  }}
  .error-header {{
    display: flex; align-items: center;
    gap: 10px; flex-wrap: wrap; margin-bottom: 8px;
  }}
  .error-msg {{
    font-family: 'DM Mono', monospace; font-size: 0.78rem;
    color: var(--red); background: #fff0f0;
    padding: 8px 10px; border-radius: 4px;
    white-space: pre-wrap; line-height: 1.5;
  }}

  .lightbox {{
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.85); z-index: 1000;
    align-items: center; justify-content: center;
    cursor: zoom-out;
  }}
  .lightbox.open {{ display: flex; }}
  .lightbox img {{
    max-width: 92vw; max-height: 92vh;
    border-radius: 8px;
  }}

  .footer {{
    margin-top: 3rem; text-align: center;
    font-size: 0.75rem; color: var(--muted);
    font-family: 'DM Mono', monospace;
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="header-left">
      <h1>VTAE — {titulo.replace("_", " ").title()}</h1>
      <p>Ambiente: {ambiente} &nbsp;·&nbsp; Gerado em {agora}</p>
    </div>
    <div class="status-badge" style="background:{status_bg};color:{status_color};">
      {status_icon} {status_global}
    </div>
  </div>

  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Testes</div>
      <div class="metric-value" style="color:var(--text);">{total_testes}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Passaram</div>
      <div class="metric-value" style="color:var(--green);">{testes_ok}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Falharam</div>
      <div class="metric-value" style="color:{'var(--red)' if testes_falhou > 0 else 'var(--muted)'};">{testes_falhou}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Steps OK</div>
      <div class="metric-value" style="color:var(--green);">{passed_steps}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Duração</div>
      <div class="metric-value" style="color:var(--text);">{round(duracao_total, 1)}s</div>
    </div>
  </div>

  <div class="progress-wrap">
    <div class="progress-label">
      <span>Taxa de sucesso dos steps</span>
      <span>{pct}%</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill"></div>
    </div>
  </div>

  <div class="section-title">Resultados por teste</div>
  <table>
    <thead>
      <tr>
        <th>Status</th>
        <th>Teste</th>
        <th>Steps</th>
        <th>Duração</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  {erros_section}

  <div class="footer">
    VTAE — Visual Test Automation Engine &nbsp;·&nbsp;
    Ambiente: {ambiente} &nbsp;·&nbsp; {agora}
  </div>

</div>

<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img" src="" alt="screenshot" />
</div>

<script>
  function openImg(el) {{
    document.getElementById('lightbox-img').src = el.src;
    document.getElementById('lightbox').classList.add('open');
  }}
  function closeLightbox() {{
    document.getElementById('lightbox').classList.remove('open');
  }}
  document.addEventListener('keydown', e => {{
    if (e.key === 'Escape') closeLightbox();
  }});
</script>
</body>
</html>"""
