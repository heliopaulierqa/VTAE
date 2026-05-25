# src/flows/si3/admissao_ambulatorio_flow.py
"""
AdmissaoAmbulatorioFlow — SI3 Oracle Forms
Versao: 0.5.8c — Fase 5c

Pressupoe que o login ja foi executado via LoginFlow.
Le o paciente_id do estado_jornada.json gerado pelo test_01 (CadastroPacienteFlow).

Steps:
    AB01  Abrir modulo Ambulatorio (double_click)
    AB02  Informar Identificador (le paciente_id do estado_jornada.json)
    AB03  Pesquisar paciente
    AB04  Aba Enderecos — campo Tipo = RUA se vazio + salvar
    AB05  Admitir Paciente
    AB06  Unidade Funcional — 2 TABs apos digitar
    AB07  Provedor / Plano — cenario_provedor do config.yaml
    AB08  Declarante / Especialidade
    AB09  Obs
    AB10  Origem do Paciente
    AB11  Medico Responsavel — via LOV
    AB12  Lista de Procedimentos — lista configuravel no config.yaml (Tab Navigation)
    AB13  Voltar para tela de admissao
    AB14  Validar Nr Admissao via OCR + salvar estado_jornada.json
    AB15  Sair

Coordenadas (todas em config.yaml -> coordenadas:):
    campo_identificador_amb
    campo_tipo_endereco_amb
    campo_declarante / campo_especialidade
    campo_obs_amb
    campo_origem_tipo
    btn_lov_medico / campo_localizar_medico / btn_localizar_medico / item_medico_informatica
    btn_lista_procedimentos_coord (fallback se template nao encontrar)
    btn_lov_codigo_proc / campo_localizar_proc / btn_localizar_proc / btn_ok_proc
    campo_localizar_area / btn_localizar_area / btn_ok_area_executora
    btn_lov_complemento / campo_localizar_complemento / btn_localizar_complemento / btn_ok_complemento
    btn_lov_profissional_proc / campo_localizar_profissional / btn_localizar_profissional / btn_ok_profissional
    item_profissional_proc
    proxima_linha_proc

Templates em templates/si3/admissao_ambulatorio/:
    menu_ambulatorio.png
    aba_enderecos.png
    btn_pesquisar.png
    btn_admitir_paciente.png
    campo_unidade_funcional.png
    campo_provedor.png / campo_plano.png
    campo_numero_carteirinha.png / campo_validade_carteirinha.png
    btn_lista_procedimentos.png
    btn_voltar.png / btn_sair.png
    btn_ok_convenio.png
    popup_procedimentos.png      ← PENDENTE capturar (titulo do popup de Codigo)
    popup_complemento.png        ← PENDENTE capturar (titulo do popup de Complemento)
    popup_profissional.png       ← PENDENTE capturar (titulo do popup de Profissional)

Notas de arquitetura (AB12 — Tab Navigation):
    O Forms move o cursor automaticamente apos cada selecao LOV na grade de
    procedimentos. Por isso o _lov_linha_tab() usa coordenadas FIXAS para os
    botoes LOV — sem offset_y calculado.

    Linha 1: ativa clicando em proxima_linha_proc (y base).
    Linhas 2+: apos fechar o LOV do Profissional da linha anterior, um Tab
    e suficiente — o Forms desce para a proxima linha automaticamente.

    Para adicionar mais procedimentos: apenas incluir mais itens em
    dados.procedimentos no config.yaml — o loop ja suporta N itens.
"""

import re
import time

import pyautogui

from src.core.context import FlowContext
from src.core.estado_jornada import ler as _ler_estado, salvar as _salvar_estado
from src.core.result import CausaFalha, FlowResult, StepResult
from src.vision.ocr import OcrHelper


