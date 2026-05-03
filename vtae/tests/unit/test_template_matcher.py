"""
Testes unitários do TemplateMatcher — src/vision/template.py

Estratégia: mocka _match_multiscale e _match_single diretamente
para controle total sobre scores — sem depender do OpenCV real.
"""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
import cv2

from src.vision.template import TemplateMatcher, MatchResult, DiagnosticReport
from src.core.types import TemplateNotFoundError


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def tmpl_fake(w=40, h=20):
    return np.zeros((h, w, 3), dtype=np.uint8)

def screen_fake(w=400, h=300):
    return np.zeros((h, w, 3), dtype=np.uint8)

def match_encontrou(x=100, y=80, score=0.95, scale=1.0, adj="none"):
    """MatchResult positivo."""
    return MatchResult(x=x, y=y, score=score, scale=scale, adjustment=adj)

def match_nao_encontrou():
    """Simula ausência de match."""
    return None

def make_matcher(confidence=0.8, scales=(1.0,), use_adj=False):
    m = TemplateMatcher(confidence=confidence, scales=scales,
                        use_adjustments=use_adj)
    m._capture_screen = lambda: screen_fake()
    m._load_template  = lambda p: tmpl_fake()
    return m


# ──────────────────────────────────────────────────────────────────────────────
# find_or_none
# ──────────────────────────────────────────────────────────────────────────────

