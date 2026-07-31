"""
Smoke tests do BaseAdmissaoFlow — vtae/flows/si3/admissao/base_admissao_flow.py

Estrategia: mesma linha de test_base_flow.py. BaseAdmissaoFlow nao tem
__init__ proprio, instanciar direto e seguro. ctx e um SimpleNamespace
com runner (MagicMock) e evidence_dir, unicos atributos que
_assert_tela_limpa le. Cobre o contrato do guard — deteccao de popup,
fechamento automatico (tolerando falha), confirmacao de tela_esperada,
e o loop de retry — nao o comportamento real de tela, que so e
validado no gate visual (vtae run). O guard nao e chamado por nenhum
flow hoje (ver docstring de admissao_ambulatorio_flow.py v0.5.25 —
tentado e abandonado por falso positivo), mas o contrato do metodo e
testado isoladamente, mesmo padrao usado para os outros metodos de
BaseFlow em test_base_flow.py.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vtae.flows.si3.admissao.base_admissao_flow import BaseAdmissaoFlow


def _ctx(**overrides):
    base = SimpleNamespace(
        runner=MagicMock(),
        evidence_dir="evidence/",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


# ----------------------------------------------------------------
# _assert_tela_limpa() — caminho sem popup
# ----------------------------------------------------------------

class TestAssertTelaLimpaSemPopup:

    def test_sem_popup_e_sem_tela_esperada_nao_lanca(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = False
        flow._assert_tela_limpa(ctx, "AB06")  # nao deve levantar

    def test_sem_popup_com_tela_esperada_confirmada_nao_lanca(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        # tentativas=1: uma unica checagem de popup (False), depois a
        # checagem de tela_esperada (True) — 2 chamadas de wait_template no total.
        ctx.runner.wait_template.side_effect = [False, True]
        flow._assert_tela_limpa(
            ctx, "AB06", tela_esperada="templates/tela.png", tentativas=1
        )

    def test_sem_popup_com_tela_esperada_nao_confirmada_lanca(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.side_effect = [False, False]
        with pytest.raises(AssertionError, match="tela esperada nao"):
            flow._assert_tela_limpa(
                ctx, "AB06", tela_esperada="templates/tela.png", tentativas=1
            )


# ----------------------------------------------------------------
# _assert_tela_limpa() — retry da deteccao de popup
# ----------------------------------------------------------------

class TestAssertTelaLimpaRetry:

    def test_detecta_popup_apenas_na_segunda_tentativa(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        # tentativa 1: sem popup / tentativa 2: popup detectado
        ctx.runner.wait_template.side_effect = [False, True]
        with pytest.raises(AssertionError, match="Guard Fail Fast: popup"):
            flow._assert_tela_limpa(ctx, "AB07", tentativas=2, intervalo=0)
        assert ctx.runner.wait_template.call_count == 2

    def test_esgota_tentativas_sem_detectar_popup(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = False
        flow._assert_tela_limpa(ctx, "AB07", tentativas=3, intervalo=0)
        assert ctx.runner.wait_template.call_count == 3


# ----------------------------------------------------------------
# _assert_tela_limpa() — caminho com popup detectado
# ----------------------------------------------------------------

class TestAssertTelaLimpaComPopup:

    def test_popup_detectado_lanca_com_screenshot_e_fechamento(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = True
        ctx.runner.screenshot.return_value = "evidence/AB07_popup_detectado.png"
        ctx.runner.safe_click.return_value = True

        with pytest.raises(AssertionError) as exc_info:
            flow._assert_tela_limpa(ctx, "AB07")

        msg = str(exc_info.value)
        assert "[AB07] Guard Fail Fast: popup 'HC - INCOR' detectado" in msg
        assert "evidence/AB07_popup_detectado.png" in msg
        assert "Fechado automaticamente: True" in msg
        ctx.runner.screenshot.assert_called_once_with(
            "evidence/AB07_popup_detectado.png"
        )
        ctx.runner.safe_click.assert_called_once()

    def test_popup_detectado_fechamento_falha_ainda_assim_lanca(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = True
        ctx.runner.safe_click.side_effect = Exception("botao nao encontrado")

        with pytest.raises(AssertionError) as exc_info:
            flow._assert_tela_limpa(ctx, "AB07")

        assert "Fechado automaticamente: False" in str(exc_info.value)

    def test_popup_detectado_screenshot_falha_e_tolerado(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = True
        ctx.runner.screenshot.side_effect = Exception("sem tela")

        with pytest.raises(AssertionError) as exc_info:
            flow._assert_tela_limpa(ctx, "AB07")

        assert "Screenshot: None" in str(exc_info.value)

    def test_popup_detectado_mensagem_registra_bootstrap_nao_calibrado(self):
        flow = BaseAdmissaoFlow()
        ctx = _ctx()
        ctx.runner.wait_template.return_value = True

        with pytest.raises(AssertionError) as exc_info:
            flow._assert_tela_limpa(ctx, "AB07")

        assert "nao calibrada (bootstrap)" in str(exc_info.value)
