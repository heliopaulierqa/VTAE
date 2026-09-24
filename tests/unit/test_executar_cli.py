"""
vtae executar — roteiro de sistema ficticio, do cabecalho ao gate.
Nenhuma linha de Python especifica do sistema: so os tres YAML.
"""
import os
import textwrap

from vtae.cli.executar import executar_roteiro
from tests.unit.test_verbos_genericos import FakeRunner


def _escrever(raiz, caminho, texto):
    arquivo = raiz / caminho
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(textwrap.dedent(texto), encoding="utf-8")


def _projeto(tmp_path):
    _escrever(tmp_path, "configs/ficticio/login/config.yaml", """
        tipo: desktop
        runner: opencv
        ambientes:
          dev:
            url: ''
        credenciais:
          usuario: ana
          senha: segredo
        dados:
          programa: ficticio.exe
    """)
    _escrever(tmp_path, "objects/ficticio/login.yaml", """
        objetos:
          tela_login: { tipo: botao, template: tela_login.png }
          usuario:    { tipo: texto, coordenada: { x: 10, y: 10 } }
          senha:      { tipo: texto, sigiloso: true, coordenada: { x: 20, y: 20 } }
          btn_entrar: { tipo: botao, coordenada: { x: 30, y: 30 } }
    """)
    _escrever(tmp_path, "flows/ficticio/login.yaml", """
        flow: login_ficticio
        objetos: objects/ficticio/login.yaml
        dados: configs/ficticio/login
        steps:
          - abrir:    "{dado:programa}"
          - esperar:  tela_login
          - preencher: { campo: senha, valor: "{dado:senha}" }
          - clicar:   btn_entrar
    """)


def test_roteiro_de_sistema_qualquer_fecha_gate_3x(tmp_path, capsys):
    _projeto(tmp_path)
    os.chdir(tmp_path)
    runner = FakeRunner()
    assert executar_roteiro("flows/ficticio/login.yaml", vezes=3, runner=runner)
    assert runner.chamadas.count(("abrir", "ficticio.exe")) == 3
    assert "GATE FECHADO — 3/3" in capsys.readouterr().out


def test_roteiro_sem_dados_no_cabecalho_explica_o_que_falta(tmp_path):
    import pytest
    from vtae.core.exceptions import ConfigError
    _projeto(tmp_path)
    os.chdir(tmp_path)
    (tmp_path / "flows/ficticio/sem_dados.yaml").write_text(
        "flow: x\nobjetos: objects/ficticio/login.yaml\nsteps:\n  - clicar: btn_entrar\n",
        encoding="utf-8")
    with pytest.raises(ConfigError, match="dados: configs"):
        executar_roteiro("flows/ficticio/sem_dados.yaml", runner=FakeRunner())
