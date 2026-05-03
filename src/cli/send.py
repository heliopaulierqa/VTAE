"""
VTAE — vtae send
Envia o relatório HTML de uma execução por e-mail.

Uso manual:
    vtae send --module sislab --to gestor@incor.org.br
    vtae send --module sislab --to a@x.com --to b@x.com
    vtae send --all --to equipe@incor.org.br
    vtae send --module sislab --date 2026-05-03 --to fulano@incor.org.br

Automático (quando configurado no config.yaml):
    Chamado ao final de qualquer vtae run se houver
    notificacoes.email.destinatarios_padrao definido.

Configuração no config.yaml:
    notificacoes:
      email:
        destinatarios_padrao:
          - gestor@incor.org.br
        assunto: "VTAE — {status} | {modulo} | {data}"
        somente_em_falha: false

Credenciais SMTP no .env da raiz do projeto:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=vtae@gmail.com
    SMTP_PASS=sua_senha_app

    Para Gmail use App Password (não a senha da conta):
    https://myaccount.google.com/apppasswords
"""

import os
import smtplib
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────────────
# Loader de .env — carrega antes de qualquer leitura de os.environ
# ──────────────────────────────────────────────────────────────────────────────

def _carregar_env_arquivo(path: Path) -> None:
    """
    Carrega variáveis do arquivo .env para os.environ.
    Só define variáveis que ainda não estão no ambiente —
    variáveis do sistema têm prioridade.
    """
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


def _garantir_env_carregado() -> None:
    """
    Garante que o .env da raiz do projeto esteja carregado.
    Tenta os caminhos mais comuns.
    """
    # raiz do projeto (onde o usuário executa o vtae)
    _carregar_env_arquivo(Path(".env"))
    # fallback — um nível acima se estiver dentro de uma subpasta
    _carregar_env_arquivo(Path("../.env"))


# ──────────────────────────────────────────────────────────────────────────────
# SMTPConfig
# ──────────────────────────────────────────────────────────────────────────────

class SMTPConfig:
    """
    Carrega configuração SMTP do .env ou de variáveis de ambiente.

    Suporte:
        Gmail        — smtp.gmail.com:587 (TLS)
        Outlook      — smtp.office365.com:587
        SMTP próprio — qualquer host/porta

    Para Gmail, use App Password (não a senha da conta):
        https://myaccount.google.com/apppasswords
    """

    def __init__(self):
        # garante que .env esteja carregado antes de ler as variáveis
        _garantir_env_carregado()

        self.host  = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.port  = int(os.environ.get("SMTP_PORT", "587"))
        self.user  = os.environ.get("SMTP_USER", "")
        self.senha = os.environ.get("SMTP_PASS", "")
        self.ssl   = os.environ.get("SMTP_SSL", "false").lower() == "true"

    def validar(self) -> list[str]:
        """Retorna lista de erros de validação (vazia = ok)."""
        erros = []
        if not self.host:
            erros.append("SMTP_HOST não definido")
        if not self.user:
            erros.append("SMTP_USER não definido")
        if not self.senha:
            erros.append("SMTP_PASS não definido")
        return erros

    @property
    def configurado(self) -> bool:
        return len(self.validar()) == 0


# ──────────────────────────────────────────────────────────────────────────────
# EmailSender
# ──────────────────────────────────────────────────────────────────────────────