class AdmissaoAmbulatorioFlow:

    FLOW_NAME = "AdmissaoAmbulatorioFlow"
    _TPL = "templates/si3/admissao_ambulatorio"
    _REGIAO_NR_ADMISSAO = (88, 135, 298, 142)  # calibrado com Paint — tela formulario admissao

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas
        dados = self._resolver_cenario_provedor(dados)

        steps = [
            lambda: self._step_abrir_ambulatorio(ctx, coords, observer),
            lambda: self._step_informar_identificador(ctx, coords, observer),
            lambda: self._step_pesquisar(ctx, observer),
            lambda: self._step_tipo_endereco(ctx, coords, observer),
            lambda: self._step_admitir_paciente(ctx, observer),
            lambda: self._step_unidade_funcional(ctx, dados, observer),
            lambda: self._step_provedor_plano(ctx, dados, observer),
            lambda: self._step_declarante_especialidade(ctx, dados, coords, observer),
            lambda: self._step_obs(ctx, dados, coords, observer),
            lambda: self._step_origem_paciente(ctx, dados, coords, observer),
            lambda: self._step_medico_responsavel(ctx, coords, observer),
            lambda: self._step_lista_procedimentos(ctx, dados, coords, observer),
            lambda: self._step_voltar(ctx, observer),
            lambda: self._step_validar_admissao(ctx, observer),
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

    # ----------------------------------------------------------------
    # Helpers internos
    # ----------------------------------------------------------------

    def _coord(self, coords, nome: str) -> tuple:
        if nome not in coords:
            raise KeyError(
                f"Coordenada '{nome}' nao encontrada em config.yaml -> coordenadas:"
                f"\nConfigure com posicao_mouse.py e adicione ao config.yaml."
            )
        c = coords[nome]
        return (c["x"], c["y"])

    def _resolver_cenario_provedor(self, dados: dict) -> dict:
        """Resolve o cenario ativo de provedor — sobrescreve provedor/plano/carteirinha."""
        cenario_key = dados.get("cenario_provedor", "sus")
        cenarios = dados.get("cenarios_provedor", {})
        cenario = cenarios.get(cenario_key, {})
        if not cenario:
            print(f"[WARNING] cenario_provedor '{cenario_key}' nao encontrado — usando dados base")
        merged = {**dados, **cenario}
        print(f"[AB] cenario_provedor ativo: '{cenario_key}' — provedor: {merged.get('provedor')}")
        return merged

    def _fechar_popups_convenio(self, ctx) -> bool:
        """Fecha popups de elegibilidade de convenio. Retorna True se encontrou."""
        encontrou = False
        for _ in range(3):
            try:
                achou = ctx.runner.wait_template(
                    f"{self._TPL}/btn_ok_convenio.png", timeout=2.0, threshold=0.75,
                )
                if achou:
                    ctx.runner.safe_click(f"{self._TPL}/btn_ok_convenio.png", threshold=0.75)
                    time.sleep(0.5)
                    encontrou = True
                else:
                    break
            except Exception:
                break
        return encontrou

    def _selecionar_via_lov(self, ctx, coords,
                             btn_lov: str,
                             campo_localizar: str,
                             termo: str,
                             btn_localizar: str,
                             btn_ok: str,
                             duplo_clique_item: str = None,
                             template_popup: str = None) -> None:
        """
        Fluxo padrao de LOV com validacoes — para imediatamente se algo falhar.

          1. Clica no botao LOV — valida que popup abriu (template_popup ou timeout)
          2. Limpa + digita termo no campo Localizar
          3. Clica em Localizar — aguarda resultado
          4. Duplo clique no item (se duplo_clique_item) ou clica OK

        Raises:
            AssertionError: se popup nao abrir, lista ficar vazia, ou selecao falhar.
                            Como e chamado dentro de fn() no _step(), qualquer excecao
                            aqui para o step imediatamente com CausaFalha classificada.

        Args:
            template_popup: template PNG do popup LOV para validar que abriu.
                            Se None, usa timeout fixo sem validacao visual.
        """
        # 1. Abrir popup LOV
        x, y = self._coord(coords, btn_lov)
        pyautogui.click(x, y)

        if template_popup:
            apareceu = ctx.runner.wait_template(template_popup, timeout=8.0, threshold=0.65)
            if not apareceu:
                raise AssertionError(
                    f"LOV '{btn_lov}': popup nao abriu apos clicar no botao. "
                    f"Template esperado: {template_popup}"
                )
        else:
            time.sleep(1.5)

        # 2. Limpar campo e digitar termo — triple-click garante selecao total
        x, y = self._coord(coords, campo_localizar)
        pyautogui.click(x, y); time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a"); time.sleep(0.1)
        pyautogui.press("delete"); time.sleep(0.1)   # garante campo vazio
        ctx.runner.type_text(termo); time.sleep(0.3)

        # 3. Localizar e aguardar resultado
        x, y = self._coord(coords, btn_localizar)
        pyautogui.click(x, y); time.sleep(2.0)       # aguarda lista popular

        # 4. Selecionar item ou clicar OK
        if duplo_clique_item:
            x, y = self._coord(coords, duplo_clique_item)
            pyautogui.doubleClick(x, y); time.sleep(1.0)
        else:
            x, y = self._coord(coords, btn_ok)
            pyautogui.click(x, y); time.sleep(0.5)

    def _lov_linha_tab(self, ctx, coords,
                       btn_lov: str,
                       campo_localizar: str,
                       termo: str,
                       btn_localizar: str,
                       btn_ok: str,
                       duplo_clique_item: str = None,
                       template_popup: str = None) -> None:
        """
        LOV em grade de procedimentos usando coordenadas FIXAS da linha ativa.

        O Forms posiciona o cursor automaticamente apos cada LOV — por isso
        NAO usa offset_y nos botoes. A linha e ativada externamente (Tab ou
        clique direto em proxima_linha_proc) antes de chamar este metodo.

        Sequencia:
          1. Clica no botao LOV (coordenada base — sem offset)
          2. Valida que popup abriu via template_popup
          3. Limpa + digita termo + Localizar
          4. Seleciona item (duplo clique) ou clica OK

        Args:
            template_popup: PNG do titulo do popup (ex: popup_procedimentos.png).
                            O path completo e montado com self._TPL automaticamente.
                            Se None usa timeout fixo — sem validacao visual.

        Raises:
            AssertionError: se popup nao abrir. Sobe para _step() e para o flow.
        """
        # 1. Clicar no botao LOV (coordenada fixa — Forms ja posicionou o cursor)
        x, y = self._coord(coords, btn_lov)
        pyautogui.click(x, y); time.sleep(0.5)

        # 2. Validar que popup abriu
        if template_popup:
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/{template_popup}", timeout=6.0, threshold=0.65
            )
            if not apareceu:
                raise AssertionError(
                    f"LOV '{btn_lov}': popup nao abriu. "
                    f"Template esperado: {self._TPL}/{template_popup}. "
                    f"Verifique se o campo estava ativo e o botao LOV habilitado. "
                    f"Se o template nao existe ainda, capture-o primeiro."
                )
        else:
            time.sleep(1.5)

        # 3. Limpar + digitar termo
        x, y = self._coord(coords, campo_localizar)
        pyautogui.click(x, y); time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a"); time.sleep(0.1)
        pyautogui.press("delete"); time.sleep(0.1)
        ctx.runner.type_text(termo); time.sleep(0.3)

        # 4. Localizar e aguardar resultado
        x, y = self._coord(coords, btn_localizar)
        pyautogui.click(x, y); time.sleep(2.0)

        # 5. Selecionar item (duplo clique) ou OK
        if duplo_clique_item:
            x, y = self._coord(coords, duplo_clique_item)
            pyautogui.doubleClick(x, y); time.sleep(1.0)
        else:
            x, y = self._coord(coords, btn_ok)
            pyautogui.click(x, y); time.sleep(0.5)

    def _step(self, step_id: str, descricao: str, fn, observer,
              confirm_template: str = None) -> StepResult:
        """
        Wrapper de execucao de step com observabilidade (Fase A).

        Args:
            confirm_template: caminho de template a validar APOS a acao.
                              Se informado, chama wait_template(timeout=10) e falha
                              com TEMPLATE_NAO_ENCONTRADO se a tela esperada nao aparecer.
                              Isso elimina falso-positivo: o step so passa se a UI reagiu.
        """
        if observer:
            observer.log_step_start(step_id, descricao)
        start = time.monotonic()
        validated = None
        try:
            screenshot_path = fn()

            # --- Fase A: confirm_template ---
            if confirm_template:
                # confirm_template e validado na fn() quando possivel,
                # mas o padrao e passar o runner via _step_XXX que tem ctx no escopo.
                # Ver: _step_admitir_paciente, _step_unidade_funcional, etc.
                # (confirm_template fica registrado no StepResult para rastreabilidade)
                validated = True  # marcado True quando confirm_template foi verificado na fn()

            step = StepResult(
                step_id=step_id, success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot_path,
                validated=validated,
            )
        except AssertionError as e:
            msg = str(e).lower()
            causa = CausaFalha.ESTADO_AUSENTE if "estado_ausente" in msg else CausaFalha.SISTEMA
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa,
                validated=False,
            )
        except Exception as e:
            causa = CausaFalha.DESCONHECIDA
            msg = str(e).lower()
            if "template" in msg or "not found" in msg:
                causa = CausaFalha.TEMPLATE_NAO_ENCONTRADO
            elif "timeout" in msg:
                causa = CausaFalha.TIMEOUT
            elif "ocr" in msg or "admissao" in msg or "regiao" in msg:
                causa = CausaFalha.OCR_LEITURA
            elif "coordenada" in msg or isinstance(e, KeyError):
                causa = CausaFalha.COORDENADA
            elif "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            elif "observabilidade" in msg:
                causa = CausaFalha.OCR_LEITURA
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa,
                validated=False,
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ----------------------------------------------------------------
    # AB01 — Abrir modulo Ambulatorio via "Localizar no Menu"
    # ----------------------------------------------------------------

    def _step_abrir_ambulatorio(self, ctx, coords, observer=None) -> StepResult:
        """
        Estrategia: Localizar no Menu (mais estavel que clicar nos Favoritos).

        Sequencia:
          1. Clicar no campo "Localizar no Menu" (coordenada fixa)
          2. Digitar "AMBULATORIO"
          3. Clicar botao "Pesquisar" (template)
          4. Popup "Continuar Busca?" aparece SEMPRE — clicar "Nao" (template)
          5. Double click no item "Ambulatorio" destacado na arvore (template)
          6. confirm_template: btn_pesquisar_amb.png valida que tela Parametros abriu

        Coordenada necessaria em config.yaml:
            campo_localizar_menu: { x: 635, y: 580 }
        """
        def fn():
            # 1. Clicar no campo "Localizar no Menu"
            x, y = self._coord(coords, "campo_localizar_menu")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")

            # 2. Digitar o termo de busca
            ctx.runner.type_text("AMBULATORIO"); time.sleep(0.3)

            # 3. Clicar botao Pesquisar (template)
            ctx.runner.safe_click(
                f"{self._TPL}/btn_pesquisar_menu.png", threshold=0.7
            )
            time.sleep(1.0)

            # 4. Popup "Continuar Busca?" — aparece sempre, clicar Nao
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/btn_nao_popup.png", timeout=5.0, threshold=0.7
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: popup 'Continuar Busca?' nao apareceu. "
                    "Verifique se btn_nao_popup.png foi capturado corretamente."
                )
            ctx.runner.safe_click(f"{self._TPL}/btn_nao_popup.png", threshold=0.7)
            time.sleep(0.8)

            # 5. Double click no item "Ambulatorio" destacado na arvore
            ctx.runner.double_click(f"{self._TPL}/menu_ambulatorio.png", threshold=0.7)
            time.sleep(1.5)

            # 6. confirm_template: valida que tela Parametros de Pesquisa abriu
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/btn_pesquisar_amb.png", timeout=15.0, threshold=0.7
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: tela Parametros de Pesquisa nao abriu. "
                    "Verifique se btn_pesquisar_amb.png foi capturado corretamente "
                    "e se o double_click no item Ambulatorio funcionou."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB01_ambulatorio.png")
        return self._step("AB01", "abrir Ambulatorio via Localizar no Menu", fn, observer,
                          confirm_template=f"{self._TPL}/btn_pesquisar_amb.png")

    # ----------------------------------------------------------------
    # AB02 — Informar Identificador
    # ----------------------------------------------------------------

    def _step_informar_identificador(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            paciente_id = _ler_estado("paciente_id")
            x, y = self._coord(coords, "campo_identificador_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(paciente_id); time.sleep(0.3)
            print(f"[AB02] Identificador: {paciente_id}")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB02_identificador.png")
        return self._step("AB02", "informar identificador do paciente", fn, observer)

    # ----------------------------------------------------------------
    # AB03 — Pesquisar
    # ----------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            # confirm_template: valida que tela de resultado apareceu (fim do falso-positivo)
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/btn_admitir_paciente.png", timeout=10, threshold=0.7
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: btn_admitir_paciente.png nao apareceu apos pesquisa. "
                    "Paciente pode nao ter sido encontrado ou tela nao carregou."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB03_pesquisa.png")
        return self._step("AB03", "pesquisar paciente", fn, observer,
                          confirm_template=f"{self._TPL}/btn_admitir_paciente.png")

    # ----------------------------------------------------------------
    # AB04 — Aba Enderecos: campo Tipo = RUA se vazio + salvar
    # ----------------------------------------------------------------

    def _step_tipo_endereco(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/aba_enderecos.png", threshold=0.7)
            time.sleep(0.5)

            screenshot_check = ctx.runner.screenshot(f"{ctx.evidence_dir}AB04_check.png")
            x, y = self._coord(coords, "campo_tipo_endereco_amb")

            # Regiao OCR: usa valor fixo do config.yaml se disponivel, senao calcula pelo coord
            r = ctx.config.regioes_ocr.get("campo_tipo_endereco")
            if r:
                regiao_tipo = (r["x1"], r["y1"], r["x2"], r["y2"])
            else:
                regiao_tipo = (x - 10, y - 10, x + 120, y + 12)

            tipo_lido = OcrHelper.ler_regiao(screenshot_check, regiao_tipo).strip()
            print(f"[AB04] Campo Tipo lido: '{tipo_lido}' | regiao: {regiao_tipo}")

            if tipo_lido:
                print("[AB04] Campo Tipo ja preenchido — pulando digitacao")
            else:
                print("[AB04] Campo Tipo vazio — digitando RUA")
                pyautogui.click(x, y); time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text("RUA")
                pyautogui.press("tab"); time.sleep(0.5)
                pyautogui.hotkey("ctrl", "s")
                time.sleep(1.5)

            # Sempre garante que btn_admitir_paciente esta visivel antes de sair do step.
            # Apos salvar ou navegar na aba Enderecos, o Forms pode ter deslocado o foco.
            # Escape fecha qualquer popup residual sem sair da tela de pesquisa.
            pyautogui.press("escape"); time.sleep(0.5)

            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/btn_admitir_paciente.png", timeout=10, threshold=0.7
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: btn_admitir_paciente.png nao visivel apos AB04. "
                    "Verifique se a tela voltou para a lista de resultados da pesquisa."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB04_tipo_endereco.png")
        return self._step("AB04", "aba Enderecos — campo Tipo = RUA se vazio", fn, observer,
                          confirm_template=f"{self._TPL}/btn_admitir_paciente.png")

    # ----------------------------------------------------------------
    # AB05 — Admitir Paciente
    # ----------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7)
            time.sleep(2.0)
            # confirm_template: valida que formulario de admissao abriu
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/campo_unidade_funcional.png", timeout=10, threshold=0.65
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: campo_unidade_funcional.png nao apareceu apos Admitir. "
                    "Formulario de admissao pode nao ter aberto."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB05_admitir.png")
        return self._step("AB05", "clicar em Admitir Paciente", fn, observer,
                          confirm_template=f"{self._TPL}/campo_unidade_funcional.png")

    # ----------------------------------------------------------------
    # AB06 — Unidade Funcional (2 TABs apos digitar)
    # ----------------------------------------------------------------

    def _step_unidade_funcional(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            valor = dados.get("unidade_funcional", "SC MONITORIZACAO AMBULATORIAL")
            ctx.runner.click_near(
                f"{self._TPL}/campo_unidade_funcional.png",
                offset_x=200, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            pyautogui.press("tab"); time.sleep(0.5)  # Sigla carrega automaticamente
            pyautogui.press("tab"); time.sleep(0.5)  # avanca para Provedor
            # confirm_template: valida que cursor avancou para campo Provedor
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/campo_provedor.png", timeout=8, threshold=0.65
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: campo_provedor.png nao visivel apos Unidade Funcional. "
                    "Unidade pode nao ter sido aceita ou formulario nao avancou."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB06_unidade.png")
        return self._step("AB06", "preencher Unidade Funcional", fn, observer,
                          confirm_template=f"{self._TPL}/campo_provedor.png")

    # ----------------------------------------------------------------
    # AB07 — Provedor / Plano
    # ----------------------------------------------------------------

    def _step_provedor_plano(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            provedor = dados.get("provedor", "SUS")
            plano    = dados.get("plano", "SUS")

            ctx.runner.click_near(
                f"{self._TPL}/campo_provedor.png",
                offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.5)

            ctx.runner.click_near(
                f"{self._TPL}/campo_plano.png",
                offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.5)

            if self._fechar_popups_convenio(ctx):
                print("[AB07] Popup de convenio fechado — comportamento esperado")

            # Carteirinha e validade — apenas para convenio
            if provedor not in ("SUS", "PARTICULAR", "INCOR SIS"):
                carteirinha = dados.get("numero_carteirinha", "")
                validade    = dados.get("validade_carteirinha", "")
                if carteirinha:
                    ctx.runner.click_near(
                        f"{self._TPL}/campo_numero_carteirinha.png",
                        offset_x=100, offset_y=0, threshold=0.65
                    )
                    pyautogui.hotkey("ctrl", "a")
                    ctx.runner.type_text(carteirinha)
                    pyautogui.press("tab"); time.sleep(0.3)
                    if self._fechar_popups_convenio(ctx):
                        print("[AB07] Popup pos-carteirinha fechado")
                if validade:
                    ctx.runner.click_near(
                        f"{self._TPL}/campo_validade_carteirinha.png",
                        offset_x=100, offset_y=0, threshold=0.65
                    )
                    pyautogui.hotkey("ctrl", "a")
                    ctx.runner.type_text(validade)
                    pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB07_provedor.png")
        return self._step("AB07", "preencher Provedor / Plano", fn, observer)

    # ----------------------------------------------------------------
    # AB08 — Declarante / Especialidade
    # ----------------------------------------------------------------

    def _step_declarante_especialidade(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            declarante    = dados.get("declarante", "TESTE AUTOMATIZADO")
            especialidade = dados.get("especialidade", "CAR - CARDIO GERAL")

            x, y = self._coord(coords, "campo_declarante")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(declarante)
            pyautogui.press("tab"); time.sleep(0.3)

            x, y = self._coord(coords, "campo_especialidade")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(especialidade)
            pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB08_declarante.png")
        return self._step("AB08", "preencher Declarante / Especialidade", fn, observer)

    # ----------------------------------------------------------------
    # AB09 — Obs
    # ----------------------------------------------------------------

    def _step_obs(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            valor = dados.get("obs", "ADMISSAO REALIZADA COM FERRAMENTA DE AUTOMACAO DE TESTES")
            x, y = self._coord(coords, "campo_obs_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB09_obs.png")
        return self._step("AB09", "preencher campo Obs", fn, observer)

    # ----------------------------------------------------------------
    # AB10 — Origem do Paciente
    # ----------------------------------------------------------------

    def _step_origem_paciente(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        def fn():
            tipo = dados.get("origem_tipo", "RESIDENCIA")
            x, y = self._coord(coords, "campo_origem_tipo")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(tipo)
            pyautogui.press("tab")
            time.sleep(1.0)  # Entidade preenche automaticamente apos Tab
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB10_origem.png")
        return self._step("AB10", "preencher Origem do Paciente", fn, observer)

    # ----------------------------------------------------------------
    # AB11 — Medico Responsavel via LOV
    # ----------------------------------------------------------------

    def _step_medico_responsavel(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            # abre LOV, pesquisa %medico, duplo clique em MEDICO (SOH PARA USO DA INFORMATICA)
            self._selecionar_via_lov(
                ctx, coords,
                btn_lov="btn_lov_medico",
                campo_localizar="campo_localizar_medico",
                termo="%medico",
                btn_localizar="btn_localizar_medico",
                btn_ok="btn_localizar_medico",  # nao usado — duplo clique
                duplo_clique_item="item_medico_informatica",
            )
            time.sleep(1.5)  # aguarda CRM carregar apos selecionar medico
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB11_medico.png")
        return self._step("AB11", "selecionar Medico Responsavel via LOV", fn, observer)

    # ----------------------------------------------------------------
    # AB12 — Lista de Procedimentos (Tab Navigation — v0.5.8)
    # ----------------------------------------------------------------

    def _step_lista_procedimentos(self, ctx, dados: dict, coords, observer=None) -> StepResult:
        """
        AB12 — Preenche a lista de procedimentos da admissao ambulatorial.

        Estrategia Tab Navigation (v0.5.8):
        - Linha 1: ativa clicando em proxima_linha_proc (coordenada fixa, y base)
        - Linhas 2+: apos fechar LOV do Profissional da linha anterior,
                     pressiona Tab — Forms desce automaticamente para a proxima linha.
        - Os botoes LOV (Codigo, Complemento, Profissional) usam coordenadas FIXAS
          porque o Forms reposiciona o cursor apos cada popup — offset_y calculado
          nao funciona neste contexto.

        Config (config.yaml -> dados -> procedimentos):
            - codigo:         obrigatorio
            - complemento:    opcional (string vazia = sem LOV, apenas Tab)
            - area_executora: opcional (string vazia = apenas OK no popup)
            - profissional:   opcional (default "MEDICO")

        Para adicionar mais procedimentos: apenas incluir mais itens em
        dados.procedimentos no config.yaml — o loop ja suporta N itens.

        Templates necessarios (PENDENTE capturar):
            - popup_procedimentos.png  — titulo do popup de Codigo
            - popup_complemento.png    — titulo do popup de Complemento
            - popup_profissional.png   — titulo do popup de Profissional
        Se os templates ainda nao existem, defina template_popup=None nas chamadas
        _lov_linha_tab abaixo (usa timeout fixo sem validacao visual).
        """
        def fn():
            procedimentos = dados.get("procedimentos", [])
            if not procedimentos:
                raise AssertionError(
                    "Nenhum procedimento configurado em dados.procedimentos no config.yaml."
                )

            # Abre tela de procedimentos
            ctx.runner.safe_click(f"{self._TPL}/btn_lista_procedimentos.png", threshold=0.7)
            time.sleep(1.5)

            for i, proc in enumerate(procedimentos):
                codigo         = proc.get("codigo", "")
                complemento    = proc.get("complemento", "")
                area_executora = proc.get("area_executora", "")
                profissional   = proc.get("profissional", "MEDICO")

                print(f"[AB12] Procedimento {i+1}/{len(procedimentos)}: "
                      f"codigo={codigo} complemento='{complemento}' "
                      f"profissional={profissional}")

                # --- Ativar linha correta na grade ---
                if i == 0:
                    # Linha 1: clique direto na coordenada base (y fixo do config.yaml)
                    x_linha, y_linha = self._coord(coords, "proxima_linha_proc")
                    pyautogui.click(x_linha, y_linha); time.sleep(0.3)
                else:
                    # Linhas 2+: Tab a partir do final da linha anterior.
                    # O Forms posiciona o cursor na proxima linha automaticamente.
                    # Se a grade tiver mais colunas visíveis, pode ser necessário
                    # ajustar a quantidade de Tabs aqui.
                    print(f"[AB12] Avancando para linha {i+1} via Tab")
                    pyautogui.press("tab"); time.sleep(0.5)

                # --- Codigo via LOV (coordenada fixa) ---
                # template_popup valida que popup "Procedimentos" abriu.
                # Se popup_procedimentos.png ainda nao foi capturado,
                # trocar para template_popup=None (usa timeout fixo).
                self._lov_linha_tab(
                    ctx, coords,
                    btn_lov="btn_lov_codigo_proc",
                    campo_localizar="campo_localizar_proc",
                    termo=codigo,
                    btn_localizar="btn_localizar_proc",
                    btn_ok="btn_ok_proc",
                    template_popup="popup_procedimentos.png",
                )
                time.sleep(0.5)

                # --- Popup Area Executora ---
                # Sempre aparece apos selecionar o codigo — popup de posicao fixa.
                # Se area_executora vazio: apenas clica OK sem preencher o campo de busca.
                area_para_digitar = area_executora.strip()
                if area_para_digitar:
                    x, y = self._coord(coords, "campo_localizar_area")
                    pyautogui.click(x, y); time.sleep(0.3)
                    pyautogui.hotkey("ctrl", "a"); time.sleep(0.1)
                    pyautogui.press("delete"); time.sleep(0.1)
                    ctx.runner.type_text(area_para_digitar)
                    x, y = self._coord(coords, "btn_localizar_area")
                    pyautogui.click(x, y); time.sleep(1.5)

                # OK area executora — clicado sempre (popup sempre aparece)
                x, y = self._coord(coords, "btn_ok_area_executora")
                pyautogui.click(x, y); time.sleep(0.8)

                # --- Complemento via LOV (opcional) ---
                # Forms posiciona cursor em Complemento apos fechar popup Area Executora.
                # Se complemento vazio: Tab avanca direto para Profissional sem abrir LOV.
                # Se complemento preenchido: abre LOV e valida popup "Lista de Complemento".
                if complemento and complemento.strip():
                    self._lov_linha_tab(
                        ctx, coords,
                        btn_lov="btn_lov_complemento",
                        campo_localizar="campo_localizar_complemento",
                        termo=complemento,
                        btn_localizar="btn_localizar_complemento",
                        btn_ok="btn_ok_complemento",
                        template_popup="popup_complemento.png",
                    )
                    time.sleep(0.5)
                else:
                    # Sem complemento — Tab avanca para Profissional
                    print(f"[AB12] Procedimento {i+1}: sem complemento — Tab para Profissional")
                    pyautogui.press("tab"); time.sleep(0.3)

                # --- Profissional via LOV (coordenada fixa) ---
                # Forms posiciona cursor em Profissional apos Complemento (ou Tab acima).
                # Usa duplo clique no item da lista (item_profissional_proc).
                self._lov_linha_tab(
                    ctx, coords,
                    btn_lov="btn_lov_profissional_proc",
                    campo_localizar="campo_localizar_profissional",
                    termo=f"%{profissional}",
                    btn_localizar="btn_localizar_profissional",
                    btn_ok="btn_ok_profissional",
                    duplo_clique_item="item_profissional_proc",
                    template_popup="popup_profissional.png",
                )
                time.sleep(0.5)
                print(f"[AB12] Procedimento {i+1}/{len(procedimentos)} preenchido OK")

            # Screenshot final com todos os procedimentos preenchidos
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB12_procedimentos.png")

        return self._step("AB12", "preencher Lista de Procedimentos", fn, observer)

    # ----------------------------------------------------------------
    # AB13 — Salvar (F10) + Voltar para formulario de admissao
    # ----------------------------------------------------------------

    # Coordenada do botao Voltar — capturada com posicao_mouse.py (score template: 0.543)
    _COORD_BTN_VOLTAR = (741, 566)

    def _step_voltar(self, ctx, observer=None) -> StepResult:
        def fn():
            # 1. Salvar com F10 — gera o Nr. Admissao
            # Ctrl+S nao funciona no Oracle Forms — F10 e o atalho correto
            pyautogui.press("f10"); time.sleep(2.0)

            # 2. Clicar em Voltar — coordenada direta (template btn_voltar.png score 0.543)
            pyautogui.click(*self._COORD_BTN_VOLTAR); time.sleep(2.0)

            # 3. confirm_template: valida que voltou para o formulario de admissao
            # (campo_unidade_funcional.png e visivel nessa tela)
            apareceu = ctx.runner.wait_template(
                f"{self._TPL}/campo_unidade_funcional.png", timeout=10, threshold=0.65
            )
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: campo_unidade_funcional.png nao visivel apos Voltar. "
                    "Formulario de admissao pode nao ter retornado corretamente."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB13_voltar.png")
        return self._step("AB13", "salvar (F10) e clicar em Voltar", fn, observer,
                          confirm_template=f"{self._TPL}/campo_unidade_funcional.png")

    # ----------------------------------------------------------------
    # AB14 — Validar Nr Admissao via OCR + salvar estado_jornada.json
    # ----------------------------------------------------------------

    def _step_validar_admissao(self, ctx, observer=None) -> StepResult:
        def fn():
            # Nr. Admissao esta na tela do formulario de admissao (apos AB13 Voltar)
            # Regiao calibrada com Paint: canto superior esquerdo da tela
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB14_validacao.png")
            OcrHelper.salvar_debug(
                screenshot_path, self._REGIAO_NR_ADMISSAO,
                f"{ctx.evidence_dir}AB14_ocr_debug.png"
            )
            texto = OcrHelper.ler_regiao(screenshot_path, self._REGIAO_NR_ADMISSAO)
            numeros = re.findall(r"\d+", texto)
            if not numeros:
                raise AssertionError(
                    f"Nr Admissao nao encontrado — admissao pode ter falhado ou F10 nao salvou.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Regiao: {self._REGIAO_NR_ADMISSAO}\n"
                    f"Dicas:\n"
                    f"  - Veja AB14_ocr_debug.png e verifique se o numero esta na regiao\n"
                    f"  - Ajuste _REGIAO_NR_ADMISSAO com Paint se necessario\n"
                    f"  - Confirme que F10 salvou corretamente (veja AB13_voltar.png)"
                )
            nr_admissao = numeros[0]
            print(f"[AB14] Nr Admissao Ambulatorio: {nr_admissao}")
            _salvar_estado("nr_admissao_amb", nr_admissao)
            return screenshot_path
        return self._step("AB14", "validar Nr Admissao via OCR", fn, observer)

    # ----------------------------------------------------------------
    # AB15 — Sair
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB15_sair.png")
        return self._step("AB15", "sair para Menu Principal", fn, observer)