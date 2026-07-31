"""
Smoke tests do SummaryGenerator — vtae/report/summary_generator.py

Estratégia: monta execution.json sintético em tmp_path (evidence_dir e
date_str são parametrizáveis nos métodos públicos) — nunca toca no
evidence/ real do projeto.
"""

import json

import pytest

from vtae.report.summary_generator import SummaryGenerator


def _execution(test_name="test_smoke", status="PASSOU", steps=None, duration=12.5):
    steps = steps if steps is not None else [
        {"step_id": "L01", "description": "login", "duration_ms": 100.0,
         "success": True, "validated": True, "error": None},
    ]
    return {
        "test_name": test_name,
        "status": status,
        "duration_seconds": duration,
        "started_at": "2026-07-28T10:00:00",
        "ambiente": {"hostname": "host-teste"},
        "flows": [{"flow_name": "LoginFlow", "steps": steps}],
    }


def _escrever_execution(tmp_path, date_str, teste, data):
    out_dir = tmp_path / date_str / teste
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "execution.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestGerar:

    def test_lanca_filenotfound_quando_nenhuma_execucao(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            SummaryGenerator.gerar(date_str="2026-07-28", evidence_dir=str(tmp_path))

    def test_gera_html_com_execucao_unica(self, tmp_path):
        _escrever_execution(tmp_path, "2026-07-28", "teste1", _execution())

        out_path = SummaryGenerator.gerar(date_str="2026-07-28", evidence_dir=str(tmp_path))

        assert out_path.endswith("summary_2026-07-28.html")
        html = open(out_path, encoding="utf-8").read()
        assert "Cadastro de Paciente" not in html  # nome nao mapeado, usa fallback
        assert "PASSOU" in html

    def test_filtro_por_jornada(self, tmp_path):
        _escrever_execution(tmp_path, "2026-07-28", "internacao", _execution(test_name="test_admissao_internacao_jornada"))
        _escrever_execution(tmp_path, "2026-07-28", "ambulatorio", _execution(test_name="test_agendamento_jornada"))

        out_path = SummaryGenerator.gerar(
            date_str="2026-07-28", evidence_dir=str(tmp_path), jornada_filtro="internacao",
        )
        html = open(out_path, encoding="utf-8").read()
        assert "Admissão Internação" in html
        assert "Agendamento" not in html

    def test_filtro_sem_match_lanca_filenotfound(self, tmp_path):
        _escrever_execution(tmp_path, "2026-07-28", "teste1", _execution())
        with pytest.raises(FileNotFoundError):
            SummaryGenerator.gerar(
                date_str="2026-07-28", evidence_dir=str(tmp_path), jornada_filtro="nao_existe",
            )

    def test_json_corrompido_e_pulado_sem_lancar(self, tmp_path):
        out_dir = tmp_path / "2026-07-28" / "corrompido"
        out_dir.mkdir(parents=True)
        (out_dir / "execution.json").write_text("{invalido", encoding="utf-8")
        _escrever_execution(tmp_path, "2026-07-28", "teste_ok", _execution())

        out_path = SummaryGenerator.gerar(date_str="2026-07-28", evidence_dir=str(tmp_path))
        assert out_path  # nao lancou, gerou com o execution.json valido


class TestGerarDeLista:

    def test_gera_html_a_partir_de_lista_de_paths(self, tmp_path):
        path1 = _escrever_execution(tmp_path, "2026-07-28", "teste1", _execution())
        out_path = str(tmp_path / "saida.html")

        resultado = SummaryGenerator.gerar_de_lista([str(path1)], out_path)

        assert resultado == out_path
        assert (tmp_path / "saida.html").exists()

    def test_ignora_paths_invalidos(self, tmp_path):
        out_path = str(tmp_path / "saida.html")
        resultado = SummaryGenerator.gerar_de_lista(
            [str(tmp_path / "nao_existe.json")], out_path,
        )
        html = open(resultado, encoding="utf-8").read()
        assert "0" in html  # zero testes executados, nao lancou excecao


class TestRenderizar:

    def test_calcula_cobertura_global_e_contadores(self):
        execucoes = [_execution(status="PASSOU"), _execution(status="FALHOU")]
        html = SummaryGenerator._renderizar(execucoes, date_str="2026-07-28")
        assert "PASSOU" in html
        assert "FALHOU" in html

    def test_step_com_falha_mostra_mensagem_de_erro(self):
        steps = [{
            "step_id": "A01", "description": "clicar em Admitir",
            "duration_ms": 500.0, "success": False, "validated": None,
            "error": "Template nao encontrado\nstack trace irrelevante",
        }]
        execucao = _execution(status="FALHOU", steps=steps)
        html = SummaryGenerator._card_execucao(execucao)
        assert "Template nao encontrado" in html
        assert "stack trace irrelevante" not in html  # so a primeira linha do erro
