# src/flows/si3/admissao_internacao_flow.py
import time
import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult
from src.vision.ocr import OcrHelper


class AdmissaoInternacaoFlow:
    """
    Fluxo de Admissão de Internação no SI3 (Oracle Forms - Desktop).
    Pressupõe que o login já foi executado via LoginFlow.

    O ID do paciente é informado via config.DADOS["paciente_id"] —
    nunca hardcoded, em conformidade com a LGPD.

    Templates em templates/si3/admissao_internacao/:
        menu_internacao, campo_identificado, btn_pesquisar,
        aba_endereco, campo_tipo_endereco, btn_admitir_paciente,
        campo_unidade_funcional, campo_provedor, campo_plano,
        campo_obs, campo_origem_tipo, campo_origem_solicitacao,
        campo_matricula_responsavel, btn_info_compl,
        campo_numero, campo_localizar, btn_localizar,
        btn_salvar, btn_retornar, campo_nr_admissao, btn_sair
    """

    FLOW_NAME = "AdmissaoInternacaoFlow"
    _TPL = "templates/si3/admissao_internacao"

    # Região para OCR do Nr Admissão — ajustar conforme resolução
    # Abra o screenshot CP13 no Paint e anote as coordenadas
    _REGIAO_NR_ADMISSAO = (500, 130, 700, 160)

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_abrir_internacao(ctx, observer),
            lambda: self._step_informar_paciente(ctx, dados, observer),
            lambda: self._step_pesquisar(ctx, observer),
            lambda: self._step_aba_endereco(ctx, observer),
            lambda: self._step_verificar_tipo_endereco(ctx, observer),
            lambda: self._step_admitir_paciente(ctx, observer),
            lambda: self._step_unidade_funcional(ctx, dados, observer),
            lambda: self._step_provedor_plano(ctx, dados, observer),
            lambda: self._step_obs(ctx, dados, observer),
            lambda: self._step_origem_paciente(ctx, dados, observer),
            lambda: self._step_origem_solicitacao(ctx, observer),
            lambda: self._step_profissional_responsavel(ctx, dados, observer),
            lambda: self._step_info_compl(ctx, observer),
            lambda: self._step_numero_medico(ctx, dados, observer),
            lambda: self._step_salvar(ctx, observer),
            lambda: self._step_retornar(ctx, observer),
            lambda: self._step_validar_admissao(ctx, observer),
            lambda: self._step_sair(ctx, observer),
        ]

        for step_fn in steps:
            step = step_fn()
            result.steps.append(step)
            if observer:
                observer.log_step_result(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    # ------------------------------------------------------------------
    # AI01 — Abrir módulo Internação
    # ------------------------------------------------------------------

    def _step_abrir_internacao(self, ctx, observer=None) -> StepResult:
        step_id = "AI01"
        if observer:
            observer.log_step_start(step_id, "duplo clique em Internação")
        start = time.monotonic()
        try:
            ctx.runner.double_click(f"{self._TPL}/menu_internacao.png", threshold=0.7)
            ctx.runner.wait_template(f"{self._TPL}/campo_identificado.png",
                                     timeout=15.0, threshold=0.7)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI01_internacao.png")
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

    # ------------------------------------------------------------------
    # AI02 — Informar ID do paciente
    # ------------------------------------------------------------------

    def _step_informar_paciente(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "AI02"
        paciente_id = dados.get("paciente_id", "")
        if observer:
            observer.log_step_start(step_id, f"informar ID do paciente")
        start = time.monotonic()
        try:
            if not paciente_id:
                raise ValueError(
                    "paciente_id não informado. "
                    "Defina SI3_PACIENTE_ID no arquivo vtae/configs/si3_internacao/.env"
                )
            # 2x Tab para chegar no campo Identificado ou clique direto
            found = ctx.runner.click_near(
                f"{self._TPL}/campo_identificado.png",
                offset_x=150, offset_y=0, threshold=0.65
            )
            if not found:
                pyautogui.press("tab")
                time.sleep(0.3)
                pyautogui.press("tab")
                time.sleep(0.3)

            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(paciente_id)
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI02_paciente.png")
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

    # ------------------------------------------------------------------
    # AI03 — Pesquisar paciente
    # ------------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None) -> StepResult:
        step_id = "AI03"
        if observer:
            observer.log_step_start(step_id, "clicar em Pesquisar")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            time.sleep(2.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI03_pesquisa.png")
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

    # ------------------------------------------------------------------
    # AI04 — Clicar na aba Endereço
    # ------------------------------------------------------------------

    def _step_aba_endereco(self, ctx, observer=None) -> StepResult:
        step_id = "AI04"
        if observer:
            observer.log_step_start(step_id, "clicar na aba Endereço")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(f"{self._TPL}/aba_endereco.png", threshold=0.7)
            time.sleep(1.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI04_endereco.png")
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

    # ------------------------------------------------------------------
    # AI05 — Verificar campo Tipo do endereço (regra de negócio)
    # ------------------------------------------------------------------

    def _step_verificar_tipo_endereco(self, ctx, observer=None) -> StepResult:
        """
        Seleciona 'RUA' no campo Tipo do endereço via LOV.
        Funciona independente de o campo estar preenchido ou vazio.

        Fluxo:
          1. Clica no botão LOV ao lado do campo Tipo (x=197, y=433)
          2. No popup, digita 'RUA' no campo Localizar (x=193, y=913)
          3. Clica em Localizar (x=177, y=361)
          4. Clica em OK para confirmar RUA (x=295, y=911)
          5. No popup de País, clica em OK com BRASIL selecionado (x=375, y=494)
        """
        step_id = "AI05"
        if observer:
            observer.log_step_start(step_id, "selecionar RUA no campo Tipo via LOV")
        start = time.monotonic()
        try:
            # 1. Abre a LOV clicando no botão [...]
            pyautogui.click(197, 433)
            time.sleep(1.5)  # aguarda o popup abrir

            # 2. Digita RUA no campo Localizar
            pyautogui.click(193, 913)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text("RUA")
            time.sleep(0.3)

            # 3. Clica em Localizar
            pyautogui.click(177, 361)
            time.sleep(1.0)  # aguarda resultado

            # 4. Clica em OK para confirmar RUA selecionado
            pyautogui.click(295, 911)
            time.sleep(1.0)

            # 5. Popup de País — BRASIL já selecionado, clica em OK
            pyautogui.click(375, 494)
            time.sleep(0.5)

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI05_tipo_end.png")
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

    # ------------------------------------------------------------------
    # AI06 — Admitir Paciente
    # ------------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None) -> StepResult:
        step_id = "AI06"
        if observer:
            observer.log_step_start(step_id, "clicar em Admitir Paciente")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7)
            time.sleep(2.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI06_admitir.png")
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

    # ------------------------------------------------------------------
    # AI07 — Unidade Funcional
    # ------------------------------------------------------------------

    def _step_unidade_funcional(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "AI07"
        valor = dados.get("unidade_funcional", "SC AMBULATORIO")
        if observer:
            observer.log_step_start(step_id, f"preencher Unidade Funcional: {valor}")
        start = time.monotonic()
        try:
            # Cursor já fica nesse campo — só digita
            ctx.runner.type_text(valor)
            pyautogui.press("tab")
            time.sleep(0.5)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI07_unidade.png")
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

    # ------------------------------------------------------------------
    # AI08 — Provedor e Plano
    # ------------------------------------------------------------------

    def _step_provedor_plano(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "AI08"
        if observer:
            observer.log_step_start(step_id, "preencher Provedor e Plano")
        start = time.monotonic()
        try:
            provedor = dados.get("provedor", "SUS")
            plano = dados.get("plano", "SUS")

            ctx.runner.click_near(
                f"{self._TPL}/campo_provedor.png",
                offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(provedor)
            pyautogui.press("tab")
            time.sleep(0.5)

            ctx.runner.click_near(
                f"{self._TPL}/campo_plano.png",
                offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(plano)
            pyautogui.press("tab")
            time.sleep(0.3)

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI08_provedor_plano.png")
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

    # ------------------------------------------------------------------
    # AI09 — Observação
    # ------------------------------------------------------------------

    def _step_obs(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "AI09"
        valor = dados.get("obs", "teste realizado com automacao")
        if observer:
            observer.log_step_start(step_id, "preencher campo Obs.")
        start = time.monotonic()
        try:
            # Campo Obs — coordenada direta validada: x=108, y=346
            pyautogui.click(108, 346)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            time.sleep(0.3)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI09_obs.png")
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

    # ------------------------------------------------------------------
    # AI10 — Origem do Paciente (Tipo + Tab → Entidade preenche auto)
    # ------------------------------------------------------------------

    def _step_origem_paciente(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "AI10"
        tipo = dados.get("origem_tipo", "RESIDENCIA")
        if observer:
            observer.log_step_start(step_id, f"preencher Origem do Paciente: {tipo}")
        start = time.monotonic()
        try:
            # Campo Tipo — coordenada direta validada: x=50, y=408
            pyautogui.click(50, 408)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(tipo)
            pyautogui.press("tab")
            time.sleep(1.0)  # Entidade preenche automaticamente após Tab
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI10_origem.png")
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

    # ------------------------------------------------------------------
    # AI11 — Origem da Solicitação de Internação (dropdown)
    # ------------------------------------------------------------------

    def _step_origem_solicitacao(self, ctx, observer=None) -> StepResult:
        """
        Seleciona a primeira opção disponível no dropdown de
        Origem da Solicitação de Internação.
        Usa seta para baixo + Enter — qualquer opção é válida.
        """
        step_id = "AI11"
        if observer:
            observer.log_step_start(step_id, "selecionar Origem da Solicitação (dropdown)")
        start = time.monotonic()
        try:
            # Abre o dropdown clicando no campo
            pyautogui.click(643, 458)
            time.sleep(1.5)  # aguarda dropdown abrir completamente

            # Clica na opção via template — funciona independente da posição
            ctx.runner.safe_click(
                f"{self._TPL}/opcao_consultorio_interno.png", threshold=0.7
            )
            time.sleep(0.5)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI11_solicitacao.png")
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

    # ------------------------------------------------------------------
    # AI12 — Profissional Responsável (matrícula 1 + Tab)
    # ------------------------------------------------------------------

    def _step_profissional_responsavel(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "AI12"
        matricula = dados.get("matricula_responsavel", "1")
        if observer:
            observer.log_step_start(step_id, f"preencher matrícula responsável: {matricula}")
        start = time.monotonic()
        try:
            # Campo Matrícula — coordenada direta validada: x=220, y=527
            pyautogui.click(220, 527)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(matricula)
            pyautogui.press("tab")
            time.sleep(1.0)  # Nome do profissional preenche automaticamente
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI12_responsavel.png")
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

    # ------------------------------------------------------------------
    # AI13 — Info. Complementar de Internação
    # ------------------------------------------------------------------

    def _step_info_compl(self, ctx, observer=None) -> StepResult:
        step_id = "AI13"
        if observer:
            observer.log_step_start(step_id, "clicar em Info. Compl de Internação")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(f"{self._TPL}/btn_info_compl.png", threshold=0.7)
            time.sleep(2.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI13_info_compl.png")
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

    # ------------------------------------------------------------------
    # AI14 — Número + Localizar médico
    # ------------------------------------------------------------------

    def _step_numero_medico(self, ctx, dados: dict, observer=None) -> StepResult:
        step_id = "AI14"
        numero = dados.get("numero_compl", "1")
        medico = dados.get("localizar_medico", "informatica")
        if observer:
            observer.log_step_start(step_id, "preencher número e localizar médico")
        start = time.monotonic()
        try:
            # Campo Número — coordenada direta validada: x=159, y=159
            pyautogui.click(159, 159)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(numero)
            pyautogui.press("tab")
            time.sleep(1.5)  # Aguarda popup de profissionais abrir

            # Popup abre em posição variável — usa template para encontrar OK
            ctx.runner.safe_click(
                f"{self._TPL}/btn_ok_popup.png", threshold=0.7
            )
            time.sleep(0.5)

            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI14_numero.png")
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

    # ------------------------------------------------------------------
    # AI15 — Salvar
    # ------------------------------------------------------------------

    def _step_salvar(self, ctx, observer=None) -> StepResult:
        step_id = "AI15"
        if observer:
            observer.log_step_start(step_id, "clicar em Salvar")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(f"{self._TPL}/btn_salvar.png", threshold=0.7)
            time.sleep(2.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI15_salvo.png")
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

    # ------------------------------------------------------------------
    # AI16 — Retornar
    # ------------------------------------------------------------------

    def _step_retornar(self, ctx, observer=None) -> StepResult:
        step_id = "AI16"
        if observer:
            observer.log_step_start(step_id, "clicar em Retornar")
        start = time.monotonic()
        try:
            # Botão Retornar — coordenada direta validada: x=779, y=239
            pyautogui.click(779, 239)
            time.sleep(1.5)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI16_retornar.png")
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

    # ------------------------------------------------------------------
    # AI17 — Validar Nr Admissão via OCR
    # ------------------------------------------------------------------

    def _step_validar_admissao(self, ctx, observer=None) -> StepResult:
        """
        Lê o campo Nr Admissão via OCR.
        Se estiver preenchido com um número, a admissão foi bem-sucedida.
        Ajuste _REGIAO_NR_ADMISSAO abrindo o screenshot AI16 no Paint.
        """
        step_id = "AI17"
        if observer:
            observer.log_step_start(step_id, "validar Nr Admissão via OCR")
        start = time.monotonic()
        try:
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AI17_validacao.png")
            texto = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_NR_ADMISSAO)

            import re
            numeros = re.findall(r'\d+', texto)
            if not numeros:
                OcrHelper.salvar_debug(
                    screenshot_path,
                    self._REGIAO_NR_ADMISSAO,
                    f"{ctx.evidence_dir}AI17_ocr_debug.png"
                )
                raise AssertionError(
                    f"Nr Admissão não encontrado — admissão pode ter falhado.\n"
                    f"Texto lido via OCR: '{texto}'\n"
                    f"Veja AI17_ocr_debug.png e ajuste _REGIAO_NR_ADMISSAO."
                )

            print(f"[AI17] Nr Admissão: {numeros[0]}")
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

    # ------------------------------------------------------------------
    # AI18 — Sair (2x) e voltar para tela de login
    # ------------------------------------------------------------------

    def _step_sair(self, ctx, observer=None) -> StepResult:
        step_id = "AI18"
        if observer:
            observer.log_step_start(step_id, "sair e voltar para tela de login")
        start = time.monotonic()
        try:
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            screenshot = ctx.runner.screenshot(f"{ctx.evidence_dir}AI18_sair.png")
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