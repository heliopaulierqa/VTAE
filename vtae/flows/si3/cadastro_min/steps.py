# vtae/flows/si3/cadastro_min/steps.py
"""
Steps nomeados da tela Cadastro de Paciente (SI3) — piloto da peca 4.

Aqui mora o UNICO codigo especifico desta tela: o que o motor nao pode
generalizar porque so um sistema mostrou como funciona (regra 64).
Tudo o mais — preencher, verificar, salvar, ler_resultado — e verbo do
motor, declarado em flows/si3/cadastro_min.yaml.

Assinatura de todo step: (ctx, motor, argumento)
    ctx       — FlowContext (runner, config, objects)
    motor     — o Executor: acoes, esperas, verificador, interpolador,
                objetos, e o metodo verificar()
    argumento — o valor do YAML, ja interpolado quando e texto

Nenhuma funcao daqui chama pyautogui: quem age e motor.acoes, quem
espera e motor.esperas. E isso que mantem a mecanica em UM lugar — e o
que faz este arquivo caber em ~140 linhas contra as 823 do flow antigo.
"""
import os

from vtae.core.exceptions import StepError

# Titulos de janela do Windows — medidos na tela real. Nao sao locators
# de ELEMENTO (esses vivem no objects/): sao janelas, e cada uma e de uma
# tela diferente do modulo.
JANELA_MENU = "Menu Principal"
JANELA_LISTA_PACIENTES = "Cadastro De Pacientes"
JANELA_POPUP_NACIONALIDADE = "Nacionalidade"

TIMEOUT_LISTA = 15.0
TIMEOUT_POPUP = 5.0

# Threshold 0.75: score maximo real medido do popup HC-INCOR = 0.785.
THRESHOLD_POPUP_ERRO = 0.75


# ──────────────────────────────────────────────────────────────────────
# Navegacao ate o formulario em branco
# ──────────────────────────────────────────────────────────────────────

def abrir_modulo(ctx, motor, nome_modulo):
    """
    Localizar no Menu -> pesquisar -> fechar o popup -> duplo clique no
    item. Nao e verbo do motor porque no MSI3 abrir um modulo seria uma
    URL: nao ha parte comum medida entre os dois (regra 64).
    """
    ctx.runner.maximizar_janela(JANELA_MENU)

    motor.acoes.preencher("localizar_menu", nome_modulo)
    motor.acoes.clicar("btn_pesquisar_menu")
    motor.acoes.clicar("btn_nao_popup")
    motor.acoes.clicar_duas_vezes("menu_cadastro_paciente")

    if not motor.esperas.esperar_visivel("nome_pesquisa"):
        raise StepError(
            f"o modulo '{nome_modulo}' nao abriu — a tela de Parametros de "
            f"Pesquisa nao apareceu.")


def pesquisar(ctx, motor, nome):
    """
    Preenche o nome e dispara a pesquisa. A tela de lista tem fundo
    variavel, entao a confirmacao e pelo TITULO da janela, nao por
    template (secao 7).
    """
    motor.acoes.preencher("nome_pesquisa", nome)
    motor.acoes.clicar("btn_pesquisar_params")

    if not motor.esperas.esperar_janela_aparecer(JANELA_LISTA_PACIENTES,
                                                 TIMEOUT_LISTA):
        raise StepError(
            f"a lista de pacientes nao carregou — janela "
            f"'{JANELA_LISTA_PACIENTES}' nao apareceu em {TIMEOUT_LISTA}s.")


def novo(ctx, motor, _argumento=None):
    """
    Abre o formulario em branco e confirma pelo TITULO da janela.

    Nao usa template de ancora: o antigo era 'Nome Social / Afetivo' —
    um rotulo sobre um campo branco vazio — e a LISTA de pacientes tem
    uma COLUNA 'Nome Social' com a mesma forma. Medido em 05/08: o
    template casou na lista, o step passou com o formulario fechado e a
    verificacao seguinte leu 'Cadastro Valido / Cadastro Mapeado' da
    lista achando que era o campo Nome.

    Titulo distingue: a lista e 'Cadastro De Pacientes', o formulario e
    'Form_Pac0010'. Esta espera pode falhar de verdade — a outra nao
    podia (regra 46).
    """
    motor.acoes.clicar("btn_novo_lista")

    titulo = motor.objetos.titulo_janela()
    if not motor.esperas.esperar_janela_aparecer(titulo, TIMEOUT_LISTA):
        raise StepError(
            f"o formulario de cadastro nao abriu — a janela '{titulo}' nao "
            f"apareceu em {TIMEOUT_LISTA}s.")


# ──────────────────────────────────────────────────────────────────────
# Nacionalidade — o unico campo com logica de negocio de verdade
# ──────────────────────────────────────────────────────────────────────

