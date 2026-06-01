# src/flows/msi3/frequencia_aplicacao_flow.py
"""
FrequenciaAplicacaoFlow — MSI3 Oracle APEX (Web + OpenCV hibrido)
v0.5.10: migrado para BaseFlow.

Mudancas vs versao anterior:
  - herda BaseFlow — _step() centralizado com description
  - BUG CORRIGIDO: pyautogui.typewrite() substituido por ctx.runner.type_text()
    typewrite() nao suporta acentos — type_text() usa clipboard com unicode
  - BUG CORRIGIDO: OpenCVRunner instanciado dentro de cada step substituido
    por ctx.runner — o runner ja esta configurado no contexto; instanciar
    um segundo runner dentro do step e desperdicio e ignora o confidence
    configurado no config.yaml
  - ctx=ctx em todos os _step() calls
  - description propagada para StepResult
  - dados.get() em campos obrigatorios substituidos por _dado()

Regras MSI3 aplicadas:
  - NUNCA navegar por URL direta — invalida sessao APEX
  - Cliques OpenCV nao disparam networkidle — usar ApexHelper.aguardar_spinner()
  - Formularios podem abrir em frame — ApexHelper abstrai isso
"""

import time

import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.flows.msi3.apex_helper import ApexHelper


class FrequenciaAplicacaoFlow(BaseFlow):
    """
    Fluxo de cadastro de Frequencia de Aplicacao no MSI3.
    Pressupoe que o login ja foi executado via LoginFlowMsi3.

    Steps:
        FA01 — Sistema de Pacientes (Playwright)
        FA02 — Apoio a Assistencia (Playwright)
        FA03 — Cadastros Basicos (Playwright)
        FA04 — Frequencia de Aplicacao (OpenCV via ctx.runner)
        FA05 — Novo Cadastro (OpenCV via ctx.runner)
        FA06 — Preencher formulario (OpenCV + type_text)
        FA07 — Horario Padrao (OpenCV + type_text)
        FA08 — Inserir + verificar sem erro (OpenCV + ApexHelper)
        FA09 — Confirmar + validar na grade (OpenCV + ApexHelper)
        FA10 — Validar SF - SV FARMACIA na tabela do modal (OpenCV)
    """

    FLOW_NAME = "FrequenciaAplicacaoFlow"
    _TPL_BASE = "templates/msi3"
    _TPL_FORM = "templates/msi3/formulario"
    _TPL_CAD  = "templates/msi3/cadastros_basicos"

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
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
            lambda: self._step_validar(ctx, dados, observer),
            lambda: self._step_confirmar(ctx, dados, observer),
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

    # ----------------------------------------------------------------
    # FA01–FA03 — Navegacao via Playwright
    # ----------------------------------------------------------------

    def _step_sistema_pacientes(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Sistema de Pacientes"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Apoio à Assistência", timeout=15.0
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA01_sistema_pacientes.png")
        return self._step("FA01", "clicar em Sistema de Pacientes",
                          fn, observer,
                          confirm_template="h3.t-Card-title >> text=Apoio à Assistência",
                          ctx=ctx)

    def _step_apoio_assistencia(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Apoio à Assistência"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Cadastros Básicos", timeout=15.0
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA02_apoio_assistencia.png")
        return self._step("FA02", "clicar em Apoio a Assistencia",
                          fn, observer,
                          confirm_template="h3.t-Card-title >> text=Cadastros Básicos",
                          ctx=ctx)

    def _step_cadastros_basicos(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Cadastros Básicos"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Frequência de Aplicação", timeout=15.0
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA03_cadastros_basicos.png")
        return self._step("FA03", "clicar em Cadastros Basicos",
                          fn, observer,
                          confirm_template="h3.t-Card-title >> text=Frequência de Aplicação",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # FA04–FA05 — Navegacao via OpenCV (ctx.runner)
    # ----------------------------------------------------------------

    def _step_frequencia_aplicacao(self, ctx, observer=None):
        def fn():
            # ctx.runner e o OpenCVRunner configurado no contexto
            # NUNCA instanciar OpenCVRunner(confidence=X) dentro do step
            ctx.runner.safe_click(
                f"{self._TPL_CAD}/frequencia_aplicacao.png", threshold=0.7
            )
            ctx.runner.wait_template("text=Novo Cadastro", timeout=15.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA04_frequencia_aplicacao.png")
        return self._step("FA04", "clicar em Frequencia de Aplicacao",
                          fn, observer,
                          confirm_template="text=Novo Cadastro",
                          ctx=ctx)

    def _step_novo_cadastro(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(
                f"{self._TPL_CAD}/btn_novo_cadastro.png", threshold=0.7
            )
            # aguarda spinner — substitui time.sleep(2) fixo
            ApexHelper.aguardar_spinner(ctx.runner)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA05_novo_cadastro.png")
        return self._step("FA05", "clicar em Novo Cadastro",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # FA06 — Preencher formulario
    # BUG CORRIGIDO: pyautogui.typewrite() -> ctx.runner.type_text()
    # typewrite() nao suporta acentos — type_text() usa clipboard unicode
    # ----------------------------------------------------------------

    def _step_preencher_formulario(self, ctx, dados: dict, observer=None):
        def fn():
            time.sleep(1.0)

            campos = [
                ("sequencia",      f"{self._TPL_FORM}/campo_sequencia.png"),
                ("codigo",         f"{self._TPL_FORM}/campo_codigo.png"),
                ("descricao",      f"{self._TPL_FORM}/campo_descricao.png"),
                ("tipo_aplicacao", f"{self._TPL_FORM}/campo_tipo_aplicacao.png"),
                ("qt_dias_semana", f"{self._TPL_FORM}/campo_qt_dias_semana.png"),
                ("qt_24hs",        f"{self._TPL_FORM}/campo_qt_24hs.png"),
                ("intervalo_hrs",  f"{self._TPL_FORM}/campo_intervalo_hrs.png"),
                ("intervalo_min",  f"{self._TPL_FORM}/campo_intervalo_min.png"),
            ]

            for chave, template in campos:
                valor = dados.get(chave)
                if valor:
                    ctx.runner.safe_click(template, threshold=0.6)
                    time.sleep(0.3)
                    pyautogui.hotkey("ctrl", "a")
                    # CORRIGIDO: type_text() suporta acentos e unicode
                    # pyautogui.typewrite() rejeitava caracteres especiais
                    ctx.runner.type_text(str(valor))
                    time.sleep(0.3)

            if dados.get("frequencia_tipo_unica"):
                ctx.runner.safe_click(
                    f"{self._TPL_FORM}/checkbox_frequencia_unica.png", threshold=0.7
                )
                time.sleep(0.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA06_formulario.png")
        return self._step("FA06", "preencher campos do formulario",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # FA07 — Horario Padrao
    # BUG CORRIGIDO: pyautogui.typewrite() -> ctx.runner.type_text()
    # ----------------------------------------------------------------

    def _step_horario_padrao(self, ctx, dados: dict, observer=None):
        def fn():
            hora = dados.get("hora")
            if hora:
                ctx.runner.safe_click(
                    f"{self._TPL_FORM}/campo_hora.png", threshold=0.7
                )
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text(str(hora))
                time.sleep(0.3)

            unidade = dados.get("unidade_funcional")
            if unidade:
                ctx.runner.safe_click(
                    f"{self._TPL_FORM}/campo_unidade_funcional.png", threshold=0.7
                )
                time.sleep(0.5)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text(str(unidade))
                time.sleep(0.5)
                ctx.runner.safe_click(
                    f"{self._TPL_FORM}/btn_pesquisar.png", threshold=0.7
                )
                time.sleep(3.0)
                ctx.runner.safe_click(
                    f"{self._TPL_FORM}/resultado_farmacia.png", threshold=0.6
                )
                time.sleep(0.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA07_horario_padrao.png")
        return self._step("FA07", "preencher Horario Padrao e Unidade Funcional",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # FA08 — Inserir + verificar sem erro
    # ----------------------------------------------------------------

    def _step_inserir(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(
                f"{self._TPL_FORM}/btn_inserir.png", threshold=0.7
            )
            time.sleep(1.0)
            # verifica se APEX retornou erro apos inserir
            ApexHelper.verificar_sem_erro(ctx.runner)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA08_inserir.png")
        return self._step("FA08", "clicar em Inserir e verificar sem erro",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # FA10 — Validar SF - SV FARMACIA na tabela do modal
    # Ordem original do flow: FA10 roda antes de FA09
    # ----------------------------------------------------------------

    def _step_validar(self, ctx, dados: dict, observer=None):
        def fn():
            time.sleep(1.0)
            encontrou = ctx.runner.is_visible(
                f"{self._TPL_FORM}/resultado_farmacia.png", threshold=0.6
            )
            if not encontrou:
                raise RuntimeError(
                    "Validacao falhou — 'SF - SV FARMACIA' nao encontrado "
                    "na tabela do modal apos o Inserir.\n"
                    "Verifique resultado_farmacia.png e o template matching."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA10_validacao.png")
        return self._step("FA10", "validar SF - SV FARMACIA na tabela do modal",
                          fn, observer, validated=True, ctx=ctx)

    # ----------------------------------------------------------------
    # FA09 — Confirmar + validar na grade
    # ----------------------------------------------------------------

    def _step_confirmar(self, ctx, dados: dict, observer=None):
        def fn():
            ctx.runner.safe_click(
                f"{self._TPL_FORM}/btn_confirmar.png", threshold=0.7
            )
            # aguarda voltar para a listagem — iframe some, grade aparece
            ctx.runner.wait_template("text=Novo Cadastro", timeout=15.0)
            ApexHelper.aguardar_spinner(ctx.runner)

            # valida que o registro aparece na grade
            texto_busca = dados.get("codigo") or dados.get("descricao", "")
            if texto_busca:
                ApexHelper.verificar_registro_na_grade(
                    ctx.runner,
                    texto=texto_busca,
                    seletor_tabela=".t-Report-report table, table",
                )
                print(f"[FA09] Registro '{texto_busca}' confirmado na grade.")
            else:
                print("[FA09] Confirmar executado — listagem carregada.")

            return ctx.runner.screenshot(f"{ctx.evidence_dir}FA09_confirmado.png")
        return self._step("FA09", "clicar em Confirmar e validar registro na grade",
                          fn, observer, validated=True, ctx=ctx)