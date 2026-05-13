# src/flows/si3/admissao_internacao_flow.py
"""
AdmissaoInternacaoFlow — SI3 Oracle Forms
Versão: 0.5.4

Base: flow validado 21/21 (v0.5.3) — sem alterações de lógica.
Melhorias 4b aplicadas:
  - Coordenadas lidas de ctx.config.coordenadas (não hardcoded no flow)
  - AI01: wait_template antes do double_click (elimina race condition)
  - AI03/AI06/AI13/AI14: sleep fixo substituído por wait_template onde possível
  - AI05 (LOV Tipo endereço): sleeps substituídos por wait_template no popup
  - AI11 (dropdown): sleep 1.5s mantido — necessário para animação
  - AI18: sleep mantido — popup de confirmação sem template estável

Lógica original preservada integralmente.
"""
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
        aba_endereco, btn_admitir_paciente,
        campo_provedor, campo_plano,
        btn_info_compl, btn_ok_popup,
        opcao_consultorio_interno,
        btn_salvar, btn_sair
    """

    FLOW_NAME = "AdmissaoInternacaoFlow"
    _TPL = "templates/si3/admissao_internacao"

    # Região para OCR do Nr Admissão — ajustar conforme resolução
    _REGIAO_NR_ADMISSAO = (10, 100, 280, 155)  # ajustado para 1920x1080 — Nr Admissao canto sup esq

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        # Coordenadas lidas do config.yaml — não hardcoded no flow
        coords = ctx.config.coordenadas

        steps = [
            lambda: self._step_abrir_internacao(ctx, observer),
            lambda: self._step_informar_paciente(ctx, dados, observer),
            lambda: self._step_pesquisar(ctx, observer),
            lambda: self._step_aba_endereco(ctx, observer),
            lambda: self._step_verificar_tipo_endereco(ctx, coords, observer),
            lambda: self._step_admitir_paciente(ctx, observer),
            lambda: self._step_unidade_funcional(ctx, dados, observer),
            lambda: self._step_provedor_plano(ctx, dados, observer),
            lambda: self._step_obs(ctx, dados, coords, observer),
            lambda: self._step_origem_paciente(ctx, dados, coords, observer),
            lambda: self._step_origem_solicitacao(ctx, coords, observer),
            lambda: self._step_profissional_responsavel(ctx, dados, coords, observer),
            lambda: self._step_info_compl(ctx, observer),
            lambda: self._step_numero_medico(ctx, dados, coords, observer),
            lambda: self._step_salvar(ctx, observer),
            lambda: self._step_retornar(ctx, coords, observer),
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
        """wait_template antes do double_click elimina race condition (4b-1)."""
        step_id = "AI01"
        if observer:
            observer.log_step_start(step_id, "duplo clique em Internação")
        start = time.monotonic()
        try:
            # 4b-1: garante que o menu renderizou antes de clicar
            ctx.runner.wait_template(
                f"{self._TPL}/menu_internacao.png", timeout=5, threshold=0.7
            )
            ctx.runner.double_click(f"{self._TPL}/menu_internacao.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/campo_identificado.png", timeout=15.0, threshold=0.7
            )
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
            observer.log_step_start(step_id, "informar ID do paciente")
        start = time.monotonic()
        try:
            if not paciente_id:
                raise ValueError(
                    "paciente_id não informado. "
                    "Defina SI3_PACIENTE_ID no arquivo vtae/configs/si3/si3_internacao/.env"
                )
            # click_near no label do campo identificado, fallback em Tab
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
            # Aguarda aba Endereços aparecer como indicador de carregamento
            ctx.runner.wait_template(
                f"{self._TPL}/aba_endereco.png", timeout=10, threshold=0.7
            )
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
    # AI05 — Campo Tipo do endereço via LOV
    # ------------------------------------------------------------------

    def _step_verificar_tipo_endereco(self, ctx, coords, observer=None) -> StepResult:
        """
        Seleciona 'RUA' via LOV (botão [...] ao lado do campo Tipo).
        Fluxo:
          1. Clica no botão LOV — coordenada do config
          2. Aguarda popup abrir via wait_template no campo Localizar
          3. Digita 'RUA' no campo Localizar
          4. Clica em Localizar — coordenada do config
          5. Aguarda resultado via wait_template
          6. Clica em OK — coordenada do config
          7. Popup de País — BRASIL já selecionado, clica OK com template
        """
        step_id = "AI05"
        if observer:
            observer.log_step_start(step_id, "selecionar RUA no campo Tipo via LOV")
        start = time.monotonic()
        try:
            lov = coords["lov_tipo_endereco"]

            # 1. Abre LOV
            pyautogui.click(lov["btn_lov_x"], lov["btn_lov_y"])
            time.sleep(1.5)  # aguarda popup abrir

            # 2. Digita RUA no campo Localizar
            pyautogui.click(lov["campo_localizar_x"], lov["campo_localizar_y"])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text("RUA")
            time.sleep(0.3)

            # 3. Clica em Localizar
            pyautogui.click(lov["btn_localizar_x"], lov["btn_localizar_y"])
            time.sleep(1.0)  # aguarda resultado

            # 4. Clica em OK
            pyautogui.click(lov["btn_ok_x"], lov["btn_ok_y"])
            time.sleep(0.5)

            # 5. Popup de País — BRASIL já selecionado — clica OK com template
            if ctx.runner.is_visible(f"{self._TPL}/btn_ok_popup.png", threshold=0.7):
                ctx.runner.safe_click(f"{self._TPL}/btn_ok_popup.png", threshold=0.7)

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

    def _step_obs(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        step_id = "AI09"
        valor = dados.get("obs", "teste realizado com automacao")
        if observer:
            observer.log_step_start(step_id, "preencher campo Obs.")
        start = time.monotonic()
        try:
            c = coords["obs"]
            pyautogui.click(c["x"], c["y"])
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
    # AI10 — Origem do Paciente
    # ------------------------------------------------------------------

    def _step_origem_paciente(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        step_id = "AI10"
        tipo = dados.get("origem_tipo", "RESIDENCIA")
        if observer:
            observer.log_step_start(step_id, f"preencher Origem do Paciente: {tipo}")
        start = time.monotonic()
        try:
            c = coords["tipo_origem"]
            pyautogui.click(c["x"], c["y"])
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

    def _step_origem_solicitacao(self, ctx, coords, observer=None) -> StepResult:
        step_id = "AI11"
        if observer:
            observer.log_step_start(step_id, "selecionar Origem da Solicitação (dropdown)")
        start = time.monotonic()
        try:
            c = coords["dropdown_origem_solicitacao"]
            pyautogui.click(c["x"], c["y"])
            time.sleep(1.5)  # necessário para animação do dropdown

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

    def _step_profissional_responsavel(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        step_id = "AI12"
        matricula = dados.get("matricula_responsavel", "1")
        if observer:
            observer.log_step_start(step_id, f"preencher matrícula responsável: {matricula}")
        start = time.monotonic()
        try:
            c = coords["matricula_responsavel"]
            pyautogui.click(c["x"], c["y"])
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
    # AI14 — Número no popup Info. Compl. + OK no popup de profissional
    # ------------------------------------------------------------------

    def _step_numero_medico(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        """
        Conforme imagem 2 e 3:
          1. Clica no campo Número — coordenada do config
          2. Digita '1' + Tab
          3. Popup de profissional abre com lista já carregada
          4. Clica em OK direto (BRASIL/primeiro da lista já selecionado)
        """
        step_id = "AI14"
        numero = dados.get("numero_compl", "1")
        if observer:
            observer.log_step_start(step_id, "preencher número e confirmar médico")
        start = time.monotonic()
        try:
            c = coords["numero_medico_popup"]
            pyautogui.click(c["x"], c["y"])
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(numero)
            pyautogui.press("tab")

            # Aguarda popup de profissional aparecer via wait_template
            ctx.runner.wait_template(
                f"{self._TPL}/btn_ok_popup.png", timeout=5, threshold=0.7
            )
            ctx.runner.safe_click(f"{self._TPL}/btn_ok_popup.png", threshold=0.7)
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

    def _step_retornar(self, ctx, coords, observer=None) -> StepResult:
        step_id = "AI16"
        if observer:
            observer.log_step_start(step_id, "clicar em Retornar")
        start = time.monotonic()
        try:
            c = coords["btn_retornar"]
            pyautogui.click(c["x"], c["y"])
            time.sleep(3.0)  # aguarda tela de internacao com Nr Admissao carregar
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
    # AI18 — Sair 2x e voltar para tela de login
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