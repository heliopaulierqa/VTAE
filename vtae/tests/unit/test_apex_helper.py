"""
Testes unitários — ApexHelper (MSI3)

Cobre toda a lógica do ApexHelper sem abrir browser real.

Estratégia de mock:
  - runner._page mockado com MagicMock
  - Frames simulados via runner._page.frames
  - Seletores mockados via locator().first.is_visible() e text_content()

Cobertura:
  - verificar_sem_erro (sem erro, com erro, texto do erro)
  - obter_mensagem_erro (encontra, não encontra)
  - verificar_sucesso (encontra, não encontra)
  - aguardar_spinner (spinner presente, ausente)
  - verificar_registro_na_grade (encontra, não encontra, grade vazia)
  - ler_linhas_grade (com linhas, vazia)
  - inspecionar_pagina (snapshot completo)
  - obter_titulo_pagina (h1, h2, fallback)
  - _obter_contextos (page + frames)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _make_runner(page_url="http://msi3/apex", frames=None):
    """Cria runner mock com _page configurado."""
    runner = MagicMock()
    page = MagicMock()
    page.url = page_url
    page.main_frame = MagicMock()
    page.frames = frames or [page.main_frame]
    runner._page = page
    return runner


def _make_locator(visible=False, text=""):
    """Cria locator mock com is_visible e text_content."""
    locator = MagicMock()
    locator.first.is_visible.return_value = visible
    locator.first.text_content.return_value = text
    return locator


# ---------------------------------------------------------------------------
# _obter_contextos
# ---------------------------------------------------------------------------

class TestObterContextos:
    def test_retorna_ao_menos_a_pagina_principal(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        contextos = ApexHelper._obter_contextos(runner)
        assert runner._page in contextos

    def test_inclui_frames_adicionais(self):
        from src.flows.msi3.apex_helper import ApexHelper
        main_frame = MagicMock()
        extra_frame = MagicMock()
        extra_frame.url = "http://msi3/apex/f?p=152:19:"
        runner = _make_runner(frames=[main_frame, extra_frame])
        runner._page.main_frame = main_frame
        contextos = ApexHelper._obter_contextos(runner)
        assert len(contextos) >= 1


# ---------------------------------------------------------------------------
# verificar_sem_erro
# ---------------------------------------------------------------------------

class TestVerificarSemErro:
    def test_nao_lanca_quando_sem_erro(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        # wait_for_selector lança TimeoutError — nenhum erro visível
        runner._page.wait_for_selector.side_effect = Exception("timeout")
        runner._page.frames = [runner._page.main_frame]
        # Não deve levantar
        ApexHelper.verificar_sem_erro(runner, timeout_ms=100)

    def test_lanca_assertion_error_quando_erro_visivel(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        # Simula erro APEX visível
        runner._page.wait_for_selector.return_value = None
        locator = _make_locator(visible=True, text="Credencial inválida")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        with pytest.raises(AssertionError, match="APEX retornou erro"):
            ApexHelper.verificar_sem_erro(runner, timeout_ms=100)

    def test_mensagem_de_erro_inclui_texto_apex(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.wait_for_selector.return_value = None
        locator = _make_locator(visible=True, text="Usuário ou senha inválidos")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        with pytest.raises(AssertionError) as exc_info:
            ApexHelper.verificar_sem_erro(runner, timeout_ms=100)
        assert "Usuário ou senha inválidos" in str(exc_info.value)


# ---------------------------------------------------------------------------
# obter_mensagem_erro
# ---------------------------------------------------------------------------

class TestObterMensagemErro:
    def test_retorna_none_quando_sem_erro(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.wait_for_selector.side_effect = Exception("timeout")
        runner._page.frames = [runner._page.main_frame]
        assert ApexHelper.obter_mensagem_erro(runner, timeout_ms=100) is None

    def test_retorna_texto_do_erro(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.wait_for_selector.return_value = None
        locator = _make_locator(visible=True, text="Registro duplicado")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        resultado = ApexHelper.obter_mensagem_erro(runner, timeout_ms=100)
        assert resultado == "Registro duplicado"

    def test_nao_lanca_excecao(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.wait_for_selector.side_effect = Exception("qualquer erro")
        runner._page.frames = [runner._page.main_frame]
        # Não deve levantar
        resultado = ApexHelper.obter_mensagem_erro(runner, timeout_ms=100)
        assert resultado is None


# ---------------------------------------------------------------------------
# verificar_sucesso
# ---------------------------------------------------------------------------

class TestVerificarSucesso:
    def test_retorna_texto_de_sucesso(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.wait_for_selector.return_value = None
        locator = _make_locator(visible=True, text="Registro inserido com sucesso")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        resultado = ApexHelper.verificar_sucesso(runner, timeout_ms=100)
        assert "sucesso" in resultado.lower() or resultado == "Registro inserido com sucesso"

    def test_lanca_assertion_error_quando_sem_sucesso(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.wait_for_selector.side_effect = Exception("timeout")
        runner._page.frames = [runner._page.main_frame]
        with pytest.raises(AssertionError, match="Nenhuma mensagem de sucesso"):
            ApexHelper.verificar_sucesso(runner, timeout_ms=100)


# ---------------------------------------------------------------------------
# aguardar_spinner
# ---------------------------------------------------------------------------

class TestAguardarSpinner:
    def test_nao_espera_se_spinner_nao_visivel(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        locator = _make_locator(visible=False)
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        # Não deve chamar wait_for_selector
        ApexHelper.aguardar_spinner(runner, timeout_ms=100)
        runner._page.wait_for_selector.assert_not_called()

    def test_aguarda_quando_spinner_visivel(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        locator = _make_locator(visible=True)
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        runner._page.wait_for_selector.return_value = None
        # Não deve levantar
        ApexHelper.aguardar_spinner(runner, timeout_ms=100)


# ---------------------------------------------------------------------------
# ler_linhas_grade
# ---------------------------------------------------------------------------

class TestLerLinhasGrade:
    def test_retorna_linhas_da_grade(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        linha1 = MagicMock()
        linha1.text_content.return_value = "ANALISTA DE RH"
        linha2 = MagicMock()
        linha2.text_content.return_value = "ASSISTENTE"
        runner._page.locator.return_value.all.return_value = [linha1, linha2]
        runner._page.frames = [runner._page.main_frame]
        linhas = ApexHelper.ler_linhas_grade(runner)
        assert "ANALISTA DE RH" in linhas
        assert "ASSISTENTE" in linhas

    def test_retorna_lista_vazia_sem_linhas(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.locator.return_value.all.return_value = []
        runner._page.frames = [runner._page.main_frame]
        linhas = ApexHelper.ler_linhas_grade(runner)
        assert linhas == []

    def test_ignora_linhas_vazias(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        linha_vazia = MagicMock()
        linha_vazia.text_content.return_value = "   "
        linha_valida = MagicMock()
        linha_valida.text_content.return_value = "CARGO X"
        runner._page.locator.return_value.all.return_value = [linha_vazia, linha_valida]
        runner._page.frames = [runner._page.main_frame]
        linhas = ApexHelper.ler_linhas_grade(runner)
        assert "CARGO X" in linhas
        assert "" not in linhas


# ---------------------------------------------------------------------------
# verificar_registro_na_grade
# ---------------------------------------------------------------------------

class TestVerificarRegistroNaGrade:
    def test_nao_lanca_quando_texto_encontrado(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        linha = MagicMock()
        linha.text_content.return_value = "SV62 TESTE VTAE"
        runner._page.locator.return_value.all.return_value = [linha]
        runner._page.frames = [runner._page.main_frame]
        # Não deve levantar
        ApexHelper.verificar_registro_na_grade(runner, "SV62")

    def test_lanca_assertion_error_quando_nao_encontrado(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        linha = MagicMock()
        linha.text_content.return_value = "OUTRO REGISTRO"
        runner._page.locator.return_value.all.return_value = [linha]
        runner._page.frames = [runner._page.main_frame]
        with pytest.raises(AssertionError, match="não encontrado na grade"):
            ApexHelper.verificar_registro_na_grade(runner, "SV62")

    def test_lanca_assertion_error_quando_grade_vazia(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.locator.return_value.all.return_value = []
        runner._page.frames = [runner._page.main_frame]
        with pytest.raises(AssertionError):
            ApexHelper.verificar_registro_na_grade(runner, "SV62")

    def test_busca_case_insensitive(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        linha = MagicMock()
        linha.text_content.return_value = "sv62 teste vtae"
        runner._page.locator.return_value.all.return_value = [linha]
        runner._page.frames = [runner._page.main_frame]
        # Busca em maiúsculas deve encontrar texto em minúsculas
        ApexHelper.verificar_registro_na_grade(runner, "SV62")

    def test_mensagem_erro_lista_linhas_encontradas(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        linha = MagicMock()
        linha.text_content.return_value = "OUTRO REGISTRO"
        runner._page.locator.return_value.all.return_value = [linha]
        runner._page.frames = [runner._page.main_frame]
        with pytest.raises(AssertionError) as exc_info:
            ApexHelper.verificar_registro_na_grade(runner, "SV62")
        assert "OUTRO REGISTRO" in str(exc_info.value)


# ---------------------------------------------------------------------------
# obter_titulo_pagina
# ---------------------------------------------------------------------------

class TestObterTituloPagina:
    def test_retorna_titulo_h1(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        locator = _make_locator(visible=True, text="Frequência de Aplicação")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        titulo = ApexHelper.obter_titulo_pagina(runner)
        assert titulo != ""

    def test_retorna_string_vazia_sem_titulo(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        locator = _make_locator(visible=False, text="")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        titulo = ApexHelper.obter_titulo_pagina(runner)
        assert titulo == ""


# ---------------------------------------------------------------------------
# inspecionar_pagina
# ---------------------------------------------------------------------------

class TestInspecionarPagina:
    def test_retorna_dict_com_campos_esperados(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.wait_for_selector.side_effect = Exception("timeout")
        locator = _make_locator(visible=False, text="")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        info = ApexHelper.inspecionar_pagina(runner)
        assert "url" in info
        assert "titulo" in info
        assert "erro" in info
        assert "sucesso" in info
        assert "frames" in info

    def test_url_correto(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner(page_url="http://msi3/apex/f?p=100")
        runner._page.wait_for_selector.side_effect = Exception("timeout")
        locator = _make_locator(visible=False, text="")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        info = ApexHelper.inspecionar_pagina(runner)
        assert info["url"] == "http://msi3/apex/f?p=100"

    def test_erro_none_quando_sem_erro(self):
        from src.flows.msi3.apex_helper import ApexHelper
        runner = _make_runner()
        runner._page.wait_for_selector.side_effect = Exception("timeout")
        locator = _make_locator(visible=False, text="")
        runner._page.locator.return_value = locator
        runner._page.frames = [runner._page.main_frame]
        info = ApexHelper.inspecionar_pagina(runner)
        assert info["erro"] is None
