# src/flows/si3/cadastro_paciente_flow.py
import time
import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult
from src.vision.ocr import OcrHelper


class CadastroPacienteFlow:
    """
    Fluxo de cadastro de paciente no SI3 (Oracle Forms - Desktop).
    Pressupõe que o login já foi executado via LoginFlow.

    Navegação:
        Menu Principal → duplo clique "Cadastro de Pacientes"
        → digita nome e pesquisa → clica Novo
        → Oracle Forms já preenche o campo Nome automaticamente
        → preenche Nome Social, Data, Sexo, Nacionalidade, Mãe, Pai,
          Cor/Etnia, CPF → Salvar → verifica matrícula via OCR

    Templates em templates/si3/paciente/:
        menu_cadastro_paciente.png
        campo_nome_pesquisa.png
        btn_pesquisar.png
        btn_novo.png
        campo_nome_social.png       (usado no wait_template do CP03)
        btn_salvar.png
        btn_ok.png
        btn_ok_nacion.png
    """

    FLOW_NAME = "CadastroPacienteFlow"

    # ------------------------------------------------------------------
    # Coordenadas de fallback — capture com: python scripts\posicao_mouse.py
    # ------------------------------------------------------------------
    _COORD_CAMPO_NOME_PESQ = (300, 280)
    _COORD_BTN_PESQUISAR   = (430, 350)
    _COORD_BTN_NOVO        = (650, 500)
    _COORD_CAMPO_NOME      = (106, 156)
    _COORD_CAMPO_SOCIAL    = (71,  202)
    _COORD_CAMPO_NASC      = (405, 203)
    _COORD_CAMPO_HORA      = (502, 203)
    _COORD_CAMPO_SEXO      = (568, 201)
    _COORD_CAMPO_NACION    = (679, 201)
    _COORD_CAMPO_MAE       = (115, 245)
    _COORD_CAMPO_PAI       = (266, 247)
    _COORD_CAMPO_COR       = (126, 289)
    _COORD_CAMPO_CPF       = (238, 450)
    _COORD_BTN_SALVAR      = (46,  52)
    _COORD_BTN_OK_POPUP    = (399, 346)
    _COORD_BTN_GERAR_MATR  = (900, 650)
    _COORD_BTN_SAIR_1      = (509, 68)
    _COORD_BTN_SAIR_2      = (507, 63)
    _COORD_BTN_SAIR_MENU   = (20,  575)

    _REGIAO_MATRICULA = (507, 139, 667, 169)

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        """
        Args:
            ctx: FlowContext com runner já autenticado.
            dados: {
                "nome":            "NOME COMPLETO",
                "nome_social":     "",         # se vazio usa o nome
                "data_nascimento": "01/01/1990",
                "hora":            "00:00",
                "sexo":            "M",        # M ou F
                "nacionalidade":   "BRASILEIRO",
                "mae":             "NOME DA MAE",
                "pai":             "NOME DO PAI",
                "cor_etnia":       "PARDA",
                "cpf":             "00000000000",
            }
        """
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_menu(ctx, observer),
            lambda: self._step_pesquisar(ctx, dados, observer),
            lambda: self._step_novo(ctx, observer),
            lambda: self._step_nome_social(ctx, dados, observer),
            lambda: self._step_data_nascimento(ctx, dados, observer),
            lambda: self._step_sexo(ctx, dados, observer),
            lambda: self._step_nacionalidade(ctx, dados, observer),
            lambda: self._step_mae(ctx, dados, observer),
            lambda: self._step_pai(ctx, dados, observer),
            lambda: self._step_cor_etnia(ctx, dados, observer),
            lambda: self._step_cpf(ctx, dados, observer),
            lambda: self._step_salvar(ctx, observer),
            lambda: self._step_gerar_matricula(ctx, observer),
            lambda: self._step_sair(ctx, observer),
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
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _clicar(self, ctx, template: str, coords: tuple, threshold: float = 0.7):
        """Tenta OpenCV; usa coordenadas como fallback."""
        encontrou = ctx.runner.click_template(template, threshold=threshold)
        if not encontrou:
            print(f"[fallback] {template} — coords {coords}")
        time.sleep(0.3)
        pyautogui.click(coords[0], coords[1])
        time.sleep(0.3)

    def _preencher(self, ctx, template: str, coords: tuple,
                   valor: str, threshold: float = 0.7):
        """Clica no campo e digita o valor com suporte a acentos."""
        self._clicar(ctx, template, coords, threshold)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor)
        time.sleep(0.2)

    # ------------------------------------------------------------------ #
    #  Navegação                                                           #
    # ------------------------------------------------------------------ #

    def _step_menu(self, ctx, observer=None) -> StepResult:
        step_id = "CP01"
        if observer:
            observer.log_step_start(step_id, "duplo clique em Cadastro de Pacientes")
        start = time.monotonic()
        try:
            ctx.runner.double_click(
                "templates/si3/paciente/menu_cadastro_paciente.png",
                threshold=0.7,
            )
            ctx.runner.wait_template(
                "templates/si3/paciente/campo_nome_pesquisa.png",
                timeout=15.0, threshold=0.7,
            )
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
            observer.log_step_start(step_id, f"pesquisar: {dados['nome']}")
        start = time.monotonic()
        try:
            self._clicar(ctx,
                "templates/si3/paciente/campo_nome_pesquisa.png",
                self._COORD_CAMPO_NOME_PESQ)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(dados["nome"])
            time.sleep(0.3)
            self._clicar(ctx,
                "templates/si3/paciente/btn_pesquisar.png",
                self._COORD_BTN_PESQUISAR)
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
            self._clicar(ctx,
                "templates/si3/paciente/btn_novo.png",
                self._COORD_BTN_NOVO)
            ctx.runner.wait_template(
                "templates/si3/paciente/campo_nome_social.png",
                timeout=15.0, threshold=0.7,
            )
            time.sleep(0.5)
            pyautogui.click(self._COORD_CAMPO_NOME[0], self._COORD_CAMPO_NOME[1])
            time.sleep(0.3)
            pyautogui.press("tab")
            time.sleep(0.3)
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

    # ------------------------------------------------------------------ #
    #  Formulário                                                          #
    # ------------------------------------------------------------------ #

    def _step_nome_social(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP04"
        nome_social = dados.get("nome_social", "").strip()
        valor = nome_social if nome_social else dados.get("nome", "")
        if observer:
            observer.log_step_start(step_id, f"Nome Social: {valor}")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_CAMPO_SOCIAL[0], self._COORD_CAMPO_SOCIAL[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            time.sleep(0.3)
            pyautogui.press("tab")
            time.sleep(0.3)
            print(f"[CP04] Nome Social preenchido: {valor}")
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP04_social.png")
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
        """
        Data e hora sem acentos — usa ctx.runner.type_text para manter
        consistência com o padrão do projeto (nunca pyautogui.typewrite direto).
        """
        step_id = "CP05"
        if observer:
            observer.log_step_start(step_id, "preencher Data de Nascimento e Hora")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_CAMPO_NASC[0], self._COORD_CAMPO_NASC[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(dados["data_nascimento"])
            time.sleep(0.2)

            pyautogui.click(self._COORD_CAMPO_HORA[0], self._COORD_CAMPO_HORA[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(dados.get("hora", "00:00"))
            time.sleep(0.2)

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

    def _step_sexo(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP06"
        if observer:
            observer.log_step_start(step_id, f"preencher Sexo: {dados.get('sexo', 'M')}")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_CAMPO_SEXO[0], self._COORD_CAMPO_SEXO[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(dados.get("sexo", "M"))
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP06_sexo.png")
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

    def _step_nacionalidade(self, ctx, dados: dict, observer=None) -> StepResult:
        """
        Nacionalidade no Oracle Forms — dois popups em sequência:
            Popup 1 — Lista de Tipo de Nacionalidade → OK
            Popup 2 — Estado / Cidade → SP + SAO PAULO → OK
        """
        step_id = "CP07"
        if observer:
            observer.log_step_start(step_id, "preencher Nacionalidade")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_CAMPO_NACION[0], self._COORD_CAMPO_NACION[1])
            time.sleep(0.3)
            ctx.runner.type_text(dados.get("nacionalidade", "BRASILEIRA"))
            pyautogui.press("tab")
            time.sleep(2.0)

            encontrou = ctx.runner.wait_template(
                "templates/si3/paciente/btn_ok.png",
                timeout=8.0, threshold=0.6,
            )
            if encontrou:
                ctx.runner.safe_click("templates/si3/paciente/btn_ok.png", threshold=0.6)
            else:
                print("[CP07] popup1 btn_ok não encontrado — Enter como fallback")
                pyautogui.press("enter")
            time.sleep(1.5)

            ctx.runner.type_text("SP")
            pyautogui.press("tab")
            time.sleep(0.5)
            ctx.runner.type_text("SAO PAULO")
            time.sleep(0.3)

            encontrou2 = ctx.runner.wait_template(
                "templates/si3/paciente/btn_ok_nacion.png",
                timeout=8.0, threshold=0.6,
            )
            if encontrou2:
                ctx.runner.safe_click("templates/si3/paciente/btn_ok_nacion.png", threshold=0.6)
            else:
                print("[CP07] popup2 btn_ok_nacion não encontrado — Enter como fallback")
                pyautogui.press("enter")
            time.sleep(0.5)

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP07_nacion.png")
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
        step_id = "CP08"
        if observer:
            observer.log_step_start(step_id, "preencher Mãe")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_CAMPO_MAE[0], self._COORD_CAMPO_MAE[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(dados["mae"])
            time.sleep(0.2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP08_mae.png")
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
        step_id = "CP09"
        if observer:
            observer.log_step_start(step_id, "preencher Pai")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_CAMPO_PAI[0], self._COORD_CAMPO_PAI[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(dados["pai"])
            time.sleep(0.2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP09_pai.png")
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

    def _step_cor_etnia(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "CP10"
        if observer:
            observer.log_step_start(step_id, "preencher Cor/Etnia")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_CAMPO_COR[0], self._COORD_CAMPO_COR[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(dados.get("cor_etnia", "PARDA"))
            pyautogui.press("tab")
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP10_cor.png")
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
        step_id = "CP11"
        if observer:
            observer.log_step_start(step_id, "preencher CPF (CIC)")
        start = time.monotonic()
        try:
            cpf = dados["cpf"].replace(".", "").replace("-", "")
            pyautogui.click(self._COORD_CAMPO_CPF[0], self._COORD_CAMPO_CPF[1])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(cpf)
            time.sleep(0.2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP11_cpf.png")
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
        step_id = "CP12"
        if observer:
            observer.log_step_start(step_id, "salvar cadastro")
        start = time.monotonic()
        try:
            self._clicar(ctx,
                "templates/si3/paciente/btn_salvar.png",
                self._COORD_BTN_SALVAR)
            time.sleep(2)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP12_salvo.png")
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

    def _step_gerar_matricula(self, ctx, observer=None) -> StepResult:
        """
        Clica em Gerar matrícula e confirma via OCR que o número foi gerado.
        Se o OCR falhar: veja CP13_ocr_debug.png e ajuste _REGIAO_MATRICULA.
        """
        step_id = "CP13"
        if observer:
            observer.log_step_start(step_id, "gerar matrícula e verificar via OCR")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_BTN_GERAR_MATR[0], self._COORD_BTN_GERAR_MATR[1])
            time.sleep(2.0)

            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}CP13_matricula.png")

            texto = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_MATRICULA)
            import re
            numeros = re.findall(r'\d+', texto)
            if not numeros:
                OcrHelper.salvar_debug(
                    screenshot_path, self._REGIAO_MATRICULA,
                    f"{ctx.evidence_dir}CP13_ocr_debug.png"
                )
                raise AssertionError(
                    f"Matrícula não gerada ou OCR não leu.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Veja CP13_ocr_debug.png e ajuste _REGIAO_MATRICULA."
                )
            print(f"[CP13] Matrícula gerada: {numeros[0]}")
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

    def _step_sair(self, ctx, observer=None) -> StepResult:
        """
        Sai do formulário de volta ao Menu Principal — 3 cliques no botão Sair.
        """
        step_id = "CP14"
        if observer:
            observer.log_step_start(step_id, "sair para o Menu Principal")
        start = time.monotonic()
        try:
            pyautogui.click(self._COORD_BTN_SAIR_1[0], self._COORD_BTN_SAIR_1[1])
            time.sleep(1.5)
            pyautogui.click(self._COORD_BTN_SAIR_2[0], self._COORD_BTN_SAIR_2[1])
            time.sleep(1.5)
            pyautogui.click(self._COORD_BTN_SAIR_MENU[0], self._COORD_BTN_SAIR_MENU[1])
            time.sleep(1.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}CP14_menu.png")
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
