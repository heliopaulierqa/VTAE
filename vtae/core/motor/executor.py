# vtae/core/motor/executor.py
"""
Executor — peca 4 do motor (Projeto v1.1, Fase 2).

Junta todas as pecas: le o plano (plano.py), valida antes do primeiro
clique (validacao.py), resolve valores (interpolacao.py), age na tela
(acoes.py), verifica (verificacao.py) e embrulha cada step em
observabilidade (passo.py).

Nao sabe o que e F9, TAB ou backspace — isso e das acoes. Nao sabe o
nome de nenhuma tela — isso vem do YAML. Nao faz boot nem login — isso
e a fixture (peca 5 do v1.1).
"""
import importlib
import time

from vtae.core.exceptions import ConfigError, StepError
from vtae.core.motor import passo as _passo
from vtae.core.motor.acoes import Acoes
from vtae.core.motor.esperas import Esperas
from vtae.core.motor.interpolacao import Interpolador
from vtae.core.motor.plano import carregar
from vtae.core.motor.resolvedor import Resolvedor
from vtae.core.motor.validacao import validar
from vtae.core.motor.verificacao import (DIVERGENTE, NAO_VERIFICAVEL, OK,
                                         VAZIO, Verificador)
from vtae.core.object_repository import ObjectRepository
from vtae.core.result import FlowResult

TIMEOUT_RESULTADO = 15.0
INTERVALO_RESULTADO = 0.5

# Releituras de um campo recem-preenchido antes de dar por divergente.
#
# Medido em 05/08, cor_etnia: o OCR leu 'PARDA 2 =' na primeira tentativa
# e o screenshot da falha, tirado logo depois, le 'PARDA' limpo — o
# ruido era a tela ainda assentando apos a LOV fechar, nao o valor.
#
# O verify_lov do runner repete ate o campo nao estar VAZIO; ele nao
# recebe o valor esperado, entao aceita ruido como leitura boa e para.
# Quem sabe o que se espera e o veredito — entao a repeticao tem que
# viver aqui, no mesmo lugar e pelo mesmo motivo que a do ler_resultado.
#
# 3 e nao 30: divergencia real (o match parcial silencioso do Forms)
# continua reprovando rapido. So o transitorio ganha segunda chance.
TENTATIVAS_VERIFICACAO = 3


