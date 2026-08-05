# vtae/core/motor/interpolacao.py
"""
Interpolacao de valores — peca 4 do motor (Projeto v1.1, Fase 2).

Traduz a string crua que o plano guardou no valor final que vai para a
tela. Nao le tela, nao le config, nao le objects: recebe o dicionario de
dados pronto e devolve texto.

    "0000"                  -> "0000"                        (literal)
    "{faker:nome}"          -> dados["nome"]
    "{sorteio:sexo_opcoes}" -> random.choice(dados["sexo_opcoes"])

O motor NUNCA chama Faker. O valor de "{faker:X}" ja foi gerado pela
secao dados_faker: do config.yaml — o prefixo declara a ORIGEM, e a
declaracao e cobrada: 'faker' exige texto, 'sorteio' exige lista.

As regras de validacao vivem em checar(), nao dentro do Interpolador: a
validacao antecipada (validacao.py) precisa das MESMAS regras sem
sortear nada. Uma fonte, dois usos — a validacao joga o retorno fora, o
resolver usa.

Tudo aqui explode com ConfigError, nunca devolve None: dado de teste
ausente ou do tipo errado e defeito de escrita, nao ambiente (regra 45).
"""
import random
import re

from vtae.core.exceptions import ConfigError

# Usado com fullmatch: ou o valor E um placeholder inteiro, ou e literal.
# "Sr. {faker:nome}" nao casa — concatenacao nasce quando um teste real
# precisar dela, medida (regra 50).
_PLACEHOLDER = re.compile(r"\{(\w+):(\w+)\}")

PREFIXOS = ("faker", "sorteio")


def checar(valor: str, dados: dict) -> tuple[str, str] | None:
    """
    Valida um valor contra o dicionario de dados, sem sortear nada.

    Devolve (prefixo, chave) quando e placeholder e None quando e
    literal — o retorno e a resposta e a prova ao mesmo tempo, no mesmo
    espirito do objeto de match do re.
    """
    casou = _PLACEHOLDER.fullmatch(valor.strip())
    if casou is None:
        _recusar_parcial(valor)
        return None

    prefixo, chave = casou.group(1), casou.group(2)
    if prefixo not in PREFIXOS:
        raise ConfigError(
            f"'{valor}': prefixo '{prefixo}' desconhecido — "
            f"aceitos: {list(PREFIXOS)}.")

    conteudo = _exigir(chave, prefixo, dados)

    if prefixo == "faker" and not isinstance(conteudo, str):
        raise ConfigError(
            f"'{{faker:{chave}}}': esperava texto em dados['{chave}'], "
            f"encontrou {type(conteudo).__name__} — para lista, "
            f"use '{{sorteio:{chave}}}'.")

    if prefixo == "sorteio":
        if not isinstance(conteudo, list):
            raise ConfigError(
                f"'{{sorteio:{chave}}}': esperava lista em dados['{chave}'], "
                f"encontrou {type(conteudo).__name__} — para texto, "
                f"use '{{faker:{chave}}}'.")
        if not conteudo:
            raise ConfigError(
                f"'{{sorteio:{chave}}}': lista vazia em dados['{chave}'].")

    return prefixo, chave


def _exigir(chave: str, prefixo: str, dados: dict):
    if chave not in dados:
        raise ConfigError(
            f"'{{{prefixo}:{chave}}}': chave '{chave}' ausente nas secoes "
            f"dados:/dados_faker: do config.yaml.\n"
            f"Chaves disponiveis: {sorted(dados)}")
    return dados[chave]


def _recusar_parcial(valor: str) -> None:
    if _PLACEHOLDER.search(valor):
        raise ConfigError(
            f"'{valor}': interpolacao parcial nao existe — o valor e um "
            f"placeholder inteiro ou e literal.")


class Interpolador:
    """
    Um por execucao. O cache de sorteio vive aqui e morre junto com ela:
    a mesma chave pedida duas vezes devolve o mesmo valor (D15). Sem
    cache, o relatorio mostraria um valor e a tela teria outro.
    """

    def __init__(self, dados: dict):
        self._dados = dados or {}
        self._sorteados: dict[str, str] = {}

    def resolver(self, valor: str) -> str:
        achado = checar(valor, self._dados)
        if achado is None:
            return valor

        prefixo, chave = achado
        if prefixo == "faker":
            return self._dados[chave]
        if chave not in self._sorteados:
            self._sorteados[chave] = str(random.choice(self._dados[chave]))
        return self._sorteados[chave]