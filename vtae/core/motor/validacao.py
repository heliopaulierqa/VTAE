# vtae/core/motor/validacao.py
"""
Validacao antecipada do plano — peca 4 do motor (Projeto v1.1, Fase 2).

Roda ANTES do primeiro clique. Nao recebe ctx nem runner: so o plano, o
repositorio de objetos, o registro de steps nomeados e os dados. Por
isso e testavel inteira sem tela.

Junta TODOS os problemas antes de explodir. YAML de dez campos com erro
descoberto um por rodada sao dez rodadas; a lista inteira e uma.
"""
from vtae.core.exceptions import ConfigError
from vtae.core.motor.interpolacao import checar
from vtae.core.motor.plano import Campo

# Qual tipo de elemento exige quais chaves de mecanica.
# FONTE UNICA: o preencher() importa desta tabela. Nos dois lugares, um
# dia a validacao aceitaria um YAML que a mecanica nao sabe executar.
CHAVES_POR_TIPO = {
    "texto": (),
    "data": (),
    "lov": ("btn_ok",),
    "lov_lista": ("campo_localizar", "btn_ok", "titulo_janela"),
}

# Chaves cujo valor e o NOME de outro elemento — esse elemento tambem
# tem que existir. 'titulo_janela' fica de fora de proposito: e o texto
# do titulo da janela do Windows, nao nome de elemento.
CHAVES_QUE_APONTAM_ELEMENTO = ("campo_localizar", "btn_ok")

# 'salvar' nao tem mais mecanica fixa (decisao 26): o argumento e o
# nome de um elemento (clica nele) ou uma tecla/combinacao (tecla).
# F10 deixou de ser conhecimento do nucleo — e so mais uma tecla.


def validar(plano, objetos, registro: dict, dados: dict) -> None:
    problemas = []
    for step in plano.steps:
        problemas += _do_step(step, objetos, registro, dados)
    if problemas:
        raise ConfigError(
            f"{plano.flow}: o YAML de flow pede coisas impossiveis:\n  - "
            + "\n  - ".join(problemas))


def _do_step(step, objetos, registro, dados) -> list[str]:
    onde = f"{step.id} ({step.verbo})"

    if step.nomeado:
        faltando = ([] if step.verbo in registro
                    else [f"{onde}: step nomeado sem funcao registrada — "
                          f"registradas: {sorted(registro)}."])
        return faltando + _dos_valores(step.argumento, onde, dados)

    if step.verbo == "preencher":
        return (_do_preencher(step.argumento, onde, objetos)
                + _dos_valores(step.argumento.valor, onde, dados))

    if step.verbo == "verificar":
        return (_do_verificar(step.argumento, onde, objetos)
                + _dos_valores(step.argumento.valor, onde, dados))

    if step.verbo == "salvar":
        return _do_salvar(step.argumento, onde, objetos)

    if step.verbo == "clicar":
        return _do_alcancavel(step.argumento, onde, objetos)

    if step.verbo == "esperar":
        return _do_esperar(step.argumento, onde, objetos)

    if step.verbo in ("abrir", "teclar"):
        return _dos_valores(step.argumento, onde, dados)

    if step.verbo == "ler_resultado":
        return _do_ler_resultado(step.argumento, onde, objetos)

    return []


def _do_preencher(campo: Campo, onde: str, objetos) -> list[str]:
    elemento = objetos.elemento(campo.campo)
    if elemento is None:
        return [f"{onde}: campo '{campo.campo}' nao declarado em objects/."]

    tipo = elemento.get("tipo", "texto")
    if tipo not in CHAVES_POR_TIPO:
        return [f"{onde}: campo '{campo.campo}' e do tipo '{tipo}', "
                f"que nao se preenche."]

    problemas = []
    for chave in CHAVES_POR_TIPO[tipo]:
        alvo = elemento.get(chave)
        if not alvo:
            problemas.append(
                f"{onde}: campo '{campo.campo}' e '{tipo}' e exige a chave "
                f"'{chave}' no objects/.")
        elif (chave in CHAVES_QUE_APONTAM_ELEMENTO
              and objetos.elemento(alvo) is None):
            problemas.append(
                f"{onde}: campo '{campo.campo}' aponta '{chave}: {alvo}', "
                f"que nao existe em objects/.")
    return problemas


def _do_verificar(campo: Campo, onde: str, objetos) -> list[str]:
    """
    Verificar exige menos que preencher: nao precisa de mecanica, so de
    um elemento que TENHA valor. 'botao' e o unico que nunca tem —
    'resultado' tem, e e justamente o que o ler_resultado le.
    """
    elemento = objetos.elemento(campo.campo)
    if elemento is None:
        return [f"{onde}: campo '{campo.campo}' nao declarado em objects/."]
    if elemento.get("tipo") == "botao":
        return [f"{onde}: '{campo.campo}' e 'botao' — "
                f"nao tem valor a verificar."]
    return []


def _do_salvar(argumento, onde: str, objetos) -> list[str]:
    """Elemento declarado -> clica nele. Qualquer outra coisa -> tecla."""
    if objetos.elemento(argumento) is not None:
        return _do_alcancavel(argumento, onde, objetos)
    return []


def _do_alcancavel(nome, onde: str, objetos) -> list[str]:
    elemento = objetos.elemento(nome)
    if elemento is None:
        return [f"{onde}: '{nome}' nao declarado em objects/."]
    if not any(elemento.get(k) for k in ("template", "coordenada", "seletor")):
        return [f"{onde}: '{nome}' nao tem template, coordenada nem seletor "
                f"— nao ha como clicar nele."]
    return []


def _do_esperar(nome, onde: str, objetos) -> list[str]:
    """
    Esperar exige template: sem imagem nao ha condicao a observar, e
    'seguir sem esperar' seria um passo que passa sem provar nada.
    """
    elemento = objetos.elemento(nome)
    if elemento is None:
        return [f"{onde}: '{nome}' nao declarado em objects/."]
    if not elemento.get("template"):
        return [f"{onde}: '{nome}' nao tem template — 'esperar' precisa de "
                f"uma imagem para saber quando a tela chegou."]
    return []


def _do_ler_resultado(nome, onde: str, objetos) -> list[str]:
    elemento = objetos.elemento(nome)
    if elemento is None:
        return [f"{onde}: '{nome}' nao declarado em objects/."]
    tipo = elemento.get("tipo")
    if tipo != "resultado":
        return [f"{onde}: '{nome}' e '{tipo}', mas ler_resultado exige "
                f"tipo 'resultado'."]
    return []


def _dos_valores(valor, onde: str, dados: dict) -> list[str]:
    """Interpolacao citada no argumento do step, quando ele for texto."""
    if not isinstance(valor, str):
        return []
    try:
        checar(valor, dados)
    except ConfigError as erro:
        return [f"{onde}: {erro}"]
    return []