# vtae/cli/executar.py
"""
vtae executar <roteiro.yaml> [--vezes N]

Roda QUALQUER roteiro declarativo, de QUALQUER sistema, sem escrever
Python: sem arquivo de teste pytest, sem fixture por sistema, sem
registrar nada no CLI (decisao 26, 24/09/2026).

O roteiro diz tudo o que o comando precisa no cabecalho:

    flow: login_meu_sistema
    objetos: objects/meu_sistema/login.yaml
    dados: configs/meu_sistema/login        # pasta com config.yaml (+ .env)

Login, abertura da aplicacao e navegacao sao PASSOS do roteiro
(abrir, esperar, clicar, preencher...), nao codigo escondido numa
fixture. --vezes 3 e o gate: tres execucoes seguidas, para na primeira
falha.
"""
from pathlib import Path

from vtae.config import ConfigLoader
from vtae.core.context import FlowContext
from vtae.core.exceptions import ConfigError
from vtae.core.motor.executor import Executor
from vtae.core.motor.plano import carregar
from vtae.core.object_repository import ObjectRepository
from vtae.report.observer import ExecutionObserver


def carregar_config(plano, ambiente=None):
    if not plano.dados:
        raise ConfigError(
            f"{plano.flow}: o roteiro precisa de 'dados: configs/<pasta>' no "
            f"cabecalho — e a pasta com o config.yaml deste teste.")
    pasta = Path(plano.dados)
    return ConfigLoader.carregar(pasta.name, ambiente=ambiente,
                                 configs_dir=pasta.parent)


def _leitor_exato(plano, config):
    """
    Camada exata e OPCIONAL: so existe se a tela declarar titulo_jab.
    O import fica aqui dentro para que quem nao usa Java nunca dependa
    do pyjab.
    """
    titulo = ObjectRepository.from_yaml(plano.objetos).titulo_jab()
    if titulo is None:
        return None
    from vtae.runners.jab_reader import LeitorJab
    return LeitorJab(titulo=titulo, jab_home=config.DADOS.get("jab_home_fake"))


def executar_roteiro(caminho: str, vezes: int = 1, ambiente=None,
                     runner=None) -> bool:
    """'runner' injetavel so para o unitario rodar sem tela."""
    plano = carregar(caminho)
    config = carregar_config(plano, ambiente)

    if runner is None:
        from vtae.runners.opencv_runner import OpenCVRunner
        runner = OpenCVRunner(confidence=config.confidence,
                              ocr_engine=config.ocr_engine)

    for vez in range(1, vezes + 1):
        config.resetar_dados()          # dados novos a cada execucao
        nome = plano.flow if vezes == 1 else f"{plano.flow}_execucao{vez}"
        observer = ExecutionObserver(test_name=nome)
        ctx = FlowContext(runner=runner, config=config,
                          evidence_dir=observer.evidence_dir)
        observer.inject_logger(ctx)

        try:
            resultado = Executor(ctx, observer=observer,
                                 leitor_exato=_leitor_exato(plano, config)
                                 ).executar(caminho)
        finally:
            relatorio = observer.report(ctx)
            ctx.print_summary()

        print(f"\n[VTAE] Execucao {vez}/{vezes}: "
              f"{'PASSOU' if resultado.success else 'FALHOU'}")
        print(f"[VTAE] Relatorio: {relatorio}")
        if not resultado.success:
            if vezes > 1:
                print(f"[VTAE] GATE NAO FECHADO — falhou na execucao {vez}.")
            return False

    if vezes > 1:
        print(f"\n[VTAE] GATE FECHADO — {vezes}/{vezes} execucoes sem falha.")
    return True
