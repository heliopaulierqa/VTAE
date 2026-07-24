# src/runners/database_runner.py
"""
DatabaseRunner — leitura apenas, Oracle via oracledb (thin mode).
Versao: v0.5.28 (NOVO)

Papel no VTAE: par de OpenCVRunner/PlaywrightRunner, mas para a camada
de banco. Prova o que o Oracle Forms de fato tem gravado, nao o que a
tela mostra (ver secao 6 do prompt de instrucao geral — matriz de
decisao). Complementa pyjab/OCR, nao substitui.

Uso pretendido (ver secao 5.3 do prompt):
    ctx.db.query("SELECT PRV_NOME FROM SI3_PROVEDORES WHERE PRV_ATIVO = 1")

Conexao:
    Persistente e cacheada — mesmo padrao ja validado do ctx.jab
    (JABDriver). Conecta sob demanda na primeira chamada de query()/
    query_one(), fica aberta pelo resto da execucao. Fechar
    explicitamente com close() no fim do fixture/teardown.

Fonte de verdade == banco. O flow (admissao_ambulatorio_flow.py) e
quem decide o fallback para YAML se query() levantar excecao — este
runner NAO faz fallback sozinho, apenas propaga a excecao para quem
chamou decidir (regra 34: fallback deve ser visivel, com WARNING
explicito no ponto de chamada, nao escondido aqui dentro).

Le apenas — nenhum metodo de escrita/commit/insert/update/delete.
Credenciais somente leitura (confirmar no .env: usuario com privilegio
apenas SELECT nas tabelas de dominio do SI3).
"""

import oracledb


class DatabaseRunner:
    """
    Runner de leitura para o Oracle do SI3 (CNPQDW:1521/DESENV).
    Conexao thin mode — nao requer Oracle Instant Client instalado.
    """

    def __init__(self, dsn: str, user: str, password: str):
        """
        Nao conecta no __init__ — conexao e sob demanda (lazy), no
        mesmo espirito do ctx.jab (JABDriver conecta na primeira
        verificacao, nao na criacao do FlowContext).

        Args:
            dsn:      string de conexao, ex: 'CNPQDW:1521/DESENV'
            user:     usuario Oracle (somente leitura)
            password: senha do usuario
        """
        self._dsn = dsn
        self._user = user
        self._password = password
        self._conn = None

    # ------------------------------------------------------------
    # Conexao sob demanda, cacheada
    # ------------------------------------------------------------

    def _conectar(self):
        if self._conn is None:
            self._conn = oracledb.connect(
                user=self._user,
                password=self._password,
                dsn=self._dsn,
            )
            print(f"[DatabaseRunner] conectado — dsn={self._dsn}")
        return self._conn

    # ------------------------------------------------------------
    # query() — leitura, multiplas linhas
    # ------------------------------------------------------------

    def query(self, sql: str, params: dict | None = None) -> list[dict]:
        """
        Executa um SELECT e retorna todas as linhas como lista de dict
        (nome da coluna -> valor), para uso direto tipo:
            [p['PRV_NOME'] for p in ctx.db.query(sql)]

        Levanta a excecao original do oracledb se a conexao ou a query
        falhar — quem chama (o flow) decide o fallback e loga o
        WARNING (regra 34). Este metodo nao esconde erro.

        Args:
            sql:    comando SELECT
            params: parametros nomeados opcionais (bind variables)

        Returns:
            Lista de dicts, uma entrada por linha retornada.
        """
        conn = self._conectar()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or {})
            colunas = [d[0] for d in cursor.description]
            linhas = cursor.fetchall()
            return [dict(zip(colunas, linha)) for linha in linhas]
        finally:
            cursor.close()

    # ------------------------------------------------------------
    # query_one() — leitura, uma linha (ou None)
    # ------------------------------------------------------------

    def query_one(self, sql: str, params: dict | None = None) -> dict | None:
        """
        Executa um SELECT e retorna a primeira linha como dict, ou
        None se a query nao retornou nenhuma linha.

        Uso tipico: verificacoes pontuais (ex: buscar 1 registro
        especifico por ID) em vez de varrer uma lista completa.
        """
        resultados = self.query(sql, params)
        return resultados[0] if resultados else None

    # ------------------------------------------------------------
    # assert_value() — db_assert pos-flow (ver secao 6 do prompt)
    # ------------------------------------------------------------

    def assert_value(self, sql: str, params: dict, coluna: str,
                      valor_esperado, step_id: str = "") -> None:
        """
        Prova que um valor foi de fato persistido no banco apos o
        flow salvar (F10) — nao apenas que a tela mostrou o valor.
        Complementa a validacao de tela (OCR/pyjab), nao substitui.

        Args:
            sql:            SELECT que deve retornar a linha gravada
                            (tipicamente filtrando por paciente_id ou
                            nr_admissao)
            params:         bind variables do SELECT (ex:
                            {"nr_admissao": "00277657"})
            coluna:         nome da coluna a comparar no resultado
            valor_esperado: valor que deveria estar gravado
            step_id:        para mensagem de erro (ex: "AB15")

        Raises:
            AssertionError: registro nao encontrado, ou coluna com
                            valor diferente do esperado.
        """
        linha = self.query_one(sql, params)
        if linha is None:
            raise AssertionError(
                f"[{step_id}] db_assert: nenhum registro encontrado no banco.\n"
                f"SQL: {sql}\nParams: {params}\n"
                f"Isso indica que o flow NAO persistiu — a tela pode ter "
                f"mostrado sucesso sem gravar de verdade."
            )
        lido = linha.get(coluna)
        if str(lido) != str(valor_esperado):
            raise AssertionError(
                f"[{step_id}] db_assert: coluna '{coluna}' com valor "
                f"INCORRETO no banco.\n"
                f"Esperado: '{valor_esperado}' | Banco tem: '{lido}'"
            )
        print(f"[{step_id}] OK (db_assert) — '{coluna}' = '{lido}' confirmado no banco")

    # ------------------------------------------------------------
    # close() — encerra a conexao explicitamente
    # ------------------------------------------------------------

    def close(self) -> None:
        """
        Fecha a conexao, se estiver aberta. Chamar no teardown do
        fixture/teste, nao no meio do flow (conexao e persistente
        durante toda a jornada — mesmo padrao do ctx.jab).
        """
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as e:
                print(f"[DatabaseRunner] AVISO ao fechar conexao: {e}")
            finally:
                self._conn = None