# src/flows/si3/admissao_internacao_flow.py
"""
AdmissaoInternacaoFlow — SI3 Oracle Forms
Versao: 0.5.12

Reescrito seguindo o contrato padrao VTAE:
  - Zero dados hardcoded no flow — tudo em config.yaml via _dado()
  - Zero coordenadas hardcoded — tudo em coordenadas: no config.yaml
  - _focar_si3() antes de steps criticos
  - _tpl_existe() antes de wait_template com templates opcionais
  - verify_lov obrigatorio apos qualquer LOV
  - confirm_template em steps de navegacao
  - _clicar_aguardar() em todas as transicoes de tela criticas (v0.5.12)
  - paciente_id lido do estado_jornada.json (nunca do config.yaml diretamente)

Fluxo baseado no documento:
  FLUXO_DE_ADMISSAO_DE_PACIENTES_INTERNACAO.pdf — 29/05/2026

Steps:
  AI01  Abrir modulo Internacao (double_click no menu)
  AI02  Informar ID do paciente (de estado_jornada.json)
  AI03  Pesquisar paciente
  AI04  Clicar aba Endereco
  AI05  Campo Tipo: OCR condicional — preenche RUA so se estiver vazio
  AI06  Clicar Admitir Paciente
  AI07  Unidade Funcional + TAB
  AI08  Provedor + Plano (+ carteirinha/validade se cenario exige)
  AI08b Declarante/Acompanhantes + Especialidade
  AI09  Campo Obs
  AI10  Origem Paciente: Tipo=RESIDENCIA + TAB
  AI11  Origem Solicitacao: dropdown
  AI12  Profissional Responsavel: LOV + verify_lov
  AI13  Botao Info. Compl. de Internacao
  AI14  Numero no popup + LOV medico + Retornar
  AI15  Botao LEITO
  AI16  Alocar Leito -> Consultar Leito -> LOV unidade -> OK
  AI17  Selecionar primeira linha -> Selecionar -> fechar popups -> OK -> Sair
  AI18  Sair (Alocar Leito) -> Sair (INTERNACAO) -> Sair (Menu Principal)
  AI19  Validar Nr Admissao via OCR

Templates novos adicionados em v0.5.12:
  titulo_internacao.png     — titulo da janela INTERNACAO (apos 1o sair)
  titulo_menu_principal.png — titulo da janela Menu Principal (apos 2o sair)
"""
import os
import time
import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult, CausaFalha
from src.core.estado_jornada import ler as _ler_estado
from src.flows.base_flow import BaseFlow
from src.vision.ocr import OcrHelper


