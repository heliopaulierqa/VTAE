# src/core/summary_generator.py
"""
Summary Generator — Onda 2
Relatorio gerencial HTML para gestores.

Diferenca vs report.html (tecnico):
  - Sem stack trace, sem coordenadas, sem ruido tecnico
  - Resultado por jornada: PASSOU / FALHOU + duracao + data
  - Steps com nome legivel (usa StepResult.description — novo v0.5.10)
  - Indicador visual de cobertura de validacao (% validated=True)
  - Pode ser gerado a qualquer momento SEM rodar testes:
      python -m src.core.summary_generator
      vtae summary --date 2026-05-30
      vtae summary --jornada internacao

Leitura:
  Varre evidence/<data>/**/execution.json
  Agrupa por jornada (nome do test_name)
  Gera evidence/<data>/summary/summary_<data>.html

Uso programatico:
    from src.core.summary_generator import SummaryGenerator
    html = SummaryGenerator.gerar(date_str="2026-05-30")
    html = SummaryGenerator.gerar()  # hoje
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime
from pathlib import Path


# ─── Mapeamento de nomes tecnicos para nomes gerenciais ──────────────────────
# Adicionar novos testes aqui conforme forem criados
_NOME_GERENCIAL = {
    "test_cadastro_paciente_jornada":              "Cadastro de Paciente",
    "test_cadastro_paciente_ambulatorio_jornada":  "Cadastro de Paciente",
    "test_cadastro_paciente_internacao_jornada":   "Cadastro de Paciente",
    "test_admissao_ambulatorio_jornada":           "Admissão Ambulatório",
    "test_agendamento_jornada":                    "Agendamento",
    "test_admissao_com_agendamento_jornada":       "Admissão com Agendamento",
    "test_admissao_internacao_jornada":            "Admissão Internação",
    "test_cadastro_funcionario_sislab":            "Cadastro Funcionário (SisLab)",
    "test_frequencia_aplicacao":                   "Frequência de Aplicação",
    "test_tipo_anestesia":                         "Tipo de Anestesia",
    "test_login_real":                             "Login SI3",
}

_NOME_JORNADA = {
    "ambulatorio":               "Jornada Ambulatório",
    "ambulatorio_com_agendamento": "Jornada Ambulatório com Agendamento",
    "internacao":                "Jornada Internação",
    "sislab":                    "SisLab",
    "msi3":                      "MSI3",
}


class SummaryGenerator:
    """
    Gera relatorio HTML gerencial a partir dos execution.json existentes.
    Nao precisa rodar testes — trabalha sobre evidencias ja geradas.
    """

    # ----------------------------------------------------------------
    # API publica
    # ----------------------------------------------------------------

    @staticmethod
    def gerar(
        date_str: str | None = None,
        evidence_dir: str = "evidence",
        jornada_filtro: str | None = None,
    ) -> str:
        """
        Gera summary HTML para uma data.

        Args:
            date_str:      Data no formato YYYY-MM-DD. Default: hoje.
            evidence_dir:  Pasta raiz de evidencias. Default: evidence/
            jornada_filtro: Se informado, filtra apenas testes da jornada.

        Returns:
            Caminho do HTML gerado.

        Raises:
            FileNotFoundError: Se nenhum execution.json for encontrado.
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        pattern = os.path.join(evidence_dir, date_str, "**", "execution.json")
        json_paths = sorted(glob.glob(pattern, recursive=True))

        if not json_paths:
            raise FileNotFoundError(
                f"Nenhum execution.json encontrado em {evidence_dir}/{date_str}/\n"
                f"Execute pelo menos um teste primeiro:\n"
                f"  vtae run --jornada internacao"
            )

        execucoes = []
        for path in json_paths:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                # filtra por jornada se solicitado
                if jornada_filtro:
                    nome = data.get("test_name", "")
                    if jornada_filtro.lower() not in nome.lower():
                        continue
                execucoes.append(data)
            except Exception as e:
                print(f"[SummaryGenerator] AVISO: erro ao ler {path}: {e}")
                continue

        if not execucoes:
            raise FileNotFoundError(
                f"Nenhuma execucao encontrada para o filtro '{jornada_filtro}' "
                f"em {date_str}."
            )

        out_dir = Path(evidence_dir) / date_str / "summary"
        out_dir.mkdir(parents=True, exist_ok=True)

        suffix = f"_{jornada_filtro}" if jornada_filtro else ""
        out_path = out_dir / f"summary_{date_str}{suffix}.html"

        html = SummaryGenerator._renderizar(execucoes, date_str)
        out_path.write_text(html, encoding="utf-8")

        print(f"[SummaryGenerator] Relatorio gerencial: {out_path}")
        return str(out_path)

    @staticmethod
    def gerar_de_lista(
        json_paths: list[str],
        output_path: str,
        titulo: str = "VTAE",
        ambiente: str = "dev",
    ) -> str:
        """
        Compatibilidade com src/cli/summary.py existente.
        Aceita lista de caminhos e gera HTML no output_path indicado.
        """
        execucoes = []
        for path in json_paths:
            try:
                with open(path, encoding="utf-8") as f:
                    execucoes.append(json.load(f))
            except Exception:
                continue

        date_str = datetime.now().strftime("%Y-%m-%d")
        html = SummaryGenerator._renderizar(execucoes, date_str, titulo=titulo)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(html, encoding="utf-8")
        return output_path

    # ----------------------------------------------------------------
    # Renderizacao HTML
    # ----------------------------------------------------------------

    @staticmethod
    def _renderizar(
        execucoes: list[dict],
        date_str: str,
        titulo: str = "VTAE",
    ) -> str:
        total     = len(execucoes)
        passou    = sum(1 for e in execucoes if e.get("status") == "PASSOU")
        falhou    = total - passou
        duracao_t = sum(e.get("duration_seconds", 0) for e in execucoes)

        # calcula cobertura de validacao global
        total_steps     = 0
        validated_steps = 0
        for e in execucoes:
            for flow in e.get("flows", []):
                for step in flow.get("steps", []):
                    total_steps += 1
                    if step.get("validated") is True:
                        validated_steps += 1

        cobertura_pct = (
            round(validated_steps / total_steps * 100) if total_steps else 0
        )

        cards_html = ""
        for e in execucoes:
            cards_html += SummaryGenerator._card_execucao(e)

        hora_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

        # cor do badge de cobertura
        if cobertura_pct >= 80:
            cob_cor = "#1D9E75"
        elif cobertura_pct >= 50:
            cob_cor = "#EF9F27"
        else:
            cob_cor = "#E24B4A"

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VTAE — Relatório Gerencial {date_str}</title>
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
  .stat .num {{ font-size: 28px; font-weight: 600; }}
  .stat .lbl {{ font-size: 11px; color: #888; margin-top: 2px; text-transform: uppercase;
                letter-spacing: 0.05em; }}
  .num-pass {{ color: #1D9E75; }}
  .num-fail {{ color: #E24B4A; }}
  .num-dur  {{ color: #2E75B6; }}
  .section {{ padding: 0 40px 32px; }}
  .section-title {{ font-size: 12px; font-weight: 500; color: #888;
                    text-transform: uppercase; letter-spacing: 0.08em;
                    margin-bottom: 12px; }}
  .card {{ background: white; border-radius: 10px; margin-bottom: 12px;
           box-shadow: 0 1px 4px rgba(0,0,0,0.07); overflow: hidden; }}
  .card-header {{ display: flex; align-items: center; padding: 14px 20px;
                  gap: 12px; cursor: pointer; }}
  .card-header:hover {{ background: #F8FAFC; }}
  .badge {{ font-size: 11px; font-weight: 600; padding: 3px 10px;
            border-radius: 12px; white-space: nowrap; }}
  .badge-pass {{ background: #E1F5EE; color: #0F6E56; }}
  .badge-fail {{ background: #FCE4E4; color: #A32D2D; }}
  .card-title {{ font-size: 14px; font-weight: 500; flex: 1; }}
  .card-meta {{ font-size: 12px; color: #999; }}
  .card-body {{ border-top: 1px solid #F0F0F0; padding: 12px 20px; }}
  .step-list {{ list-style: none; }}
  .step-item {{ display: flex; align-items: flex-start; gap: 8px;
                padding: 5px 0; border-bottom: 1px solid #F8F8F8;
                font-size: 12px; }}
  .step-item:last-child {{ border-bottom: none; }}
  .step-icon {{ width: 16px; text-align: center; flex-shrink: 0; margin-top: 1px; }}
  .step-id {{ font-weight: 600; color: #444; min-width: 40px; }}
  .step-desc {{ color: #555; flex: 1; }}
  .step-dur {{ color: #AAA; white-space: nowrap; }}
  .step-val {{ font-size: 10px; padding: 1px 6px; border-radius: 8px;
               background: #E1F5EE; color: #0F6E56; white-space: nowrap; }}
  .step-err {{ color: #C0392B; font-size: 11px; margin-top: 2px;
               padding: 4px 8px; background: #FFF5F5; border-radius: 4px;
               border-left: 3px solid #E24B4A; }}
  .step-fail-row {{ flex-direction: column; }}
  .cob-badge {{ display: inline-flex; align-items: center; gap: 6px;
                padding: 4px 12px; border-radius: 20px; font-size: 12px;
                font-weight: 500; background: #F0F0F0; }}
  .footer {{ text-align: center; padding: 24px; font-size: 11px; color: #AAA; }}
  details > summary {{ list-style: none; }}
  details > summary::-webkit-details-marker {{ display: none; }}
</style>
</head>
<body>

<div class="header">
  <h1>VTAE — Relatório Gerencial</h1>
  <div class="sub">InCor · Automação de Testes · {date_str} · Gerado em {hora_geracao}</div>
</div>

<div class="stats">
  <div class="stat">
    <div class="num">{total}</div>
    <div class="lbl">Testes executados</div>
  </div>
  <div class="stat">
    <div class="num num-pass">{passou}</div>
    <div class="lbl">Passaram</div>
  </div>
  <div class="stat">
    <div class="num num-fail">{falhou}</div>
    <div class="lbl">Falharam</div>
  </div>
  <div class="stat">
    <div class="num num-dur">{duracao_t:.0f}s</div>
    <div class="lbl">Tempo total</div>
  </div>
  <div class="stat">
    <div class="num" style="color:{cob_cor}">{cobertura_pct}%</div>
    <div class="lbl">Cobertura validação</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Resultados por teste</div>
  {cards_html}
</div>

<div class="footer">
  VTAE v0.5.10 · InCor — Automação de Testes · {hora_geracao}
</div>

</body>
</html>"""

    @staticmethod
    def _card_execucao(e: dict) -> str:
        test_name  = e.get("test_name", "desconhecido")
        status     = e.get("status", "?")
        duracao    = e.get("duration_seconds", 0)
        started    = e.get("started_at", "")[:16].replace("T", " ")
        ambiente   = e.get("ambiente", {})
        hostname   = ambiente.get("hostname", "")

        nome_leg  = _NOME_GERENCIAL.get(test_name, test_name.replace("_", " ").title())
        badge_cls = "badge-pass" if status == "PASSOU" else "badge-fail"
        badge_txt = "✓ PASSOU" if status == "PASSOU" else "✗ FALHOU"
        icone_h   = "✓" if status == "PASSOU" else "✗"
        cor_h     = "#1D9E75" if status == "PASSOU" else "#E24B4A"

        # steps
        steps_html = ""
        total_steps = 0
        val_steps   = 0
        falha_desc  = ""

        for flow in e.get("flows", []):
            for step in flow.get("steps", []):
                total_steps += 1
                sid   = step.get("step_id", "?")
                desc  = step.get("description", "")
                dur   = step.get("duration_ms", 0)
                ok    = step.get("success", False)
                val   = step.get("validated")
                err   = step.get("error", "")

                if val is True:
                    val_steps += 1

                icone   = "✓" if ok else "✗"
                cor_ico = "#1D9E75" if ok else "#E24B4A"
                val_tag = '<span class="step-val">✓ validado</span>' if val else ""

                # nome legivel: "AB01 — clicar em Admitir Paciente"
                nome_step = f"{sid}"
                if desc:
                    nome_step = f"{sid} — {desc}"

                dur_fmt = f"{dur/1000:.1f}s" if dur >= 1000 else f"{dur:.0f}ms"

                if ok:
                    steps_html += f"""
                    <li class="step-item">
                      <span class="step-icon" style="color:{cor_ico}">{icone}</span>
                      <span class="step-desc">{nome_step}</span>
                      {val_tag}
                      <span class="step-dur">{dur_fmt}</span>
                    </li>"""
                else:
                    # step com falha — mostra erro simplificado (sem stack trace)
                    err_curto = err.split("\n")[0][:120] if err else "erro desconhecido"
                    falha_desc = f"Falhou em: {nome_step}"
                    steps_html += f"""
                    <li class="step-item step-fail-row">
                      <div style="display:flex;align-items:center;gap:8px">
                        <span class="step-icon" style="color:{cor_ico}">{icone}</span>
                        <span class="step-desc" style="color:#C0392B;font-weight:500">{nome_step}</span>
                        <span class="step-dur">{dur_fmt}</span>
                      </div>
                      <div class="step-err">{err_curto}</div>
                    </li>"""

        # cobertura de validacao deste teste
        cob_pct  = round(val_steps / total_steps * 100) if total_steps else 0
        cob_cor2 = "#1D9E75" if cob_pct >= 80 else ("#EF9F27" if cob_pct >= 50 else "#E24B4A")

        # resumo curto para gestor — sem ruido tecnico
        resumo = f"{total_steps} steps em {duracao:.0f}s"
        if hostname:
            resumo += f" · {hostname}"
        if falha_desc and status != "PASSOU":
            resumo += f" · {falha_desc}"

        return f"""
<div class="card">
  <details>
    <summary>
      <div class="card-header">
        <span style="font-size:16px;color:{cor_h}">{icone_h}</span>
        <span class="card-title">{nome_leg}</span>
        <span class="badge {badge_cls}">{badge_txt}</span>
        <span class="card-meta">{started} · {resumo}</span>
        <span class="cob-badge" style="color:{cob_cor2}">
          {cob_pct}% validado
        </span>
      </div>
    </summary>
    <div class="card-body">
      <ul class="step-list">
        {steps_html}
      </ul>
    </div>
  </details>
</div>"""