class Executor:
    """
    O 'motor' que o step nomeado recebe: acoes, esperas, verificador,
    objetos e interpolador sao atributos publicos de proposito — e o que
    permite ao step nomeado reusar a mecanica em vez de reescrever
    pyautogui.
    """

    def __init__(self, ctx, observer=None, registro=None,
                 leitor_exato=None, pausar=time.sleep):
        self._ctx = ctx
        self._observer = observer
        self._registro_injetado = registro
        self._leitor_exato = leitor_exato
        self._pausar = pausar
        self.objetos = None
        self.acoes = None
        self.esperas = None
        self.verificador = None
        self.interpolador = None
        self.registro = {}
        # Coleta do step em execucao — e o que permite ao step nomeado
        # registrar um veredito no StepResult certo (metodo verificar).
        self._coleta_atual = None

    # ------------------------------------------------------------------
    def executar(self, caminho_yaml: str) -> FlowResult:
        plano = carregar(caminho_yaml)
        self.objetos = ObjectRepository.from_yaml(plano.objetos)
        self.registro = self._resolver_registro(plano)
        dados = self._ctx.config.DADOS

        # Antes do primeiro clique: YAML errado nao chega na tela (regra 45).
        validar(plano, self.objetos, self.registro, dados)

        runner = self._ctx.runner
        self.interpolador = Interpolador(dados)
        self.esperas = Esperas(self.objetos, runner)
        self.verificador = Verificador(self.objetos, runner,
                                       leitor_exato=self._leitor_exato)
        self.acoes = Acoes(self.objetos, runner,
                           Resolvedor(self.objetos, runner),
                           self.esperas, pausar=self._pausar)

        resultado = FlowResult(flow_name=plano.flow)
        for step in plano.steps:
            resultado.steps.append(self._executar_step(step))
            if not resultado.steps[-1].success:
                break  # abort-on-failure, como nos flows

        self._ctx.add_result(resultado)
        if self._observer:
            self._observer.log_flow_result(resultado)
        return resultado

    # ------------------------------------------------------------------
    def _resolver_registro(self, plano) -> dict:
        if self._registro_injetado is not None:
            return self._registro_injetado
        if not plano.steps_python:
            return {}
        try:
            modulo = importlib.import_module(plano.steps_python)
        except ImportError as erro:
            raise ConfigError(
                f"{plano.flow}: 'steps_python: {plano.steps_python}' nao pode "
                f"ser importado — {erro}")
        registro = getattr(modulo, "STEPS", None)
        if not isinstance(registro, dict):
            raise ConfigError(
                f"{plano.flow}: o modulo '{plano.steps_python}' nao expoe um "
                f"dicionario STEPS.")
        return registro

    def _executar_step(self, step):
        coleta = _passo.Coleta()
        self._coleta_atual = coleta
        return _passo.executar(
            step.id, step.descricao,
            lambda: self._despachar(step, coleta),
            observer=self._observer, ctx=self._ctx, coleta=coleta)

    def _despachar(self, step, coleta) -> str:
        if step.nomeado:
            self._nomeado(step)
        elif step.verbo == "preencher":
            self._preencher(step.argumento, coleta)
        elif step.verbo == "verificar":
            self._verificar_declarado(step.argumento, coleta)
        elif step.verbo == "salvar":
            self.acoes.salvar(step.argumento)
        elif step.verbo == "ler_resultado":
            self._ler_resultado(step.argumento, coleta)
        # Evidencia sempre, com ou sem verificacao: pyjab prova o que o
        # sistema TEM, o screenshot prova o que o usuario VE.
        return self._ctx.runner.screenshot(
            f"{self._ctx.evidence_dir}{step.id}_{step.verbo}.png")

    def _nomeado(self, step) -> None:
        argumento = step.argumento
        if isinstance(argumento, str):
            argumento = self.interpolador.resolver(argumento)
        self.registro[step.verbo](self._ctx, self, argumento)

    def _preencher(self, campo, coleta) -> None:
        valor = self.interpolador.resolver(campo.valor)
        self.acoes.preencher(campo.campo, valor)
        self._aplicar(self._verificar_estavel(campo.campo, valor), coleta)

    def _verificar_estavel(self, nome, esperado):
        """
        Verifica de novo enquanto o veredito for DIVERGENTE.

        So DIVERGENTE se repete: VAZIO e o campo que nao recebeu o valor
        (releitura nao inventa texto), e NAO_VERIFICAVEL e defeito de
        configuracao — repetir os dois seria so gastar tempo para chegar
        na mesma resposta.
        """
        for tentativa in range(TENTATIVAS_VERIFICACAO):
            veredito = self.verificador.verificar(nome, esperado)
            if veredito.status != DIVERGENTE:
                return veredito
            if tentativa < TENTATIVAS_VERIFICACAO - 1:
                self._pausar(INTERVALO_RESULTADO)
        return veredito

    def _verificar_declarado(self, campo, coleta) -> None:
        """
        Verbo 'verificar': prova o valor SEM tocar no campo. E o caso do
        Nome do cadastro, que chega pre-preenchido da tela de pesquisa.
        """
        esperado = self.interpolador.resolver(campo.valor)
        self._aplicar(self._verificar_estavel(campo.campo, esperado),
                      coleta, explicito=True)

    def verificar(self, nome: str, esperado=None) -> None:
        """
        Publico: e por aqui que o step nomeado registra um veredito no
        StepResult do step em execucao — sem isso, o que ele verifica nao
        chega ao relatorio. Explicito: NAO_VERIFICAVEL aqui e falha.
        """
        coleta = (self._coleta_atual if self._coleta_atual is not None
                  else _passo.Coleta())
        self._aplicar(self.verificador.verificar(nome, esperado),
                      coleta, explicito=True)

    def _ler_resultado(self, nome, coleta) -> None:
        """
        Polling: o valor e gerado pelo sistema e demora. Espera pela
        CONDICAO (o veredito ficar OK), nunca por tempo fixo (regra 51).
        Contamos tentativas em vez de relogio para que o unitario, com
        pausar falso, nao gire 15 segundos de verdade.
        """
        tentativas = max(1, int(TIMEOUT_RESULTADO / INTERVALO_RESULTADO))
        for _ in range(tentativas):
            veredito = self.verificador.verificar(nome)
            if veredito.aprovado:
                break
            self._pausar(INTERVALO_RESULTADO)
        self._aplicar(veredito, coleta)

    def _aplicar(self, veredito, coleta, explicito: bool = False) -> None:
        """
        Traduz o Veredito da peca 3 em consequencia — a tabela do §6.

        'explicito' muda a POLITICA, nao o calculo: a leitura, a
        comparacao e o veredito sao os mesmos. So a consequencia de um
        status muda. NAO_VERIFICAVEL na auto-verificacao e AVISO (campo
        cego e limitacao conhecida do mapeamento, nao defeito do sistema
        sob teste); quando o teste PEDIU a prova, e falha — pedir prova e
        nao conseguir le-la significa que nada foi provado.
        """
        coleta.ocr_lido = veredito.lido_ocr
        coleta.jab_lido = veredito.lido_exato
        coleta.validated = veredito.status == OK

        if veredito.status in (DIVERGENTE, VAZIO):
            raise StepError(f"[{veredito.elemento}] {veredito.motivo}")

        if veredito.status == NAO_VERIFICAVEL:
            if explicito:
                raise StepError(
                    f"[{veredito.elemento}] o teste pediu a verificacao, mas o "
                    f"campo nao e verificavel — {veredito.motivo}")
            coleta.avisos.append(
                f"{veredito.elemento}: nao verificavel — {veredito.motivo}")
            return

        if veredito.degradado:
            coleta.avisos.append(
                f"{veredito.elemento}: verificado sem a camada exata que a "
                f"tela declara")
        if veredito.divergencia:
            coleta.avisos.append(
                f"{veredito.elemento}: camada exata e OCR discordam "
                f"(exata='{veredito.lido_exato}', ocr='{veredito.lido_ocr}')")