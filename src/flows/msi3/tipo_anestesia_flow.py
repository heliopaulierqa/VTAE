# src/flows/msi3/tipo_anestesia_flow.py
"""
TipoAnestesiaFlow — MSI3 Oracle APEX (Web — Playwright puro)
v0.5.10

Caminho de navegacao (confirmado via DevTools):
  Login → Sistema de Pacientes → Cirurgia (NOVO) →
  Cadastros Basicos → Intra-operatório (card unico) →
  Tipo Anestesia → Novo Tipo Anestesia →
  preenche (Codigo, Descricao, Tipo) → Confirmar

Atencao: texto exato do card e "Intra-operatório" (o minusculo).

Steps:
  TA01 — clicar em Sistema de Pacientes
  TA02 — clicar em Cirurgia (NOVO)
  TA03 — clicar em Cadastros Basicos  → confirma card Intra-operatório
  TA04 — clicar em Intra-operatório   → confirma card Tipo Anestesia
  TA05 — clicar em Tipo Anestesia     → confirma botao Novo Tipo Anestesia
  TA06 — clicar em Novo Tipo Anestesia
  TA07 — preencher formulario
  TA08 — confirmar e validar na grade
"""

import time

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.flows.msi3.apex_helper import ApexHelper


class TipoAnestesiaFlow(BaseFlow):

    FLOW_NAME = "TipoAnestesiaFlow"
    _TPL      = "templates/msi3/tipo_anestesia"

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        steps = [
            lambda: self._step_sistema_pacientes(ctx, observer),
            lambda: self._step_cirurgia_novo(ctx, observer),
            lambda: self._step_cadastros_basicos(ctx, observer),
            lambda: self._step_intra_operatorio(ctx, observer),
            lambda: self._step_tipo_anestesia(ctx, observer),
            lambda: self._step_novo_tipo_anestesia(ctx, observer),
            lambda: self._step_preencher_formulario(ctx, dados, observer),
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
    # TA01–TA05 — Navegacao via Playwright
    # ----------------------------------------------------------------

    def _step_sistema_pacientes(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Sistema de Pacientes"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Cirurgia (NOVO)", timeout=15.0
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}TA01_sistema_pacientes.png")
        return self._step("TA01", "clicar em Sistema de Pacientes",
                          fn, observer,
                          confirm_template="h3.t-Card-title >> text=Cirurgia (NOVO)",
                          ctx=ctx)

    def _step_cirurgia_novo(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Cirurgia (NOVO)"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Cadastros Básicos", timeout=15.0
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}TA02_cirurgia_novo.png")
        return self._step("TA02", "clicar em Cirurgia (NOVO)",
                          fn, observer,
                          confirm_template="h3.t-Card-title >> text=Cadastros Básicos",
                          ctx=ctx)

    def _step_cadastros_basicos(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Cadastros Básicos"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            # Abre com card unico "Intra-operatório" (o minusculo — confirmado via DevTools)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Intra-operatório", timeout=15.0
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}TA03_cadastros_basicos.png")
        return self._step("TA03", "clicar em Cadastros Basicos",
                          fn, observer,
                          confirm_template="h3.t-Card-title >> text=Intra-operatório",
                          ctx=ctx)

    def _step_intra_operatorio(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Intra-operatório"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "h3.t-Card-title >> text=Tipo Anestesia", timeout=15.0
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}TA04_intra_operatorio.png")
        return self._step("TA04", "clicar em Intra-operatorio",
                          fn, observer,
                          confirm_template="h3.t-Card-title >> text=Tipo Anestesia",
                          ctx=ctx)

    def _step_tipo_anestesia(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "h3.t-Card-title", has_text="Tipo Anestesia"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "text=Novo Tipo Anestesia", timeout=15.0
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}TA05_tipo_anestesia.png")
        return self._step("TA05", "clicar em Tipo Anestesia",
                          fn, observer,
                          confirm_template="text=Novo Tipo Anestesia",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # TA06 — Novo Tipo Anestesia
    # ----------------------------------------------------------------

    def _step_novo_tipo_anestesia(self, ctx, observer=None):
        def fn():
            ctx.runner._page.locator(
                "button, a", has_text="Novo Tipo Anestesia"
            ).click()
            ApexHelper.aguardar_spinner(ctx.runner)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}TA06_novo_tipo_anestesia.png")
        return self._step("TA06", "clicar em Novo Tipo Anestesia",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # TA07 — Preencher formulario
    # ----------------------------------------------------------------

    def _step_preencher_formulario(self, ctx, dados: dict, observer=None):
        def fn():
            codigo    = self._dado(dados, "codigo", "TA07")
            descricao = self._dado(dados, "descricao", "TA07")
            tipo      = self._dado(dados, "tipo_anestesia", "TA07")

            page = ctx.runner._page

            # Tenta localizar frame do formulario APEX
            target = page
            for f in page.frames:
                try:
                    if f.locator("input, select, textarea").count() > 2:
                        target = f
                        break
                except Exception:
                    pass

            # Codigo
            campo_cod = target.locator(
                "input[name*='ODIGO'], input[id*='ODIGO'], input[placeholder*='dig']"
            ).first
            campo_cod.click()
            time.sleep(0.3)
            campo_cod.fill(str(codigo))
            time.sleep(0.3)

            # Descricao
            campo_desc = target.locator(
                "input[name*='ESC'], textarea[name*='ESC'], "
                "input[id*='ESC'], textarea[id*='ESC']"
            ).first
            campo_desc.click()
            time.sleep(0.3)
            campo_desc.fill(str(descricao))
            time.sleep(0.3)

            # Tipo de Anestesia — dropdown
            select = target.locator(
                "select[name*='TIPO'], select[id*='TIPO'], "
                "select[name*='ANEST'], select[id*='ANEST']"
            ).first
            select.select_option(label=tipo)
            time.sleep(0.5)

            print(f"[TA07] codigo={codigo} | descricao={descricao} | tipo={tipo}")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}TA07_formulario.png")
        return self._step("TA07", "preencher formulario Tipo Anestesia",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # TA08 — Confirmar + validar na grade
    # Sem mensagem de sucesso — volta para listagem apos confirmar
    # ----------------------------------------------------------------

    def _step_confirmar(self, ctx, dados: dict, observer=None):
        def fn():
            page = ctx.runner._page

            target = page
            for f in page.frames:
                try:
                    btn = f.locator("button:has-text('Confirmar'), input[value='Confirmar']")
                    if btn.count() > 0:
                        target = f
                        break
                except Exception:
                    pass

            target.locator(
                "button:has-text('Confirmar'), input[value='Confirmar']"
            ).first.click()

            ApexHelper.aguardar_spinner(ctx.runner)
            ctx.runner.wait_template(
                "text=Novo Tipo Anestesia", timeout=15.0
            )

            codigo = dados.get("codigo", "")
            if codigo:
                ApexHelper.verificar_registro_na_grade(
                    ctx.runner,
                    texto=codigo,
                    seletor_tabela=".t-Report-report table, table",
                )
                print(f"[TA08] Registro '{codigo}' confirmado na grade.")
            else:
                print("[TA08] Confirmar executado — listagem carregada.")

            return ctx.runner.screenshot(f"{ctx.evidence_dir}TA08_confirmado.png")
        return self._step("TA08", "confirmar e validar registro na grade",
                          fn, observer, validated=True, ctx=ctx)

    # ----------------------------------------------------------------
    # Helper
    # ----------------------------------------------------------------

    def _dado(self, dados: dict, chave: str, step_id: str):
        if chave not in dados:
            raise AssertionError(
                f"[{step_id}] Dado obrigatorio ausente: '{chave}'.\n"
                f"Adicionar em dados: no config.yaml de msi3_tipo_anestesia."
            )
        return dados[chave]