def preencher_nacionalidade(ctx, motor, tipo):
    """
    Tres sub-popups atras de uma LOV. E o exemplo que o v1.1 §4 da de
    "logica de negocio real vira step nomeado" — nao cabe num preencher.
    """
    item = _ITEM_DA_LISTA.get(tipo)
    if item is None:
        raise StepError(
            f"nacionalidade '{tipo}' desconhecida — conhecidas: "
            f"{sorted(_ITEM_DA_LISTA)}.")

    motor.acoes.clicar("btn_lov_nacionalidade")
    motor.acoes.clicar(item)
    motor.acoes.clicar("btn_ok_lista_nac")

    _POPUP[tipo](ctx, motor)

    _conferir_popup_erro(ctx, motor, tipo)
    motor.esperas.esperar_janela_sumir(JANELA_POPUP_NACIONALIDADE,
                                       TIMEOUT_POPUP)

    # Step nomeado nao ganha auto-verificacao: quem pede e ele.
    motor.verificar("nacionalidade", tipo)


def _popup_brasileiro(ctx, motor):
    """Estado sorteado; a Cidade e a do PAR daquele estado (negocio)."""
    estado = motor.interpolador.resolver("{sorteio:estados_brasileiro}")
    cidades = ctx.config.DADOS["cidades_por_estado"]
    motor.acoes.preencher("estado_brasileiro", estado)
    motor.acoes.preencher("cidade_brasileiro", cidades.get(estado, estado))
    motor.acoes.clicar("btn_ok_popup_brasileiro")


def _popup_estrangeiro(ctx, motor):
    resolver = motor.interpolador.resolver
    motor.acoes.preencher("pais_estrangeiro",
                          resolver(_chave_paises(ctx, "estrangeiro")))
    motor.acoes.preencher("data_entrada_brasil",
                          resolver("{faker:data_entrada_brasil}"))
    motor.acoes.preencher("estado_estrangeiro",
                          resolver("{faker:estado_estrangeiro}"))
    motor.acoes.preencher("municipio_estrangeiro",
                          resolver("{faker:municipio_estrangeiro}"))
    motor.acoes.clicar("btn_ok_popup_estrangeiro")


def _popup_naturalizado(ctx, motor):
    resolver = motor.interpolador.resolver
    motor.acoes.preencher("pais_naturalizado",
                          resolver(_chave_paises(ctx, "naturalizado")))
    motor.acoes.preencher("data_naturalizacao",
                          resolver("{faker:data_naturalizacao}"))
    motor.acoes.preencher("nr_portaria", resolver("{faker:nr_portaria}"))
    motor.acoes.clicar("btn_ok_popup_naturalizado")


def _chave_paises(ctx, sufixo: str) -> str:
    """
    Cenario negativo troca a lista de paises por uma com valor invalido —
    e ai o teste ESPERA o HC-INCOR. Quem decide e o config (regra 40).
    """
    cenario = ctx.config.DADOS.get("cenario", "positivo")
    sufixo_negativo = "_negativo" if cenario == "negativo" else ""
    return f"{{sorteio:paises_{sufixo}{sufixo_negativo}}}"


def _conferir_popup_erro(ctx, motor, tipo):
    """
    O HC-INCOR e modal interno do Forms: nao tem handle de janela, entao
    pygetwindow nao o ve. So template matching detecta (secao 7).
    """
    template = motor.objetos.template("popup_erro_incor")
    if not os.path.exists(template):
        return  # bootstrap: template ainda nao capturado
    if not ctx.runner.is_visible(template, threshold=THRESHOLD_POPUP_ERRO):
        return

    ctx.runner.screenshot(f"{ctx.evidence_dir}erro_incor_{tipo}.png")
    motor.acoes.clicar("btn_ok_erro_incor")
    motor.acoes.clicar("btn_cancelar_popup_nac")
    raise StepError(
        f"popup HC-INCOR apos preencher Nacionalidade ({tipo}) — o sistema "
        f"rejeitou os dados. Em cenario negativo, isto e o esperado.")


# ──────────────────────────────────────────────────────────────────────
# Fechamento
# ──────────────────────────────────────────────────────────────────────

def gerar_matricula(ctx, motor, _argumento=None):
    """
    O F10 e o verbo 'salvar' do YAML; este clique e o botao que gera a
    matricula. Fica como step nomeado porque so o SI3 mostrou que ele
    existe (regra 64).
    """
    motor.acoes.clicar("btn_gerar_matricula")


def sair(ctx, motor, _argumento=None):
    """Tres cliques ate o Menu Principal."""
    for botao in ("btn_sair_1", "btn_sair_2", "btn_sair_3"):
        motor.acoes.clicar(botao)


# ──────────────────────────────────────────────────────────────────────
# Registro cobrado pela validacao antecipada, antes do primeiro clique
# ──────────────────────────────────────────────────────────────────────

_ITEM_DA_LISTA = {
    "BRASILEIRO": "item_lista_brasileiro",
    "ESTRANGEIRO": "item_lista_estrangeiro",
    "NATURALIZADO": "item_lista_naturalizado",
}

_POPUP = {
    "BRASILEIRO": _popup_brasileiro,
    "ESTRANGEIRO": _popup_estrangeiro,
    "NATURALIZADO": _popup_naturalizado,
}

STEPS = {
    "abrir_modulo": abrir_modulo,
    "pesquisar": pesquisar,
    "novo": novo,
    "preencher_nacionalidade": preencher_nacionalidade,
    "gerar_matricula": gerar_matricula,
    "sair": sair,
}
