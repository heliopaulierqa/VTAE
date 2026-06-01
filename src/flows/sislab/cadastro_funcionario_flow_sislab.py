# src/flows/sislab/cadastro_funcionario_flow.py
"""
CadastroFuncionarioFlowSislab — SisLab Oracle Forms (Desktop)
v0.5.10: migrado para BaseFlow.

Mudancas vs versao anterior:
  - herda BaseFlow — _step() centralizado com description
  - import corrigido: OcrHelper de src.vision.ocr (nao src.core.ocr_helper)
  - coordenadas hardcoded movidas para constantes de classe documentadas
    (pendente: mover para config.yaml quando o SisLab tiver config proprio)
  - ctx=ctx em todos os _step() calls
  - description propagada para StepResult

Nota sobre coordenadas hardcoded:
  _COORD_BTN_FUNCIONARIOS, _COORD_BTN_NOVO, _COORD_BTN_SALVAR ainda sao
  constantes de classe porque o SisLab nao tem config.yaml proprio ainda.
  Quando criar configs/sislab/sislab_funcionario/config.yaml, mover para
  coordenadas: e usar self._coord(coords, "btn_funcionarios") etc.
"""

import time

import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.vision.ocr import OcrHelper


class CadastroFuncionarioFlowSislab(BaseFlow):
    """
    Flow de cadastro de funcionario no SisLab (Oracle Forms desktop).

    Pre-condicao: usuario ja esta logado e a tela de Cadastro de Funcionarios
    esta visivel.

    Estrategia de preenchimento:
        Apos clicar em Novo, o foco vai automaticamente para o campo Nome.
        A navegacao entre campos e feita via Tab — sem cliques intermediarios.

    Steps:
        CF01 — Clica em Funcionarios no menu principal
        CF02 — Clica em Novo (foco vai para Nome automaticamente)
        CF03 — Digita Nome (Tab para avancar)
        CF04 — Digita CPF (Tab para avancar)
        CF05 — Tab ate Cargo + seleciona com seta
        CF06 — Tab ate Departamento + seleciona com seta
        CF07 — Tab ate Salario + digita
        CF08 — Tab ate Admissao + digita
        CF09 — Clica em Salvar + valida mensagem de sucesso
        CF10 — Verifica nome na grade via OCR

    Templates em templates/sislab/funcionario/:
        btn_novo.png, btn_salvar.png, campo_nome.png,
        tela_cadastro_funcionario.png, msg_sucesso.png

    Templates em templates/sislab/menu/:
        menu_principal.png, btn_funcionarios.png
    """

    FLOW_NAME = "CadastroFuncionarioFlowSislab"

    # Coordenadas hardcoded — mover para config.yaml quando SisLab tiver config proprio
    _COORD_BTN_FUNCIONARIOS = (79,  233)
    _COORD_BTN_NOVO         = (25,  146)
    _COORD_BTN_SALVAR       = (85,  148)

    # Regiao da grade — linha abaixo do cabecalho
    _REGIAO_GRADE = (0, 615, 1366, 760)

    # Posicao nos dropdowns (0=selecione, 1=primeira opcao, 2=segunda opcao)
    _CARGO_POSICAO = 2   # ANALISTA DE RH
    _DEPTO_POSICAO = 2   # ADMINISTRACAO

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)

        for step_fn in [
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
        ]:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    # ----------------------------------------------------------------
    # Helper privado — clique com fallback para coordenada
    # Especifico deste flow — nao vai para BaseFlow
    # ----------------------------------------------------------------

    def _clicar_com_fallback(self, ctx, template: str,
                              coords: tuple, threshold: float = 0.7) -> None:
        """Tenta template OpenCV; usa coordenadas fixas como fallback."""
        try:
            ctx.runner.safe_click(template, threshold=threshold)
        except Exception:
            print(f"[fallback] '{template}' nao encontrado — coords {coords}")
            pyautogui.click(coords[0], coords[1])
            time.sleep(0.5)

    # ----------------------------------------------------------------
    # CF01 — Abrir Funcionarios
    # ----------------------------------------------------------------

    def _step_abrir_funcionarios(self, ctx, observer=None):
        def fn():
            ctx.runner.wait_template(
                "templates/sislab/menu/menu_principal.png",
                timeout=10.0, threshold=0.7,
            )
            self._clicar_com_fallback(
                ctx,
                "templates/sislab/menu/btn_funcionarios.png",
                self._COORD_BTN_FUNCIONARIOS,
            )
            ctx.runner.wait_template(
                "templates/sislab/funcionario/tela_cadastro_funcionario.png",
                timeout=10.0, threshold=0.7,
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF01.png")
        return self._step("CF01", "clicar em Funcionarios no menu principal",
                          fn, observer,
                          confirm_template="templates/sislab/funcionario/tela_cadastro_funcionario.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # CF02 — Clicar Novo
    # ----------------------------------------------------------------

    def _step_clicar_novo(self, ctx, observer=None):
        def fn():
            self._clicar_com_fallback(
                ctx,
                "templates/sislab/funcionario/btn_novo.png",
                self._COORD_BTN_NOVO,
            )
            ctx.runner.wait_template(
                "templates/sislab/funcionario/campo_nome.png",
                timeout=10.0, threshold=0.7,
            )
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF02.png")
        return self._step("CF02", "clicar em Novo — foco vai para Nome",
                          fn, observer,
                          confirm_template="templates/sislab/funcionario/campo_nome.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # CF03 — Preencher Nome
    # ----------------------------------------------------------------

    def _step_preencher_nome(self, ctx, observer=None):
        def fn():
            nome = self._dado(ctx.config.DADOS, "nome", "CF03")
            ctx.runner.type_text(nome)
            time.sleep(0.3)
            pyautogui.press("tab")  # avanca para CPF
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF03.png")
        return self._step("CF03", "preencher Nome do funcionario",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # CF04 — Preencher CPF
    # ----------------------------------------------------------------

    def _step_preencher_cpf(self, ctx, observer=None):
        def fn():
            cpf = self._dado(ctx.config.DADOS, "cpf", "CF04")
            ctx.runner.type_text(cpf)
            time.sleep(0.3)
            pyautogui.press("tab")  # E-mail
            time.sleep(0.3)
            pyautogui.press("tab")  # Telefone
            time.sleep(0.3)
            pyautogui.press("tab")  # Cargo
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF04.png")
        return self._step("CF04", "preencher CPF do funcionario",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # CF05 — Selecionar Cargo
    # ----------------------------------------------------------------

    def _step_selecionar_cargo(self, ctx, observer=None):
        def fn():
            cargo = self._dado(ctx.config.DADOS, "cargo", "CF05")
            print(f"[CF05] Selecionando cargo: {cargo} (posicao {self._CARGO_POSICAO})")
            for _ in range(self._CARGO_POSICAO):
                pyautogui.press("down"); time.sleep(0.2)
            pyautogui.press("tab")  # avanca para Departamento
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF05.png")
        return self._step("CF05", "selecionar Cargo no dropdown",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # CF06 — Selecionar Departamento
    # ----------------------------------------------------------------

    def _step_selecionar_departamento(self, ctx, observer=None):
        def fn():
            depto = self._dado(ctx.config.DADOS, "departamento", "CF06")
            print(f"[CF06] Selecionando departamento: {depto} (posicao {self._DEPTO_POSICAO})")
            for _ in range(self._DEPTO_POSICAO):
                pyautogui.press("down"); time.sleep(0.2)
            pyautogui.press("tab")  # avanca para Salario
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF06.png")
        return self._step("CF06", "selecionar Departamento no dropdown",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # CF07 — Preencher Salario
    # ----------------------------------------------------------------

    def _step_preencher_salario(self, ctx, observer=None):
        def fn():
            salario = self._dado(ctx.config.DADOS, "salario", "CF07")
            ctx.runner.type_text(salario)
            time.sleep(0.3)
            pyautogui.press("tab")  # avanca para Admissao
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF07.png")
        return self._step("CF07", "preencher Salario",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # CF08 — Preencher Data de Admissao
    # ----------------------------------------------------------------

    def _step_preencher_admissao(self, ctx, observer=None):
        def fn():
            admissao = self._dado(ctx.config.DADOS, "admissao", "CF08")
            ctx.runner.type_text(admissao)
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF08.png")
        return self._step("CF08", "preencher Data de Admissao",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # CF09 — Salvar + validar mensagem de sucesso
    # ----------------------------------------------------------------

    def _step_salvar(self, ctx, observer=None):
        def fn():
            self._clicar_com_fallback(
                ctx,
                "templates/sislab/funcionario/btn_salvar.png",
                self._COORD_BTN_SALVAR,
            )
            sucesso = ctx.runner.wait_template(
                "templates/sislab/funcionario/msg_sucesso.png",
                timeout=10.0, threshold=0.7,
            )
            if not sucesso:
                raise AssertionError(
                    "Mensagem de sucesso nao apareceu apos Salvar.\n"
                    "Verifique se o formulario foi preenchido corretamente."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CF09.png")
        return self._step("CF09", "clicar em Salvar e validar mensagem de sucesso",
                          fn, observer,
                          confirm_template="templates/sislab/funcionario/msg_sucesso.png",
                          validated=True,
                          ctx=ctx)

    # ----------------------------------------------------------------
    # CF10 — Verificar nome na grade via OCR
    # ----------------------------------------------------------------

    def _step_verificar_salvo_ocr(self, ctx, observer=None):
        def fn():
            time.sleep(0.8)
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}CF10.png")
            nome_esperado = self._dado(ctx.config.DADOS, "nome", "CF10").upper()

            encontrado, token = OcrHelper.contem_qualquer_token(
                screenshot_path,
                tokens=nome_esperado.split(),
                regiao=self._REGIAO_GRADE,
            )
            if not encontrado:
                OcrHelper.salvar_debug(
                    screenshot_path, self._REGIAO_GRADE,
                    f"{ctx.evidence_dir}CF10_ocr_debug.png"
                )
                texto_lido = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_GRADE)
                raise AssertionError(
                    f"Nome '{nome_esperado}' nao encontrado na grade.\n"
                    f"Texto lido pelo OCR:\n{texto_lido}\n"
                    f"Veja: {ctx.evidence_dir}CF10_ocr_debug.png\n"
                    f"Ajuste _REGIAO_GRADE = (x1, y1, x2, y2) conforme o screenshot."
                )
            print(f"[CF10] OCR confirmou '{token}' na grade.")
            return screenshot_path
        return self._step("CF10", "verificar nome do funcionario na grade via OCR",
                          fn, observer, validated=True, ctx=ctx)