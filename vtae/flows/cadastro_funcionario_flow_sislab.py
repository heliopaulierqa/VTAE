# vtae/flows/cadastro_funcionario_flow_sislab.py
import time
import pyautogui
from vtae.core.context import FlowContext
from vtae.core.ocr_helper import OcrHelper
from vtae.core.result import FlowResult, StepResult


class CadastroFuncionarioFlowSislab:
    """
    Flow de cadastro de funcionário no SisLab (simulação Oracle Forms desktop).

    Pré-condição: usuário já está logado e a tela de Cadastro de Funcionários
    está visível em http://127.0.0.1:5000/funcionarios/

    Estratégia de preenchimento — padrão Oracle Forms:
        Após clicar em Novo, o foco vai automaticamente para o campo Nome.
        A navegação entre campos é feita via Tab — sem cliques intermediários.
        Isso é o comportamento real do Oracle Forms e do SisLab.

    Passos:
        CF01 — Clica em Funcionários no menu principal
        CF02 — Clica em Novo (foco vai para Nome automaticamente)
        CF03 — Digita Nome (Tab para avançar)
        CF04 — Digita CPF (Tab para avançar)
        CF05 — Tab até Cargo + seleciona com seta
        CF06 — Tab até Departamento + seleciona com seta
        CF07 — Tab até Salário + digita
        CF08 — Tab até Admissão + digita
        CF09 — Clica em Salvar
        CF10 — Verifica nome na grade via OCR

    Templates em templates/sislab/funcionario/:
        btn_novo.png
        btn_salvar.png
        campo_nome.png
        tela_cadastro_funcionario.png

    Templates em templates/sislab/menu/:
        menu_principal.png
        btn_funcionarios.png
    """

    FLOW_NAME = "CadastroFuncionarioFlowSislab"

    # ------------------------------------------------------------------
    # Coordenadas — usadas apenas para Novo e Salvar (botões)
    # Os campos são preenchidos via Tab — sem coordenadas
    # ------------------------------------------------------------------
    _COORD_BTN_FUNCIONARIOS = (79,  233)
    _COORD_BTN_NOVO         = (25,  146)
    _COORD_BTN_SALVAR       = (85,  148)

    # Região da grade — linha abaixo do cabeçalho
    _REGIAO_GRADE = (0, 620, 1366, 660)

    # Posição do Cargo no dropdown (0 = selecione, 1 = ANALISYTA DE QA, 2 = ANALISTA DE RH)
    # Posição do Departamento (0 = selecione, 1 = TECNOLOGIA DA INFOMAÇÃO, 2 = ADMINISTRAÇÃO)
    _CARGO_POSICAO = 2
    _DEPTO_POSICAO = 2

    # ------------------------------------------------------------------ #
    #  Ponto de entrada                                                    #
    # ------------------------------------------------------------------ #

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            self._step_abrir_funcionarios,
            self._step_clicar_novo,
            self._step_preencher_nome,
            self._step_preencher_cpf,
            self._step_selecionar_cargo,
            self._step_selecionar_departamento,
            self._step_preencher_salario,
            self._step_preencher_admissao,
            self._step_salvar,
            self._step_verificar_salvo_ocr,
        ]

        for step_fn in steps:
            step = step_fn(ctx, observer)
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    # ------------------------------------------------------------------ #
    #  Helper — clicar com fallback                                        #
    # ------------------------------------------------------------------ #

    def _clicar(self, ctx: FlowContext, template: str, coords: tuple,
                threshold: float = 0.7):
        """Tenta OpenCV; usa coordenadas fixas como fallback."""
        encontrou = ctx.runner.click_template(template, threshold=threshold)
        if not encontrou:
            print(f"[fallback] '{template}' — coords {coords}")
        time.sleep(0.3)
        pyautogui.click(coords[0], coords[1])
        time.sleep(0.5)

    # ------------------------------------------------------------------ #
    #  Steps de navegação                                                  #
    # ------------------------------------------------------------------ #

    def _step_abrir_funcionarios(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF01"
        if observer:
            observer.log_step_start(step_id, "clicar em Funcionários no menu principal")
        start = time.monotonic()
        try:
            ctx.runner.wait_template(
                "templates/sislab/menu/menu_principal.png",
                timeout=10.0, threshold=0.7,
            )
            self._clicar(ctx,
                "templates/sislab/menu/btn_funcionarios.png",
                self._COORD_BTN_FUNCIONARIOS)
            ctx.runner.wait_template(
                "templates/sislab/funcionario/tela_cadastro_funcionario.png",
                timeout=10.0, threshold=0.7,
            )
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF01.png")
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

    def _step_clicar_novo(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF02"
        if observer:
            observer.log_step_start(step_id, "clicar em Novo — foco vai para Nome")
        start = time.monotonic()
        try:
            self._clicar(ctx,
                "templates/sislab/funcionario/btn_novo.png",
                self._COORD_BTN_NOVO)
            # aguarda campo Nome ficar amarelo (estado ativo após Novo)
            ctx.runner.wait_template(
                "templates/sislab/funcionario/campo_nome.png",
                timeout=10.0, threshold=0.7,
            )
            time.sleep(0.5)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF02.png")
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
    #  Steps de preenchimento — navegação por Tab                          #
    # ------------------------------------------------------------------ #

    def _step_preencher_nome(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Foco já está no Nome após clicar em Novo.
        Digita diretamente e avança com Tab.
        """
        step_id = "CF03"
        nome = ctx.config.DADOS["nome"]
        if observer:
            observer.log_step_start(step_id, f"Preencher Nome: {nome}")
        start = time.monotonic()
        try:
            # foco já está no campo Nome — digita direto
            ctx.runner.type_text(nome)
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para CPF
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF03.png")
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

    def _step_preencher_cpf(self, ctx: FlowContext, observer=None) -> StepResult:
        """Foco está no CPF após Tab do Nome."""
        step_id = "CF04"
        if observer:
            observer.log_step_start(step_id, "Preencher CPF")
        start = time.monotonic()
        try:
            ctx.runner.type_text(ctx.config.DADOS["cpf"])
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para E-mail
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para Telefone
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para Cargo
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF04.png")
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

    def _step_selecionar_cargo(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Foco está no dropdown Cargo.
        Navega pelas opções com seta para baixo.
        _CARGO_POSICAO = 2 → ANALISTA DE RH (0=selecione, 1=ANALISYTA DE QA, 2=ANALISTA DE RH)
        """
        step_id = "CF05"
        cargo = ctx.config.DADOS["cargo"]
        if observer:
            observer.log_step_start(step_id, f"Selecionar Cargo: {cargo}")
        start = time.monotonic()
        try:
            for _ in range(self._CARGO_POSICAO):
                pyautogui.press("down")
                time.sleep(0.2)
            pyautogui.press("tab")  # avança para Departamento
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF05.png")
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

    def _step_selecionar_departamento(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Foco está no dropdown Departamento.
        _DEPTO_POSICAO = 2 → ADMINISTRAÇÃO (0=selecione, 1=TECNOLOGIA DA INFOMAÇÃO, 2=ADMINISTRAÇÃO)
        """
        step_id = "CF06"
        depto = ctx.config.DADOS["departamento"]
        if observer:
            observer.log_step_start(step_id, f"Selecionar Departamento: {depto}")
        start = time.monotonic()
        try:
            for _ in range(self._DEPTO_POSICAO):
                pyautogui.press("down")
                time.sleep(0.2)
            pyautogui.press("tab")  # avança para Salário
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF06.png")
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

    def _step_preencher_salario(self, ctx: FlowContext, observer=None) -> StepResult:
        """Foco está no campo Salário após Tab do Departamento."""
        step_id = "CF07"
        if observer:
            observer.log_step_start(step_id, "Preencher Salário")
        start = time.monotonic()
        try:
            ctx.runner.type_text(ctx.config.DADOS["salario"])
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para Admissão
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF07.png")
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

    def _step_preencher_admissao(self, ctx: FlowContext, observer=None) -> StepResult:
        """Foco está no campo Admissão após Tab do Salário."""
        step_id = "CF08"
        if observer:
            observer.log_step_start(step_id, "Preencher Data de Admissão")
        start = time.monotonic()
        try:
            ctx.runner.type_text(ctx.config.DADOS["admissao"])
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF08.png")
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

    def _step_salvar(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Clica em Salvar e valida a mensagem de sucesso via template matching.
        Template: templates/sislab/funcionario/msg_sucesso.png
        """
        step_id = "CF09"
        if observer:
            observer.log_step_start(step_id, "Clicar em Salvar e validar mensagem")
        start = time.monotonic()
        try:
            self._clicar(ctx,
                "templates/sislab/funcionario/btn_salvar.png",
                self._COORD_BTN_SALVAR)

            # valida mensagem de sucesso — mais confiável que OCR para confirmar save
            sucesso = ctx.runner.wait_template(
                "templates/sislab/funcionario/msg_sucesso.png",
                timeout=10.0, threshold=0.7,
            )
            if not sucesso:
                raise AssertionError(
                    "Mensagem 'Funcionário salvo com sucesso' não apareceu.\n"
                    "Verifique se o formulário foi preenchido corretamente."
                )

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CF09.png")
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

    def _step_verificar_salvo_ocr(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Verifica que o funcionário aparece na grade após salvar via OCR.
        A grade fica na parte inferior da mesma tela de cadastro.

        Se o OCR falhar: abra CF10_ocr_debug.png e ajuste _REGIAO_GRADE.
        """
        step_id = "CF10"
        if observer:
            observer.log_step_start(step_id, "Verificar nome na grade via OCR")
        start = time.monotonic()
        try:
            time.sleep(0.8)
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}CF10.png")

            nome_esperado = ctx.config.DADOS["nome"].upper()
            encontrado, token = OcrHelper.contem_qualquer_token(
                screenshot_path,
                tokens=nome_esperado.split(),
                regiao=self._REGIAO_GRADE,
            )

            if not encontrado:
                OcrHelper.salvar_debug(screenshot_path, self._REGIAO_GRADE,
                                       f"{ctx.evidence_dir}CF10_ocr_debug.png")
                texto_lido = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_GRADE)
                raise AssertionError(
                    f"Nome '{nome_esperado}' não encontrado na grade.\n"
                    f"Texto lido pelo OCR:\n{texto_lido}\n"
                    f"Veja o debug em: {ctx.evidence_dir}CF10_ocr_debug.png\n"
                    f"Ajuste _REGIAO_GRADE = (x1, y1, x2, y2) conforme o screenshot."
                )

            print(f"[CF10] OCR confirmou '{token}' do nome '{nome_esperado}' na grade.")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot_path)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        if observer:
            observer.log_step_result(step)
        return step
