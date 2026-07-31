"""
Smoke tests do Health Check — vtae/core/health_check.py

Estratégia: mocka subprocess.run (tasklist) — nunca lista processos
reais do SO, determinístico em qualquer máquina/CI.
"""

from unittest.mock import MagicMock, patch

from vtae.core.health_check import verificar, _processos_ativos


def _tasklist_saida(*nomes):
    """Simula a saída do `tasklist /fo csv /nh` para os processos dados."""
    linhas = [f'"{nome}","1234","Console","1","10.000 K"' for nome in nomes]
    return "\n".join(linhas)


class TestProcessosAtivos:

    def test_retorna_lista_de_nomes_em_lower(self):
        fake = MagicMock(stdout=_tasklist_saida("JAVA.EXE", "chrome.exe"))
        with patch("subprocess.run", return_value=fake):
            ativos = _processos_ativos()
        assert "java.exe" in ativos
        assert "chrome.exe" in ativos

    def test_retorna_lista_vazia_em_excecao(self):
        with patch("subprocess.run", side_effect=OSError("tasklist indisponivel")):
            assert _processos_ativos() == []


class TestVerificar:

    def test_ok_quando_processo_esperado_esta_ativo(self):
        fake = MagicMock(stdout=_tasklist_saida("java.exe"))
        with patch("subprocess.run", return_value=fake):
            ok, avisos = verificar(["si3"])
        assert ok is True
        assert avisos == []

    def test_avisa_quando_nenhum_processo_esperado_ativo(self):
        fake = MagicMock(stdout=_tasklist_saida("notepad.exe"))
        with patch("subprocess.run", return_value=fake):
            ok, avisos = verificar(["si3"])
        assert ok is False
        assert len(avisos) == 1
        assert "si3" in avisos[0]

    def test_sistema_desconhecido_e_ignorado(self):
        fake = MagicMock(stdout=_tasklist_saida("notepad.exe"))
        with patch("subprocess.run", return_value=fake):
            ok, avisos = verificar(["sistema_sem_mapeamento"])
        assert ok is True
        assert avisos == []

    def test_multiplos_sistemas_um_ausente(self):
        fake = MagicMock(stdout=_tasklist_saida("java.exe"))
        with patch("subprocess.run", return_value=fake):
            ok, avisos = verificar(["si3", "msi3"])
        assert ok is False
        assert len(avisos) == 1
        assert "msi3" in avisos[0]

    def test_lista_vazia_retorna_ok(self):
        fake = MagicMock(stdout="")
        with patch("subprocess.run", return_value=fake):
            ok, avisos = verificar([])
        assert ok is True
        assert avisos == []