class EmailSender:
    """Envia e-mails com relatório VTAE anexado."""

    def __init__(self, smtp: SMTPConfig = None):
        self.smtp = smtp or SMTPConfig()

    def enviar(self,
               destinatarios: list[str],
               assunto: str,
               corpo_html: str,
               anexo_path: str = None) -> bool:
        """
        Envia e-mail com corpo HTML e anexo opcional.

        Returns:
            True se enviado com sucesso, False caso contrário.
        """
        erros = self.smtp.validar()
        if erros:
            print(f"[vtae send] ❌ SMTP não configurado:")
            for e in erros:
                print(f"  • {e}")
            print("  Defina as variáveis no .env na raiz do projeto:")
            print("    SMTP_HOST=smtp.gmail.com")
            print("    SMTP_PORT=587")
            print("    SMTP_USER=seu@email.com")
            print("    SMTP_PASS=sua_app_password")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"]    = self.smtp.user
        msg["To"]      = ", ".join(destinatarios)

        msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        # anexo do relatório HTML
        if anexo_path and Path(anexo_path).exists():
            with open(anexo_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            nome_arquivo = Path(anexo_path).name
            part.add_header("Content-Disposition",
                            f"attachment; filename={nome_arquivo}")
            msg.attach(part)

        try:
            if self.smtp.ssl:
                with smtplib.SMTP_SSL(self.smtp.host, self.smtp.port) as server:
                    server.login(self.smtp.user, self.smtp.senha)
                    server.sendmail(self.smtp.user, destinatarios, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp.host, self.smtp.port) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(self.smtp.user, self.smtp.senha)
                    server.sendmail(self.smtp.user, destinatarios, msg.as_string())
            return True

        except smtplib.SMTPAuthenticationError:
            print("[vtae send] ❌ Falha de autenticação SMTP.")
            print("  Para Gmail: use App Password, não a senha da conta.")
            print("  https://myaccount.google.com/apppasswords")
            return False

        except smtplib.SMTPException as e:
            print(f"[vtae send] ❌ Erro SMTP: {e}")
            return False

        except Exception as e:
            print(f"[vtae send] ❌ Erro inesperado: {e}")
            return False


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de conteúdo
# ──────────────────────────────────────────────────────────────────────────────

def _carregar_json(json_path: str) -> dict:
    """Lê um execution.json e retorna o dict."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _montar_assunto(template: str, modulo: str,
                    status: str, data: str) -> str:
    """Substitui variáveis no template de assunto."""
    icone = "✅" if status == "PASSOU" else "❌"
    return (template
            .replace("{status}", f"{icone} {status}")
            .replace("{modulo}", modulo.upper())
            .replace("{data}", data))


def _montar_corpo(execucoes: list[dict], modulo: str,
                  ambiente: str, data: str) -> str:
    """Gera corpo HTML do e-mail com métricas resumidas."""

    total_testes  = len(execucoes)
    testes_ok     = sum(1 for e in execucoes if e.get("status") == "PASSOU")
    testes_falhou = total_testes - testes_ok
    total_steps   = sum(e.get("summary", {}).get("total_steps", 0)
                        for e in execucoes)
    passed_steps  = sum(e.get("summary", {}).get("passed_steps", 0)
                        for e in execucoes)
    duracao       = sum(e.get("duration_seconds", 0) for e in execucoes)

    status_global = "PASSOU" if testes_falhou == 0 else "FALHOU"
    cor_status    = "#1D9E75" if status_global == "PASSOU" else "#E24B4A"
    icone         = "✅" if status_global == "PASSOU" else "❌"

    # linhas da tabela por teste
    linhas = ""
    for e in execucoes:
        e_status = e.get("status", "?")
        e_cor    = "#1D9E75" if e_status == "PASSOU" else "#E24B4A"
        e_nome   = e.get("test_name", "").replace("_", " ").title()
        e_ok     = e.get("summary", {}).get("passed_steps", 0)
        e_total  = e.get("summary", {}).get("total_steps", 0)
        e_dur    = f"{round(e.get('duration_seconds', 0), 1)}s"
        linhas += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;">
            <span style="color:{e_cor};font-weight:600;">{e_status}</span>
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;">{e_nome}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;
                     font-family:monospace;">{e_ok}/{e_total}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;
                     font-family:monospace;">{e_dur}</td>
        </tr>"""

    # erros
    erros_html = ""
    for e in execucoes:
        if e.get("status") == "PASSOU":
            continue
        for flow in e.get("flows", []):
            for step in flow.get("steps", []):
                if not step.get("success"):
                    msg_erro = (step.get("error") or "").split("\n")[0]
                    erros_html += f"""
        <div style="background:#fff0f0;border-left:4px solid #E24B4A;
                    padding:10px 14px;margin-bottom:8px;border-radius:4px;">
          <strong style="color:#E24B4A;">
            {flow.get('flow_name','')} › {step.get('step_id','')}
          </strong><br>
          <span style="font-family:monospace;font-size:12px;color:#333;">
            {msg_erro}
          </span>
        </div>"""

    erros_section = ""
    if erros_html:
        erros_section = f"""
      <h3 style="color:#E24B4A;margin:24px 0 12px;">Erros encontrados</h3>
      {erros_html}"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;background:#f4f3f0;
             margin:0;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;
              border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,0.08);">

    <div style="background:{cor_status};padding:24px 28px;">
      <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700;">
        {icone} VTAE — {status_global}
      </h1>
      <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:14px;">
        Módulo: {modulo.upper()} &nbsp;·&nbsp;
        Ambiente: {ambiente} &nbsp;·&nbsp; {data}
      </p>
    </div>

    <div style="display:flex;gap:0;border-bottom:1px solid #eee;">
      <div style="flex:1;padding:16px 20px;text-align:center;
                  border-right:1px solid #eee;">
        <div style="font-size:28px;font-weight:700;color:#1a1a1a;">
          {total_testes}
        </div>
        <div style="font-size:11px;color:#888;text-transform:uppercase;
                    letter-spacing:.05em;">Testes</div>
      </div>
      <div style="flex:1;padding:16px 20px;text-align:center;
                  border-right:1px solid #eee;">
        <div style="font-size:28px;font-weight:700;color:#1D9E75;">
          {testes_ok}
        </div>
        <div style="font-size:11px;color:#888;text-transform:uppercase;
                    letter-spacing:.05em;">Passaram</div>
      </div>
      <div style="flex:1;padding:16px 20px;text-align:center;
                  border-right:1px solid #eee;">
        <div style="font-size:28px;font-weight:700;
                    color:{'#E24B4A' if testes_falhou > 0 else '#aaa'};">
          {testes_falhou}
        </div>
        <div style="font-size:11px;color:#888;text-transform:uppercase;
                    letter-spacing:.05em;">Falharam</div>
      </div>
      <div style="flex:1;padding:16px 20px;text-align:center;">
        <div style="font-size:28px;font-weight:700;color:#1a1a1a;">
          {round(duracao, 1)}s
        </div>
        <div style="font-size:11px;color:#888;text-transform:uppercase;
                    letter-spacing:.05em;">Duração</div>
      </div>
    </div>

    <div style="padding:24px 28px;">
      <h3 style="color:#1a1a1a;margin:0 0 12px;">Resultados por teste</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#f8f8f6;">
            <th style="text-align:left;padding:8px 12px;font-size:11px;
                       text-transform:uppercase;color:#888;">Status</th>
            <th style="text-align:left;padding:8px 12px;font-size:11px;
                       text-transform:uppercase;color:#888;">Teste</th>
            <th style="text-align:left;padding:8px 12px;font-size:11px;
                       text-transform:uppercase;color:#888;">Steps</th>
            <th style="text-align:left;padding:8px 12px;font-size:11px;
                       text-transform:uppercase;color:#888;">Duração</th>
          </tr>
        </thead>
        <tbody>{linhas}</tbody>
      </table>
      {erros_section}
      <p style="font-size:12px;color:#aaa;margin:24px 0 0;text-align:center;">
        Relatório completo em anexo &nbsp;·&nbsp;
        Gerado pelo VTAE &nbsp;·&nbsp; {data}
      </p>
    </div>

  </div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# Função principal
# ──────────────────────────────────────────────────────────────────────────────

def enviar_relatorio(modulo: str,
                     destinatarios: list[str],
                     ambiente: str = "dev",
                     data: str = None,
                     assunto_template: str = "VTAE — {status} | {modulo} | {data}",
                     somente_em_falha: bool = False) -> bool:
    """
    Localiza os execution.json do módulo na data informada,
    monta o e-mail e envia.
    """
    from src.cli.run import MODULOS

    data     = data or datetime.now().strftime("%Y-%m-%d")
    data_fmt = datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")

    if modulo == "all":
        arquivos = [f for files in MODULOS.values() for f in files]
        titulo   = "Execução Completa"
    elif modulo in MODULOS:
        arquivos = MODULOS[modulo]
        titulo   = f"Módulo {modulo.upper()}"
    else:
        print(f"[vtae send] ❌ Módulo '{modulo}' não encontrado.")
        return False

    # localiza os execution.json
    json_paths = []
    for arq in arquivos:
        test_name = Path(arq).stem
        json_path = Path(f"evidence/{data}/{test_name}/execution.json")
        if json_path.exists():
            json_paths.append(str(json_path))

    if not json_paths:
        print(f"[vtae send] ⚠ Nenhum relatório encontrado para '{modulo}' em {data}.")
        print(f"  Esperado em: evidence/{data}/<teste>/execution.json")
        return False

    execucoes     = [_carregar_json(p) for p in json_paths]
    status_global = ("PASSOU" if all(e.get("status") == "PASSOU"
                                     for e in execucoes) else "FALHOU")

    if somente_em_falha and status_global == "PASSOU":
        print("[vtae send] ℹ Skipped — somente_em_falha=true e resultado é PASSOU.")
        return True

    # localiza o anexo
    summary_path = (f"evidence/{data}/summary/"
                    f"{titulo.lower().replace(' ', '_')}_{ambiente}.html")
    if not Path(summary_path).exists() and len(json_paths) == 1:
        test_name    = Path(json_paths[0]).parent.name
        summary_path = f"evidence/{data}/{test_name}/report.html"

    anexo  = summary_path if Path(summary_path).exists() else None
    assunto = _montar_assunto(assunto_template, modulo, status_global, data_fmt)
    corpo   = _montar_corpo(execucoes, modulo, ambiente, data_fmt)
    sender  = EmailSender()

    print(f"[vtae send] Enviando relatório...")
    print(f"  Para   : {', '.join(destinatarios)}")
    print(f"  Assunto: {assunto}")
    if anexo:
        print(f"  Anexo  : {anexo}")

    ok = sender.enviar(destinatarios, assunto, corpo, anexo)

    if ok:
        print(f"[vtae send] ✅ E-mail enviado para "
              f"{len(destinatarios)} destinatário(s).")
    return ok


def enviar_automatico(modulo: str,
                      ambiente: str,
                      sistemas: list[str] = None) -> None:
    """
    Chamado automaticamente ao final do vtae run quando há
    destinatários configurados no config.yaml.
    """
    try:
        import yaml
        from src.cli.run import MODULOS

        sistemas_do_modulo = (sistemas or
                              ([modulo] if modulo != "all"
                               else list(MODULOS.keys())))

        for sistema in sistemas_do_modulo:
            yaml_path = Path(f"vtae/configs/{sistema}/config.yaml")
            if not yaml_path.exists():
                continue

            raw   = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            notif = raw.get("notificacoes", {}).get("email", {})

            destinatarios = notif.get("destinatarios_padrao", [])
            if not destinatarios:
                continue

            enviar_relatorio(
                modulo=modulo,
                destinatarios=destinatarios,
                ambiente=ambiente,
                assunto_template=notif.get(
                    "assunto", "VTAE — {status} | {modulo} | {data}"),
                somente_em_falha=notif.get("somente_em_falha", False),
            )

    except Exception as e:
        print(f"[vtae send] ⚠ Envio automático falhou: {e}")
