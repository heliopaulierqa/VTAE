# vtae/runners/jab_reader.py
"""
Leitor exato via Java Access Bridge — o adaptador que faltava entre o
pyjab e o motor.

O Verificador (peca 3) pede um objeto com .ler(locator) -> str | None e
nunca importa pyjab. Este e esse objeto para Oracle Forms; o equivalente
web (Playwright input_value) e a peca 5.

Padrao de conexao copiado do AB07 do admissao_ambulatorio_flow.py, que
esta validado 3x em tela real:
  - JAVA_HOME de mentira vem do config (.env), NUNCA de setx (regra 31)
  - tem que ser setado ANTES do import pyjab: a DLL e procurada no import
  - conexao sob demanda, cacheada — nao reconecta a cada campo

Tolerante por decisao (regra 45): .ler devolve None quando nao consegue
ler. Quem transforma isso em aviso ou falha e o Verificador, que sabe se
o tipo do campo EXIGE camada exata. Explodir aqui tiraria essa decisao
de quem tem contexto para toma-la.
"""
import os

# Segundos que o JABDriver pode gastar procurando a janela Java antes de
# desistir. O default do pyjab e longo: em 05/08 o teste ficou 2min40
# parado no S07, dentro de jabdriver.py:205, ate o Ctrl+C. Camada de
# verificacao nao pode segurar a jornada — se o Access Bridge nao
# responde, isso e degradacao (aviso), nao motivo para travar.
TIMEOUT_CONEXAO = 10


class LeitorJab:
    """
    titulo: titulo da janela Java — e o 'tela.titulo_jab' do objects/,
    nao um titulo de janela do Windows. No cadastro e 'Form_Pac0010'.
    """

    def __init__(self, titulo: str, jab_home: str = None, logger=None,
                 timeout: int = TIMEOUT_CONEXAO):
        self._titulo = titulo
        self._jab_home = jab_home
        self._logger = logger
        self._timeout = timeout
        self._driver = None
        # Uma falha de conexao nao se repete a cada campo: 14 steps
        # tentando abrir o Access Bridge que nao existe custaria minutos.
        self._desistiu = False

    def _log(self, msg: str) -> None:
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)

    def _conectar(self) -> None:
        if self._driver is not None or self._desistiu:
            return
        try:
            if self._jab_home:
                os.environ["JAVA_HOME"] = self._jab_home
            from pyjab.jabdriver import JABDriver
            self._driver = JABDriver(title=self._titulo,
                                     timeout=self._timeout)
            self._log(f"[jab] conectado a janela Java '{self._titulo}'")
        except Exception as erro:
            self._desistiu = True
            self._log(f"[jab] AVISO: nao conectou a '{self._titulo}' — a "
                      f"verificacao cai para OCR nesta execucao: {erro}")

    def ler(self, nome: str) -> str | None:
        self._conectar()
        if self._driver is None:
            return None
        try:
            elementos = self._driver.find_elements_by_name(nome)
        except Exception as erro:
            self._log(f"[jab] AVISO: falha ao procurar '{nome}': {erro}")
            return None
        if not elementos:
            self._log(f"[jab] AVISO: nenhum elemento com name '{nome}'")
            return None
        return elementos[0].text
