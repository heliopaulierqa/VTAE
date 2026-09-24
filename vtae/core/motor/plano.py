# vtae/core/motor/plano.py
"""
Plano de flow — peca 4 do motor (Projeto v1.1, Fase 2).

Le o YAML de flow no formato do Projeto v1.1 §4 (linhas 63-76) e
devolve estruturas Python validadas. Nao executa nada: nao clica, nao
espera, nao verifica, nao interpola dado.

A interpolacao de "{faker:nome}" / "{sorteio:sexo_opcoes}" NAO acontece
aqui — o plano guarda a string crua. Quem resolve e o executor, que tem
o config.DADOS na mao. Separar as duas coisas e o que permite testar
este arquivo inteiro sem config, sem runner e sem tela.

Cada step do YAML e um dicionario de UMA chave:

    - abrir_modulo: CADASTRO DE PACIENTE
    - preencher: { campo: nome, valor: "{faker:nome}" }
    - preencher_nacionalidade: "{sorteio:nacionalidade_opcoes}"
    - salvar: f10
    - ler_resultado: matricula

O cabecalho aceita 'steps_python:' — o modulo Python onde vivem as
funcoes dos steps nomeados daquela tela (v1.1 §4 + D6). Opcional aqui:
quem cobra a existencia da funcao e a validacao.    

A chave e o verbo. Quatro sao do motor (VERBOS_MOTOR); qualquer outra
chave e STEP NOMEADO — logica de negocio real que vira funcao Python
registrada para aquela tela (v1.1 §4, linhas 95-96). Por isso NAO
existe "verbo desconhecido" aqui: nome que o motor nao conhece e step
nomeado, e a cobranca acontece no executor, que sabe o que esta
registrado.

Ao contrario das pecas 2 e 3, aqui erro e FATAL. Tela e ambiente:
degrada, oscila, e quem chama decide se mata (regra 45). YAML de flow
malformado nao e ambiente — e defeito de escrita do teste, e tem que
explodir antes do primeiro clique.
"""
from dataclasses import dataclass

import yaml

from vtae.core.exceptions import ConfigError

# Verbos implementados pelo motor — os tres que sao genericos entre
# desktop e web. 'abrir_modulo' NAO esta aqui de proposito: no SI3 e
# menu+pesquisa+popup+duplo clique, no MSI3 seria uma URL, e os dois
# nao tem nada em comum medido ainda. Fica como step nomeado ate o
# teste web mostrar o que generalizar (regra 50).
#
# 24/09/2026 — verbos genericos (decisao 26). Todo sistema, desktop ou
# web, tem campo livre, campo de dominio e botao; toda interacao se
# escreve com estes oito verbos. Nenhum deles conhece sistema algum.
VERBOS_MOTOR = ("abrir", "esperar", "clicar", "teclar",
                "preencher", "verificar", "salvar", "ler_resultado")

# Verbos que recebem { campo: <nome>, valor: <valor> }.
# 'verificar' nasceu de um caso real (regra 50): o campo Nome do cadastro
# chega PRE-PREENCHIDO da tela de pesquisa. O teste precisa provar o
# valor sem tocar no campo — digitar por cima mudaria comportamento ja
# validado 3x (regra 7).
VERBOS_DE_CAMPO = ("preencher", "verificar")

# Verbos do motor cujo argumento e um texto simples.
VERBOS_ESCALARES = ("abrir", "esperar", "clicar", "teclar",
                    "salvar", "ler_resultado")


@dataclass(frozen=True)
class Campo:
    """Argumento dos verbos 'preencher' e 'verificar'."""
    campo: str
    valor: str


@dataclass(frozen=True)
class Step:
    ordem: int
    verbo: str
    argumento: object = None
    nomeado: bool = False

    @property
    def id(self) -> str:
        """
        Id do step. O v1.1 nao declara id no YAML, entao ele e derivado
        da ordem — os CM01..CM10 dos flows antigos morrem junto com eles
        na Fase 3.
        """
        return f"S{self.ordem:02d}"

    @property
    def descricao(self) -> str:
        if isinstance(self.argumento, Campo):
            return f"{self.verbo} {self.argumento.campo}"
        if self.argumento is None:
            return self.verbo
        return f"{self.verbo} {self.argumento}"


@dataclass(frozen=True)
class Plano:
    flow: str
    objetos: str
    steps: tuple[Step, ...]
    steps_python: str | None = None
    # Pasta com config.yaml (+ .env) deste roteiro — usada pelo
    # 'vtae executar'. Opcional aqui para nao quebrar quem ja roda via
    # fixture; o 'vtae executar' cobra a presenca.
    dados: str | None = None


def carregar(caminho: str) -> Plano:
    with open(caminho, "r", encoding="utf-8") as f:
        cru = yaml.safe_load(f) or {}
    return montar(cru, caminho)


def montar(cru: dict, origem: str = "<memoria>") -> Plano:
    for chave in ("flow", "objetos", "steps"):
        if not cru.get(chave):
            raise ConfigError(
                f"{origem}: '{chave}' ausente ou vazio no YAML de flow.")
    steps = tuple(_step(item, origem, i)
                  for i, item in enumerate(cru["steps"], 1))
    return Plano(flow=cru["flow"], objetos=cru["objetos"], steps=steps,
                 steps_python=cru.get("steps_python"),
                 dados=cru.get("dados"))


def _step(item, origem: str, ordem: int) -> Step:
    onde = f"{origem}: step {ordem}"
    if not isinstance(item, dict) or len(item) != 1:
        raise ConfigError(
            f"{onde}: cada step e um dicionario de UMA chave (o verbo) — "
            f"recebeu {item!r}.")

    verbo, argumento = next(iter(item.items()))
    onde = f"{origem}: step {ordem} ('{verbo}')"

    if verbo in VERBOS_DE_CAMPO:
        return Step(ordem, verbo, _campo(argumento, onde, verbo))

    if verbo in VERBOS_ESCALARES:
        if not isinstance(argumento, str) or not argumento.strip():
            raise ConfigError(
                f"{onde}: '{verbo}' exige um texto como argumento — "
                f"recebeu {argumento!r}.")
        return Step(ordem, verbo, argumento)

    # Nao e verbo do motor: e step nomeado (v1.1 §4, linhas 95-96).
    # Quem cobra a existencia da funcao e o executor, que conhece o
    # registro daquela tela.
    return Step(ordem, verbo, argumento, nomeado=True)


def _campo(argumento, onde: str, verbo: str = "preencher") -> Campo:
    if not isinstance(argumento, dict):
        raise ConfigError(
            f"{onde}: '{verbo}' exige "
            f"{{ campo: <nome>, valor: <valor> }} — recebeu {argumento!r}.")
    faltando = [c for c in ("campo", "valor") if not argumento.get(c)]
    if faltando:
        raise ConfigError(f"{onde}: '{verbo}' sem {faltando}.")
    sobrando = set(argumento) - {"campo", "valor"}
    if sobrando:
        raise ConfigError(
            f"{onde}: '{verbo}' com chave desconhecida {sorted(sobrando)} — "
            f"aceita apenas 'campo' e 'valor'.")
    return Campo(argumento["campo"], str(argumento["valor"]))
