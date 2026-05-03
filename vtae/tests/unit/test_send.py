"""
Testes unitários do vtae send — src/cli/send.py

Testa SMTPConfig, montagem de assunto/corpo e envio com mock SMTP.
Sem envio real — smtplib é mockado em todos os testes de envio.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.cli.send import (
    SMTPConfig,
    EmailSender,
    _montar_assunto,
    _montar_corpo,
    enviar_relatorio,
    _carregar_json,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

EXECUTION_JSON_PASSOU = {
    "test_name": "test_cadastro_funcionario_sislab",
    "status": "PASSOU",
    "duration_seconds": 28.5,
    "summary": {
        "total_steps": 13,
        "passed_steps": 13,
        "failed_steps": 0
    },
    "flows": [
        {
            "flow_name": "CadastroFuncionarioFlowSislab",
            "success": True,
            "total_duration_ms": 25000,
            "steps": [
                {"step_id": "CF01", "success": True,
                 "duration_ms": 2500, "error": None,
                 "screenshot": None, "timestamp": "2026-05-03T08:57:21"},
            ]
        }
    ]
}

EXECUTION_JSON_FALHOU = {
    "test_name": "test_cadastro_funcionario_sislab",
    "status": "FALHOU",
    "duration_seconds": 30.2,
    "summary": {
        "total_steps": 13,
        "passed_steps": 11,
        "failed_steps": 2
    },
    "flows": [
        {
            "flow_name": "CadastroFuncionarioFlowSislab",
            "success": False,
            "total_duration_ms": 28000,
            "steps": [
                {"step_id": "CF09", "success": False,
                 "duration_ms": 14000,
                 "error": "Mensagem 'Funcionário salvo com sucesso' não apareceu.",
                 "screenshot": None,
                 "timestamp": "2026-05-03T08:57:34"},
            ]
        }
    ]
}


def criar_execution_json(tmp_path: Path, data: str,
                          test_name: str, conteudo: dict) -> Path:
    """Cria um execution.json de teste."""
    pasta = tmp_path / "evidence" / data / test_name
    pasta.mkdir(parents=True)
    json_path = pasta / "execution.json"
    json_path.write_text(json.dumps(conteudo), encoding="utf-8")
    return json_path


# ──────────────────────────────────────────────────────────────────────────────
# SMTPConfig
# ──────────────────────────────────────────────────────────────────────────────

class TestSMTPConfig:

    def test_defaults(self):
        """Valores padrão quando variáveis não estão definidas."""
        env_limpo = {k: v for k, v in os.environ.items()
                     if k not in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER",
                                   "SMTP_PASS", "SMTP_SSL")}
        with patch.dict(os.environ, env_limpo, clear=True):
            smtp = SMTPConfig()
        assert smtp.host == "smtp.gmail.com"
        assert smtp.port == 587
        assert smtp.ssl  is False

    def test_lê_variaveis_do_ambiente(self):
        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.meuservidor.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "vtae@meuservidor.com",
            "SMTP_PASS": "minha_senha",
            "SMTP_SSL":  "true",
        }):
            smtp = SMTPConfig()

        assert smtp.host  == "smtp.meuservidor.com"
        assert smtp.port  == 465
        assert smtp.user  == "vtae@meuservidor.com"
        assert smtp.senha == "minha_senha"
        assert smtp.ssl   is True

    def test_validar_sem_user(self):
        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_PASS": "senha"
        }):
            # remove SMTP_USER do ambiente
            os.environ.pop("SMTP_USER", None)
            smtp = SMTPConfig()
            smtp.user = ""   # força vazio independente do .env
        erros = smtp.validar()
        assert any("SMTP_USER" in e for e in erros)

    def test_validar_sem_pass(self):
        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_USER": "user@gmail.com",
        }):
            os.environ.pop("SMTP_PASS", None)
            smtp = SMTPConfig()
            smtp.senha = ""   # força vazio independente do .env
        erros = smtp.validar()
        assert any("SMTP_PASS" in e for e in erros)

    def test_validar_completo_ok(self):
        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@gmail.com",
            "SMTP_PASS": "senha",
        }):
            smtp = SMTPConfig()
        assert smtp.validar() == []
        assert smtp.configurado is True

    def test_configurado_false_sem_credenciais(self):
        smtp = SMTPConfig()
        smtp.user  = ""
        smtp.senha = ""
        assert smtp.configurado is False


# ──────────────────────────────────────────────────────────────────────────────
# _montar_assunto
# ──────────────────────────────────────────────────────────────────────────────

class TestMontarAssunto:

    def test_passou(self):
        resultado = _montar_assunto(
            "VTAE — {status} | {modulo} | {data}",
            modulo="sislab", status="PASSOU", data="03/05/2026"
        )
        assert "✅" in resultado
        assert "PASSOU" in resultado
        assert "SISLAB" in resultado
        assert "03/05/2026" in resultado

    def test_falhou(self):
        resultado = _montar_assunto(
            "VTAE — {status} | {modulo} | {data}",
            modulo="sislab", status="FALHOU", data="03/05/2026"
        )
        assert "❌" in resultado
        assert "FALHOU" in resultado

    def test_modulo_em_maiusculas(self):
        resultado = _montar_assunto(
            "{modulo}", modulo="sislab", status="PASSOU", data="hoje"
        )
        assert "SISLAB" in resultado

    def test_template_customizado(self):
        resultado = _montar_assunto(
            "Relatório {modulo} — {data}",
            modulo="msi3", status="PASSOU", data="03/05/2026"
        )
        assert "MSI3" in resultado
        assert "03/05/2026" in resultado


# ──────────────────────────────────────────────────────────────────────────────
# _montar_corpo
# ──────────────────────────────────────────────────────────────────────────────

class TestMontarCorpo:

    def test_retorna_html_valido(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_PASSOU], "sislab", "dev", "03/05/2026"
        )
        assert "<!DOCTYPE html>" in corpo
        assert "<html" in corpo

    def test_contem_status_passou(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_PASSOU], "sislab", "dev", "03/05/2026"
        )
        assert "PASSOU" in corpo

    def test_contem_status_falhou(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_FALHOU], "sislab", "dev", "03/05/2026"
        )
        assert "FALHOU" in corpo

    def test_contem_metricas(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_PASSOU], "sislab", "dev", "03/05/2026"
        )
        assert "13" in corpo   # total steps
        assert "28" in corpo   # duração aproximada

    def test_contem_secao_erros_quando_falha(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_FALHOU], "sislab", "dev", "03/05/2026"
        )
        assert "Erros encontrados" in corpo
        assert "CF09" in corpo

    def test_sem_secao_erros_quando_passa(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_PASSOU], "sislab", "dev", "03/05/2026"
        )
        assert "Erros encontrados" not in corpo

    def test_contem_modulo(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_PASSOU], "sislab", "dev", "03/05/2026"
        )
        assert "SISLAB" in corpo

    def test_contem_ambiente(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_PASSOU], "sislab", "homologacao", "03/05/2026"
        )
        assert "homologacao" in corpo

    def test_multiplos_testes(self):
        corpo = _montar_corpo(
            [EXECUTION_JSON_PASSOU, EXECUTION_JSON_FALHOU],
            "all", "dev", "03/05/2026"
        )
        assert "PASSOU" in corpo
        assert "FALHOU" in corpo


# ──────────────────────────────────────────────────────────────────────────────
# EmailSender.enviar
# ──────────────────────────────────────────────────────────────────────────────

class TestEmailSender:

    def _smtp_configurado(self) -> SMTPConfig:
        smtp = SMTPConfig.__new__(SMTPConfig)
        smtp.host  = "smtp.gmail.com"
        smtp.port  = 587
        smtp.user  = "vtae@gmail.com"
        smtp.senha = "senha_app"
        smtp.ssl   = False
        return smtp

    def test_retorna_false_sem_credenciais(self, capsys):
        smtp = SMTPConfig.__new__(SMTPConfig)
        smtp.host  = "smtp.gmail.com"
        smtp.port  = 587
        smtp.user  = ""
        smtp.senha = ""
        smtp.ssl   = False

        sender = EmailSender(smtp=smtp)
        resultado = sender.enviar(["dest@email.com"], "Assunto", "<p>corpo</p>")

        assert resultado is False
        saida = capsys.readouterr().out
        assert "não configurado" in saida

    def test_envia_com_tls(self):
        smtp = self._smtp_configurado()
        sender = EmailSender(smtp=smtp)

        mock_server = MagicMock()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_server.sendmail = MagicMock()

            resultado = sender.enviar(
                ["dest@email.com"], "Assunto", "<p>corpo</p>"
            )

        assert resultado is True

    def test_envia_com_ssl(self):
        smtp = self._smtp_configurado()
        smtp.ssl = True
        sender = EmailSender(smtp=smtp)

        mock_server = MagicMock()
        with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
            mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_server.sendmail = MagicMock()

            resultado = sender.enviar(
                ["dest@email.com"], "Assunto", "<p>corpo</p>"
            )

        assert resultado is True

    def test_retorna_false_em_auth_error(self, capsys):
        import smtplib
        smtp = self._smtp_configurado()
        sender = EmailSender(smtp=smtp)

        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value.__enter__ = MagicMock(
                side_effect=smtplib.SMTPAuthenticationError(535, b"auth failed")
            )
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

            resultado = sender.enviar(
                ["dest@email.com"], "Assunto", "<p>corpo</p>"
            )

        assert resultado is False
        saida = capsys.readouterr().out
        assert "autenticação" in saida.lower() or "app password" in saida.lower()


# ──────────────────────────────────────────────────────────────────────────────
# enviar_relatorio
# ──────────────────────────────────────────────────────────────────────────────

class TestEnviarRelatorio:

    def test_modulo_invalido(self, capsys):
        resultado = enviar_relatorio(
            modulo="modulo_inexistente",
            destinatarios=["dest@email.com"]
        )
        assert resultado is False
        saida = capsys.readouterr().out
        assert "não encontrado" in saida

    def test_sem_execution_json(self, tmp_path, capsys, monkeypatch):
        """Sem execution.json, deve avisar e retornar False."""
        monkeypatch.chdir(tmp_path)

        resultado = enviar_relatorio(
            modulo="sislab",
            destinatarios=["dest@email.com"],
            data="2026-05-03"
        )

        assert resultado is False
        saida = capsys.readouterr().out
        assert "Nenhum relatório" in saida

    def test_envia_quando_execution_json_existe(self, tmp_path, monkeypatch):
        """Com execution.json presente, deve tentar enviar."""
        monkeypatch.chdir(tmp_path)

        criar_execution_json(
            tmp_path, "2026-05-03",
            "test_cadastro_funcionario_sislab",
            EXECUTION_JSON_PASSOU
        )

        enviados = []

        def mock_enviar(self, dest, assunto, corpo, anexo=None):
            enviados.append({"dest": dest, "assunto": assunto})
            return True

        with patch.object(EmailSender, "enviar", mock_enviar):
            resultado = enviar_relatorio(
                modulo="sislab",
                destinatarios=["dest@email.com"],
                data="2026-05-03"
            )

        assert resultado is True
        assert len(enviados) == 1
        assert "dest@email.com" in enviados[0]["dest"]

    def test_somente_em_falha_nao_envia_quando_passa(self,
                                                      tmp_path, monkeypatch):
        """somente_em_falha=True não deve enviar quando o resultado é PASSOU."""
        monkeypatch.chdir(tmp_path)

        criar_execution_json(
            tmp_path, "2026-05-03",
            "test_cadastro_funcionario_sislab",
            EXECUTION_JSON_PASSOU
        )

        enviados = []

        def mock_enviar(self, dest, assunto, corpo, anexo=None):
            enviados.append(True)
            return True

        with patch.object(EmailSender, "enviar", mock_enviar):
            resultado = enviar_relatorio(
                modulo="sislab",
                destinatarios=["dest@email.com"],
                data="2026-05-03",
                somente_em_falha=True
            )

        assert resultado is True   # True porque skippou (não é erro)
        assert len(enviados) == 0  # não enviou

    def test_somente_em_falha_envia_quando_falha(self, tmp_path, monkeypatch):
        """somente_em_falha=True deve enviar quando o resultado é FALHOU."""
        monkeypatch.chdir(tmp_path)

        criar_execution_json(
            tmp_path, "2026-05-03",
            "test_cadastro_funcionario_sislab",
            EXECUTION_JSON_FALHOU
        )

        enviados = []

        def mock_enviar(self, dest, assunto, corpo, anexo=None):
            enviados.append(True)
            return True

        with patch.object(EmailSender, "enviar", mock_enviar):
            enviar_relatorio(
                modulo="sislab",
                destinatarios=["dest@email.com"],
                data="2026-05-03",
                somente_em_falha=True
            )

        assert len(enviados) == 1  # enviou porque falhou


# ──────────────────────────────────────────────────────────────────────────────
# _carregar_json
# ──────────────────────────────────────────────────────────────────────────────

class TestCarregarJson:

    def test_carrega_json_valido(self, tmp_path):
        json_path = tmp_path / "execution.json"
        json_path.write_text('{"status": "PASSOU"}', encoding="utf-8")
        dados = _carregar_json(str(json_path))
        assert dados["status"] == "PASSOU"

    def test_retorna_dict_vazio_para_arquivo_inexistente(self):
        dados = _carregar_json("/nao/existe/execution.json")
        assert dados == {}

    def test_retorna_dict_vazio_para_json_invalido(self, tmp_path):
        json_path = tmp_path / "execution.json"
        json_path.write_text("{ invalido }", encoding="utf-8")
        dados = _carregar_json(str(json_path))
        assert dados == {}
