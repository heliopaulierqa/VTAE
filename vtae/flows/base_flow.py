# vtae/flows/base_flow.py
"""
BaseFlow — Classe base para todos os flows do VTAE.
Versao: 0.5.25 — verificacao estrutural via pyjab (Java Access Bridge)

Centraliza os helpers que antes eram duplicados em cada flow:
    _step()                    — wrapper padrao com observabilidade completa
    _dado()                    — leitura segura de dado obrigatorio do config.yaml
    _coord()                   — leitura de coordenada com erro claro
    _tpl_existe()               — verifica se template PNG existe antes de usar
    _focar_si3()                — foca janela Oracle Forms (janela nativa)
    _focar_navegador_sislab()  — foca janela do browser (SisLab via navegador)
    _clicar_aguardar()          — clique robusto com confirmacao de tela
    _verify_campo_obrigatorio() — Fase 1: AssertionError se campo ficar vazio ou incorreto (via OCR)
    _verify_campo_opcional()   — Fase 1: aviso nao-bloqueante se campo ficar vazio ou incorreto (via OCR)
    _verify_campo_via_jab()    — v0.5.25: verificacao estrutural EXATA via pyjab,
                                  PARALELA ao OCR — cobre o caso em que a tela
                                  esta "limpa" mas o valor esta errado (match
                                  parcial silencioso em LOV). Ver secao 3.3/3.4
                                  do prompt de instrucao geral v0.5.25.

Todos os flows herdam desta classe e NADA MAIS precisam definir
desses helpers. O _step() canonico foi extraido do AgendamentoFlow
(versao mais completa: confirm_template + validated + CausaFalha).

Migracao:
    Antes: class MeuFlow:
    Depois: class MeuFlow(BaseFlow):
    Remover: _step, _dado, _coord, _tpl_existe, _focar_si3 do flow
    Ajustar: _coord(coords, nome)  — nao passa mais ctx

Novo campo StepResult.description:
    O _step() agora propaga descricao -> StepResult.description
    Isso habilita nomes legiveis nos screenshots e no JSON:
    "L01 - clicar no campo usuario e digitar"

Comparacao OCR (v0.5.19):
    _normalizar() remove acentos antes de comparar — EasyOCR perde acentos
    em fontes Oracle Forms (ex: CAMARA vs CÂMARA).
    _similar() usa distancia de edicao (Levenshtein) com tolerancia de 20%
    para aceitar ruido de OCR em caracteres similares (B/3, O/D, V/I).
    Isso garante que valores corretos passem sem abaixar o rigor para
    valores genuinamente errados.

Verificacao estrutural via pyjab (v0.5.25):
    _verify_campo_via_jab() le o valor REAL do campo via Java Access
    Bridge (.text), nao um bitmap. Comparacao EXATA (via _normalizar),
    SEM tolerancia Levenshtein — nao ha ruido de OCR nessa leitura, entao
    _similar() perderia precisao sem necessidade (regra 30). Usa
    ctx.jab (JABDriver ja conectado, instanciado no fixture ao lado do
    OpenCVRunner) — nao reconecta a cada verificacao. Roda em PARALELO
    a _verify_campo_obrigatorio/_verify_campo_opcional, nao substitui.
"""

import os
import time
import unicodedata

from vtae.core.result import CausaFalha, StepResult


