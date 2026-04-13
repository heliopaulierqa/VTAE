import time
import pyautogui

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult


class FrequenciaAplicacaoFlow:
    """
    Fluxo de cadastro de Frequência de Aplicação no MSI3.
    Pressupõe que o login já foi executado via LoginFlowMsi3.

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
            lambda: self._step_validar(ctx, observer),   # valida antes do confirmar
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

    # ──────────────────────────────────────────────
    # Navegação (Playwright)
    # ──────────────────────────────────────────────

    def _step_sistema_pacientes(self, ctx, observer=None) -> StepResult:
        step_id = "FA01"
        if observer:
            observer.log_step_start(step_id, "clicar em Sistema de Pacientes")
        start = time.monotonic()
        try:
            ctx.runner._page.locator("h3.t-Card-title", has_text="Sistema de Pacientes").click()
            ctx.runner.wait_template("h3.t-Card-title >> text=Apoio à Assistência", timeout=15.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA01_sistema_pacientes.png")
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
            ctx.runner._page.locator("h3.t-Card-title", has_text="Apoio à Assistência").click()
            ctx.runner.wait_template("h3.t-Card-title >> text=Cadastros Básicos", timeout=15.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA02_apoio_assistencia.png")
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
            ctx.runner._page.locator("h3.t-Card-title", has_text="Cadastros Básicos").click()
            ctx.runner.wait_template("h3.t-Card-title >> text=Frequência de Aplicação", timeout=15.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA03_cadastros_basicos.png")
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

    # ──────────────────────────────────────────────
    # Navegação (OpenCV)
    # ──────────────────────────────────────────────

    def _step_frequencia_aplicacao(self, ctx, observer=None) -> StepResult:
        step_id = "FA04"
        if observer:
            observer.log_step_start(step_id, "clicar em Frequência de Aplicação")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/cadastros_basicos/frequencia_aplicacao.png")
            ctx.runner.wait_template("text=Novo Cadastro", timeout=15.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA04_frequencia_aplicacao.png")
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
            time.sleep(2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA05_novo_cadastro.png")
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

    # ──────────────────────────────────────────────
    # Formulário (OpenCV + PyAutoGUI)
    # ──────────────────────────────────────────────

    def _step_preencher_formulario(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "FA06"
        if observer:
            observer.log_step_start(step_id, "preencher campos do formulário")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.6)

            time.sleep(1)

            if dados.get("sequencia"):
                cv.safe_click("templates/msi3/formulario/campo_sequencia.png")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["sequencia"], interval=0.05)
                time.sleep(0.3)

            if dados.get("codigo"):
                cv.safe_click("templates/msi3/formulario/campo_codigo.png")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["codigo"], interval=0.05)
                time.sleep(0.3)

            if dados.get("descricao"):
                cv.safe_click("templates/msi3/formulario/campo_descricao.png")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["descricao"], interval=0.05)
                time.sleep(0.3)

            if dados.get("tipo_aplicacao"):
                cv.safe_click("templates/msi3/formulario/campo_tipo_aplicacao.png")
                time.sleep(0.5)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["tipo_aplicacao"], interval=0.05)
                time.sleep(0.3)

            if dados.get("qt_dias_semana"):
                cv.safe_click("templates/msi3/formulario/campo_qt_dias_semana.png")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["qt_dias_semana"], interval=0.05)
                time.sleep(0.3)

            if dados.get("qt_24hs"):
                cv.safe_click("templates/msi3/formulario/campo_qt_24hs.png")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["qt_24hs"], interval=0.05)
                time.sleep(0.3)

            if dados.get("intervalo_hrs"):
                cv.safe_click("templates/msi3/formulario/campo_intervalo_hrs.png")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["intervalo_hrs"], interval=0.05)
                time.sleep(0.3)

            if dados.get("intervalo_min"):
                cv.safe_click("templates/msi3/formulario/campo_intervalo_min.png")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.typewrite(dados["intervalo_min"], interval=0.05)
                time.sleep(0.3)

            # checkbox por último
            if dados.get("frequencia_tipo_unica"):
                cv.safe_click("templates/msi3/formulario/checkbox_frequencia_unica.png")
                time.sleep(0.5)

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA06_formulario.png")
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

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA07_horario_padrao.png")
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
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA08_inserir.png")
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

    # ──────────────────────────────────────────────
    # Validação — antes do confirmar
    # ──────────────────────────────────────────────

    def _step_validar(self, ctx, observer=None) -> StepResult:
        step_id = "FA10"
        if observer:
            observer.log_step_start(step_id, "validar SF - SV FARMACIA na tabela do modal")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.6)

            time.sleep(1)

            # verifica se o resultado aparece na tabela do modal
            encontrou = cv.is_visible("templates/msi3/formulario/resultado_farmacia.png")
            if not encontrou:
                raise RuntimeError(
                    "Validação falhou — 'SF - SV FARMACIA' não encontrado "
                    "na tabela do modal após o Inserir."
                )

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA10_validacao.png")
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
        step_id = "FA09"
        if observer:
            observer.log_step_start(step_id, "clicar em Confirmar")
        start = time.monotonic()
        try:
            from vtae.runners.opencv_runner import OpenCVRunner
            cv = OpenCVRunner(confidence=0.7)
            cv.safe_click("templates/msi3/formulario/btn_confirmar.png")
            time.sleep(2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}FA09_confirmado.png")
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
