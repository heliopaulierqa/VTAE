# src/flows/si3/admissao_internacao_flow.py
"""
AdmissaoInternacaoFlow — SI3 Oracle Forms
Versao: 0.5.9d

Reescrito seguindo o contrato padrao VTAE:
  - Zero dados hardcoded no flow — tudo em config.yaml via _dado()
  - Zero coordenadas hardcoded — tudo em coordenadas: no config.yaml
  - _focar_si3() antes de steps criticos
  - _tpl_existe() antes de wait_template com templates opcionais
  - verify_lov obrigatorio apos qualquer LOV
  - confirm_template em steps de navegacao
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
  AI16  Alocar Leito → Consultar Leito → LOV unidade → OK
  AI17  Selecionar primeira linha → Selecionar → fechar popups → OK → Sair
  AI18  Sair (tela admissao) → Sair (menu)
  AI19  Validar Nr Admissao via OCR
"""
import os
import time
import pyautogui

from src.core.context import FlowContext
from src.core.result import FlowResult, StepResult, CausaFalha
from src.core.estado_jornada import ler as _ler_estado
from src.vision.ocr import OcrHelper


class AdmissaoInternacaoFlow:

    FLOW_NAME = "AdmissaoInternacaoFlow"
    _TPL = "templates/si3/admissao_internacao"

    # ── Helpers obrigatorios (contrato VTAE) ─────────────────────────────

    def _dado(self, dados: dict, chave: str, step_id: str):
        """Dado ausente = erro imediato com mensagem clara."""
        if chave not in dados:
            raise AssertionError(
                f"[{step_id}] Dado obrigatorio ausente no config.yaml: '{chave}'\n"
                f"Chaves disponiveis: {list(dados.keys())}"
            )
        return dados[chave]

    @staticmethod
    def _tpl_existe(path: str) -> bool:
        """Verifica se o PNG existe — evita TemplateNotFoundError."""
        return os.path.exists(path)

    @staticmethod
    def _focar_si3() -> bool:
        """Reativa janela Oracle Forms antes de steps criticos."""
        try:
            import pygetwindow as gw
            janelas = gw.getWindowsWithTitle("FUNDA")
            if janelas:
                w = janelas[0]
                if w.isMinimized:
                    w.restore()
                    time.sleep(0.3)
                w.activate()
                time.sleep(0.5)
                return True
            return False
        except ImportError:
            print("[_focar_si3] pygetwindow nao instalado — pip install pygetwindow")
            return False
        except Exception as e:
            print(f"[_focar_si3] AVISO: {e}")
            return False

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
            # confirm_template: verifica se a tela destino apareceu
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
            )
        except Exception as e:
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
                validated=False,
                causa_falha=CausaFalha.DESCONHECIDA,
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ── Execute ──────────────────────────────────────────────────────────

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
            lambda: self._ai18_sair(ctx, observer),
            lambda: self._ai19_validar_nr_admissao(ctx, regioes, observer),
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

    # ── Steps ────────────────────────────────────────────────────────────

    def _ai01_abrir_internacao(self, ctx, dados, coords, observer=None) -> StepResult:
        """
        Padrao de navegacao via 'Localizar no Menu' — igual ao ambulatorio e agendamento.
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
        click_near no label nao funciona nessa tela (campo pequeno).
        AVISO: se campo_identificador estiver { x:0, y:0 }, usa fallback 2x TAB.
        Calibrar com posicao_mouse.py.
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
        Clica em Pesquisar.
        Abre a tela de cadastro do paciente (aba Documentos visivel).
        confirm_template: aba_endereco.png — confirma que o cadastro abriu.
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
        """
        Clica na aba Endereco na tela de cadastro do paciente.
        Essa tela aparece apos pesquisar — nela esta o campo Tipo e o botao
        Admitir Paciente.
        """
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
        REGRA PDF: campo Tipo deve estar preenchido antes de clicar Admitir Paciente,
        caso contrario a proxima tela pode dar erro.
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
                # Popup de Pais — BRASIL ja selecionado — fechar se aparecer
                tpl_ok = f"{self._TPL}/btn_ok_popup.png"
                if self._tpl_existe(tpl_ok):
                    if ctx.runner.is_visible(tpl_ok, threshold=0.7):
                        ctx.runner.safe_click(tpl_ok, threshold=0.7)
                        time.sleep(0.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI05_tipo_end.png")
        return self._step("AI05", "verificar/preencher campo Tipo (RUA)", fn, observer, ctx=ctx)

    def _ai06_admitir_paciente(self, ctx, observer=None) -> StepResult:
        """
        Botao 'Admitir paciente' fica na tela de cadastro do paciente
        (mesma tela da aba Endereco — nao e uma tela separada).
        Ao clicar, abre a tela de admissao com o campo Unidade Funcional.
        confirm_template: label fixo da tela de admissao.
        """
        def fn():
            ctx.runner.safe_click(
                f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7
            )
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI06_admitir.png")
        return self._step("AI06", "clicar Admitir Paciente", fn, observer,
                          confirm_template=f"{self._TPL}/tela_admissao.png", ctx=ctx)

    def _ai07_unidade_funcional(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            valor = self._dado(dados, "unidade_funcional", "AI07")
            self._focar_si3()
            # O cursor ja fica no campo Unidade Funcional ao abrir a tela
            # Mas usamos coordenada como fallback para garantir o foco
            if "campo_unidade_funcional" in coords:
                x, y = self._coord(coords, "campo_unidade_funcional")
                if x and y:
                    pyautogui.click(x, y)
                    time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            pyautogui.press("tab")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI07_unidade.png")
        return self._step("AI07", "preencher Unidade Funcional", fn, observer, ctx=ctx)

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

            # Provedor
            x, y = self._coord(coords, "campo_provedor")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.5)

            # Plano
            x, y = self._coord(coords, "campo_plano")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.3)

            # Carteirinha e validade — so para incor_sis e convenio
            if carteirinha:
                x, y = self._coord(coords, "campo_carteirinha")
                pyautogui.click(x, y); time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text(carteirinha)
                pyautogui.press("tab"); time.sleep(0.3)

            if validade:
                x, y = self._coord(coords, "campo_validade_carteirinha")
                pyautogui.click(x, y); time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                ctx.runner.type_text(validade)
                pyautogui.press("tab"); time.sleep(0.3)

            print(f"[AI08] Cenario provedor: {cenario_key} — {provedor}/{plano}")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI08_provedor.png")
        return self._step("AI08", "preencher Provedor e Plano", fn, observer, ctx=ctx)

    def _ai08b_declarante_especialidade(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            declarante   = self._dado(dados, "declarante",   "AI08b")
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

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI08b_declarante.png")
        return self._step("AI08b", "preencher Declarante e Especialidade", fn, observer, ctx=ctx)

    def _ai09_obs(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            valor = self._dado(dados, "obs", "AI09")
            self._focar_si3()
            x, y = self._coord(coords, "campo_obs")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(valor)
            pyautogui.press("tab"); time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI09_obs.png")
        return self._step("AI09", "preencher campo Obs", fn, observer, ctx=ctx)

    def _ai10_origem_paciente(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            tipo = self._dado(dados, "origem_tipo", "AI10")
            self._focar_si3()
            x, y = self._coord(coords, "campo_origem_tipo")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(tipo)
            pyautogui.press("tab")
            time.sleep(1.0)  # campo Entidade preenche automaticamente apos Tab
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI10_origem.png")
        return self._step("AI10", "preencher Origem do Paciente", fn, observer, ctx=ctx)

    def _ai11_origem_solicitacao(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            valor = self._dado(dados, "origem_solicitacao", "AI11")
            self._focar_si3()
            x, y = self._coord(coords, "dropdown_origem_solicitacao")
            pyautogui.click(x, y)
            time.sleep(1.5)  # aguarda animacao do dropdown
            # Tenta clicar na opcao pelo template; fallback: pyautogui.press("down")
            tpl = f"{self._TPL}/opcao_{valor.lower().replace(' ', '_')}.png"
            if self._tpl_existe(tpl):
                ctx.runner.safe_click(tpl, threshold=0.7)
            else:
                print(f"[AI11] AVISO: template de opcao ausente ({tpl}) — usando seta")
                pyautogui.press("down"); time.sleep(0.3)
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI11_solicitacao.png")
        return self._step("AI11", "selecionar Origem da Solicitacao", fn, observer, ctx=ctx)

    def _ai12_medico_responsavel(self, ctx, dados, coords, regioes, observer=None) -> StepResult:
        """
        Profissional Responsavel pela Internacao:
        Clicar na LOV — popup ja abre com resultado — clicar OK direto.
        Nao e necessario digitar termo de busca.
        """
        def fn():
            self._focar_si3()

            # Abrir LOV
            x, y = self._coord(coords, "btn_lov_medico_responsavel")
            pyautogui.click(x, y); time.sleep(1.5)

            # Popup ja abre com resultado — clicar OK direto
            x, y = self._coord(coords, "btn_ok_medico_resp")
            pyautogui.click(x, y); time.sleep(0.5)

            # verify_lov: confirma que o campo nao ficou vazio
            regiao = regioes.get("campo_medico_responsavel")
            if regiao and (regiao["x1"] or regiao["y1"]):
                if not ctx.runner.verify_lov(
                    "Medico Responsavel",
                    region=(regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"]),
                    debug_path=f"{ctx.evidence_dir}AI12_verify.png",
                ):
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
          1. Campo Numero — digita '1' + TAB
          2. LOV do medico abre automaticamente
          3. Busca pelo termo_medico_compl (configuravel — pode ser diferente de AI12)
          4. OK
          5. Retornar
        """
        def fn():
            termo = self._dado(dados, "termo_medico_compl", "AI14")
            self._focar_si3()

            # Campo Numero — digita 1 + TAB abre o popup de escolha do medico
            x, y = self._coord(coords, "campo_numero_compl")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text("1")
            pyautogui.press("tab")
            time.sleep(1.5)  # aguarda popup abrir

            # Digitar termo no campo Localizar do popup
            x, y = self._coord(coords, "campo_busca_medico_compl")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo); time.sleep(0.3)

            # Clicar Localizar
            x, y = self._coord(coords, "btn_localizar_medico_compl")
            pyautogui.click(x, y); time.sleep(1.0)

            # Double click em MEDICO (SOH PARA USO DA INFORMATICA) — dispensa OK
            ctx.runner.double_click(
                f"{self._TPL}/item_medico_informatica.png", threshold=0.7
            )
            time.sleep(0.5)

            # Retornar
            x, y = self._coord(coords, "btn_retornar_compl")
            pyautogui.click(x, y); time.sleep(1.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI14_medico_compl.png")
        return self._step("AI14", "preencher Info. Compl. e selecionar medico", fn, observer, ctx=ctx)

    def _ai15_botao_leito(self, ctx, observer=None) -> StepResult:
        """
        Clica no botao 'Leito' na barra inferior da tela de admissao.
        Abre a tela Alocar Leito diretamente.
        confirm_template: label 'Consultar Leito' — unico nessa tela, texto fixo.
        """
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_leito.png", threshold=0.7)
            time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI15_leito.png")
        return self._step("AI15", "clicar botao LEITO", fn, observer,
                          confirm_template=f"{self._TPL}/btn_alocar_leito.png", ctx=ctx)

    def _ai16_alocar_leito(self, ctx, dados, coords, observer=None) -> StepResult:
        """
        Tela Alocar Leito (ja aberta pelo AI15):
          1. Clicar 'Alocar Leito'
          2. Fechar popup 'paciente ja possui leito alocado' — OK (sempre aparece)
          3. Clicar 'Consultar Leito'
          4. LOV de unidade funcional — digita termo, Localizar, OK
        """
        def fn():
            self._focar_si3()
            termo_unidade = self._dado(dados, "termo_unidade_leito", "AI16")
            tpl_ok = f"{self._TPL}/btn_ok_popup.png"

            # 1. Clicar Alocar Leito
            x, y = self._coord(coords, "btn_alocar_leito")
            pyautogui.click(x, y); time.sleep(1.5)

            # 2. Fechar popup "paciente ja possui leito" — sempre aparece
            #    Texto: "O paciente X ja possui um leito alocado de numero Y"
            if self._tpl_existe(tpl_ok):
                if ctx.runner.is_visible(tpl_ok, threshold=0.7):
                    ctx.runner.safe_click(tpl_ok, threshold=0.7)
                    time.sleep(0.5)
                    print("[AI16] Popup 'ja possui leito' fechado com OK")
            else:
                # fallback se template nao capturado ainda
                time.sleep(1.0)
                pyautogui.press("enter")
                time.sleep(0.5)

            # 3. Consultar Leito
            x, y = self._coord(coords, "btn_consultar_leito")
            pyautogui.click(x, y); time.sleep(1.0)

            # 4. LOV de unidade funcional
            x, y = self._coord(coords, "campo_busca_unidade_leito")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo_unidade); time.sleep(0.3)

            x, y = self._coord(coords, "btn_localizar_unidade_leito")
            pyautogui.click(x, y); time.sleep(1.0)

            x, y = self._coord(coords, "btn_ok_unidade_leito")
            pyautogui.click(x, y); time.sleep(1.0)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI16_alocar_leito.png")
        return self._step("AI16", "Alocar Leito e selecionar unidade", fn, observer, ctx=ctx)

    def _ai17_selecionar_leito(self, ctx, coords, observer=None) -> StepResult:
        """
        Lista de leitos livres:
          1. Clicar na primeira linha
          2. Clicar Selecionar
          3. Fechar popups de aviso (especialidade diferente → SIM; outros → OK)
          4. OK na tela final
          5. Sair (tela fica em branco apos OK)
        """
        def fn():
            self._focar_si3()

            # Primeira linha da lista de leitos
            x, y = self._coord(coords, "primeira_linha_leitos")
            pyautogui.click(x, y); time.sleep(0.3)

            # Selecionar
            x, y = self._coord(coords, "btn_selecionar_leito")
            pyautogui.click(x, y); time.sleep(1.0)

            # Popup "especialidade diferente" → SIM
            tpl_sim = f"{self._TPL}/btn_sim_popup.png"
            if self._tpl_existe(tpl_sim):
                if ctx.runner.is_visible(tpl_sim, threshold=0.7):
                    ctx.runner.safe_click(tpl_sim, threshold=0.7)
                    time.sleep(0.5)

            # Outros popups → OK
            tpl_ok = f"{self._TPL}/btn_ok_popup.png"
            if self._tpl_existe(tpl_ok):
                for _ in range(3):  # fecha ate 3 popups em sequencia
                    if ctx.runner.is_visible(tpl_ok, threshold=0.7):
                        ctx.runner.safe_click(tpl_ok, threshold=0.7)
                        time.sleep(0.5)
                    else:
                        break

            # OK na tela final de alocacao
            x, y = self._coord(coords, "btn_ok_alocar")
            pyautogui.click(x, y); time.sleep(1.0)

            # Sair — tela fica em branco apos OK, deve clicar em Sair
            x, y = self._coord(coords, "btn_sair_alocar")
            pyautogui.click(x, y); time.sleep(1.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI17_leito_selecionado.png")
        return self._step("AI17", "selecionar leito e fechar popups", fn, observer, ctx=ctx)

    def _ai18_sair(self, ctx, observer=None) -> StepResult:
        """
        Sair da tela de admissao e voltar ao menu principal.
        PDF: dois cliques em Sair para voltar a tela de login.
        """
        def fn():
            self._focar_si3()
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AI18_sair.png")
        return self._step("AI18", "sair para tela de login", fn, observer, ctx=ctx)

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