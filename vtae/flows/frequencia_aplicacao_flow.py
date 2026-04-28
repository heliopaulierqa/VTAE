# vtae/flows/frequencia_aplicacao_flow.py
import time
import pyautogui

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult
from vtae.core.apex_helper import ApexHelper


class FrequenciaAplicacaoFlow:
    """
    Fluxo de cadastro de Frequência de Aplicação no MSI3.
    Pressupõe que o login já foi executado via LoginFlowMsi3.

    Melhorias com ApexHelper:
        FA01/02/03 — aguardar_spinner após navegação (substitui sleep implícito)
        FA05       — aguardar_spinner substitui time.sleep(2) fixo
        FA08       — verificar_sem_erro após inserir
        FA09       — verificar_sucesso após confirmar + inspecionar_pagina no except
        FA10       — mantém OpenCV como validação primária (template visual
                     é mais confiável que seletor no modal do MSI3)

    Ordem de execução:
        FA01 → Sistema de Pacientes
        FA02 → Apoio à Assistência
        FA03 → Cadastros Básicos
        FA04 → Frequência de Aplicação (OpenCV)
        FA05 → Novo Cadastro (OpenCV)
        FA06 → Preencher formulário
        FA07 → Horário Padrão
        FA08 → Inserir
        FA10 → Validar (SF - SV FARMACIA na tabela do modal)
        FA09 → Confirmar
    """

    FLOW_NAME = "FrequenciaAplicacaoFlow"

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        """
        Args:
            ctx: FlowContext com runner já autenticado.
            dados: dicionário com os dados do cadastro.
                {
                    "sequencia": "4537",
                    "codigo": "SV62",
                    "descricao": "TESTE VTAE AKTC4853",
                    "tipo_aplicacao": "Medicamento",
                    "frequencia_tipo_unica": True,
                    "qt_dias_semana": "6",
                    "qt_24hs": "6",
                    "intervalo_hrs": "24",
                    "intervalo_min": "12",
                    "hora": "12:00",
                    "unidade_funcional": "SF - SV FARMACIA",
                }
        """
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_sistema_pacientes(ctx, observer),
            lambda: self._step_apoio_assistencia(ctx, observer),
            lambda: self._step_cadastros_basicos(ctx, observer),
            lambda: self._step_frequencia_aplicacao(ctx, observer),
            lambda: self._step_novo_cadastro(ctx, observer),
            lambda: self._step_preencher_formulario(ctx, dados, observer),
            lambda: self._step_horario_padrao(ctx, dados, observer),
            lambda: self._step_inserir(ctx, observer),
            lambda: self._step_validar(ctx, observer),
            lambda: self._step_confirmar(ctx, observer),
        ]

        for step_fn in steps:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)

        return result

    # ------------------------------------------------------------------ #
    #  Navegação — Playwright                                             #
    # ------------------------------------------------------------------ #

    def _step_sistema_pacientes(self, ctx, observer=None) -> StepResult:
        step_id = "FA01"
        if observer:
            observer.log_step_start(step_id, "clicar em Sistema de Pacientes")
        start = time.monotonic()
        try:
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Sistema de Pacientes"
            ).click()

            # MELHORIA — aguarda spinner do APEX sumir após clique AJAX
            # antes: implícito no wait_template (mas spinner pode conflitar)
            # depois: spinner some → wait_template confirma a tela
            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Apoio à Assistência", timeout=15.0
            )

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA01_sistema_pacientes.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_apoio_assistencia(self, ctx, observer=None) -> StepResult:
        step_id = "FA02"
        if observer:
            observer.log_step_start(step_id, "clicar em Apoio à Assistência")
        start = time.monotonic()
        try:
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Apoio à Assistência"
            ).click()

            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Cadastros Básicos", timeout=15.0
            )

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA02_apoio_assistencia.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_cadastros_basicos(self, ctx, observer=None) -> StepResult:
        step_id = "FA03"
        if observer:
            observer.log_step_start(step_id, "clicar em Cadastros Básicos")
        start = time.monotonic()
        try:
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Cadastros Básicos"
            ).click()

            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Frequência de Aplicação", timeout=15.0
            )

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA03_cadastros_basicos.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    # ------------------------------------------------------------------ #
    #  Navegação — OpenCV                                                 #
    # ------------------------------------------------------------------ #

    def _step_frequencia_aplicacao(self, ctx, observer=None) -> StepResult:
        step_id = "FA04"
        if observer:
            observer.log_step_start(step_id, "clicar em Frequência de Aplicação")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/cadastros_basicos/frequencia_aplicacao.png")

            # Playwright confirma que a tela carregou
            ctx.runner.wait_template("text=Novo Cadastro", timeout=15.0)

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA04_frequencia_aplicacao.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_novo_cadastro(self, ctx, observer=None) -> StepResult:
        step_id = "FA05"
        if observer:
            observer.log_step_start(step_id, "clicar em Novo Cadastro")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/cadastros_basicos/btn_novo_cadastro.png")

            # MELHORIA — aguarda spinner em vez de sleep fixo
            # antes: time.sleep(2)
            # depois: aguarda o APEX terminar de renderizar o formulário
            ApexHelper.aguardar_spinner(ctx.runner)

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA05_novo_cadastro.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    # ------------------------------------------------------------------ #
    #  Formulário — OpenCV + PyAutoGUI                                    #
    # ------------------------------------------------------------------ #

    def _step_preencher_formulario(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "FA06"
        if observer:
            observer.log_step_start(step_id, "preencher campos do formulário")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.6)

            time.sleep(1)

            campos = [
                ("sequencia",        "templates/msi3/formulario/campo_sequencia.png"),
                ("codigo",           "templates/msi3/formulario/campo_codigo.png"),
                ("descricao",        "templates/msi3/formulario/campo_descricao.png"),
                ("tipo_aplicacao",   "templates/msi3/formulario/campo_tipo_aplicacao.png"),
                ("qt_dias_semana",   "templates/msi3/formulario/campo_qt_dias_semana.png"),
                ("qt_24hs",          "templates/msi3/formulario/campo_qt_24hs.png"),
                ("intervalo_hrs",    "templates/msi3/formulario/campo_intervalo_hrs.png"),
                ("intervalo_min",    "templates/msi3/formulario/campo_intervalo_min.png"),
            ]

            for chave, template in campos:
                if dados.get(chave):
                    cv.safe_click(template)
                    time.sleep(0.3)
                    pyautogui.hotkey("ctrl", "a")
                    pyautogui.typewrite(dados[chave], interval=0.05)
                    time.sleep(0.3)

            if dados.get("frequencia_tipo_unica"):
                cv.safe_click("templates/msi3/formulario/checkbox_frequencia_unica.png")
                time.sleep(0.5)

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA06_formulario.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_horario_padrao(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "FA07"
        if observer:
            observer.log_step_start(step_id, "preencher Horário Padrão")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.7)

            if dados.get("hora"):
                cv.safe_click("templates/msi3/formulario/campo_hora.png")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["hora"], interval=0.05)
                time.sleep(0.3)

            if dados.get("unidade_funcional"):
                cv.safe_click("templates/msi3/formulario/campo_unidade_funcional.png")
                time.sleep(0.5)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["unidade_funcional"], interval=0.05)
                time.sleep(0.5)
                cv.safe_click("templates/msi3/formulario/btn_pesquisar.png")
                time.sleep(3.0)
                cv.confidence = 0.6
                cv.safe_click("templates/msi3/formulario/resultado_farmacia.png")
                cv.confidence = 0.7
                time.sleep(0.5)

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA07_horario_padrao.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_inserir(self, ctx, observer=None) -> StepResult:
        step_id = "FA08"
        if observer:
            observer.log_step_start(step_id, "clicar em Inserir")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/formulario/btn_inserir.png")
            time.sleep(1)

            # MELHORIA — verifica se o APEX retornou erro após inserir
            # antes: seguia para FA10 sem saber se o insert funcionou
            # depois: erro do APEX vira mensagem clara no log
            ApexHelper.verificar_sem_erro(ctx.runner)

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA08_inserir.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    # ------------------------------------------------------------------ #
    #  Validação e confirmação                                            #
    # ------------------------------------------------------------------ #

    def _step_validar(self, ctx, observer=None) -> StepResult:
        """
        Valida SF - SV FARMACIA na tabela do modal.
        Mantém OpenCV como estratégia primária — o modal do MSI3
        renderiza elementos visuais que o template matching captura
        com mais confiança do que seletores CSS nesse contexto.
        """
        step_id = "FA10"
        if observer:
            observer.log_step_start(
                step_id, "validar SF - SV FARMACIA na tabela do modal"
            )
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.6)

            time.sleep(1)

            encontrou = cv.is_visible(
                "templates/msi3/formulario/resultado_farmacia.png"
            )
            if not encontrou:
                raise RuntimeError(
                    "Validação falhou — 'SF - SV FARMACIA' não encontrado "
                    "na tabela do modal após o Inserir."
                )

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA10_validacao.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step

    def _step_confirmar(self, ctx, observer=None) -> StepResult:
        """
        Clica em Confirmar e valida o sucesso lendo a grade de resultados.

        Por que grade e não mensagem de sucesso:
            O MSI3 não exibe mensagem explícita após confirmar — ele
            simplesmente volta para a listagem. A validação real é
            verificar que o registro aparece na grade com o código
            ou descrição cadastrados.

        Seletor da grade validado no ambiente:
            Tabela "Cadastro de Frequência de Aplicação"
            colunas: Editar | Sequência | Código | Descrição
        """
        step_id = "FA09"
        if observer:
            observer.log_step_start(step_id, "clicar em Confirmar e validar na grade")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/formulario/btn_confirmar.png")

            # aguarda voltar para a listagem — iframe some, grade aparece
            ctx.runner.wait_template("text=Novo Cadastro", timeout=15.0)
            ApexHelper.aguardar_spinner(ctx.runner)

            # valida que o registro aparece na grade
            # usa código ou descrição — ambos únicos pelo Faker
            texto_busca = (
                ctx.dados.get("codigo") or
                ctx.dados.get("descricao", "")
            ) if hasattr(ctx, "dados") else ""

            if texto_busca:
                ApexHelper.verificar_registro_na_grade(
                    ctx.runner,
                    texto=texto_busca,
                    seletor_tabela=".t-Report-report table, table",
                )
                print(f"[FA09] Registro '{texto_busca}' confirmado na grade.")
            else:
                # sem dados para validar — pelo menos confirma que voltou
                # para a listagem (wait_template já garantiu isso)
                print("[FA09] Confirmar executado — listagem carregada.")

            screenshot = ctx.runner.screenshot(
                f"{ctx.evidence_dir}FA09_confirmado.png"
            )
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            try:
                info = ApexHelper.inspecionar_pagina(ctx.runner)
                print(
                    f"[FA09 debug] URL: {info['url']} | "
                    f"Título: {info['titulo']} | "
                    f"Erro APEX: {info['erro']} | "
                    f"Frames: {info['frames']}"
                )
            except Exception:
                pass
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step
