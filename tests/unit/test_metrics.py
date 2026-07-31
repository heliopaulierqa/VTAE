"""
Smoke tests do MetricsAnalyzer — vtae/report/metrics.py

Estratégia: todos os métodos são offline (leem flakiness.json/execution.json
do disco). Usa tmp_path para isolar — nunca toca no evidence/ real do
projeto. flakiness_path e evidence_dir são parametrizáveis, então não
precisa de monkeypatch.chdir.
"""

import json

from vtae.report.metrics import MetricsAnalyzer


def _escrever_flakiness(tmp_path, dados):
    path = tmp_path / "flakiness.json"
    path.write_text(json.dumps(dados), encoding="utf-8")
    return str(path)


def _escrever_execution(tmp_path, date_str, teste, data):
    out_dir = tmp_path / date_str / teste
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "execution.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _step(step_id="L01", success=True, validated=True, description="step"):
    return {
        "step_id": step_id,
        "success": success,
        "validated": validated,
        "description": description,
    }


class TestAnalisar:

    def test_retorna_erro_quando_flakiness_ausente(self, tmp_path):
        rel = MetricsAnalyzer.analisar(flakiness_path=str(tmp_path / "nao_existe.json"))
        assert "erro" in rel

    def test_step_estavel_nao_entra_em_criticos(self, tmp_path):
        path = _escrever_flakiness(tmp_path, {
            "L01": {"pass_count": 10, "fail_count": 0, "avg_duration_ms": 100, "max_duration_ms": 150},
        })
        rel = MetricsAnalyzer.analisar(flakiness_path=path, threshold=30)
        assert rel["steps_criticos"] == []
        assert rel["steps_estaveis"] == 1

    def test_step_acima_do_threshold_gera_alerta(self, tmp_path):
        path = _escrever_flakiness(tmp_path, {
            "A01": {"pass_count": 5, "fail_count": 5, "avg_duration_ms": 80, "max_duration_ms": 120,
                    "description": "clicar em Admitir", "last_causa_falha": "timeout"},
        })
        rel = MetricsAnalyzer.analisar(flakiness_path=path, threshold=30)
        assert len(rel["steps_criticos"]) == 1
        assert rel["steps_criticos"][0]["step_id"] == "A01"
        assert rel["steps_criticos"][0]["taxa_falha_pct"] == 50.0
        assert len(rel["alertas"]) == 1
        assert "A01" in rel["alertas"][0]

    def test_step_flaky_falhou_e_passou(self, tmp_path):
        path = _escrever_flakiness(tmp_path, {
            "A01": {"pass_count": 3, "fail_count": 1, "avg_duration_ms": 50, "max_duration_ms": 60},
        })
        rel = MetricsAnalyzer.analisar(flakiness_path=path)
        assert len(rel["steps_flaky"]) == 1

    def test_step_com_total_zero_e_ignorado(self, tmp_path):
        path = _escrever_flakiness(tmp_path, {
            "L01": {"pass_count": 0, "fail_count": 0},
        })
        rel = MetricsAnalyzer.analisar(flakiness_path=path)
        assert rel["total_steps"] == 1
        assert rel["steps_criticos"] == []
        assert rel["steps_flaky"] == []

    def test_top_limita_resultado(self, tmp_path):
        dados = {
            f"S{i}": {"pass_count": 0, "fail_count": 5, "avg_duration_ms": 10, "max_duration_ms": 10}
            for i in range(5)
        }
        path = _escrever_flakiness(tmp_path, dados)
        rel = MetricsAnalyzer.analisar(flakiness_path=path, threshold=10, top=2)
        assert len(rel["steps_criticos"]) == 2


class TestAlertas:

    def test_retorna_lista_vazia_sem_criticos(self, tmp_path):
        path = _escrever_flakiness(tmp_path, {
            "L01": {"pass_count": 10, "fail_count": 0, "avg_duration_ms": 10, "max_duration_ms": 10},
        })
        assert MetricsAnalyzer.alertas(flakiness_path=path) == []

    def test_retorna_mensagens_quando_ha_criticos(self, tmp_path):
        path = _escrever_flakiness(tmp_path, {
            "A01": {"pass_count": 0, "fail_count": 5, "avg_duration_ms": 10, "max_duration_ms": 10},
        })
        alertas = MetricsAnalyzer.alertas(threshold=10, flakiness_path=path)
        assert len(alertas) == 1


class TestCoberturaValidacao:

    def test_sem_execucoes_retorna_zero(self, tmp_path):
        cob = MetricsAnalyzer.cobertura_validacao(date_str="2026-07-28", evidence_dir=str(tmp_path))
        assert cob["total_steps"] == 0
        assert cob["cobertura_pct"] == 0

    def test_calcula_cobertura_a_partir_de_execution_json(self, tmp_path):
        _escrever_execution(tmp_path, "2026-07-28", "teste1", {
            "test_name": "teste1",
            "flows": [{
                "flow_name": "LoginFlow",
                "steps": [
                    _step("L01", success=True, validated=True),
                    _step("L02", success=True, validated=False),
                ],
            }],
        })
        cob = MetricsAnalyzer.cobertura_validacao(date_str="2026-07-28", evidence_dir=str(tmp_path))
        assert cob["total_steps"] == 2
        assert cob["validated_steps"] == 1
        assert cob["cobertura_pct"] == 50
        assert cob["por_flow"]["LoginFlow"]["total"] == 2
        assert len(cob["steps_sem_validacao"]) == 1

    def test_step_com_falha_e_ignorado_na_cobertura(self, tmp_path):
        _escrever_execution(tmp_path, "2026-07-28", "teste1", {
            "test_name": "teste1",
            "flows": [{
                "flow_name": "LoginFlow",
                "steps": [_step("L01", success=False, validated=False)],
            }],
        })
        cob = MetricsAnalyzer.cobertura_validacao(date_str="2026-07-28", evidence_dir=str(tmp_path))
        assert cob["total_steps"] == 0

    def test_json_corrompido_e_ignorado_sem_lancar(self, tmp_path):
        out_dir = tmp_path / "2026-07-28" / "teste1"
        out_dir.mkdir(parents=True)
        (out_dir / "execution.json").write_text("{nao e json valido", encoding="utf-8")
        cob = MetricsAnalyzer.cobertura_validacao(date_str="2026-07-28", evidence_dir=str(tmp_path))
        assert cob["total_steps"] == 0


class TestGerarDashboard:

    def test_gera_arquivo_html(self, tmp_path):
        flak_path = _escrever_flakiness(tmp_path, {
            "L01": {"pass_count": 10, "fail_count": 0, "avg_duration_ms": 10, "max_duration_ms": 10},
        })
        out = MetricsAnalyzer.gerar_dashboard(
            date_str="2026-07-28",
            evidence_dir=str(tmp_path),
            flakiness_path=flak_path,
        )
        assert (tmp_path / "2026-07-28" / "summary" / "metrics_2026-07-28.html").exists()
        assert out.endswith("metrics_2026-07-28.html")