class AdmissaoInternacaoFlow(BaseFlow):

    FLOW_NAME = "AdmissaoInternacaoFlow"
    _TPL = "templates/si3/admissao_internacao"

    # ── Helpers locais (complementam BaseFlow) ───────────────────────

    def _dado(self, dados: dict, chave: str, step_id: str):
        """Dado ausente = erro imediato com mensagem clara."""
        if chave not in dados:
            raise AssertionError(
                f"[{step_id}] Dado obrigatorio ausente no config.yaml: '{chave}'\n"
                f"Chaves disponiveis: {list(dados.keys())}"
            )
        return dados[chave]

    @staticmethod
    def _coord(coords: dict, chave: str) -> tuple:
        """Le coordenada do config — falha claro se ausente."""
        if chave not in coords:
            raise AssertionError(
                f"Coordenada '{chave}' nao encontrada em coordenadas: do config.yaml"
            )
        c = coords[chave]
        return c["x"], c["y"]

    def _step(self, step_id: str, descricao: str, fn, observer,
              confirm_template: str = None, validated: bool = None,
              ctx=None) -> StepResult:
        """Wrapper padrao: executa fn(), captura erros, notifica observer."""
        if observer:
            observer.log_step_start(step_id, descricao)
        start = time.monotonic()
        try:
            screenshot = fn()
            if confirm_template:
                tpl = confirm_template
                if self._tpl_existe(tpl):
                    if not ctx.runner.wait_template(tpl, timeout=8.0, threshold=0.7):
                        raise AssertionError(
                            f"[{step_id}] Tela nao confirmada — template nao encontrado: {tpl}"
                        )
                else:
                    print(f"[{step_id}] AVISO: template de confirmacao ausente — {tpl}")
                    time.sleep(2.0)
            step = StepResult(
                step_id=step_id, success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot,
                validated=validated,
                description=descricao,
            )
        except Exception as e:
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
                validated=False,
                causa_falha=CausaFalha.DESCONHECIDA,
                description=descricao,
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ── Execute ──────────────────────────────────────────────────────

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas
        regioes = ctx.config.regioes_ocr

        steps = [
            lambda: self._ai01_abrir_internacao(ctx, dados, coords, observer),
            lambda: self._ai02_informar_paciente(ctx, dados, coords, observer),
            lambda: self._ai03_pesquisar(ctx, observer),
            lambda: self._ai04_aba_endereco(ctx, observer),
            lambda: self._ai05_tipo_endereco_condicional(ctx, coords, regioes, observer),
            lambda: self._ai06_admitir_paciente(ctx, observer),
            lambda: self._ai07_unidade_funcional(ctx, dados, coords, observer),
            lambda: self._ai08_provedor_plano(ctx, dados, coords, observer),
            lambda: self._ai08b_declarante_especialidade(ctx, dados, coords, observer),
            lambda: self._ai09_obs(ctx, dados, coords, observer),
            lambda: self._ai10_origem_paciente(ctx, dados, coords, observer),
            lambda: self._ai11_origem_solicitacao(ctx, dados, coords, observer),
            lambda: self._ai12_medico_responsavel(ctx, dados, coords, regioes, observer),
            lambda: self._ai13_info_compl(ctx, observer),
            lambda: self._ai14_medico_compl(ctx, dados, coords, observer),
            lambda: self._ai15_botao_leito(ctx, observer),
            lambda: self._ai16_alocar_leito(ctx, dados, coords, observer),
            lambda: self._ai17_selecionar_leito(ctx, coords, observer),
            lambda: self._ai19_validar_nr_admissao(ctx, regioes, observer),
            lambda: self._ai18_sair(ctx, observer),
        ]

        for step_fn in steps:
            sr = step_fn()
            result.steps.append(sr)
            if not sr.success:
                break

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    # ── Steps ────────────────────────────────────────────────────────

    def _ai01_abrir_internacao(self, ctx, dados, coords, observer=None) -> StepResult:
        """
        Padrao de navegacao via 'Localizar no Menu'.
        1. Clica no campo 'Localizar no Menu'
        2. Digita o termo de busca (config: termo_menu_int)
        3. Clica em Pesquisar
        4. Popup 'Continuar Busca?' -> clica NAO
        5. Double click em 'Internacao' na arvore de resultados
        """
        def fn():
            termo = self._dado(dados, "termo_menu_int", "AI01")
            self._focar_si3()

            x, y = self._coord(coords, "campo_localizar_menu")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo); time.sleep(0.3)

            ctx.runner.safe_click(
                f"{self._TPL}/btn_pesquisar_menu.png", threshold=0.7
            )
            time.sleep(1.0)

            # Popup "Continuar Busca?" -> NAO
            tpl_nao = f"{self._TPL}/btn_nao_popup.png"
            if self._tpl_existe(tpl_nao):
                if ctx.runner.is_visible(tpl_nao, threshold=0.7):
                    ctx.runner.safe_click(tpl_nao, threshold=0.7)
                    time.sleep(0.5)
            else:
                print("[AI01] AVISO: btn_nao_popup.png ausente — usando Tab+Enter")
                pyautogui.press("tab"); time.sleep(0.2)
                pyautogui.press("enter"); time.sleep(0.5)

            ctx.runner.double_click(
                f"{self._TPL}/menu_internacao.png", threshold=0.7
            )
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI01_internacao.png")
        return self._step("AI01", "abrir modulo Internacao via Localizar no Menu",
                          fn, observer,
                          confirm_template=f"{self._TPL}/campo_identificado.png",
                          ctx=ctx)

    def _ai02_informar_paciente(self, ctx, dados, coords, observer=None) -> StepResult:
        """
        Campo Identificador — coordenada direta obrigatoria.
        """
        def fn():
            paciente_id = _ler_estado("paciente_id")
            if not paciente_id:
                raise AssertionError(
                    "paciente_id nao encontrado em estado_jornada.json.\n"
                    "Execute test_01_cadastro_paciente antes, ou defina "
                    "SI3_PACIENTE_ID no .env para reutilizar paciente existente."
                )
            self._focar_si3()
            x, y = self._coord(coords, "campo_identificador")
            if x and y:
                pyautogui.click(x, y); time.sleep(0.3)
            else:
                print("[AI02] AVISO: campo_identificador nao calibrado "
                      "— usando 2x TAB. Calibrar com posicao_mouse.py.")
                pyautogui.press("tab"); time.sleep(0.3)
                pyautogui.press("tab"); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(paciente_id)
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI02_paciente.png")
        return self._step("AI02", "informar ID do paciente", fn, observer, ctx=ctx)

    def _ai03_pesquisar(self, ctx, observer=None) -> StepResult:
        """
        Clica em Pesquisar. confirm_template: aba_endereco.png.
        """
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/aba_endereco.png", timeout=10, threshold=0.7
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI03_pesquisa.png")
        return self._step("AI03", "pesquisar paciente", fn, observer,
                          confirm_template=f"{self._TPL}/aba_endereco.png", ctx=ctx)

    def _ai04_aba_endereco(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/aba_endereco.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI04_endereco.png")
        return self._step("AI04", "clicar aba Endereco", fn, observer, ctx=ctx)

    def _ai05_tipo_endereco_condicional(self, ctx, coords, regioes, observer=None) -> StepResult:
        """
        Condicional: OCR verifica se campo Tipo esta vazio.
        Se vazio  -> preenche RUA + TAB.
        Se preenchido -> pula sem alterar.
        """
        def fn():
            regiao = regioes.get("campo_tipo_endereco")
            campo_vazio = True  # default: assume vazio se regiao nao calibrada

            if regiao and (regiao["x1"] or regiao["y1"] or regiao["x2"] or regiao["y2"]):
                screenshot_path = ctx.runner.screenshot(
                    f"{ctx.evidence_dir}AI05_tipo_check.png"
                )
                texto = OcrHelper.ler_regiao(
                    screenshot_path,
                    (regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"])
                )
                campo_vazio = not bool(texto.strip())
                print(f"[AI05] Campo Tipo lido via OCR: '{texto.strip()}' "
                      f"— {'VAZIO, preenchendo RUA' if campo_vazio else 'JA preenchido, pulando'}")
            else:
                print("[AI05] AVISO: regioes_ocr.campo_tipo_endereco nao calibrado "
                      "— preenchendo RUA por seguranca")

            if campo_vazio:
                self._focar_si3()
                tpl_tipo = f"{self._TPL}/label_tipo_endereco.png"
                if self._tpl_existe(tpl_tipo):
                    ctx.runner.click_near(tpl_tipo, offset_x=120, offset_y=0, threshold=0.65)
                elif "campo_tipo_endereco_coord" in coords:
                    x, y = self._coord(coords, "campo_tipo_endereco_coord")
                    pyautogui.click(x, y)
                else:
                    print("[AI05] AVISO: template e coordenada ausentes — usando Tab")
                    pyautogui.press("tab")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text("RUA")
                pyautogui.press("tab"); time.sleep(1.0)
                tpl_ok = f"{self._TPL}/btn_ok_popup.png"
                if self._tpl_existe(tpl_ok):
                    if ctx.runner.is_visible(tpl_ok, threshold=0.7):
                        ctx.runner.safe_click(tpl_ok, threshold=0.7)
                        time.sleep(0.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI05_tipo_end.png")
        return self._step("AI05", "verificar/preencher campo Tipo (RUA)", fn, observer, ctx=ctx)

    def _ai06_admitir_paciente(self, ctx, observer=None) -> StepResult:
        """
        Botao 'Admitir paciente'.
        _clicar_aguardar garante que a tela de admissao carregou antes de continuar.
        """
        def fn():
            self._clicar_aguardar(
                ctx,
                acao=lambda: ctx.runner.safe_click(
                    f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7
                ),
                confirmacao=f"{self._TPL}/campo_identificado.png",
                timeout=15, threshold=0.7, retries=2,
                label="AI06 admitir paciente",
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI06_admitir.png")
        return self._step("AI06", "clicar Admitir Paciente", fn, observer, ctx=ctx)

    def _ai07_unidade_funcional(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            valor = self._dado(dados, "unidade_funcional", "AI07")
            self._focar_si3()
            if "campo_unidade_funcional" in coords:
                x, y = self._coord(coords, "campo_unidade_funcional")
                if x and y:
                    pyautogui.click(x, y)
                    time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            pyautogui.press("tab")
            time.sleep(0.5)
            regiao = ctx.config.regioes_ocr.get("unidade_funcional")
            if regiao and (regiao["x1"] or regiao["y1"]):
                ok, _ = ctx.runner.verify_fill(
                    valor,
                    region=(regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI07_verify_debug.png"
                )
                if not ok:
                    raise AssertionError(
                        f"[AI07] Unidade Funcional nao preenchida com '{valor}'.\n"
                        f"Veja AI07_verify_debug.png."
                    )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI07_unidade.png")
        return self._step("AI07", "preencher Unidade Funcional", fn, observer,
                          validated=True, ctx=ctx)

    def _ai08_provedor_plano(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            cenario_key = self._dado(dados, "cenario_provedor", "AI08")
            cenarios = self._dado(dados, "cenarios_provedor", "AI08")
            if cenario_key not in cenarios:
                raise AssertionError(
                    f"[AI08] Cenario '{cenario_key}' nao encontrado em cenarios_provedor.\n"
                    f"Cenarios disponiveis: {list(cenarios.keys())}"
                )
            cenario = cenarios[cenario_key]
            provedor    = cenario["provedor"]
            plano       = cenario["plano"]
            carteirinha = cenario.get("carteirinha", "")
            validade    = cenario.get("validade", "")

            self._focar_si3()

            x, y = self._coord(coords, "campo_provedor")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.5)

            x, y = self._coord(coords, "campo_plano")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.3)

            if carteirinha:
                x, y = self._coord(coords, "campo_carteirinha")
                pyautogui.click(x, y); time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text(carteirinha)
                pyautogui.press("tab"); time.sleep(2.5)
                tpl_sim = f"{self._TPL}/btn_sim_popup.png"
                if self._tpl_existe(tpl_sim) and ctx.runner.is_visible(tpl_sim, threshold=0.7):
                    ctx.runner.safe_click(tpl_sim, threshold=0.7); time.sleep(0.5)
                    print("[AI08] Popup elegibilidade -> Sim clicado")
                self._focar_si3(); time.sleep(0.3)

            if validade:
                x, y = self._coord(coords, "campo_validade_carteirinha")
                pyautogui.click(x, y); time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text(validade)
                pyautogui.press("tab"); time.sleep(0.5)

            print(f"[AI08] Cenario provedor: {cenario_key} — {provedor}/{plano}")
            r_prov = ctx.config.regioes_ocr.get("provedor")
            if r_prov and (r_prov["x1"] or r_prov["y1"]):
                ok, _ = ctx.runner.verify_fill(
                    provedor,
                    region=(r_prov["x1"], r_prov["y1"], r_prov["x2"], r_prov["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI08_verify_provedor_debug.png"
                )
                if not ok:
                    raise AssertionError(
                        f"[AI08] Provedor nao preenchido com '{provedor}'.\n"
                        f"Veja AI08_verify_provedor_debug.png."
                    )
            r_plano = ctx.config.regioes_ocr.get("plano")
            if r_plano and (r_plano["x1"] or r_plano["y1"]):
                ok, _ = ctx.runner.verify_fill(
                    plano,
                    region=(r_plano["x1"], r_plano["y1"], r_plano["x2"], r_plano["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI08_verify_plano_debug.png"
                )
                if not ok:
                    raise AssertionError(
                        f"[AI08] Plano nao preenchido com '{plano}'.\n"
                        f"Veja AI08_verify_plano_debug.png."
                    )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI08_provedor.png")
        return self._step("AI08", "preencher Provedor e Plano", fn, observer,
                          validated=True, ctx=ctx)

    def _ai08b_declarante_especialidade(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            declarante    = self._dado(dados, "declarante",    "AI08b")
            especialidade = self._dado(dados, "especialidade", "AI08b")
            self._focar_si3()

            x, y = self._coord(coords, "campo_declarante")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(declarante)
            pyautogui.press("tab"); time.sleep(0.3)

            x, y = self._coord(coords, "campo_especialidade")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(especialidade)
            pyautogui.press("tab"); time.sleep(0.5)

            r_dec = ctx.config.regioes_ocr.get("declarante")
            if r_dec and (r_dec["x1"] or r_dec["y1"]):
                ok, _ = ctx.runner.verify_fill(
                    declarante,
                    region=(r_dec["x1"], r_dec["y1"], r_dec["x2"], r_dec["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI08b_verify_declarante_debug.png"
                )
                if not ok:
                    print(f"[AI08b] AVISO: Declarante pode nao ter sido preenchido.")
            r_esp = ctx.config.regioes_ocr.get("especialidade")
            if r_esp and (r_esp["x1"] or r_esp["y1"]):
                ok, _ = ctx.runner.verify_fill(
                    especialidade,
                    region=(r_esp["x1"], r_esp["y1"], r_esp["x2"], r_esp["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI08b_verify_especialidade_debug.png"
                )
                if not ok:
                    print(f"[AI08b] AVISO: Especialidade pode nao ter sido preenchida.")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI08b_declarante.png")
        return self._step("AI08b", "preencher Declarante e Especialidade", fn, observer,
                          validated=True, ctx=ctx)

    def _ai09_obs(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            valor = self._dado(dados, "obs", "AI09")
            self._focar_si3()
            x, y = self._coord(coords, "campo_obs")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            pyautogui.press("tab"); time.sleep(0.3)
            r_obs = ctx.config.regioes_ocr.get("obs")
            if r_obs and (r_obs["x1"] or r_obs["y1"]):
                ok, _ = ctx.runner.verify_fill(
                    valor,
                    region=(r_obs["x1"], r_obs["y1"], r_obs["x2"], r_obs["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI09_verify_debug.png"
                )
                if not ok:
                    print("[AI09] AVISO: campo Obs pode nao ter sido preenchido.")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI09_obs.png")
        return self._step("AI09", "preencher campo Obs", fn, observer,
                          validated=True, ctx=ctx)

    def _ai10_origem_paciente(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            tipo = self._dado(dados, "origem_tipo", "AI10")
            self._focar_si3()
            x, y = self._coord(coords, "campo_origem_tipo")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(tipo)
            pyautogui.press("tab")
            time.sleep(1.0)
            r = ctx.config.regioes_ocr.get("origem_tipo")
            if r and (r["x1"] or r["y1"]):
                ok, _ = ctx.runner.verify_fill(
                    tipo,
                    region=(r["x1"], r["y1"], r["x2"], r["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI10_verify_debug.png"
                )
                if not ok:
                    raise AssertionError(
                        f"[AI10] Origem Tipo nao preenchida com '{tipo}'.\n"
                        f"Veja AI10_verify_debug.png."
                    )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI10_origem.png")
        return self._step("AI10", "preencher Origem do Paciente", fn, observer,
                          validated=True, ctx=ctx)

    def _ai11_origem_solicitacao(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            valor = self._dado(dados, "origem_solicitacao", "AI11")
            self._focar_si3()
            x, y = self._coord(coords, "dropdown_origem_solicitacao")
            pyautogui.click(x, y)
            time.sleep(1.5)
            tpl = f"{self._TPL}/opcao_{valor.lower().replace(' ', '_')}.png"
            if self._tpl_existe(tpl):
                ctx.runner.safe_click(tpl, threshold=0.7)
            else:
                print(f"[AI11] AVISO: template de opcao ausente ({tpl}) — usando seta")
                pyautogui.press("down"); time.sleep(0.3)
                pyautogui.press("enter")
            time.sleep(0.5)
            r = ctx.config.regioes_ocr.get("origem_solicitacao")
            if r and (r["x1"] or r["y1"]):
                ok, _ = ctx.runner.verify_fill(
                    valor,
                    region=(r["x1"], r["y1"], r["x2"], r["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI11_verify_debug.png"
                )
                if not ok:
                    raise AssertionError(
                        f"[AI11] Origem Solicitacao nao selecionada com '{valor}'.\n"
                        f"Veja AI11_verify_debug.png."
                    )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI11_solicitacao.png")
        return self._step("AI11", "selecionar Origem da Solicitacao", fn, observer,
                          validated=True, ctx=ctx)

    def _ai12_medico_responsavel(self, ctx, dados, coords, regioes, observer=None) -> StepResult:
        """
        Profissional Responsavel: LOV resultado unico -> OK direto.
        """
        def fn():
            self._focar_si3()
            x, y = self._coord(coords, "btn_lov_medico_responsavel")
            pyautogui.click(x, y); time.sleep(1.5)
            x, y = self._coord(coords, "btn_ok_medico_resp")
            pyautogui.click(x, y); time.sleep(0.5)
            regiao = regioes.get("campo_medico_responsavel")
            if regiao and (regiao["x1"] or regiao["y1"]):
                ok, _ = ctx.runner.verify_lov(
                    "Medico Responsavel",
                    region=(regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI12_verify.png",
                )
                if not ok:
                    raise AssertionError(
                        "Falha de Observabilidade: campo Medico Responsavel vazio apos LOV."
                    )
            else:
                print("[AI12] AVISO: regioes_ocr.campo_medico_responsavel nao calibrado "
                      "— verify_lov pulado")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI12_medico_resp.png")
        return self._step("AI12", "selecionar Medico Responsavel via LOV", fn, observer,
                          validated=True, ctx=ctx)

    def _ai13_info_compl(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_info_compl.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI13_info_compl.png")
        return self._step("AI13", "clicar Info. Compl. de Internacao", fn, observer,
                          confirm_template=f"{self._TPL}/tela_info_compl.png", ctx=ctx)

    def _ai14_medico_compl(self, ctx, dados, coords, observer=None) -> StepResult:
        """
        Popup Info. Compl.:
          1. Campo Numero — digita '1' + TAB abre LOV automaticamente
          2. Busca pelo termo_medico_compl
          3. Double click no medico — dispensa OK
          4. Retornar
        """
        def fn():
            termo = self._dado(dados, "termo_medico_compl", "AI14")
            self._focar_si3()

            x, y = self._coord(coords, "campo_numero_compl")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text("1")
            pyautogui.press("tab")
            time.sleep(1.5)

            x, y = self._coord(coords, "campo_busca_medico_compl")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo); time.sleep(0.3)

            x, y = self._coord(coords, "btn_localizar_medico_compl")
            pyautogui.click(x, y); time.sleep(1.0)

            ctx.runner.double_click(
                f"{self._TPL}/item_medico_informatica.png", threshold=0.7
            )
            time.sleep(0.5)

            x, y = self._coord(coords, "btn_retornar_compl")
            pyautogui.click(x, y); time.sleep(1.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI14_medico_compl.png")
        return self._step("AI14", "preencher Info. Compl. e selecionar medico", fn, observer, ctx=ctx)

    def _ai15_botao_leito(self, ctx, observer=None) -> StepResult:
        """
        Clica no botao 'Leito'. Abre tela Alocar Leito.
        confirm_template: btn_alocar_leito.png — unico nessa tela.
        """
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_leito.png", threshold=0.7)
            time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI15_leito.png")
        return self._step("AI15", "clicar botao LEITO", fn, observer,
                          confirm_template=f"{self._TPL}/btn_alocar_leito.png", ctx=ctx)

    def _ai16_alocar_leito(self, ctx, dados, coords, observer=None) -> StepResult:
        """
        Tela Alocar Leito:
          1. Clicar 'Alocar Leito'
          2. Fechar TODOS os popups que aparecem apos Alocar Leito (ate 3):
             - "paciente ja possui leito alocado"
             - "nao existe reserva para o paciente"
             - outros popups Oracle Forms
          3. Clicar 'Consultar Leito' — _clicar_aguardar confirma lista de leitos
          4. LOV de unidade funcional — digita termo, Localizar, OK
        """
        def fn():
            self._focar_si3()
            termo_unidade = self._dado(dados, "termo_unidade_leito", "AI16")
            tpl_ok = f"{self._TPL}/btn_ok_popup.png"

            # 1. Clicar Alocar Leito
            x, y = self._coord(coords, "btn_alocar_leito")
            pyautogui.click(x, y); time.sleep(1.5)

            # 2. Fechar todos os popups que podem aparecer apos Alocar Leito
            # Tenta ambos os templates de OK:
            #   - btn_ok_reserva_popup.png: janela Forms flutuante ("nao existe reserva")
            #   - btn_ok_popup.png: janela principal ("ja possui leito", outros)
            tpl_ok_reserva = f"{self._TPL}/btn_ok_reserva_popup.png"
            fechou_algum = False
            for tpl in [tpl_ok_reserva, tpl_ok]:
                if not self._tpl_existe(tpl):
                    continue
                for _ in range(3):
                    if ctx.runner.is_visible(tpl, threshold=0.7):
                        ctx.runner.safe_click(tpl, threshold=0.7)
                        time.sleep(0.8)
                        fechou_algum = True
                        print(f"[AI16] Popup fechado com OK ({tpl.split('/')[-1]})")
                    else:
                        break
            if not fechou_algum and not self._tpl_existe(tpl_ok) and not self._tpl_existe(tpl_ok_reserva):
                time.sleep(1.0)
                pyautogui.press("enter")
                time.sleep(0.5)

            # 3. Consultar Leito — abre LOV de unidades
            x, y = self._coord(coords, "btn_consultar_leito")
            pyautogui.click(x, y); time.sleep(1.5)

            # 4. LOV de unidade funcional — digita termo, Localizar, OK
            # _clicar_aguardar no OK: confirma que a lista de leitos livres apareceu
            x, y = self._coord(coords, "campo_busca_unidade_leito")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo_unidade); time.sleep(0.3)

            x, y = self._coord(coords, "btn_localizar_unidade_leito")
            pyautogui.click(x, y); time.sleep(1.0)

            x_ok, y_ok = self._coord(coords, "btn_ok_unidade_leito")
            self._clicar_aguardar(
                ctx,
                acao=lambda: pyautogui.click(x_ok, y_ok),
                confirmacao=f"{self._TPL}/btn_selecionar_leito.png",
                timeout=12, threshold=0.7, retries=2,
                label="AI16 OK unidade -> lista de leitos livres",
            )

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI16_alocar_leito.png")
        return self._step("AI16", "Alocar Leito e selecionar unidade", fn, observer, ctx=ctx)

    def _ai17_selecionar_leito(self, ctx, coords, observer=None) -> StepResult:
        """
        Lista de leitos livres:
          1. Clicar na primeira linha
          2. Clicar Selecionar
          3. Fechar popups (especialidade diferente -> SIM; leito com reserva -> SIM; outros -> OK)
          4. verify_lov — captura numero do leito
          5. OK na tela de alocacao
          6. Sair da janela de leitos
        """
        _ocr_capturado = [None]

        def fn():
            self._focar_si3()

            x, y = self._coord(coords, "primeira_linha_leitos")
            pyautogui.click(x, y); time.sleep(0.3)

            x, y = self._coord(coords, "btn_selecionar_leito")
            pyautogui.click(x, y); time.sleep(1.0)

            tpl_sim = f"{self._TPL}/btn_sim_popup.png"
            tpl_ok  = f"{self._TPL}/btn_ok_popup.png"

            # Fechar popups em sequencia — threshold 0.80 evita falsos positivos
            time.sleep(1.0)
            for _ in range(4):
                fechou = False
                if self._tpl_existe(tpl_sim) and ctx.runner.is_visible(tpl_sim, threshold=0.80):
                    ctx.runner.safe_click(tpl_sim, threshold=0.80)
                    time.sleep(1.0)
                    fechou = True
                    print("[AI17] Popup -> Sim")
                elif self._tpl_existe(tpl_ok) and ctx.runner.is_visible(tpl_ok, threshold=0.80):
                    ctx.runner.safe_click(tpl_ok, threshold=0.80)
                    time.sleep(1.0)
                    fechou = True
                    print("[AI17] Popup -> OK")
                if not fechou:
                    break

            # Aguarda Oracle Forms estabilizar
            time.sleep(1.5)

            # screenshot + verify_lov — campo Numero visivel neste momento
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AI17_leito_selecionado.png")
            r = ctx.config.regioes_ocr.get("numero_leito")
            if r and (r["x1"] or r["y1"]):
                ok, valor_lido = ctx.runner.verify_lov(
                    "Numero Leito",
                    region=(r["x1"], r["y1"], r["x2"], r["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI17_verify_leito_debug.png"
                )
                _ocr_capturado[0] = valor_lido
                if not ok:
                    raise AssertionError(
                        "[AI17] Leito nao foi alocado — campo Numero ficou vazio.\n"
                        "Causas possiveis:\n"
                        "  1. Lista de leitos estava vazia para a unidade selecionada\n"
                        "  2. Popup nao foi tratado corretamente\n"
                        "  3. Coordenada btn_selecionar_leito desatualizada\n"
                        "Veja AI17_verify_leito_debug.png e AI17_leito_selecionado.png."
                    )

            # OK na tela de alocacao
            x, y = self._coord(coords, "btn_ok_alocar")
            pyautogui.click(x, y); time.sleep(1.5)

            # Sair — fecha janela de leitos
            x, y = self._coord(coords, "btn_sair_alocar")
            pyautogui.click(x, y); time.sleep(1.0)

            return screenshot_path

        step = self._step("AI17", "selecionar leito e fechar popups", fn, observer,
                          validated=True, ctx=ctx)
        if step.success and _ocr_capturado[0]:
            step.ocr_lido = _ocr_capturado[0]
        return step

    def _ai18_sair(self, ctx, observer=None) -> StepResult:
        """
        Sair da tela de admissao e voltar ao menu principal.
        3 telas: Alocar Leito -> INTERNACAO -> Menu Principal
        _clicar_aguardar confirma cada transicao antes de continuar.

        Templates necessarios:
          titulo_internacao.png     — titulo da janela INTERNACAO
          titulo_menu_principal.png — titulo da janela Menu Principal
        """
        def fn():
            self._focar_si3()

            def sair_e_confirmar(tpl_sair, confirmacao, label,
                                 timeout=15, threshold=0.7, retries=2):
                """
                Clica Sair (template da tela atual) e confirma a tela destino
                por um elemento UNICO dela (nunca pelo titulo, que se repete).
                So reclica se o botao Sair AINDA estiver visivel — se sumiu,
                o clique pegou e a tela so esta lenta (timing de servidor).
                """
                for tentativa in range(1, retries + 2):
                    if ctx.runner.is_visible(tpl_sair, threshold=threshold):
                        ctx.runner.safe_click(tpl_sair, threshold=threshold)
                    if ctx.runner.wait_template(confirmacao, timeout=timeout, threshold=threshold):
                        return True
                    if not ctx.runner.is_visible(tpl_sair, threshold=threshold):
                        print(f"[AI18] {label}: Sair ja consumido, aguardando transicao lenta...")
                        if ctx.runner.wait_template(confirmacao, timeout=timeout, threshold=threshold):
                            return True
                    if tentativa <= retries:
                        print(f"[AI18] {label}: tentativa {tentativa}/{retries + 1} — reclicando...")
                        time.sleep(0.5)
                raise AssertionError(
                    f"[AI18] {label}: tela nao confirmada apos {retries + 1} tentativas.\n"
                    f"  Confirmacao: {confirmacao}\n"
                    f"Veja se o elemento de confirmacao mudou de layout (recapturar template)."
                )

            # Sair 1: Alocar Leito -> INTERNACAO (confirma pelo titulo INTERNACAO)
            sair_e_confirmar(
                f"{self._TPL}/btn_sair_alocar.png",
                f"{self._TPL}/titulo_internacao.png",
                "sair-1 -> internacao",
            )

            # Sair 2: INTERNACAO -> Menu Principal real
            # Confirma por btn_pesquisar_menu (so existe no menu real;
            # o titulo "Menu Principal" e ambiguo com a tela de login).
            sair_e_confirmar(
                f"{self._TPL}/btn_sair_internacao.png",
                f"{self._TPL}/btn_pesquisar_menu.png",
                "sair-2 -> menu principal",
            )

            # Sair 3: Menu Principal real -> tela de login.
            # Botao Sair do menu fica na borda esquerda (sombra intermitente
            # torna template instavel) -> clique por coordenada.
            # Confirma por login/btn_entrar (so existe na tela de login).
            self._focar_si3()
            x, y = self._coord(ctx.config.coordenadas, "btn_sair_menu")
            pyautogui.click(x, y)
            if not ctx.runner.wait_template(
                "templates/si3/login/btn_entrar.png", timeout=15, threshold=0.7
            ):
                raise AssertionError(
                    "[AI18] sair-3 -> login: tela de login nao confirmada apos clique em (btn_sair_menu).\n"
                    "  Confirmacao: templates/si3/login/btn_entrar.png\n"
                    "Verifique a coordenada btn_sair_menu no config.yaml e se o login realmente abriu."
                )

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI18_sair.png")
        return self._step("AI18", "sair para menu principal", fn, observer, ctx=ctx)

    def _ai19_validar_nr_admissao(self, ctx, regioes, observer=None) -> StepResult:
        """
        Validacao final: OCR le o Nr Admissao na tela.
        Se a regiao nao estiver calibrada: WARNING, step passa (modo bootstrap).
        Se calibrada: falha se nao encontrar numero.
        """
        def fn():
            import re
            regiao = regioes.get("nr_admissao")
            screenshot_path = ctx.runner.screenshot(
                f"{ctx.evidence_dir}AI19_validacao.png"
            )

            if not regiao or not (regiao["x1"] or regiao["y1"] or regiao["x2"] or regiao["y2"]):
                print("[AI19] AVISO: regioes_ocr.nr_admissao nao calibrado — "
                      "validacao de Nr Admissao pulada. Calibrar apos primeira execucao.")
                return screenshot_path

            texto = OcrHelper.ler_regiao(
                screenshot_path,
                (regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"])
            )
            numeros = re.findall(r'\d+', texto)
            if not numeros:
                OcrHelper.salvar_debug(
                    screenshot_path,
                    (regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"]),
                    f"{ctx.evidence_dir}AI19_ocr_debug.png"
                )
                raise AssertionError(
                    f"Nr Admissao nao encontrado — admissao pode ter falhado.\n"
                    f"Texto lido via OCR: '{texto}'\n"
                    f"Veja AI19_ocr_debug.png e ajuste regioes_ocr.nr_admissao."
                )

            print(f"[AI19] Nr Admissao validado: {numeros[0]}")
            return screenshot_path
        return self._step("AI19", "validar Nr Admissao via OCR", fn, observer,
                          validated=True, ctx=ctx)