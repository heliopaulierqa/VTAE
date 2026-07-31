"""
Smoke tests do browser_launcher — vtae/runners/browser_launcher.py

Estratégia: nunca abre o Edge de verdade. subprocess.Popen e time.sleep
são mockados — cobre só o contrato (caminho do Edge, URL repassada,
sleep de espera), não o comportamento real do navegador.
"""

from unittest.mock import patch

from vtae.runners.browser_launcher import abrir_si3_navegador


class TestAbrirSi3Navegador:

    def test_chama_popen_com_edge_e_url(self):
        with patch("vtae.runners.browser_launcher.subprocess.Popen") as popen, \
             patch("vtae.runners.browser_launcher.time.sleep") as sleep:
            abrir_si3_navegador("http://si3.exemplo.local")

        args = popen.call_args[0][0]
        assert args[0].endswith("msedge.exe")
        assert args[1] == "http://si3.exemplo.local"
        sleep.assert_called_once_with(12)

    def test_nao_lanca_excecao_com_url_vazia(self):
        with patch("vtae.runners.browser_launcher.subprocess.Popen"), \
             patch("vtae.runners.browser_launcher.time.sleep"):
            abrir_si3_navegador("")
