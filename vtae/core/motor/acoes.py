# vtae/core/motor/acoes.py
"""
Acoes — peca 4 do motor (Projeto v1.1, Fase 2).

Tudo que MEXE na tela. O executor diz "preenche este campo com este
valor"; a receita (clique, backspace, F9, TAB, OK, esperas) sai do
'tipo:' do elemento no objects/.

Nao importa pyautogui: core decide O QUE, runner faz COMO. E o que
mantem o motor testavel com runner falso, e o que vai permitir Citrix e
web sem reescrever a decisao.

Erro aqui e excecao (StepError). Isso nao briga com a regra 45:
resolvedor e verificador OBSERVAM e devolvem estado; acao EXECUTA, e
execucao impossivel nao tem estado intermediario util. Quem transforma
a excecao em StepResult e o passo.py.
"""
import time

from vtae.core.exceptions import StepError

# Pausa entre eventos de teclado/mouse — o Forms precisa dela para
# registrar o evento anterior, mesma natureza da regra 17. NAO e
# "esperar a tela ficar pronta": isso e espera por condicao (esperas.py).
PAUSA = 0.3
PAUSA_CLIQUE = 0.5

# N fixo generoso em vez de Ctrl+A: campo com LOV anexada ignora Ctrl+A
# no Oracle Forms (padrao consolidado, secao 7 do prompt).
BACKSPACES = 20

# Tempo que a LOV do Forms leva para desenhar apos o F9.
#
# Por que PAUSA e nao espera por condicao, contrariando a regra 51: as
# LOVs do SI3 (Lista de Pais, Grupo etnico, Lista de UF, Lista de Ci)
# sao janelas INTERNAS do Oracle Forms. Medido em 05/08 com a Lista de
# Pais aberta na tela: o pygetwindow lista apenas 'Form_Pac0010' — a LOV
# nao tem handle no Windows, entao esperar_janela_aparecer nunca pode
# dar certo. Era o que travava o S08.
#
# A prova de que a LOV abriu nao se perde: ela mudou de lugar. O
# executor verifica o valor do campo depois de preencher (camada exata
# para lov_lista), entao uma LOV que nao abriu produz valor errado e o
# step falha na verificacao — que e uma prova mais forte do que "uma
# janela apareceu".
#
# Substituir por template do proprio popup quando houver um recorte
# medido (o btn_ok_lov_generico.png do repo esta quebrado — e uma tira
# em branco).
PAUSA_LOV = 1.0


