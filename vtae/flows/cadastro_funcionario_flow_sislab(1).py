# vtae/flows/cadastro_funcionario_flow_sislab.py
import time
import pyautogui
from vtae.core.context import FlowContext
from vtae.core.ocr_helper import OcrHelper
from vtae.core.result import FlowResult, StepResult


class CadastroFuncionarioFlowSislab:
    """
    Flow de cadastro de funcionário no SisLab (Oracle Forms desktop).

    Pré-condição: usuário já está logado e o Menu Principal está visível.

    Passos:
        CF01 — Clicar em Funcionários (menu Cadastros)
        CF02 — Clicar no botão Novo
        CF03 — Preencher Nome
        CF04 — Preencher CPF
        CF05 — Preencher Cargo
        CF06 — Preencher Salário
        CF07 — Preencher Data de Admissão
        CF08 — Clicar em Salvar
        CF09 — Verificar nome na grade via OCR
    """

    FLOW_NAME = "CadastroFuncionarioFlowSislab"

    # Coordenadas de fallback — capture com scripts/posicao_mouse.py
    _COORD_MENU_FUNCIONARIOS = (130, 185)
    _COORD_BTN_NOVO          = (55,  68)
    _COORD_CAMPO_NOME        = (370, 160)
    _COORD_CAMPO_CPF         = (370, 183)
    _COORD_CAMPO_CARGO       = (370, 206)
    _COORD_CAMPO_SALARIO     = (370, 229)
    _COORD_CAMPO_ADMISSAO    = (370, 252)
    _COORD_BTN_SALVAR        = (110, 68)

    # Região da grade (x1, y1, x2, y2) — ajuste para o ambiente
    # Recorta só a tabela de resultados, descartando o formulário acima
    _REGIAO_GRADE = (0, 320, 950, 620)

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
            self._step_preencher_cargo,
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
    #  Helpers internos                                                    #
    # ------------------------------------------------------------------ #

    def _clicar(self, ctx: FlowContext, template: str, coords: tuple,
                threshold: float = 0.7):
        """Tenta OpenCV; usa coordenadas fixas como fallback."""
        encontrou = ctx.runner.click_template(template, threshold=threshold)
        if not encontrou:
            print(f"[fallback] template não encontrado — usando coordenadas {coords}")
        time.sleep(0.3)
        pyautogui.click(coords[0], coords[1])
        time.sleep(0.3)

    def _preencher_campo(self, ctx: FlowContext, template: str, coords: tuple,
                         valor: str, threshold: float = 0.7):
        """Clica no campo (OpenCV ou fallback) e digita o valor."""
        self._clicar(ctx, template, coords, threshold)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor)
        time.sleep(0.2)

    # ------------------------------------------------------------------ #
    #  Steps                                                               #
    # ------------------------------------------------------------------ #

    def _step_abrir_funcionarios(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF01"
        if observer:
            observer.log_step_start(step_id, "Clicar em Funcionários no menu Cadastros")
        start = time.monotonic()
        try:
            ctx.runner.wait_template(
                "templates/sislab/menu/menu_principal.png",
                timeout=10.0, threshold=0.7,
            )
            self._clicar(ctx,
                "templates/sislab/menu/btn_funcionarios.png",
                self._COORD_MENU_FUNCIONARIOS)
            ctx.runner.wait_template(
                "templates/sislab/funcionario/tela_cadastro_funcionario.png",
                timeout=10.0, threshold=0.7,
            )
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step

    def _step_clicar_novo(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF02"
        if observer:
            observer.log_step_start(step_id, "Clicar no botão Novo")
        start = time.monotonic()
        try:
            self._clicar(ctx,
                "templates/sislab/funcionario/btn_novo.png",
                self._COORD_BTN_NOVO)
            time.sleep(0.5)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step

    def _step_preencher_nome(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF03"
        nome = ctx.config.DADOS["nome"]
        if observer:
            observer.log_step_start(step_id, f"Preencher Nome: {nome}")
        start = time.monotonic()
        try:
            self._preencher_campo(ctx,
                "templates/sislab/funcionario/campo_nome.png",
                self._COORD_CAMPO_NOME, nome)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step

    def _step_preencher_cpf(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF04"
        if observer:
            observer.log_step_start(step_id, "Preencher CPF")
        start = time.monotonic()
        try:
            self._preencher_campo(ctx,
                "templates/sislab/funcionario/campo_cpf.png",
                self._COORD_CAMPO_CPF, ctx.config.DADOS["cpf"])
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step

    def _step_preencher_cargo(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF05"
        if observer:
            observer.log_step_start(step_id, "Preencher Cargo")
        start = time.monotonic()
        try:
            self._preencher_campo(ctx,
                "templates/sislab/funcionario/campo_cargo.png",
                self._COORD_CAMPO_CARGO, ctx.config.DADOS["cargo"])
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step

    def _step_preencher_salario(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF06"
        if observer:
            observer.log_step_start(step_id, "Preencher Salário")
        start = time.monotonic()
        try:
            self._preencher_campo(ctx,
                "templates/sislab/funcionario/campo_salario.png",
                self._COORD_CAMPO_SALARIO, ctx.config.DADOS["salario"])
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step

    def _step_preencher_admissao(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF07"
        if observer:
            observer.log_step_start(step_id, "Preencher Data de Admissão")
        start = time.monotonic()
        try:
            self._preencher_campo(ctx,
                "templates/sislab/funcionario/campo_admissao.png",
                self._COORD_CAMPO_ADMISSAO, ctx.config.DADOS["admissao"])
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step

    def _step_salvar(self, ctx: FlowContext, observer=None) -> StepResult:
        step_id = "CF08"
        if observer:
            observer.log_step_start(step_id, "Clicar em Salvar")
        start = time.monotonic()
        try:
            self._clicar(ctx,
                "templates/sislab/funcionario/btn_salvar.png",
                self._COORD_BTN_SALVAR)
            time.sleep(1.0)  # aguarda resposta do Oracle Forms
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step

    def _step_verificar_salvo_ocr(self, ctx: FlowContext, observer=None) -> StepResult:
        """
        Verifica que o funcionário aparece na grade após salvar.

        Por que OCR aqui:
            O Oracle Forms renderiza a grade como interface nativa — não é HTML
            acessível via seletor CSS, e o OpenCV com template não serve porque
            o conteúdo da linha muda a cada execução (Faker gera dados únicos).
            O OCR é a única forma de ler o texto da grade e confirmar o registro.

        Estratégia de busca:
            Verifica token a token do nome (ignorando partículas com <= 3 chars)
            para tolerar pequenos erros de reconhecimento do Tesseract.
        """
        step_id = "CF09"
        if observer:
            observer.log_step_start(step_id, "Verificar nome na grade via OCR")
        start = time.monotonic()
        try:
            time.sleep(0.8)  # aguarda grade atualizar após salvar

            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}.png")

            nome_esperado = ctx.config.DADOS["nome"].upper()
            encontrado, token = OcrHelper.contem_qualquer_token(
                screenshot_path,
                tokens=nome_esperado.split(),
                regiao=self._REGIAO_GRADE,
            )

            if not encontrado:
                # salva imagem de debug para facilitar ajuste da _REGIAO_GRADE
                OcrHelper.salvar_debug(screenshot_path, self._REGIAO_GRADE,
                                       f"{ctx.evidence_dir}{step_id}_ocr_debug.png")
                texto_lido = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_GRADE)
                raise AssertionError(
                    f"Nome '{nome_esperado}' não encontrado na grade.\n"
                    f"Texto lido pelo OCR:\n{texto_lido}\n"
                    f"Veja o debug em: {ctx.evidence_dir}{step_id}_ocr_debug.png"
                )

            print(f"[CF09] OCR confirmou token '{token}' do nome '{nome_esperado}' na grade.")
            step = StepResult(step_id=step_id, success=True,
                              duration_ms=(time.monotonic() - start) * 1000,
                              screenshot_path=screenshot_path)
        except Exception as e:
            step = StepResult(step_id=step_id, success=False,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=str(e))
        finally:
            if observer:
                observer.log_step_result(step)
        return step
