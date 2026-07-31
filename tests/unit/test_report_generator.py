"""
Smoke tests do Report Generator — vtae/report/report_generator.py

Estratégia: monta execution.json sintético em memória (dict), sem
depender de execução real de flow. Isola evidence/flakiness.json via
monkeypatch.chdir(tmp_path) — nunca toca no evidence/ real do projeto.
"""

import json

from vtae.report.report_generator import (
    _build_html,
    _img_to_base64,
    _ler_flakiness,
    _score_bar,
    generate,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def step_ok(step_id="L01", ocr_lido="", validated=None):
    return {
        "step_id": step_id,
        "description": "step de teste",
        "success": True,
        "duration_ms": 120.0,
        "screenshot": None,
        "error": None,
        "causa_falha": None,
        "validated": validated,
        "ocr_lido": ocr_lido,
        "timestamp": "2026-07-28T10:00:00",
    }


def step_falhou(step_id="A01", causa="template_nao_encontrado",
                error="Template nao encontrado"):
    return {
        "step_id": step_id,
        "description": "step de teste",
        "success": False,
        "duration_ms": 90.0,
        "screenshot": None,
        "error": error,
        "causa_falha": causa,
        "validated": None,
        "ocr_lido": None,
        "timestamp": "2026-07-28T10:00:01",
    }


def execution_data(status="PASSOU", steps=None):
    steps = steps if steps is not None else [step_ok()]
    return {
        "execution_id": "abc12345-0000-0000-0000-000000000000",
        "test_name": "test_smoke",
        "status": status,
        "started_at": "2026-07-28T10:00:00",
        "duration_seconds": 1.5,
        "summary": {
            "total_steps": len(steps),
            "passed_steps": sum(1 for s in steps if s["success"]),
            "failed_steps": sum(1 for s in steps if not s["success"]),
        },
        "flows": [
            {
                "flow_name": "FlowDeTeste",
                "success": all(s["success"] for s in steps),
                "total_duration_ms": sum(s["duration_ms"] for s in steps),
                "steps": steps,
            }
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# generate() — caso feliz
# ──────────────────────────────────────────────────────────────────────────────

class TestGenerate:

    def test_gera_html_com_status_passou(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = execution_data(status="PASSOU")
        json_path = tmp_path / "execution.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        html_path = generate(str(json_path))

        assert html_path == str(tmp_path / "report.html")
        conteudo = (tmp_path / "report.html").read_text(encoding="utf-8")
        assert "test_smoke" in conteudo.lower() or "Test Smoke" in conteudo
        assert "PASSOU" in conteudo
        assert "✅" in conteudo

    def test_gera_html_com_status_falhou(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = execution_data(status="FALHOU", steps=[step_falhou()])
        json_path = tmp_path / "execution.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        generate(str(json_path))

        conteudo = (tmp_path / "report.html").read_text(encoding="utf-8")
        assert "FALHOU" in conteudo
        assert "❌" in conteudo
        assert "Template nao encontrado" in conteudo

    def test_output_path_customizado(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = execution_data()
        json_path = tmp_path / "execution.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")
        out_path = tmp_path / "custom" / "meu_relatorio.html"
        out_path.parent.mkdir()

        resultado = generate(str(json_path), str(out_path))

        assert resultado == str(out_path)
        assert out_path.exists()


# ──────────────────────────────────────────────────────────────────────────────
# Seção de alertas
# ──────────────────────────────────────────────────────────────────────────────

class TestAlertas:

    def test_alerta_aparece_para_step_que_falhou(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # isola _ler_flakiness (evidence/flakiness.json)
        data = execution_data(status="FALHOU", steps=[step_falhou(step_id="A02")])
        html = _build_html(data)
        assert "Atenção" in html
        assert "A02" in html

    def test_sem_alerta_quando_tudo_passa(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = execution_data(status="PASSOU")
        html = _build_html(data)
        # "alertas-wrap" sempre existe como classe CSS no <style>;
        # o que importa é a div real não ser instanciada.
        assert '<div class="alertas-wrap">' not in html

    def test_alerta_regressao_silenciosa(self, tmp_path, monkeypatch):
        """
        Step passou hoje mas tem >=30% de falha historica em >=3 execucoes
        — regressão silenciosa. Antes deste teste, essa branch (o segundo
        loop de alertas em _build_html) não tinha nenhuma cobertura.
        """
        monkeypatch.chdir(tmp_path)
        (tmp_path / "evidence").mkdir()
        flakiness = {
            "L01": {"pass_count": 2, "fail_count": 1, "last_10_results": [1, 0, 1]}
        }
        (tmp_path / "evidence" / "flakiness.json").write_text(
            json.dumps(flakiness), encoding="utf-8"
        )
        data = execution_data(status="PASSOU", steps=[step_ok(step_id="L01")])
        html = _build_html(data)
        assert "historico" in html or "taxa histórica" in html
        assert "L01" in html


# ──────────────────────────────────────────────────────────────────────────────
# _score_bar — três faixas de cor
# ──────────────────────────────────────────────────────────────────────────────

class TestScoreBar:

    def test_score_alto_e_verde(self):
        assert "#1D9E75" in _score_bar(0.9)

    def test_score_medio_e_laranja(self):
        assert "#f59e0b" in _score_bar(0.6)

    def test_score_baixo_e_vermelho(self):
        assert "#E24B4A" in _score_bar(0.3)

    def test_score_no_limite_075_e_verde(self):
        assert "#1D9E75" in _score_bar(0.75)

    def test_score_no_limite_055_e_laranja(self):
        assert "#f59e0b" in _score_bar(0.55)


# ──────────────────────────────────────────────────────────────────────────────
# Badges de integridade
# ──────────────────────────────────────────────────────────────────────────────

class TestBadges:

    def test_badge_validado(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = execution_data(steps=[step_ok(validated=True)])
        html = _build_html(data)
        assert "VALIDADO" in html

    def test_badge_sem_validacao(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = execution_data(steps=[step_ok(validated=None)])
        html = _build_html(data)
        assert "sem validação" in html

    def test_badge_falha_integridade(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        step = step_falhou(error="falha de observabilidade no verify_fill")
        data = execution_data(status="FALHOU", steps=[step])
        html = _build_html(data)
        assert "FALHA DE INTEGRIDADE" in html


# ──────────────────────────────────────────────────────────────────────────────
# OCR lido
# ──────────────────────────────────────────────────────────────────────────────

class TestOcrLido:

    def test_ocr_lido_aparece_quando_validado(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = execution_data(steps=[step_ok(validated=True, ocr_lido="6016")])
        html = _build_html(data)
        assert "OCR leu" in html
        assert "6016" in html

    def test_ocr_lido_nao_aparece_sem_validacao(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = execution_data(steps=[step_ok(validated=None, ocr_lido="6016")])
        html = _build_html(data)
        assert "OCR leu" not in html


# ──────────────────────────────────────────────────────────────────────────────
# _ler_flakiness
# ──────────────────────────────────────────────────────────────────────────────

class TestLerFlakiness:

    def test_retorna_vazio_quando_arquivo_ausente(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert _ler_flakiness() == {}

    def test_le_json_valido(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "evidence").mkdir()
        conteudo = {"L01": {"pass_count": 5, "fail_count": 1}}
        (tmp_path / "evidence" / "flakiness.json").write_text(
            json.dumps(conteudo), encoding="utf-8"
        )
        assert _ler_flakiness() == conteudo

    def test_retorna_vazio_quando_json_corrompido(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "evidence").mkdir()
        (tmp_path / "evidence" / "flakiness.json").write_text(
            "{isso nao e json valido", encoding="utf-8"
        )
        assert _ler_flakiness() == {}


# ──────────────────────────────────────────────────────────────────────────────
# _img_to_base64
# ──────────────────────────────────────────────────────────────────────────────

class TestImgToBase64:

    def test_retorna_none_quando_path_vazio(self):
        assert _img_to_base64("") is None
        assert _img_to_base64(None) is None

    def test_retorna_none_quando_arquivo_nao_existe(self):
        assert _img_to_base64("nao/existe/screenshot.png") is None

    def test_retorna_data_uri_quando_arquivo_existe(self, tmp_path):
        img_path = tmp_path / "fake.png"
        img_path.write_bytes(b"conteudo-fake-nao-precisa-ser-png-valido")
        resultado = _img_to_base64(str(img_path))
        assert resultado.startswith("data:image/png;base64,")
