import time
import pyautogui

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult


class CadastroPacienteFlow:
    """
    Fluxo de cadastro de paciente no SI3 (Oracle Forms — Desktop).
    Pressupõe que o login já foi executado via LoginFlow.

    Navegação:
        Menu Principal → Cadastro de Pacientes (duplo clique)
        → Pesquisar pelo nome → Novo
        → Preencher formulário → Salvar

    Templates necessários em templates/si3/paciente/:
        menu_cadastro_paciente.png
        campo_nome_pesquisa.png
        btn_pesquisar.png
        btn_novo.png
        campo_nome.png
        campo_data_nascimento.png
        campo_hora.png
        campo_mae.png
        campo_pai.png
        campo_cpf.png
        btn_salvar.png
    """

    FLOW_NAME = "CadastroPacienteFlow"

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        """
        Args:
            ctx: FlowContext com runner já autenticado.
            dados: dicionário com os dados do paciente.
                {
                    "nome": "NOME TESTE DE PACIENTE",
                    "data_nascimento": "01/01/1990",
                    "hora": "00:00",
                    "mae": "NOME DA MAE",
                    "pai": "NOME DO PAI",
                    "cpf": "00000000000",
                }
        """
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_menu(ctx, observer),
            lambda: self._step_pesquisar(ctx, dados, observer),
            lambda: self._step_novo(ctx, observer),
            lambda: self._step_nome(ctx, dados, observer),
            lambda: self._step_data_nascimento(ctx, dados, observer),
            lambda: self._step_mae(ctx, dados, observer),
            lambda: self._step_pai(ctx, dados, observer),
            lambda: self._step_cpf(ctx, dados, observer),
            lambda: self._step_salvar(ctx, observer),
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
    # Navegação
    # ──────────────────────────────────────────────

    def _step_menu(self, ctx, observer=None) -> StepResult:
        step_id = "CP01"
        if observer:
            observer.log_step_start(step_id, "duplo clique em Cadastro de Pacientes")
        start = time.monotonic()
        try:
            # Oracle Forms exige duplo clique nos itens de menu
            ctx.runner.double_click(
                "templates/si3/paciente/menu_cadastro_paciente.png",
                threshold=0.7,
            )
            time.sleep(3)  # aguarda a tela de pesquisa abrir
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP01_menu.png")
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

    def _step_pesquisar(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP02"
        if observer:
            observer.log_step_start(step_id, "digitar nome e pesquisar")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(
                "templates/si3/paciente/campo_nome_pesquisa.png",
                threshold=0.7,
            )
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(dados["nome"], interval=0.05)
            time.sleep(0.3)
            ctx.runner.safe_click(
                "templates/si3/paciente/btn_pesquisar.png",
                threshold=0.7,
            )
            time.sleep(2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP02_pesquisa.png")
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

    def _step_novo(self, ctx, observer=None) -> StepResult:
        step_id = "CP03"
        if observer:
            observer.log_step_start(step_id, "clicar em Novo")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(
                "templates/si3/paciente/btn_novo.png",
                threshold=0.7,
            )
            time.sleep(2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP03_novo.png")
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
    # Formulário
    # ──────────────────────────────────────────────

    def _step_nome(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP04"
        if observer:
            observer.log_step_start(step_id, "preencher campo Nome")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(
                "templates/si3/paciente/campo_nome.png",
                threshold=0.7,
            )
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(dados["nome"], interval=0.05)
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP04_nome.png")
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

    def _step_data_nascimento(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP05"
        if observer:
            observer.log_step_start(step_id, "preencher Data de Nascimento e Hora")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(
                "templates/si3/paciente/campo_data_nascimento.png",
                threshold=0.7,
            )
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(dados["data_nascimento"], interval=0.05)
            time.sleep(0.3)

            ctx.runner.safe_click(
                "templates/si3/paciente/campo_hora.png",
                threshold=0.7,
            )
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(dados.get("hora", "00:00"), interval=0.05)
            time.sleep(0.3)

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP05_data.png")
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

    def _step_mae(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP06"
        if observer:
            observer.log_step_start(step_id, "preencher campo Mãe")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(
                "templates/si3/paciente/campo_mae.png",
                threshold=0.7,
            )
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(dados["mae"], interval=0.05)
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP06_mae.png")
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

    def _step_pai(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP07"
        if observer:
            observer.log_step_start(step_id, "preencher campo Pai")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(
                "templates/si3/paciente/campo_pai.png",
                threshold=0.7,
            )
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(dados["pai"], interval=0.05)
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP07_pai.png")
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

    def _step_cpf(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP08"
        if observer:
            observer.log_step_start(step_id, "preencher campo CPF (CIC)")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(
                "templates/si3/paciente/campo_cpf.png",
                threshold=0.7,
            )
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            # remove formatação — Oracle Forms aceita só números
            cpf_numeros = dados["cpf"].replace(".", "").replace("-", "")
            pyautogui.typewrite(cpf_numeros, interval=0.05)
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP08_cpf.png")
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

    def _step_salvar(self, ctx, observer=None) -> StepResult:
        step_id = "CP09"
        if observer:
            observer.log_step_start(step_id, "salvar o cadastro")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(
                "templates/si3/paciente/btn_salvar.png",
                threshold=0.7,
            )
            time.sleep(2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP09_salvo.png")
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
