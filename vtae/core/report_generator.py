"""
VTAE Report Generator
Gera relatório HTML profissional a partir do execution.json.
É chamado automaticamente pelo ExecutionObserver ao final de cada execução.
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


def _build_html(data: dict) -> str:
    status = data.get("status", "?")
    test_name = data.get("test_name", "Execução")
    started = data.get("started_at", "")[:19].replace("T", " ")
    duration = data.get("duration_seconds", 0)
    summary = data.get("summary", {})
    flows = data.get("flows", [])

    status_color = "#1D9E75" if status == "PASSOU" else "#E24B4A"
    status_bg = "#E1F5EE" if status == "PASSOU" else "#FCEBEB"
    status_icon = "✅" if status == "PASSOU" else "❌"

    total = summary.get("total_steps", 0)
    passed = summary.get("passed_steps", 0)
    failed = summary.get("failed_steps", 0)
    pct = round((passed / total * 100) if total > 0 else 0)

    flows_html = ""
    for flow in flows:
        flow_ok = flow.get("success", False)
        flow_color = "#1D9E75" if flow_ok else "#E24B4A"
        flow_bg = "#E1F5EE" if flow_ok else "#FCEBEB"
        flow_icon = "✅" if flow_ok else "❌"
        flow_ms = round(flow.get("total_duration_ms", 0))

        steps_html = ""
        for step in flow.get("steps", []):
            s_ok = step.get("success", False)
            s_color = "#1D9E75" if s_ok else "#E24B4A"
            s_bg = "#f8fffe" if s_ok else "#fff8f8"
            s_icon = "✅" if s_ok else "❌"
            s_id = step.get("step_id", "")
            s_ms = round(step.get("duration_ms", 0))
            s_err = step.get("error") or ""
            s_ts = step.get("timestamp", "")[:19].replace("T", " ")
            s_img = _img_to_base64(step.get("screenshot"))

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
            <div class="step" style="border-left: 3px solid {s_color}; background: {s_bg};">
                <div class="step-header">
                    <span class="step-icon">{s_icon}</span>
                    <span class="step-id">{s_id}</span>
                    <span class="step-time">{s_ms}ms</span>
                    <span class="step-ts">{s_ts}</span>
                </div>
                {err_html}
                {img_html}
            </div>"""

        flows_html += f"""
        <div class="flow-card">
            <div class="flow-header" style="background: {flow_bg}; border-left: 4px solid {flow_color};">
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
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

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
    --blue: #2563eb;
  }}

  body {{
    font-family: 'DM Sans', sans-serif;
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
  }}
  .header-left p {{
    font-size: 0.85rem; color: var(--muted); margin-top: 4px;
    font-family: 'DM Mono', monospace;
  }}
  .status-badge {{
    padding: 6px 18px; border-radius: 99px;
    font-weight: 600; font-size: 0.9rem; letter-spacing: 0.02em;
  }}

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
    font-size: 0.75rem; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;
  }}
  .metric-value {{
    font-size: 1.8rem; font-weight: 600; letter-spacing: -0.03em;
    font-family: 'DM Mono', monospace;
  }}

  /* PROGRESS BAR */
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
    background: {status_color};
    width: {pct}%;
    transition: width 1s ease;
  }}

  /* FLOWS */
  .section-title {{
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted);
    margin-bottom: 1rem;
  }}
  .flow-card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; margin-bottom: 1.25rem; overflow: hidden;
  }}
  .flow-header {{
    display: flex; align-items: center; gap: 10px;
    padding: 0.9rem 1.25rem; flex-wrap: wrap;
  }}
  .flow-icon {{ font-size: 1rem; }}
  .flow-name {{ font-weight: 600; font-size: 0.95rem; flex: 1; }}
  .flow-steps {{ font-size: 0.8rem; color: var(--muted); font-family: 'DM Mono', monospace; }}
  .flow-duration {{ font-size: 0.8rem; color: var(--muted); font-family: 'DM Mono', monospace; }}

  .steps-container {{ padding: 0.75rem 1rem; display: flex; flex-direction: column; gap: 8px; }}

  .step {{
    border-radius: 6px; padding: 0.6rem 0.9rem;
  }}
  .step-header {{
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  }}
  .step-icon {{ font-size: 0.85rem; }}
  .step-id {{
    font-family: 'DM Mono', monospace; font-weight: 500;
    font-size: 0.8rem; min-width: 48px;
  }}
  .step-time {{
    font-family: 'DM Mono', monospace; font-size: 0.78rem;
    color: var(--muted); min-width: 60px;
  }}
  .step-ts {{ font-size: 0.75rem; color: var(--muted); margin-left: auto; }}
  .step-error {{
    margin-top: 6px; font-size: 0.78rem; color: var(--red);
    font-family: 'DM Mono', monospace; line-height: 1.4;
    background: #fff0f0; padding: 6px 8px; border-radius: 4px;
  }}

  .step-screenshot {{
    margin-top: 8px;
  }}
  .step-screenshot img {{
    max-width: 100%; max-height: 220px; border-radius: 6px;
    border: 1px solid var(--border); cursor: zoom-in;
    transition: opacity .15s;
  }}
  .step-screenshot img:hover {{ opacity: 0.9; }}
  .img-hint {{
    display: block; font-size: 0.7rem; color: var(--muted);
    margin-top: 3px;
  }}

  /* LIGHTBOX */
  .lightbox {{
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.85); z-index: 1000;
    align-items: center; justify-content: center;
    cursor: zoom-out;
  }}
  .lightbox.open {{ display: flex; }}
  .lightbox img {{
    max-width: 92vw; max-height: 92vh;
    border-radius: 8px; box-shadow: 0 20px 60px rgba(0,0,0,.5);
  }}

  /* FOOTER */
  .footer {{
    margin-top: 3rem; text-align: center;
    font-size: 0.75rem; color: var(--muted);
    font-family: 'DM Mono', monospace;
  }}
</style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <div class="header">
    <div class="header-left">
      <h1>VTAE — {test_name.replace("_", " ").title()}</h1>
      <p>Execução iniciada em {started} &nbsp;·&nbsp; {round(duration, 1)}s total</p>
    </div>
    <div class="status-badge" style="background:{status_bg}; color:{status_color};">
      {status_icon} {status}
    </div>
  </div>

  <!-- METRICS -->
  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Steps totais</div>
      <div class="metric-value" style="color: var(--text);">{total}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Passaram</div>
      <div class="metric-value" style="color: var(--green);">{passed}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Falharam</div>
      <div class="metric-value" style="color: {'var(--red)' if failed > 0 else 'var(--muted)'};">{failed}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Duração</div>
      <div class="metric-value" style="color: var(--text);">{round(duration, 1)}s</div>
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
    Gerado automaticamente pelo VTAE &nbsp;·&nbsp;
    {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
  </div>

</div>

<!-- LIGHTBOX -->
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
  document.addEventListener('keydown', e => {{
    if (e.key === 'Escape') closeLightbox();
  }});
</script>
</body>
</html>"""