class TestFindOrNone:

    def test_retorna_coordenadas_quando_encontra(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale',
                          return_value=match_encontrou(100, 80)):
            result = m.find_or_none("qualquer.png")
        assert result == (100, 80)

    def test_retorna_none_quando_ausente(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale', return_value=None):
            result = m.find_or_none("qualquer.png")
        assert result is None

    def test_nao_lanca_excecao_quando_ausente(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale', return_value=None):
            result = m.find_or_none("qualquer.png")
        assert result is None  # sem exceção


# ──────────────────────────────────────────────────────────────────────────────
# find
# ──────────────────────────────────────────────────────────────────────────────

class TestFind:

    def test_retorna_coordenadas_quando_encontra(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale',
                          return_value=match_encontrou(200, 150)):
            cx, cy = m.find("qualquer.png")
        assert cx == 200
        assert cy == 150

    def test_lanca_template_not_found_quando_ausente(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale', return_value=None):
            with pytest.raises(TemplateNotFoundError):
                m.find("qualquer.png")

    def test_lanca_file_not_found_arquivo_inexistente(self):
        m = TemplateMatcher()
        m._capture_screen = lambda: screen_fake()
        with pytest.raises(FileNotFoundError):
            m.find("nao_existe/arquivo.png")

    def test_mensagem_erro_contem_diagnostico(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale', return_value=None):
            with pytest.raises(TemplateNotFoundError) as exc_info:
                m.find("meu_btn.png")
        assert "score=" in str(exc_info.value)


# ──────────────────────────────────────────────────────────────────────────────
# find_best
# ──────────────────────────────────────────────────────────────────────────────

class TestFindBest:

    def test_retorna_match_result_quando_encontra(self):
        m = make_matcher()
        esperado = match_encontrou(100, 80, score=0.95, scale=1.0)
        with patch.object(m, '_try_multiscale', return_value=esperado):
            result = m.find_best("qualquer.png")
        assert isinstance(result, MatchResult)
        assert result.score == 0.95
        assert result.scale == 1.0
        assert result.adjustment == "none"

    def test_retorna_none_quando_ausente(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale', return_value=None):
            assert m.find_best("qualquer.png") is None

    def test_match_result_tem_todos_os_campos(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale',
                          return_value=match_encontrou()):
            result = m.find_best("qualquer.png")
        for attr in ('x', 'y', 'score', 'scale', 'adjustment'):
            assert hasattr(result, attr)

    def test_find_best_score_retorna_float(self):
        m = make_matcher()
        with patch.object(m, '_match_single', return_value=(0.73, (0, 0))):
            score = m.find_best_score("qualquer.png")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_find_best_score_valor_correto(self):
        m = make_matcher()
        with patch.object(m, '_match_single', return_value=(0.82, (10, 10))):
            score = m.find_best_score("qualquer.png")
        assert abs(score - 0.82) < 0.01


# ──────────────────────────────────────────────────────────────────────────────
# Multi-scale (F2-A)
# ──────────────────────────────────────────────────────────────────────────────

class TestMultiScale:

    def test_testa_multiplas_escalas(self):
        """Verifica que _match_single é chamado para cada escala."""
        m = make_matcher(scales=(1.0, 0.9, 1.1), use_adj=False)
        calls = []

        def fake_match(screen, tmpl, scale):
            calls.append(scale)
            return (0.5, (0, 0))  # score abaixo do threshold

        with patch.object(m, '_match_single', side_effect=fake_match):
            m.find_best("qualquer.png")

        assert 1.0 in calls
        assert 0.9 in calls
        assert 1.1 in calls

    def test_para_cedo_com_score_alto_em_1x(self):
        """Score >= 0.9 em escala 1.0 deve parar sem testar outras escalas."""
        m = make_matcher(confidence=0.8, scales=(1.0, 0.9, 1.1), use_adj=False)
        calls = []

        def fake_match(screen, tmpl, scale):
            calls.append(scale)
            if scale == 1.0:
                return (0.95, (50, 50))  # score alto → para cedo
            return (0.5, (0, 0))

        with patch.object(m, '_match_single', side_effect=fake_match):
            result = m.find_best("qualquer.png")

        assert result is not None
        assert result.scale == 1.0
        assert 0.9 not in calls   # não testou outras escalas

    def test_continua_escalas_quando_score_baixo(self):
        """Score baixo em 1.0 deve continuar testando outras escalas."""
        m = make_matcher(confidence=0.8, scales=(1.0, 0.9), use_adj=False)
        calls = []

        def fake_match(screen, tmpl, scale):
            calls.append(scale)
            return (0.5, (0, 0))  # sempre abaixo do threshold

        with patch.object(m, '_match_single', side_effect=fake_match):
            m.find_best("qualquer.png")

        assert 1.0 in calls
        assert 0.9 in calls

    def test_threshold_override_por_parametro(self):
        """Threshold no parâmetro sobrescreve o confidence da instância."""
        m = make_matcher(confidence=0.99, use_adj=False)

        # com threshold padrão alto (0.99) → não encontra (score=0.85)
        with patch.object(m, '_try_multiscale', return_value=None) as mock:
            result1 = m.find_or_none("qualquer.png")
        assert result1 is None

        # com override baixo (0.5) → encontra
        with patch.object(m, '_try_multiscale',
                          return_value=match_encontrou()) as mock:
            result2 = m.find_or_none("qualquer.png", threshold=0.5)
        assert result2 is not None


# ──────────────────────────────────────────────────────────────────────────────
# is_visible
# ──────────────────────────────────────────────────────────────────────────────

class TestIsVisible:

    def test_retorna_true_quando_presente(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale',
                          return_value=match_encontrou()):
            assert m.is_visible("qualquer.png") is True

    def test_retorna_false_quando_ausente(self):
        m = make_matcher()
        with patch.object(m, '_try_multiscale', return_value=None):
            assert m.is_visible("qualquer.png") is False


# ──────────────────────────────────────────────────────────────────────────────
# find_all
# ──────────────────────────────────────────────────────────────────────────────

class TestFindAll:

    def test_encontra_multiplas_ocorrencias(self):
        """Mocka matchTemplate no módulo correto — 3 pontos conhecidos."""
        m = make_matcher()

        result_matrix = np.zeros((80, 260), dtype=np.float32)
        result_matrix[20, 30]  = 1.0
        result_matrix[20, 130] = 1.0
        result_matrix[20, 230] = 1.0

        with patch('src.vision.template.cv2.matchTemplate',
                   return_value=result_matrix):
            results = m.find_all("qualquer.png", threshold=0.99)

        assert len(results) == 3

    def test_retorna_lista_vazia_quando_ausente(self):
        """Sem pontos acima do threshold, retorna lista vazia."""
        m = make_matcher()

        result_matrix = np.zeros((80, 260), dtype=np.float32)

        with patch('src.vision.template.cv2.matchTemplate',
                   return_value=result_matrix):
            results = m.find_all("qualquer.png", threshold=0.99)

        assert results == []


# ──────────────────────────────────────────────────────────────────────────────
# find_anchor (F2-C)
# ──────────────────────────────────────────────────────────────────────────────

class TestFindAnchor:

    def test_retorna_posicao_com_offset(self):
        m = make_matcher()
        with patch.object(m, 'find', return_value=(120, 110)):
            ax, ay = m.find_anchor("qualquer.png", offset_x=200, offset_y=0)
        assert ax == 320
        assert ay == 110

    def test_offset_zero_retorna_centro(self):
        m = make_matcher()
        with patch.object(m, 'find', return_value=(150, 100)):
            ax, ay = m.find_anchor("qualquer.png", offset_x=0, offset_y=0)
        assert ax == 150
        assert ay == 100

    def test_offset_negativo(self):
        m = make_matcher()
        with patch.object(m, 'find', return_value=(200, 200)):
            ax, ay = m.find_anchor("qualquer.png", offset_x=-50, offset_y=-30)
        assert ax == 150
        assert ay == 170

    def test_lanca_erro_quando_ancora_ausente(self):
        m = make_matcher()
        with patch.object(m, 'find',
                          side_effect=TemplateNotFoundError("não encontrado")):
            with pytest.raises(TemplateNotFoundError):
                m.find_anchor("qualquer.png", offset_x=100)


# ──────────────────────────────────────────────────────────────────────────────
# DiagnosticReport (F2-B)
# ──────────────────────────────────────────────────────────────────────────────

class TestDiagnosticReport:

    def test_diagnose_retorna_report(self):
        m = make_matcher(use_adj=True)
        with patch.object(m, '_match_single', return_value=(0.65, (0, 0))):
            report = m.diagnose("qualquer.png")
        assert isinstance(report, DiagnosticReport)
        assert report.threshold == 0.8
        assert len(report.attempts) >= 1

    def test_diagnose_sem_heuristicas_tem_uma_tentativa(self):
        m = make_matcher(use_adj=False)
        with patch.object(m, '_match_single', return_value=(0.5, (0, 0))):
            report = m.diagnose("qualquer.png")
        assert len(report.attempts) == 1
        assert report.attempts[0][0] == "original (multi-scale)"

    def test_diagnose_com_heuristicas_tem_cinco_tentativas(self):
        m = make_matcher(use_adj=True)
        with patch.object(m, '_match_single', return_value=(0.5, (0, 0))):
            report = m.diagnose("qualquer.png")
        # original + contrast + brightness + equalize + gray = 5
        assert len(report.attempts) == 5

    def test_summary_contem_scores(self):
        m = make_matcher(use_adj=False)
        with patch.object(m, '_match_single', return_value=(0.63, (0, 0))):
            report = m.diagnose("qualquer.png")
        summary = report.summary()
        assert "score=" in summary
        assert "0.63" in summary

    def test_template_not_found_inclui_diagnostico(self):
        m = make_matcher(use_adj=False)
        # mocka find_best para retornar None E _match_single para score conhecido
        with patch.object(m, 'find_best', return_value=None), \
             patch.object(m, '_match_single', return_value=(0.63, (0, 0))):
            with pytest.raises(TemplateNotFoundError) as exc_info:
                m.find("qualquer.png")
        assert "score=" in str(exc_info.value)


# ──────────────────────────────────────────────────────────────────────────────
# MatchResult
# ──────────────────────────────────────────────────────────────────────────────

class TestMatchResult:

    def test_str_sem_adjustment(self):
        r = MatchResult(x=100, y=200, score=0.923, scale=1.0, adjustment="none")
        s = str(r)
        assert "0.923" in s
        assert "1.00" in s
        assert "adj=" not in s   # adjustment "none" não aparece

    def test_str_com_adjustment(self):
        r = MatchResult(x=100, y=200, score=0.812, scale=1.1, adjustment="contrast")
        s = str(r)
        assert "0.812" in s
        assert "1.10" in s
        assert "contrast" in s

    def test_campos_corretos(self):
        r = MatchResult(x=50, y=60, score=0.9, scale=0.9)
        assert r.x == 50
        assert r.y == 60
        assert r.score == 0.9
        assert r.scale == 0.9
        assert r.adjustment == "none"


# ──────────────────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_template_maior_que_tela_retorna_none(self):
        """_match_single retorna (0.0, (0,0)) quando template > tela."""
        m = make_matcher(use_adj=False)
        tmpl_grande  = np.zeros((400, 500, 3), dtype=np.uint8)
        tela_pequena = np.zeros((100, 200, 3), dtype=np.uint8)
        score, _ = m._match_single(tela_pequena, tmpl_grande, 1.0)
        assert score == 0.0

    def test_threshold_alto_nao_encontra(self):
        """Score mockado abaixo do threshold alto → não encontra."""
        m = make_matcher(confidence=0.99, use_adj=False)
        with patch.object(m, '_match_single', return_value=(0.5, (0, 0))):
            assert m.find_or_none("qualquer.png") is None

    def test_threshold_baixo_encontra(self):
        """Score mockado acima do threshold baixo → encontra."""
        m = make_matcher(confidence=0.5, use_adj=False)
        with patch.object(m, '_match_single', return_value=(0.8, (10, 5))):
            result = m.find_or_none("qualquer.png")
        assert result is not None

    def test_confidence_padrao_e_0_8(self):
        m = TemplateMatcher()
        assert m.confidence == 0.8

    def test_scales_padrao(self):
        m = TemplateMatcher()
        assert 1.0 in m.scales
        assert 0.9 in m.scales
        assert 1.1 in m.scales

    def test_use_adjustments_padrao_true(self):
        m = TemplateMatcher()
        assert m.use_adjustments is True
