# vtae/flows/cadastro_paciente_flow.py
import time
import pyautogui

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult
from vtae.core.ocr_helper import OcrHelper


class CadastroPacienteFlow:
    """
    Fluxo de cadastro de paciente no SI3 (Oracle Forms - Desktop).
    Pressupoe que o login ja foi executado via LoginFlow.

    Navegacao:
        Menu Principal -> duplo clique "Cadastro de Pacientes"
        -> digita nome e pesquisa -> clica Novo
        -> Oracle Forms ja preenche o campo Nome automaticamente
        -> Tab cai no Nome Social -> preenche restante -> Salvar

    Templates em templates/si3/paciente/:
        menu_cadastro_paciente.png
        campo_nome_pesquisa.png
        btn_pesquisar.png
        btn_novo.png
        campo_nome.png              (usado so no wait_template do CP03)
        campo_nome_social.png       (opcional)
        campo_data_nascimento.png
        campo_hora.png
        campo_sexo.png
        campo_nacionalidade.png
        campo_mae.png
        campo_pai.png
        campo_cor_etnia.png
        campo_cpf.png               (recorte linha CIC + icone LOV)
        btn_salvar.png
        btn_ok.png
    """

    FLOW_NAME = "CadastroPacienteFlow"

    # Coordenadas de fallback — capture com: python scripts\posicao_mouse.py
    _COORD_MENU_CADASTRO   = (300, 200)
    _COORD_CAMPO_NOME_PESQ = (300, 280)
    _COORD_BTN_PESQUISAR   = (430, 350)
    _COORD_BTN_NOVO        = (650, 500)
    _COORD_CAMPO_NASC      = (310, 153)
    _COORD_CAMPO_HORA      = (385, 153)
    _COORD_CAMPO_SEXO      = (445, 153)
    _COORD_CAMPO_NACION    = (590, 153)
    _COORD_CAMPO_MAE       = (110, 187)
    _COORD_CAMPO_PAI       = (310, 187)
    _COORD_CAMPO_COR       = (80,  218)
    _COORD_CAMPO_CPF       = (200, 341)
    _COORD_BTN_SALVAR      = (46,  52)

    # Regiao do campo Matricula para OCR — ajuste apos ver tela salva
    _REGIAO_MATRICULA = (440, 100, 650, 120)

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        """
        Args:
            ctx: FlowContext com runner ja autenticado.
            dados: {
                "nome":            "NOME COMPLETO",
                "nome_social":     "",         # opcional
                "data_nascimento": "01/01/1990",
                "hora":            "00:00",
                "sexo":            "M",        # M ou F
                "nacionalidade":   "BRASILEIRA,
                "mae":             "NOME DA MAE",
                "pai":             "NOME DO PAI",
                "cor_etnia":       "BRANCA",
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
            lambda: self._step_verificar_matricula(ctx, observer),
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
    #  Helpers                                                            #
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
        """Clica no campo e digita o valor."""
        self._clicar(ctx, template, coords, threshold)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor)
        time.sleep(0.2)

    # ------------------------------------------------------------------ #
    #  Navegacao                                                          #
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
            # usa _clicar + type_text (suporta acentos) em vez de typewrite
            self._clicar(ctx,
                "templates/si3/paciente/campo_nome_pesquisa.png",
                self._COORD_CAMPO_NOME_PESQ)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(dados["nome"])
            time.sleep(0.2)
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
        """
        Clica em Novo e aguarda o formulario abrir.
        O Oracle Forms ja preenche o campo Nome com o valor da pesquisa.
        Pressiona Tab para mover o foco para Nome Social / Afetivo.
        """
        step_id = "CP03"
        if observer:
            observer.log_step_start(step_id, "clicar em Novo")
        start = time.monotonic()
        try:
            self._clicar(ctx,
                "templates/si3/paciente/btn_novo.png",
                self._COORD_BTN_NOVO)
            # aguarda formulario abrir — Nome ja vem preenchido
            # cursor ja esta no campo Nome quando o formulario abre
            ctx.runner.wait_template(
                "templates/si3/paciente/campo_nome.png",
                timeout=10.0, threshold=0.7,
            )
            time.sleep(0.5)
            # clica diretamente no campo Nome Social — mais confiavel que Tab
            # porque o Oracle Forms abre com foco na tabela de documentos
            ctx.runner.safe_click(
                "templates/si3/paciente/campo_nome_social.png",
                threshold=0.7,
            )
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
    #  Formulario                                                         #
    # ------------------------------------------------------------------ #

    def _step_nome_social(self, ctx, dados: dict, observer=None) -> StepResult:
        """
        Nome Social / Afetivo — opcional na digitacao.
        Foco ja esta neste campo apos o Tab do CP03.
        So preenche se vier nos dados e nao estiver vazio.
        """
        step_id = "CP04"
        nome_social = dados.get("nome_social", "").strip()
        if observer:
            observer.log_step_start(
                step_id,
                f"Nome Social: {nome_social}" if nome_social
                else "Nome Social nao informado — pulando"
            )
        start = time.monotonic()
        try:
            if nome_social:
                # clica no campo e digita
                ctx.runner.safe_click(
                    "templates/si3/paciente/campo_nome_social.png",
                    threshold=0.7,
                )
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text(nome_social)
                time.sleep(0.2)
            else:
                print("[CP04] nome_social vazio — campo ignorado")
                # clica no campo mesmo vazio para garantir foco correto
                ctx.runner.safe_click(
                    "templates/si3/paciente/campo_nome_social.png",
                    threshold=0.7,
                )
                time.sleep(0.2)
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
        step_id = "CP05"
        if observer:
            observer.log_step_start(step_id, "preencher Data de Nascimento e Hora")
        start = time.monotonic()
        try:
            self._preencher(ctx,
                "templates/si3/paciente/campo_data_nascimento.png",
                self._COORD_CAMPO_NASC,
                dados["data_nascimento"])
            self._preencher(ctx,
                "templates/si3/paciente/campo_hora.png",
                self._COORD_CAMPO_HORA,
                dados.get("hora", "00:00"))
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
            self._clicar(ctx,
                "templates/si3/paciente/campo_sexo.png",
                self._COORD_CAMPO_SEXO)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(dados.get("sexo", "M"), interval=0.05)
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
        Nacionalidade no Oracle Forms:
        digita -> Tab abre popup -> Tab campo Estado -> SP
        -> Tab campo Cidade -> SAO PAULO -> Tab -> OK
        Padrao secao 5.2 do manual VTAE.
        """
        step_id = "CP07"
        if observer:
            observer.log_step_start(step_id, "preencher Nacionalidade")
        start = time.monotonic()
        try:
            self._clicar(ctx,
                "templates/si3/paciente/campo_nacionalidade.png",
                self._COORD_CAMPO_NACION)
            pyautogui.typewrite(
                dados.get("nacionalidade", "BRASILEIRO"), interval=0.05
            )
            pyautogui.press("tab")
            time.sleep(1.5)
            pyautogui.press("tab")
            pyautogui.typewrite("SP", interval=0.05)
            pyautogui.press("tab")
            pyautogui.typewrite("SAO PAULO", interval=0.05)
            pyautogui.press("tab")
            ctx.runner.safe_click(
                "templates/si3/paciente/btn_ok.png",
                threshold=0.7,
            )
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
            observer.log_step_start(step_id, "preencher Mae")
        start = time.monotonic()
        try:
            self._preencher(ctx,
                "templates/si3/paciente/campo_mae.png",
                self._COORD_CAMPO_MAE,
                dados["mae"])
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
            self._preencher(ctx,
                "templates/si3/paciente/campo_pai.png",
                self._COORD_CAMPO_PAI,
                dados["pai"])
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
            self._clicar(ctx,
                "templates/si3/paciente/campo_cor_etnia.png",
                self._COORD_CAMPO_COR)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(
                dados.get("cor_etnia", "BRANCA"), interval=0.05
            )
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
        """
        CPF na linha CIC da tabela de documentos.
        Template campo_cpf.png = linha CIC + icone LOV.
        Clique cai no campo de conteudo ao lado do icone.
        Oracle Forms aceita somente numeros.
        """
        step_id = "CP11"
        if observer:
            observer.log_step_start(step_id, "preencher CPF (CIC)")
        start = time.monotonic()
        try:
            cpf = dados["cpf"].replace(".", "").replace("-", "")
            self._preencher(ctx,
                "templates/si3/paciente/campo_cpf.png",
                self._COORD_CAMPO_CPF,
                cpf)
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

    def _step_verificar_matricula(self, ctx, observer=None) -> StepResult:
        """
        Confirma que o cadastro foi salvo verificando que o campo
        Matricula foi preenchido automaticamente pelo sistema via OCR.
        Se falhar: veja CP13_ocr_debug.png e ajuste _REGIAO_MATRICULA.
        """
        step_id = "CP13"
        if observer:
            observer.log_step_start(step_id, "verificar matricula via OCR")
        start = time.monotonic()
        try:
            time.sleep(0.5)
            screenshot_path = ctx.runner.screenshot(
                f"{ctx.evidence_dir}CP13_matricula.png"
            )
            texto = OcrHelper.ler_regiao(
                screenshot_path, self._REGIAO_MATRICULA
            )
            import re
            numeros = re.findall(r'\d+', texto)
            if not numeros:
                OcrHelper.salvar_debug(
                    screenshot_path, self._REGIAO_MATRICULA,
                    f"{ctx.evidence_dir}CP13_ocr_debug.png"
                )
                raise AssertionError(
                    f"Matricula nao encontrada apos salvar.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Ajuste _REGIAO_MATRICULA e veja CP13_ocr_debug.png"
                )
            print(f"[CP13] Cadastro salvo — Matricula: {numeros[0]}")
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
