# vtae/core/apex_helper.py
"""
Helper centralizado para interações específicas do Oracle APEX (MSI3).

Segue o mesmo padrão do OcrHelper — métodos estáticos, independente
do runner, reutilizável por qualquer flow web.

IMPORTANTE — estrutura do MSI3:
    O formulário "Cadastro de Frequência de Aplicação" (e possivelmente
    outros) é renderizado dentro de um iframe. Os seletores do Playwright
    precisam entrar no contexto do iframe antes de localizar elementos.

    Este helper abstrai isso — tenta a página principal primeiro e, se
    não encontrar, tenta dentro do iframe automaticamente.

Seletores validados no MSI3 — APEX 23.1 / Universal Theme 42.

Uso em qualquer flow MSI3:
    from vtae.core.apex_helper import ApexHelper

    ApexHelper.verificar_sem_erro(ctx.runner)
    ApexHelper.aguardar_spinner(ctx.runner)
    ApexHelper.verificar_registro_na_grade(ctx.runner, ctx.config.DADOS["nome"])
"""


class ApexHelper:
    """
    Métodos estáticos para verificação e interação com páginas Oracle APEX.
    Seletores validados no ambiente MSI3 (APEX 23.1 / Universal Theme 42).
    """

    # ------------------------------------------------------------------ #
    #  Seletores — validados no MSI3 (APEX 23.1 / Universal Theme 42)    #
    #                                                                      #
    #  Estrutura real observada:                                           #
    #    - Formulários renderizados dentro de iframe                       #
    #    - Erro:    span#APEX_ERROR_MESSAGE.apex-page-error               #
    #               > div#t_Alert_Notification[role="alert"]               #
    #    - Sucesso: span#APEX_SUCCESS_MESSAGE.apex-page-success            #
    #    - Estilo:  .apex-page-success { display: block } quando visível   #
    # ------------------------------------------------------------------ #

    _SELETORES_ERRO = [
        "#APEX_ERROR_MESSAGE.apex-page-error",
        "#t_Alert_Notification[role='alert']",
        ".t-Alert--warning.t-Alert--page",
        ".apex-page-error",
        "[role='alert']",
    ]

    _SELETORES_SUCESSO = [
        "#APEX_SUCCESS_MESSAGE.apex-page-success",
        ".apex-page-success",
        ".t-Alert--success",
    ]

    _SELETORES_SPINNER = [
        ".u-Processing",
        "#apexir_LOADER",
        ".apex-spinner",
    ]

    # Seletor do iframe do formulário — título visível no DevTools
    _IFRAME_FORMULARIO = "iframe[title='Cadastro de Frequência de Aplicação']"
    # Fallback genérico — pega qualquer iframe de conteúdo do APEX
    _IFRAME_GENERICO   = "iframe[src*='/apex']"

    # ------------------------------------------------------------------ #
    #  Helpers de contexto — página principal ou iframe                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _obter_contextos(runner):
        """
        Retorna lista de contextos para busca: página principal + iframes.
        Garante que verificações funcionam independente de o elemento
        estar na página principal ou dentro de um iframe.
        """
        contextos = [runner._page]

        for seletor_iframe in [
            ApexHelper._IFRAME_FORMULARIO,
            ApexHelper._IFRAME_GENERICO,
        ]:
            try:
                frames = runner._page.frames
                for frame in frames:
                    if frame != runner._page.main_frame:
                        contextos.append(frame)
                break
            except Exception:
                pass

        return contextos

    @staticmethod
    def _wait_em_contextos(runner, seletor: str,
                           state: str, timeout_ms: int):
        """
        Tenta wait_for_selector em todos os contextos disponíveis.
        Retorna (contexto, elemento) se encontrar, lança exceção se não.
        """
        contextos = ApexHelper._obter_contextos(runner)
        ultimo_erro = None

        for ctx_frame in contextos:
            try:
                ctx_frame.wait_for_selector(
                    seletor, state=state, timeout=timeout_ms
                )
                return ctx_frame
            except Exception as e:
                ultimo_erro = e
                continue

        raise ultimo_erro

    @staticmethod
    def _get_text_em_contextos(runner, seletor: str) -> str:
        """
        Busca texto de um elemento em todos os contextos disponíveis.
        Retorna string vazia se não encontrar.
        """
        for ctx_frame in ApexHelper._obter_contextos(runner):
            try:
                el = ctx_frame.locator(seletor).first
                texto = el.text_content()
                if texto and texto.strip():
                    return texto.strip()
            except Exception:
                continue
        return ""

    @staticmethod
    def _is_visible_em_contextos(runner, seletor: str) -> bool:
        """
        Verifica visibilidade em todos os contextos disponíveis.
        """
        for ctx_frame in ApexHelper._obter_contextos(runner):
            try:
                if ctx_frame.locator(seletor).first.is_visible():
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------ #
    #  Verificação de erros                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def verificar_sem_erro(runner, timeout_ms: int = 2000) -> None:
        """
        Verifica que nenhuma mensagem de erro está visível.
        Busca na página principal E dentro de iframes.
        Lança AssertionError com o texto do erro se encontrar.

        Chame após qualquer ação crítica: salvar, submeter, confirmar.

        Exemplo:
            ctx.runner.safe_click("text=Inserir")
            ApexHelper.verificar_sem_erro(ctx.runner)
        """
        for seletor in ApexHelper._SELETORES_ERRO:
            try:
                ApexHelper._wait_em_contextos(
                    runner, seletor, state="visible", timeout_ms=timeout_ms
                )
                texto = ApexHelper._get_text_em_contextos(runner, seletor)
                raise AssertionError(
                    f"APEX retornou erro:\n"
                    f"  Seletor : {seletor}\n"
                    f"  Mensagem: {texto or 'erro sem texto'}"
                )
            except AssertionError:
                raise
            except Exception:
                continue

    @staticmethod
    def obter_mensagem_erro(runner, timeout_ms: int = 2000) -> str | None:
        """
        Retorna o texto do erro se houver, ou None.
        Não lança exceção — útil para tratar o erro no flow.

        Exemplo:
            erro = ApexHelper.obter_mensagem_erro(ctx.runner)
            if erro:
                print(f"[AVISO] {erro}")
        """
        for seletor in ApexHelper._SELETORES_ERRO:
            try:
                ApexHelper._wait_em_contextos(
                    runner, seletor, state="visible", timeout_ms=timeout_ms
                )
                return ApexHelper._get_text_em_contextos(runner, seletor)
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------ #
    #  Verificação de sucesso                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def verificar_sucesso(runner, timeout_ms: int = 5000) -> str:
        """
        Aguarda e retorna texto da mensagem de sucesso.
        Busca na página principal E dentro de iframes.
        Lança AssertionError se não encontrar.

        Exemplo:
            msg = ApexHelper.verificar_sucesso(ctx.runner)
            print(f"[OK] {msg}")
        """
        for seletor in ApexHelper._SELETORES_SUCESSO:
            try:
                ApexHelper._wait_em_contextos(
                    runner, seletor, state="visible", timeout_ms=timeout_ms
                )
                return ApexHelper._get_text_em_contextos(runner, seletor) or "sucesso"
            except Exception:
                continue

        raise AssertionError(
            f"Nenhuma mensagem de sucesso encontrada após {timeout_ms}ms.\n"
            f"Use obter_mensagem_erro() para verificar se o APEX retornou erro."
        )

    # ------------------------------------------------------------------ #
    #  Estado da página                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def aguardar_spinner(runner, timeout_ms: int = 10000) -> None:
        """
        Aguarda o spinner de carregamento do APEX sumir.
        Útil após ações AJAX — complementa o networkidle do navigate().

        Exemplo:
            ctx.runner._page.locator("h3.t-Card-title").click()
            ApexHelper.aguardar_spinner(ctx.runner)
        """
        for seletor in ApexHelper._SELETORES_SPINNER:
            if ApexHelper._is_visible_em_contextos(runner, seletor):
                try:
                    ApexHelper._wait_em_contextos(
                        runner, seletor, state="hidden", timeout_ms=timeout_ms
                    )
                    print(f"[ApexHelper] spinner '{seletor}' sumiu.")
                except Exception:
                    print(f"[ApexHelper] timeout aguardando spinner '{seletor}'.")

    @staticmethod
    def obter_titulo_pagina(runner) -> str:
        """
        Retorna o título da página ou dialog atual.
        Busca na página principal e dentro de iframes.

        Exemplo:
            titulo = ApexHelper.obter_titulo_pagina(ctx.runner)
            assert "Cadastro" in titulo
        """
        for seletor in [".t-Dialog-title", ".t-Body-title",
                        ".t-Region-title", "h1", "h2"]:
            texto = ApexHelper._get_text_em_contextos(runner, seletor)
            if texto:
                return texto
        return ""

    # ------------------------------------------------------------------ #
    #  Leitura de grade                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ler_linhas_grade(runner, seletor_tabela: str = "table") -> list[str]:
        """
        Lê todas as linhas de uma grade do APEX.
        Busca na página principal e dentro de iframes.

        Em sistemas WEB prefira sempre este método ao OcrHelper.
        OcrHelper é para sistemas desktop (Oracle Forms).

        Exemplo:
            linhas = ApexHelper.ler_linhas_grade(ctx.runner)
        """
        for ctx_frame in ApexHelper._obter_contextos(runner):
            try:
                linhas = ctx_frame.locator(
                    f"{seletor_tabela} tbody tr"
                ).all()
                resultado = [
                    l.text_content().strip()
                    for l in linhas
                    if l.text_content().strip()
                ]
                if resultado:
                    return resultado
            except Exception:
                continue
        return []

    @staticmethod
    def verificar_registro_na_grade(
        runner,
        texto: str,
        seletor_tabela: str = "table",
    ) -> None:
        """
        Verifica que um texto aparece em alguma linha da grade.
        Lança AssertionError com as linhas encontradas se não achar.

        Exemplo:
            ApexHelper.verificar_registro_na_grade(
                ctx.runner,
                texto=ctx.config.DADOS["nome"],
                seletor_tabela=".t-Report-report table",
            )
        """
        linhas = ApexHelper.ler_linhas_grade(runner, seletor_tabela)
        encontrado = any(texto.upper() in l.upper() for l in linhas)

        if not encontrado:
            detalhe = (
                "\n".join(f"  {i+1}. {l}" for i, l in enumerate(linhas))
                if linhas else "  (grade vazia ou seletor incorreto)"
            )
            raise AssertionError(
                f"Texto '{texto}' não encontrado na grade.\n"
                f"Linhas encontradas:\n{detalhe}"
            )

        print(f"[ApexHelper] '{texto}' confirmado na grade.")

    # ------------------------------------------------------------------ #
    #  Debug                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def inspecionar_pagina(runner) -> dict:
        """
        Snapshot do estado atual da página para debug.
        Inclui informações de iframes quando presentes.

        Exemplo:
            info = ApexHelper.inspecionar_pagina(ctx.runner)
            print(info)
        """
        frames_info = []
        try:
            for i, frame in enumerate(runner._page.frames):
                frames_info.append({
                    "index": i,
                    "url":   frame.url,
                })
        except Exception:
            pass

        return {
            "url":     runner._page.url,
            "titulo":  ApexHelper.obter_titulo_pagina(runner),
            "erro":    ApexHelper.obter_mensagem_erro(runner),
            "sucesso": ApexHelper._tentar_obter_sucesso(runner),
            "frames":  frames_info,
        }

    @staticmethod
    def _tentar_obter_sucesso(runner) -> str | None:
        """Interno — tenta ler mensagem de sucesso sem lançar exceção."""
        for seletor in ApexHelper._SELETORES_SUCESSO:
            if ApexHelper._is_visible_em_contextos(runner, seletor):
                return ApexHelper._get_text_em_contextos(runner, seletor)
        return None
