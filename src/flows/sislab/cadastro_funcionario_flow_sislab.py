# src/flows/sislab/cadastro_funcionario_flow_sislab.py
"""
CadastroFuncionarioFlowSislab — SisLab Oracle Forms
Versao: 0.5.7c — Fase A (Observabilidade)

Migrado para _step() centralizado com:
- validated no StepResult
- confirm_template em CF01 (tela de cadastro), CF02 (campo Nome), CF09 (msg_sucesso)
- CausaFalha classificada automaticamente
"""
import time
import pyautogui

from src.core.context import FlowContext
from src.core.result import CausaFalha, FlowResult, StepResult
from src.vision.ocr import OcrHelper


class CadastroFuncionarioFlowSislab:
    """
    Flow de cadastro de funcionário no SisLab (Oracle Forms desktop).

    Pré-condição: usuário já está logado e a tela de Cadastro de Funcionários
    está visível em http://127.0.0.1:5000/funcionarios/

    Estratégia de preenchimento — padrão Oracle Forms:
        Após clicar em Novo, o foco vai automaticamente para o campo Nome.
        A navegação entre campos é feita via Tab — sem cliques intermediários.

    Passos:
        CF01 — Clica em Funcionários no menu principal
        CF02 — Clica em Novo (foco vai para Nome automaticamente)
        CF03 — Digita Nome (Tab para avançar)
        CF04 — Digita CPF (Tab para avançar)
        CF05 — Tab até Cargo + seleciona com seta
        CF06 — Tab até Departamento + seleciona com seta
        CF07 — Tab até Salário + digita
        CF08 — Tab até Admissão + digita
        CF09 — Clica em Salvar + confirm_template msg_sucesso
        CF10 — Verifica nome na grade via OCR

    Templates em templates/sislab/funcionario/:
        btn_novo.png, btn_salvar.png, campo_nome.png,
        tela_cadastro_funcionario.png, msg_sucesso.png

    Templates em templates/sislab/menu/:
        menu_principal.png, btn_funcionarios.png
    """

    FLOW_NAME = "CadastroFuncionarioFlowSislab"

    # Coordenadas — usadas apenas como fallback para botões
    _COORD_BTN_FUNCIONARIOS = (79,  233)
    _COORD_BTN_NOVO         = (25,  146)
    _COORD_BTN_SALVAR       = (85,  148)

    # Região da grade — linha abaixo do cabeçalho
    _REGIAO_GRADE = (0, 615, 1366, 760)

    # Posição do Cargo no dropdown (0=selecione, 1=ANALISYTA DE QA, 2=ANALISTA DE RH)
    # Posição do Departamento    (0=selecione, 1=TECNOLOGIA DA INFOMAÇÃO, 2=ADMINISTRAÇÃO)
    _CARGO_POSICAO = 2
    _DEPTO_POSICAO = 2

    # ------------------------------------------------------------------ #
    #  Ponto de entrada                                                    #
    # ------------------------------------------------------------------ #

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_abrir_funcionarios(ctx, observer),
            lambda: self._step_clicar_novo(ctx, observer),
            lambda: self._step_preencher_nome(ctx, observer),
            lambda: self._step_preencher_cpf(ctx, observer),
            lambda: self._step_selecionar_cargo(ctx, observer),
            lambda: self._step_selecionar_departamento(ctx, observer),
            lambda: self._step_preencher_salario(ctx, observer),
            lambda: self._step_preencher_admissao(ctx, observer),
            lambda: self._step_salvar(ctx, observer),
            lambda: self._step_verificar_salvo_ocr(ctx, observer),
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
    #  Helper — wrapper centralizado de step (Fase A)                      #
    # ------------------------------------------------------------------ #

    def _step(self, step_id: str, descricao: str, fn, observer,
              confirm_template: str = None) -> StepResult:
        """
        Wrapper de execução de step com observabilidade.

        confirm_template: quando informado, o step já executou wait_template
        dentro da fn() e o StepResult.validated reflete essa validacao.
        O parâmetro é registrado para rastreabilidade mesmo quando a validacao
        é feita diretamente na fn().
        """
        if observer:
            observer.log_step_start(step_id, descricao)
        start = time.monotonic()
        validated = None
        try:
            screenshot_path = fn()
            validated = True if confirm_template else None
            step = StepResult(
                step_id=step_id, success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot_path,
                validated=validated,
            )
        except AssertionError as e:
            msg = str(e).lower()
            causa = (CausaFalha.ESTADO_AUSENTE if "estado_ausente" in msg
                     else CausaFalha.SISTEMA)
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa, validated=False,
            )
        except Exception as e:
            msg = str(e).lower()
            causa = CausaFalha.DESCONHECIDA
            if "template" in msg or "not found" in msg:
                causa = CausaFalha.TEMPLATE_NAO_ENCONTRADO
            elif "timeout" in msg:
                causa = CausaFalha.TIMEOUT
            elif "ocr" in msg or "regiao" in msg:
                causa = CausaFalha.OCR_LEITURA
            elif "coordenada" in msg or isinstance(e, KeyError):
                causa = CausaFalha.COORDENADA
            elif "observabilidade" in msg:
                causa = CausaFalha.OCR_LEITURA
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa, validated=False,
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ------------------------------------------------------------------ #
    #  Helper — clicar com fallback de coordenada                          #
    # ------------------------------------------------------------------ #

    def _clicar(self, ctx: FlowContext, template: str, coords: tuple,
                threshold: float = 0.7):
        """Tenta OpenCV; usa coordenadas fixas como fallback silencioso."""
        encontrou = ctx.runner.click_template(template, threshold=threshold)
        if not encontrou:
            print(f"[fallback] '{template}' nao encontrado — usando coords {coords}")
            pyautogui.click(coords[0], coords[1])
            time.sleep(0.5)

    # ------------------------------------------------------------------ #
    #  Steps                                                               #
    # ------------------------------------------------------------------ #

    def _step_abrir_funcionarios(self, ctx: FlowContext, observer=None) -> StepResult:
        def fn():
            ctx.runner.wait_template(
                "templates/sislab/menu/menu_principal.png",
                timeout=10.0, threshold=0.7,
            )
            self._clicar(ctx,
                "templates/sislab/menu/btn_funcionarios.png",
                self._COORD_BTN_FUNCIONARIOS)
            # confirm_template: tela de cadastro deve aparecer
            apareceu = ctx.runner.wait_template(
                "templates/sislab/funcionario/tela_cadastro_funcionario.png",
                timeout=10.0, threshold=0.7,
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: tela_cadastro_funcionario.png nao apareceu. "
                    "Navegacao para Funcionarios pode ter falhado."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF01.png")
        return self._step("CF01", "clicar em Funcionários no menu principal", fn, observer,
                          confirm_template="templates/sislab/funcionario/tela_cadastro_funcionario.png")

    def _step_clicar_novo(self, ctx: FlowContext, observer=None) -> StepResult:
        def fn():
            self._clicar(ctx,
                "templates/sislab/funcionario/btn_novo.png",
                self._COORD_BTN_NOVO)
            # confirm_template: campo Nome deve ficar ativo (amarelo)
            apareceu = ctx.runner.wait_template(
                "templates/sislab/funcionario/campo_nome.png",
                timeout=10.0, threshold=0.7,
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: campo_nome.png nao apareceu apos clicar em Novo. "
                    "Formulario pode nao ter aberto."
                )
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF02.png")
        return self._step("CF02", "clicar em Novo — foco vai para Nome", fn, observer,
                          confirm_template="templates/sislab/funcionario/campo_nome.png")

    def _step_preencher_nome(self, ctx: FlowContext, observer=None) -> StepResult:
        def fn():
            # foco já está no campo Nome após CF02
            ctx.runner.type_text(ctx.config.DADOS["nome"])
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para CPF
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF03.png")
        return self._step("CF03", f"preencher Nome: {ctx.config.DADOS.get('nome', '')}", fn, observer)

    def _step_preencher_cpf(self, ctx: FlowContext, observer=None) -> StepResult:
        def fn():
            ctx.runner.type_text(ctx.config.DADOS["cpf"])
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para E-mail
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para Telefone
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para Cargo
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF04.png")
        return self._step("CF04", "preencher CPF", fn, observer)

    def _step_selecionar_cargo(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Foco está no dropdown Cargo.
        _CARGO_POSICAO = 2 → ANALISTA DE RH (0=selecione, 1=ANALISYTA DE QA, 2=ANALISTA DE RH)
        """
        def fn():
            for _ in range(self._CARGO_POSICAO):
                pyautogui.press("down")
                time.sleep(0.2)
            pyautogui.press("tab")  # avança para Departamento
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF05.png")
        return self._step("CF05", f"selecionar Cargo: {ctx.config.DADOS.get('cargo', '')}", fn, observer)

    def _step_selecionar_departamento(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Foco está no dropdown Departamento.
        _DEPTO_POSICAO = 2 → ADMINISTRAÇÃO
        """
        def fn():
            for _ in range(self._DEPTO_POSICAO):
                pyautogui.press("down")
                time.sleep(0.2)
            pyautogui.press("tab")  # avança para Salário
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF06.png")
        return self._step("CF06", f"selecionar Departamento: {ctx.config.DADOS.get('departamento', '')}", fn, observer)

    def _step_preencher_salario(self, ctx: FlowContext, observer=None) -> StepResult:
        def fn():
            ctx.runner.type_text(ctx.config.DADOS["salario"])
            time.sleep(0.3)
            pyautogui.press("tab")  # avança para Admissão
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF07.png")
        return self._step("CF07", "preencher Salário", fn, observer)

    def _step_preencher_admissao(self, ctx: FlowContext, observer=None) -> StepResult:
        def fn():
            ctx.runner.type_text(ctx.config.DADOS["admissao"])
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF08.png")
        return self._step("CF08", "preencher Data de Admissão", fn, observer)

    def _step_salvar(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Clica em Salvar e valida a mensagem de sucesso via confirm_template.
        confirm_template: templates/sislab/funcionario/msg_sucesso.png
        """
        def fn():
            self._clicar(ctx,
                "templates/sislab/funcionario/btn_salvar.png",
                self._COORD_BTN_SALVAR)
            # confirm_template: mensagem de sucesso deve aparecer
            apareceu = ctx.runner.wait_template(
                "templates/sislab/funcionario/msg_sucesso.png",
                timeout=10.0, threshold=0.7,
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: msg_sucesso.png nao apareceu apos Salvar. "
                    "Verifique se o formulário foi preenchido corretamente."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF09.png")
        return self._step("CF09", "clicar em Salvar e validar mensagem", fn, observer,
                          confirm_template="templates/sislab/funcionario/msg_sucesso.png")

    def _step_verificar_salvo_ocr(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Verifica que o funcionário aparece na grade após salvar via OCR.
        A grade fica na parte inferior da mesma tela de cadastro.

        Se o OCR falhar: abra CF10_ocr_debug.png e ajuste _REGIAO_GRADE.
        """
        def fn():
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
            return screenshot_path
        return self._step("CF10", "verificar nome na grade via OCR", fn, observer)