def _normalizar(texto: str) -> str:
    """
    Remove acentos, separadores de data e converte para maiusculo.
    Necessario porque:
    - EasyOCR perde acentos em fontes Oracle Forms (CAMARA vs CÂMARA)
    - Oracle Forms exibe datas como DD/MM/YYYY mas o flow digita DDMMYYYY
    - Separadores / e - sao removidos para comparar apenas os digitos
    """
    sem_acento = (
        unicodedata.normalize("NFD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    sem_separadores = sem_acento.replace("/", "").replace("-", "").replace(".", "")
    return sem_separadores.upper().strip()


def _similar(lido: str, esperado: str, tolerancia: float = 0.230) -> bool:
    """
    Compara dois textos com tolerancia a erros de OCR via distancia de edicao.

    tolerancia=0.20 aceita ate 20% de caracteres diferentes.
    Exemplos reais observados no SI3 (Oracle Forms via Edge, CPU):
      BRUNA  (5 chars)  -> 1 erro permitido  -> '3RUNA' passa  (B/3)
      OLIVIA COSTA (11) -> 2 erros permitidos -> 'DLIIA COSTA' passa (O/D, V/I)
      CÂMARA -> CAMARA  -> ja tratado por _normalizar antes de chegar aqui

    Valores genuinamente errados (ex: 'TESTE ERRO' no lugar de 'AMARELA')
    tem distancia alta e nao passam mesmo com a tolerancia.

    NAO usar em comparacao via pyjab (_verify_campo_via_jab) — leitura
    exata via Access Bridge nao tem ruido de OCR, entao a tolerancia
    perderia precisao sem necessidade (regra 30).

    Args:
        lido:       texto lido pelo OCR (ja normalizado)
        esperado:   texto esperado (ja normalizado)
        tolerancia: fracao maxima de erros permitidos (default 0.20 = 20%)

    Returns:
        True se os textos sao suficientemente similares.
    """
    if not lido or not esperado:
        return False
    # containment rapido — se um contem o outro, OK direto
    if esperado in lido or lido in esperado:
        return True
    # distancia de edicao (Levenshtein) — implementacao iterativa O(n*m)
    a, b = lido, esperado
    if len(a) > len(b):
        a, b = b, a
    distancias = range(len(a) + 1)
    for c2 in b:
        distancias_ = [distancias[0] + 1]
        for c1, d0, d1 in zip(a, distancias, distancias[1:]):
            distancias_.append(min(d1 + 1, d0 + 1, d0 + (c1 != c2)))
        distancias = distancias_
    dist = distancias[-1]
    max_erros = max(1, int(len(esperado) * tolerancia))
    return dist <= max_erros


class BaseFlow:
    """
    Classe base para todos os flows do VTAE.
    Nao instanciar diretamente — usar sempre uma subclasse concreta.
    """

    # ----------------------------------------------------------------
    # _step() — wrapper canonico de execucao de step
    # Versao mais completa: confirm_template + validated + CausaFalha
    # Fonte: AgendamentoFlow v0.5.9 (melhor versao encontrada)
    # ----------------------------------------------------------------

    def _step(
        self,
        step_id: str,
        descricao: str,
        fn,
        observer,
        confirm_template: str = None,
        validated: bool = None,
        ctx=None,
        ocr_lido: str = None,
        ocr_holder: list = None,
        jab_holder: list = None,
    ) -> StepResult:
        """
        Wrapper padrao para todos os steps do VTAE.

        Args:
            step_id:          ID do step (ex: "AB01")
            descricao:        Descricao legivel (ex: "abrir modulo Ambulatorio")
                              Gravada em StepResult.description — aparece no
                              nome do screenshot e no execution.json
            fn:               Funcao lambda sem argumentos que executa o step
            observer:         ExecutionObserver ou None
            confirm_template: Caminho do template PNG que deve aparecer apos
                              a acao — validated=True automatico se encontrar
            validated:        True explicito quando fn() executou verify_lov
                              ou verify_fill internamente
            ctx:              FlowContext — obrigatorio quando confirm_template
                              esta sendo usado

        Returns:
            StepResult com success, duration_ms, description, causa_falha

        Comportamento:
            - confirm_template ausente: tira screenshot, nao verifica tela
            - confirm_template presente: wait_template(8s) + validated=True
            - Falha: classifica CausaFalha automaticamente pelo tipo de excecao
            - Auto-screenshot de diagnostico em caso de falha
        """
        if observer:
            observer.log_step_start(step_id, descricao)
        start = time.monotonic()
        _validated = None
        try:
            screenshot_path = fn()

            # confirm_template: verifica tela destino e marca validated
            if confirm_template and ctx:
                if not ctx.runner.wait_template(confirm_template, timeout=8, threshold=0.7):
                    raise StepError(
                        f"[{step_id}] Tela nao confirmada — template nao encontrado: "
                        f"{confirm_template}"
                    )

            _validated = True if (confirm_template or validated) else None

            # Os holders sao preenchidos pelos helpers de verificacao DURANTE
            # o fn(). Ler AQUI, antes de montar o StepResult, e o que faz o
            # valor chegar ao log: o observer loga na saida do _step, e a
            # atribuicao que os flows fazem depois do return chega tarde.
            _ocr = ocr_lido
            if ocr_holder and ocr_holder[0] is not None:
                _ocr = ocr_holder[0]
            _jab = jab_holder[0] if (jab_holder and jab_holder[0] is not None) else None

            step = StepResult(
                step_id=step_id,
                success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot_path,
                validated=_validated,
                description=descricao,
                ocr_lido=_ocr,
                jab_lido=_jab,
            )
        except AssertionError as e:
            msg = str(e).lower()
            if "ausente no config" in msg:
                causa = CausaFalha.CONFIGURACAO
            elif "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            else:
                causa = CausaFalha.SISTEMA
            step = StepResult(
                step_id=step_id,
                success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
                causa_falha=causa,
                validated=False,
                description=descricao,
            )
            # auto-screenshot de diagnostico
            if ctx:
                try:
                    ctx.runner.screenshot(
                        f"{ctx.evidence_dir}{step_id}_auto_diag_001.png"
                    )
                except Exception:
                    pass
        except Exception as e:
            msg = str(e).lower()
            if "template" in msg or "not found" in msg:
                causa = CausaFalha.TEMPLATE_NAO_ENCONTRADO
            elif "timeout" in msg:
                causa = CausaFalha.TIMEOUT
            elif "coordenada" in msg or isinstance(e, KeyError):
                causa = CausaFalha.COORDENADA
            elif "ocr" in msg or "matricula" in msg or "regiao" in msg:
                causa = CausaFalha.OCR_LEITURA
            elif "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            else:
                causa = CausaFalha.DESCONHECIDA
            step = StepResult(
                step_id=step_id,
                success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
                causa_falha=causa,
                validated=False,
                description=descricao,
            )
            if ctx:
                try:
                    ctx.runner.screenshot(
                        f"{ctx.evidence_dir}{step_id}_auto_diag_001.png"
                    )
                except Exception:
                    pass
        if observer:
            observer.log_step_result(step)
        return step

    # ----------------------------------------------------------------
    # _dado() — leitura segura de dado obrigatorio
    # ----------------------------------------------------------------

    def _dado(self, dados: dict, chave: str, step_id: str):
        """
        Le um dado obrigatorio do config.yaml.
        Falha imediatamente com mensagem clara se a chave nao existir.

        Regra 19: dados.get("chave", "DEFAULT") e PROIBIDO nos flows.
        Todo acesso a dado de teste passa por _dado().

        Raises:
            AssertionError: com mensagem indicando qual chave falta e onde.
        """
        if chave not in dados:
            raise AssertionError(
                f"[{step_id}] Dado obrigatorio ausente no config.yaml: '{chave}'\n"
                f"Adicione '{chave}: <valor>' na secao dados: do config.yaml.\n"
                f"Chaves disponiveis: {list(dados.keys())}"
            )
        return dados[chave]

    # ----------------------------------------------------------------
    # _coord() — leitura de coordenada com erro claro
    # ----------------------------------------------------------------

    def _coord(self, coords: dict, nome: str) -> tuple:
        """
        Le coordenada do dicionario coords (ctx.config.coordenadas).
        Lanca KeyError com mensagem clara se nao configurada.

        Assinatura: _coord(coords, nome) — nao passa ctx.
        Uso: x, y = self._coord(coords, "campo_nome")
        """
        if nome not in coords:
            raise KeyError(
                f"Coordenada '{nome}' nao encontrada em config.yaml -> coordenadas:\n"
                f"Configure com posicao_mouse.py e adicione ao config.yaml."
            )
        c = coords[nome]
        return (c["x"], c["y"])

    # ----------------------------------------------------------------
    # _tpl_existe() — verifica existencia de template antes de usar
    # ----------------------------------------------------------------

    @staticmethod
    def _tpl_existe(path: str) -> bool:
        """
        Verifica se template PNG existe antes de usar wait_template.
        Evita TemplateNotFoundError por arquivo ainda nao capturado.

        Uso obrigatorio antes de qualquer wait_template com template
        que pode nao existir (templates condicionais, em calibracao).
        """
        return os.path.exists(path)

    # ----------------------------------------------------------------
    # _focar_si3() — foca janela Oracle Forms (janela nativa)
    # ----------------------------------------------------------------

    @staticmethod
    def _focar_si3() -> bool:
        """
        Tenta focar a janela do SI3 (Oracle Forms).
        Tolerante — nunca para o flow se falhar.

        Chamar antes de steps criticos que dependem de foco:
        digitacao em campo, cliques em popup, LOV.

        Requer: pip install pygetwindow
        Fallback: retorna False e o flow continua normalmente.
        """
        try:
            import pygetwindow as gw
            janelas = gw.getWindowsWithTitle("FUNDA")
            if not janelas:
                janelas = gw.getWindowsWithTitle("FZ -")
            if not janelas:
                janelas = gw.getWindowsWithTitle("Menu Principal")
            if janelas:
                w = janelas[0]
                if w.isMinimized:
                    w.restore()
                    time.sleep(0.3)
                w.activate()
                time.sleep(0.5)
                return True
            print("[_focar_si3] AVISO: janela SI3 nao encontrada pelo titulo")
            return False
        except ImportError:
            print("[_focar_si3] AVISO: pygetwindow nao instalado — pip install pygetwindow")
            return False
        except Exception as e:
            print(f"[_focar_si3] AVISO: {e}")
            return False

    # ----------------------------------------------------------------
    # _focar_navegador_sislab() — foca janela do browser (SisLab)
    # ----------------------------------------------------------------

    @staticmethod
    def _focar_navegador_sislab(titulo_parcial: str = "SisLab") -> bool:
        """
        Tenta focar a janela do navegador onde o SisLab esta aberto.
        Tolerante — nunca para o flow se falhar.

        Diferente do SI3 (janela nativa separada do Forms), o SisLab abre
        DENTRO da janela do navegador — o foco e pelo titulo da aba/janela
        do browser, nao por um titulo de Forms.

        Chamar antes de steps criticos que dependem de foco:
        digitacao em campo, cliques em popup, F10 de salvar.

        titulo_parcial: parte do titulo da aba do browser onde o SisLab
        esta aberto. Confirmar o titulo exato com o browser aberto antes
        de usar — varia conforme o sistema e o browser.

        Requer: pip install pygetwindow
        Fallback: retorna False e o flow continua normalmente.
        """
        try:
            import pygetwindow as gw
            janelas = [t for t in gw.getAllTitles() if titulo_parcial in t]
            if janelas:
                w = gw.getWindowsWithTitle(janelas[0])[0]
                if w.isMinimized:
                    w.restore()
                    time.sleep(0.3)
                w.activate()
                time.sleep(0.5)
                return True
            print(
                f"[_focar_navegador_sislab] AVISO: janela contendo "
                f"'{titulo_parcial}' nao encontrada"
            )
            return False
        except ImportError:
            print("[_focar_navegador_sislab] AVISO: pygetwindow nao instalado — pip install pygetwindow")
            return False
        except Exception as e:
            print(f"[_focar_navegador_sislab] AVISO: {e}")
            return False

    # ----------------------------------------------------------------
    # _clicar_aguardar() — clique robusto com confirmacao de tela
    # ----------------------------------------------------------------

    def _clicar_aguardar(
        self,
        ctx,
        acao,
        confirmacao: str,
        timeout: float = 12.0,
        threshold: float = 0.7,
        retries: int = 2,
        label: str = "",
    ) -> bool:
        """
        Executa uma acao de clique e aguarda confirmacao visual da tela destino.
        Se a tela nao aparecer no timeout, repete o clique (retry).

        Uso desktop (template PNG):
            self._clicar_aguardar(
                ctx,
                acao=lambda: ctx.runner.safe_click("templates/.../btn.png"),
                confirmacao="templates/.../tela_destino.png",
                label="AI06 admitir paciente",
            )

        Uso web (seletor CSS ou texto):
            self._clicar_aguardar(
                ctx,
                acao=lambda: ctx.runner.safe_click("#btn-salvar"),
                confirmacao="#tela-destino",
                label="MW03 salvar formulario",
            )

        Args:
            ctx:          FlowContext
            acao:         callable sem argumentos — o clique a executar
            confirmacao:  template PNG (desktop) ou seletor/texto (web)
            timeout:      segundos para aguardar confirmacao por tentativa
            threshold:    confianca minima para template matching
            retries:      numero maximo de tentativas apos o clique inicial
            label:        identificacao para mensagem de erro

        Returns:
            True se confirmacao apareceu dentro do timeout.

        Raises:
            AssertionError se esgotou retries sem confirmar.
        """
        # Fallback: se template nao existe ainda, executa sem confirmacao visual
        if not os.path.exists(confirmacao):
            print(
                f"[_clicar_aguardar] AVISO: template ausente — {confirmacao}\n"
                f"  Executando acao sem confirmacao visual (sleep {min(timeout, 3.0)}s).\n"
                f"  Capturar o template para habilitar retry automatico."
            )
            acao()
            time.sleep(min(timeout, 3.0))
            return True

        for tentativa in range(1, retries + 2):  # +2: tentativa inicial + retries
            acao()
            confirmou = ctx.runner.wait_template(
                confirmacao, timeout=timeout, threshold=threshold
            )
            if confirmou:
                return True
            if tentativa <= retries:
                print(
                    f"[_clicar_aguardar] tentativa {tentativa}/{retries + 1} — "
                    f"tela nao confirmada ({label}), reclicando..."
                )
                time.sleep(0.5)

        raise AssertionError(
            f"[_clicar_aguardar] Tela nao confirmada apos {retries + 1} tentativas.\n"
            f"  Label:       {label}\n"
            f"  Confirmacao: {confirmacao}\n"
            f"  Timeout:     {timeout}s por tentativa\n"
            f"Verifique se o template existe e se a tela realmente aparece."
        )

    # ----------------------------------------------------------------
    # _conectar_db() / _obter_via_banco_ou_yaml() — v0.5.28
    # Padrao UNICO de fallback banco->YAML para qualquer campo LOV.
    # Sobe para BaseFlow (nao fica local em nenhum flow especifico)
    # para que o mesmo padrao sirva Ambulatorio, Internacao, SADT, PS
    # sem reinvencao — evita N flows com N logicas de fallback
    # diferentes (regra 5/6 — nao criar variacoes de um padrao ja
    # estabelecido).
    #
    # Excecao conhecida e documentada: campos que precisam de um PAR
    # de valores associados (ex: provedor+plano, que tambem carregam
    # carteirinha/validade do cenario) NAO usam este helper genérico —
    # tem logica propria no flow (ver _resolver_cenario_provedor em
    # admissao_ambulatorio_flow.py). Este helper serve apenas o caso
    # comum: uma lista simples de valores validos para um unico campo.
    # ----------------------------------------------------------------

    def _conectar_db(self, ctx) -> None:
        """
        Conecta o DatabaseRunner sob demanda, cacheado em ctx.db — mesmo
        padrao ja validado do ctx.jab (conecta na primeira necessidade,
        reutilizado pelos steps seguintes do mesmo flow). Nao lanca
        excecao: se falhar, ctx.db permanece None e quem chamar decide
        o fallback (regra 34 — nunca silencioso).

        Le as credenciais de ctx.config.DADOS (db_dsn/db_user/db_senha),
        mesmo padrao ja usado para jab_home_fake — resolvidas via .env,
        nunca hardcoded no config.yaml.
        """
        if getattr(ctx, "db", None):
            return
        try:
            dsn   = ctx.config.DADOS.get("db_dsn")
            user  = ctx.config.DADOS.get("db_user")
            senha = ctx.config.DADOS.get("db_senha")
            from vtae.runners.database_runner import DatabaseRunner
            ctx.db = DatabaseRunner(dsn=dsn, user=user, password=senha)
        except Exception as e:
            print(f"[DB] AVISO: DatabaseRunner nao conectou — "
                  f"fallback YAML sera usado nesta execucao: {e}")

    def _obter_via_banco_ou_yaml(
        self,
        ctx,
        dados: dict,
        step_id: str,
        sql: str,
        coluna: str,
        chave_yaml: str,
        params: dict = None,
    ) -> list:
        """
        Padrao UNICO de fallback banco->YAML para qualquer campo LOV
        com lista simples de valores (Unidade, Procedimento, etc.).

        Fonte de verdade: DatabaseRunner. Fallback: dados[chave_yaml],
        com WARNING explicito (regra 34) — nunca silencioso. Execucao
        em fallback nao conta para o gate de "3x com banco real".

        Interface identica entre banco e YAML — quem chama faz
        random.choice(lista) do mesmo jeito nos dois casos.

        Args:
            ctx:        FlowContext (usa ctx.db, conecta via _conectar_db)
            dados:      dict de dados do config.yaml (fallback)
            step_id:    para mensagens de log (ex: "AB06")
            sql:        SELECT a executar
            coluna:     nome da coluna que vira a lista de valores
            chave_yaml: chave em dados[] com a lista de fallback
            params:     bind variables opcionais do SQL

        Returns:
            Lista de valores (do banco OU do YAML — interface identica).
        """
        self._conectar_db(ctx)
        if getattr(ctx, "db", None):
            try:
                linhas = ctx.db.query(sql, params)
                valores = [l[coluna] for l in linhas]
                if valores:
                    print(f"[{step_id}] '{chave_yaml}' via DatabaseRunner "
                          f"({len(valores)} opcoes)")
                    return valores
                print(f"[{step_id}] WARNING: DatabaseRunner retornou lista "
                      f"vazia para '{chave_yaml}' — usando fallback YAML.")
            except Exception as e:
                print(f"[{step_id}] WARNING: DatabaseRunner indisponivel "
                      f"({e}) — usando fallback YAML para '{chave_yaml}'.")
        return dados.get(chave_yaml) or []
    
    # ----------------------------------------------------------------
    # _resolver_regiao_ocr() — Fase 0.2
    # Fonte UNICA de decisao sobre de onde vem a regiao OCR de um campo.
    # Precedencia: ctx.objects (objects/*.yaml) -> ctx.config.regioes_ocr
    # (config.yaml, para os flows ainda nao migrados ao ObjectRepository).
    # ----------------------------------------------------------------

    def _resolver_regiao_ocr(self, ctx, regiao_key: str):
        """
        Devolve (x1, y1, x2, y2) ou None se a regiao nao esta calibrada
        em nenhuma das duas fontes.

        Bootstrap {0,0,0,0} conta como NAO calibrada: o objects nao
        bloqueia uma regiao que o config ainda tem calibrada.

        O isinstance(r, tuple) e proposital, nao paranoia: 5 arquivos de
        teste unitario usam ctx = MagicMock(), onde ctx.objects existe e
        devolve Mock truthy para qualquer chamada. Validar a FORMA do
        retorno (e nao o tipo de quem o produziu) faz o Mock cair no
        fallback e mantem o BaseFlow desacoplado do ObjectRepository.
        """
        repo = getattr(ctx, "objects", None)
        if repo is not None:
            r = repo.regiao_ocr(regiao_key)
            if isinstance(r, tuple) and len(r) == 4 and any(r):
                return r
        regiao = ctx.config.regioes_ocr.get(regiao_key)
        if regiao and (regiao["x1"] or regiao["y1"]
                       or regiao["x2"] or regiao["y2"]):
            return (regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"])
        return None

    # ----------------------------------------------------------------
    # _verify_campo_obrigatorio() / _verify_campo_opcional()
    # Fase 1 (GATE) — Passo A
    # Implementam o contrato de classificacao de campo:
    # Obrigatorio / Opcional / Popup de erro (ver Fase 1 no roadmap).
    #
    # v0.5.19: comparacao com _similar() (Levenshtein, tolerancia 20%)
    # para aceitar ruido de OCR em fontes Oracle Forms sem abaixar o
    # rigor para valores genuinamente errados.
    # ----------------------------------------------------------------

    def _verify_campo_obrigatorio(
        self,
        ctx,
        nome_campo: str,
        valor_esperado: str,
        step_id: str,
        regiao_key: str,
        ocr_holder: list,
    ) -> None:
        """
        Confirma via OCR que um campo OBRIGATORIO foi preenchido apos
        digitacao/selecao, e que o valor lido e compativel com o esperado.

        Se a regiao OCR ainda nao estiver calibrada
        (bootstrap {x1:0,y1:0,x2:0,y2:0}), avisa e pula a verificacao —
        nao quebra flows que ainda nao foram calibrados campo a campo.

        Comparacao: _normalizar() remove acentos, _similar() aceita ate
        20% de erros de OCR (ruido de fonte Oracle Forms).

        Args:
            ctx:            FlowContext
            nome_campo:     nome do campo para verify_lov (rotulo/log)
            valor_esperado: valor que deveria ter sido digitado/selecionado
            step_id:        ID do step atual (ex: "AB06")
            regiao_key:     nome do objeto em objects/*.yaml; fallback
                            para ctx.config.regioes_ocr
            ocr_holder:     lista de 1 posicao (ex: [None]) — recebe o
                            valor lido, para propagar a StepResult.ocr_lido
                            no padrao ja estabelecido (closure list)

        Raises:
            AssertionError: campo obrigatorio ficou vazio ou com valor incorreto.
        """
        regiao_tupla = self._resolver_regiao_ocr(ctx, regiao_key)
        if regiao_tupla is None:
            print(f"[{step_id}] AVISO: regiao '{regiao_key}' nao calibrada — "
                  f"verificacao OBRIGATORIA pulada (bootstrap).")
            return
        ok, lido = ctx.runner.verify_lov(nome_campo, region=regiao_tupla, timeout=3.0)
        ocr_holder[0] = lido
        lido_norm = _normalizar(lido)
        esperado_norm = _normalizar(str(valor_esperado))
        if not ok or not lido_norm:
            raise AssertionError(
                f"[{step_id}] Campo OBRIGATORIO '{nome_campo}' ficou vazio "
                f"apos digitacao.\n"
                f"Esperado: '{valor_esperado}' | OCR leu: '{lido}'\n"
                f"Verifique se o valor foi aceito pelo sistema."
            )
        if not _similar(lido_norm, esperado_norm):
            raise AssertionError(
                f"[{step_id}] Campo OBRIGATORIO '{nome_campo}' com valor INCORRETO.\n"
                f"Esperado: '{valor_esperado}' | OCR leu: '{lido}'\n"
                f"Distancia de edicao acima do tolerado (20% de '{esperado_norm}').\n"
                f"Possivel valor residual de execucao anterior ou dado rejeitado pelo sistema."
            )
        print(f"[{step_id}] OK — '{nome_campo}' = '{lido}'")

    def _verify_campo_opcional(
        self,
        ctx,
        nome_campo: str,
        valor_esperado: str,
        step_id: str,
        regiao_key: str,
        ocr_holder: list,
    ) -> None:
        """
        Confirma via OCR um campo OPCIONAL. Nunca falha o flow — apenas
        avisa (nao-bloqueante) quando o campo ficou vazio ou com valor
        diferente do esperado, e propaga o valor lido para
        StepResult.ocr_lido via ocr_holder.

        Se a regiao OCR ainda nao estiver calibrada (bootstrap), nao faz
        nada — silenciosamente, sem aviso, ja que campos opcionais nunca
        bloqueiam e a calibracao desses campos e prioridade mais baixa
        (Fase 1 Passo D.5).

        Comparacao: _normalizar() remove acentos, _similar() aceita ate
        20% de erros de OCR (ruido de fonte Oracle Forms).
        """
        regiao_tupla = self._resolver_regiao_ocr(ctx, regiao_key)
        if regiao_tupla is None:
            return
        ok, lido = ctx.runner.verify_lov(nome_campo, region=regiao_tupla, timeout=3.0)
        ocr_holder[0] = lido
        lido_norm = _normalizar(lido)
        esperado_norm = _normalizar(str(valor_esperado))
        if not ok or not lido_norm:
            print(f"[{step_id}] AVISO (nao-bloqueante): campo opcional "
                  f"'{nome_campo}' ficou vazio")
        elif not _similar(lido_norm, esperado_norm):
            print(f"[{step_id}] AVISO (nao-bloqueante): campo opcional "
                  f"'{nome_campo}' com valor DIFERENTE do esperado.\n"
                  f"  Esperado: '{valor_esperado}' | OCR leu: '{lido}'\n"
                  f"  Distancia de edicao acima do tolerado (20% de '{esperado_norm}').\n"
                  f"  Possivel valor residual ou dado nao aceito pelo sistema.")
        else:
            print(f"[{step_id}] OK — '{nome_campo}' = '{lido}'")

    # ----------------------------------------------------------------
    # _verify_campo_via_jab() — v0.5.25
    # Verificacao estrutural EXATA via Java Access Bridge (pyjab).
    # PARALELA a _verify_campo_obrigatorio/_verify_campo_opcional — nao
    # substitui a rede de seguranca OCR ja validada 3x, cobre o caso que
    # o OCR/template estruturalmente nao alcancam: tela "limpa" (sem
    # popup) mas valor errado por match parcial silencioso em LOV.
    # Ver secao 3.3/3.4 do prompt de instrucao geral v0.5.25 — Medicao 3
    # capturou 'PALMEIRAS'/'BASICO' reais apos match parcial incorreto.
    # ----------------------------------------------------------------

    def _verify_campo_via_jab(
        self,
        ctx,
        nome_campo_jab: str,
        valor_esperado: str,
        step_id: str,
        ocr_holder: list,
    ) -> None:
        """
        Confirma o valor REAL de um campo lendo via Java Access Bridge
        (pyjab), nao um bitmap. Roda em PARALELO a
        _verify_campo_obrigatorio/_verify_campo_opcional — nao substitui,
        cobre o caso em que a tela esta "limpa" mas o valor esta errado
        (match parcial silencioso em LOV, ver secao 3.3/3.4 do prompt).

        Comparacao EXATA (via _normalizar), sem tolerancia Levenshtein —
        nao ha ruido de OCR nessa leitura, entao _similar() perderia
        precisao sem necessidade (regra 30).

        Se ctx.jab nao estiver conectado, avisa e pula — mesmo espirito
        do bootstrap de regioes_ocr nao calibradas: nao quebra flows que
        ainda nao tem essa camada ativa.

        Args:
            ctx:            FlowContext — usa ctx.jab (JABDriver conectado)
            nome_campo_jab: o "name" do elemento no Access Bridge
                            (ex: 'Descricao do provedor.')
            valor_esperado: valor que deveria estar no campo
            step_id:        ID do step atual (ex: "AB07")
            ocr_holder:     lista de 1 posicao — recebe o valor lido,
                            mesmo padrao de propagacao para StepResult.ocr_lido

        Raises:
            AssertionError: campo nao encontrado via pyjab, ou valor
                            lido diferente do esperado.
        """
        if not getattr(ctx, "jab", None):
            print(f"[{step_id}] AVISO: ctx.jab nao conectado — "
                  f"verificacao via pyjab pulada.")
            return

        elementos = ctx.jab.find_elements_by_name(nome_campo_jab)
        if not elementos:
            raise AssertionError(
                f"[{step_id}] Campo '{nome_campo_jab}' nao encontrado via pyjab.\n"
                f"Verifique se o name esta correto ou se a janela mudou de foco."
            )

        lido = elementos[0].text
        ocr_holder[0] = lido
        lido_norm = _normalizar(lido)
        esperado_norm = _normalizar(str(valor_esperado))

        if lido_norm != esperado_norm:
            raise AssertionError(
                f"[{step_id}] Campo '{nome_campo_jab}' via pyjab com valor INCORRETO.\n"
                f"Esperado: '{valor_esperado}' | pyjab leu: '{lido}'\n"
                f"Comparacao exata (sem tolerancia) — possivel match parcial "
                f"em LOV ou dado rejeitado pelo sistema."
            )
        print(f"[{step_id}] OK (pyjab) — '{nome_campo_jab}' = '{lido}'")


# Import local para evitar dependencia circular — StepError usado no _step()
try:
    from vtae.core.exceptions import StepError
except ImportError:
    # Fallback se types nao existir — usa AssertionError
    StepError = AssertionError