class Acoes:
    """
    pausar e injetavel para que o unitario nao durma de verdade — e o
    mesmo motivo de o runner ser injetado: manter o tempo e a tela fora
    da decisao.
    """

    def __init__(self, objetos, runner, resolvedor, esperas,
                 logger=None, pausar=time.sleep):
        self._objetos = objetos
        self._runner = runner
        self._resolvedor = resolvedor
        self._esperas = esperas
        self._logger = logger
        self._pausar = pausar
        # Despacho por dicionario: a lista de tipos que a mecanica sabe
        # executar vira um DADO que se pode ler e comparar com a
        # CHAVES_POR_TIPO da validacao. Uma cadeia de if esconderia essa
        # lista dentro do fluxo de controle.
        self._receitas = {
            "texto": self._receita_digitar,
            "data": self._receita_digitar,
            "lov": self._receita_lov,
            "lov_lista": self._receita_lov_lista,
        }

    def tipos_preenchiveis(self) -> tuple[str, ...]:
        return tuple(self._receitas)

    def _log(self, msg: str) -> None:
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)

    # ------------------------------------------------------------------
    def preencher(self, nome: str, valor: str) -> None:
        elemento = self._elemento(nome)
        tipo = elemento.get("tipo", "texto")
        receita = self._receitas.get(tipo)
        if receita is None:
            raise StepError(f"'{nome}' e do tipo '{tipo}', que nao se preenche.")
        receita(nome, elemento, valor)

    def clicar(self, nome: str) -> None:
        self._runner.click_xy(*self._ponto(nome))
        self._pausar(PAUSA_CLIQUE)

    def clicar_duas_vezes(self, nome: str) -> None:
        """
        Duplo clique — o item de menu do SI3 abre assim. Dois cliques
        separados nao sao equivalentes: o sistema mede o intervalo.
        """
        self._runner.double_click_xy(*self._ponto(nome))
        self._pausar(PAUSA_CLIQUE)

    def _ponto(self, nome: str) -> tuple[int, int]:
        alvo = self._resolvedor.resolver(nome)
        if alvo is None or alvo.ponto is None:
            raise StepError(
                f"'{nome}' inalcancavel — sem template encontrado e sem "
                f"coordenada utilizavel.")
        if alvo.degradado:
            self._log(f"[acoes] '{nome}' resolvido por coordenada fixa — "
                      f"template nao encontrado")
        return alvo.ponto

    def salvar(self, alvo: str) -> None:
        """
        Elemento declarado -> clica nele (botao Salvar). Qualquer outra
        coisa e tecla ou combinacao (f10, ctrl+s). O nucleo nao sabe
        como cada sistema salva — quem sabe e o roteiro.
        """
        if self._objetos.elemento(alvo) is not None:
            self.clicar(alvo)
            return
        self.teclar(alvo)

    def teclar(self, tecla: str) -> None:
        """
        Uma tecla ('enter', 'f10') ou combinacao ('ctrl+s'). Foca a janela
        declarada antes: tecla vai para quem tem o foco.
        """
        self._focar()
        partes = [p.strip().lower() for p in str(tecla).split("+") if p.strip()]
        if not partes:
            raise StepError(f"tecla vazia: {tecla!r}")
        if hasattr(self._runner, "teclar"):
            self._runner.teclar(partes)
        elif len(partes) == 1:
            self._runner.press(partes[0])
        else:
            raise StepError(f"o runner nao sabe teclar combinacoes: {tecla!r}")
        self._pausar(PAUSA_CLIQUE)

    def abrir(self, comando: str) -> None:
        """Inicia a aplicacao sob teste. COMO iniciar e do runner."""
        if not hasattr(self._runner, "abrir_aplicacao"):
            raise StepError("o runner nao sabe abrir aplicacoes.")
        self._runner.abrir_aplicacao(comando)

    # ------------------------------------------------------------------
    def _receita_digitar(self, nome, elemento, valor) -> None:
        self.clicar(nome)
        self._limpar_e_digitar(valor)

    def _receita_lov(self, nome, elemento, valor) -> None:
        self.clicar(nome)
        self._limpar_e_digitar(valor)
        self._runner.press("tab")
        self._pausar(PAUSA_CLIQUE)
        self.clicar(elemento["btn_ok"])

    def _receita_lov_lista(self, nome, elemento, valor) -> None:
        self.clicar(nome)
        self._runner.press("f9")
        self._pausar(PAUSA_LOV)

        self.clicar(elemento["campo_localizar"])
        self._limpar_e_digitar(valor)
        # ENTER dispara a busca: funciona em qualquer LOV do Forms, sem
        # depender da coordenada do botao Localizar (regra 21).
        self._runner.press("enter")
        self._pausar(PAUSA_CLIQUE)
        self.clicar(elemento["btn_ok"])
        self._pausar(PAUSA_CLIQUE)

    def _limpar_e_digitar(self, valor) -> None:
        self._runner.press("backspace", vezes=BACKSPACES)
        self._runner.type_text(str(valor))
        self._pausar(PAUSA)

    def _focar(self) -> None:
        titulo = self._objetos.titulo_janela()
        if not titulo:
            self._log("[acoes] AVISO: tela sem 'titulo_janela' declarado — "
                      "tecla global enviada sem garantir foco")
            return
        if not self._runner.focar_janela(titulo):
            self._log(f"[acoes] AVISO: janela '{titulo}' nao encontrada")

    def _elemento(self, nome: str) -> dict:
        elemento = self._objetos.elemento(nome)
        if elemento is None:
            raise StepError(f"'{nome}' nao declarado em objects/.")
        return elemento