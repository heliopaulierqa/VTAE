# src/flows/si3/cadastro_paciente_flow.py
"""
CadastroPacienteFlow - Cadastro completo de paciente no SI3 (Oracle Forms).

Presupoe que o login ja foi executado via LoginFlow.

Steps:
    CP01  Menu cadastro paciente
    CP02  Pesquisar nome
    CP03  Clicar Novo
    CP04  Nome Social
    CP05  Data Nascimento + Hora
    CP06  Sexo
    CP07  Nacionalidade (2 popups)
    CP08  Mae
    CP09  Pai
    CP10  Conjuge
    CP11  Responsavel
    CP12  Cor/Etnia
    CP13  Religiao
    CP14  Estado Civil
    CP15  Ocupacao
    CP16  Situacao Familiar
    CP17  Tipo de Deficiencia
    CP18  Escolaridade + Frequenta Escola
    CP19  CPF + RG + CNS  (aba Documentos)
    CP20  Aba Enderecos
    CP21  Aba Comunicacao (celular + e-mail)
    CP22  Gerar Matricula + Salvar + OCR + salvar estado_jornada.json
    CP23  Sair

Coordenadas:
    TODAS as coordenadas ficam no config.yaml em coordenadas:
    Use python scripts/posicao_mouse.py para capturar cada campo
    que nao pode ser localizado por template OpenCV.

Templates em templates/si3/cadastro_paciente/:
    menu_cadastro_paciente.png
    campo_nome_pesquisa.png
    btn_pesquisar.png
    btn_novo.png
    campo_nome_social.png
    btn_ok.png
    btn_ok_nacion.png
    btn_ok_erro.png   <- popup de erro Oracle Forms (FRM-* / HC-INCOR)
    aba_documentos.png
    aba_enderecos.png
    aba_comunicacao.png
    btn_salvar.png
    btn_gerar_matricula.png  (ou coordenada se nao tiver template)

Regra de popup Oracle Forms:
    - Popups ESPERADOS (CP21 salvar, CP22 gerar matricula): fechados silenciosamente
      pelo proprio step com _fechar_popups_oracle() — registra WARNING no log, nao falha
    - Popups INESPERADOS: o step lanca AssertionError manualmente quando necessario
    - O wrapper _step NAO verifica popup automaticamente — cada step e responsavel

Estado da jornada:
    - CP22 salva paciente_id via src.core.estado_jornada.salvar()
    - test_02+ leem via src.core.estado_jornada.ler("paciente_id")
    - Falha na leitura gera CausaFalha.ESTADO_AUSENTE
"""

import re
import time
from datetime import date, timedelta

import pyautogui
import pyperclip

from src.core.context import FlowContext
from src.core.estado_jornada import salvar as _salvar_estado_jornada  # helper centralizado
from src.core.result import CausaFalha, FlowResult, StepResult
from src.flows.base_flow import BaseFlow
from src.vision.ocr import OcrHelper


class CadastroPacienteFlow(BaseFlow):
    """
    Fluxo completo de cadastro de paciente no SI3.
    Ao final salva a matricula gerada em evidence/estado_jornada.json
    para uso nos testes seguintes da jornada do ambulatorio.
    """

    FLOW_NAME = "CadastroPacienteFlow"
    _TPL = "templates/si3/cadastro_paciente"

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
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
            lambda: self._step_conjuge(ctx, dados, observer),
            lambda: self._step_responsavel(ctx, dados, observer),
            lambda: self._step_cor_etnia(ctx, dados, observer),
            lambda: self._step_religiao(ctx, dados, observer),
            lambda: self._step_estado_civil(ctx, dados, observer),
            lambda: self._step_ocupacao(ctx, dados, observer),
            lambda: self._step_situacao_familiar(ctx, dados, observer),
            lambda: self._step_tipo_deficiencia(ctx, dados, observer),
            lambda: self._step_escolaridade(ctx, dados, observer),
            lambda: self._step_documentos(ctx, dados, observer),
            lambda: self._step_enderecos(ctx, dados, observer),
            lambda: self._step_comunicacao(ctx, dados, observer),
            lambda: self._step_gerar_matricula_salvar(ctx, observer),
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

    def _coord(self, ctx, nome: str) -> tuple:
        """Le coordenada do config.yaml. Lanca KeyError se nao configurada."""
        coords = ctx.config.coordenadas
        if nome not in coords:
            raise KeyError(
                f"Coordenada '{nome}' nao encontrada em config.yaml -> coordenadas:"
                f"\nConfigure com posicao_mouse.py e adicione ao config.yaml."
            )
        c = coords[nome]
        return (c["x"], c["y"])

    def _clicar_coord(self, ctx, nome: str) -> None:
        x, y = self._coord(ctx, nome)
        pyautogui.click(x, y)
        time.sleep(0.3)

    def _preencher_coord(self, ctx, nome: str, valor: str) -> None:
        """Clique direto + limpar + digitar. Para campos pequenos."""
        x, y = self._coord(ctx, nome)
        pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor)
        time.sleep(0.2)

    def _preencher_template(self, ctx, template: str, nome_coord: str,
                             valor: str, offset_x: int = 150) -> None:
        """click_near com fallback para coordenada. Para campos grandes e unicos."""
        try:
            ctx.runner.click_near(f"{self._TPL}/{template}", offset_x=offset_x,
                                  offset_y=0, threshold=0.65)
        except Exception:
            x, y = self._coord(ctx, nome_coord)
            pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor)
        time.sleep(0.2)

    def _clicar_aba(self, ctx, template: str, nome_coord: str) -> None:
        """Clica em aba por template com fallback para coordenada."""
        try:
            ctx.runner.safe_click(f"{self._TPL}/{template}", threshold=0.7)
        except Exception:
            x, y = self._coord(ctx, nome_coord)
            pyautogui.click(x, y)
        time.sleep(0.5)

    def _fechar_popups_oracle(self, ctx) -> bool:
        """
        Fecha popups de erro Oracle Forms (FRM-* / HC-INCOR) se aparecerem.
        Retorna True se encontrou e fechou pelo menos um popup.
        Retorna False se nao encontrou nenhum popup.
        Uso: steps que sabem que podem receber popup fecham silenciosamente.
        """
        encontrou_popup = False
        for _ in range(6):
            try:
                encontrou = ctx.runner.wait_template(
                    f"{self._TPL}/btn_ok_erro.png",
                    timeout=2.0, threshold=0.75,
                )
                if encontrou:
                    ctx.runner.safe_click(f"{self._TPL}/btn_ok_erro.png", threshold=0.75)
                    time.sleep(0.5)
                    encontrou_popup = True
                else:
                    break
            except Exception:
                break
        return encontrou_popup

    def _step(self, step_id: str, descricao: str, fn, observer,
              confirm_template: str = None,
              validated: bool = None) -> StepResult:
        """
        Wrapper padrao para todos os steps com observabilidade.

        Args:
            confirm_template: template da tela destino — validated=True automatico.
            validated: True explicito quando fn() executou verify_lov/verify_fill
                       internamente. Corrige bug onde validated ficava None mesmo
                       com verify_lov/fill rodando dentro de fn().

        StepResult.validated:
            True  — acao executou E resultado confirmado (confirm_template ou verify_*)
            False — step falhou (excecao capturada)
            None  — step executou sem validacao pos-acao

        Nao verifica popup automaticamente — cada step e responsavel
        por tratar popups esperados dentro do proprio fn().
        """
        if observer:
            observer.log_step_start(step_id, descricao)
        start = time.monotonic()
        _validated = None
        try:
            screenshot_path = fn()
            _validated = True if (confirm_template or validated) else None
            step = StepResult(
                step_id=step_id, success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot_path,
                validated=_validated,
                description=descricao,
            )
        except AssertionError as e:
            msg = str(e).lower()
            if "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            else:
                causa = CausaFalha.SISTEMA
            step = StepResult(
                step_id=step_id, success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e), causa_falha=causa,
                validated=False,
                description=descricao,
            )
        except Exception as e:
            causa = CausaFalha.DESCONHECIDA
            msg = str(e).lower()
            if "template" in msg or "not found" in msg:
                causa = CausaFalha.TEMPLATE_NAO_ENCONTRADO
            elif "timeout" in msg:
                causa = CausaFalha.TIMEOUT
            elif "ocr" in msg or "matricula" in msg or "regiao" in msg:
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
                description=descricao,
            )
        if observer:
            observer.log_step_result(step)
        return step

    # ----------------------------------------------------------------
    # Helper _verify_campo — validacao pós-digitacao centralizada
    # Evita duplicar o padrao verify_fill em cada step
    # ----------------------------------------------------------------

    def _verify_campo(self, ctx, nome_regiao: str, valor: str,
                      step_id: str, obrigatorio: bool = True) -> str:
        """
        Verifica via OCR se o campo foi preenchido com o valor esperado.
        Retorna o valor lido pelo OCR para propagacao em ocr_lido do StepResult.

        Args:
            ctx:           FlowContext
            nome_regiao:   chave em regioes_ocr do config.yaml
            valor:         valor esperado no campo
            step_id:       ID do step para mensagem de erro
            obrigatorio:   True = falha o step; False = avisa mas continua
        """
        if not valor:
            return ""
        regiao = ctx.config.regioes_ocr.get(nome_regiao)
        if not regiao or not (regiao["x1"] or regiao["y1"]):
            print(f"[{step_id}] AVISO: regioes_ocr.{nome_regiao} nao calibrado — "
                  f"verify_fill pulado")
            return ""
        ok, valor_lido = ctx.runner.verify_fill(
            valor,
            region=(regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"]),
            debug_path=f"{ctx.evidence_dir}{step_id}_verify_{nome_regiao}_debug.png"
        )
        if not ok:
            msg = (f"[{step_id}] Campo '{nome_regiao}' nao preenchido com '{valor}'.\n"
                   f"OCR leu: '{valor_lido}'\n"
                   f"Veja {step_id}_verify_{nome_regiao}_debug.png.")
            if obrigatorio:
                raise AssertionError(msg)
            else:
                print(f"AVISO: {msg}")
        return valor_lido

    # ----------------------------------------------------------------
    # Steps CP01-CP03: Navegacao
    # ----------------------------------------------------------------

    def _step_menu(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.double_click(f"{self._TPL}/menu_cadastro_paciente.png", threshold=0.7)
            apareceu = ctx.runner.wait_template(f"{self._TPL}/campo_nome_pesquisa.png",
                                     timeout=15.0, threshold=0.7)
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: campo_nome_pesquisa.png nao apareceu apos abrir menu. "
                    "Tela de pesquisa de paciente pode nao ter carregado."
                )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP01_menu.png")
        return self._step("CP01", "duplo clique em Cadastro de Pacientes", fn, observer,
                          confirm_template=f"{self._TPL}/campo_nome_pesquisa.png")

    def _step_pesquisar(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_template(ctx, "campo_nome_pesquisa.png",
                                     "campo_nome_pesquisa", dados["nome"])
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            time.sleep(3.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP02_pesquisa.png")
        return self._step("CP02", f"pesquisar: {dados['nome']}", fn, observer)

    def _step_novo(self, ctx, observer=None) -> StepResult:
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_novo.png", threshold=0.7)
            apareceu = ctx.runner.wait_template(f"{self._TPL}/campo_nome_social.png",
                                     timeout=15.0, threshold=0.7)
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: campo_nome_social.png nao apareceu apos clicar Novo. "
                    "Formulario de cadastro pode nao ter aberto."
                )
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP03_novo.png")
        return self._step("CP03", "clicar em Novo", fn, observer,
                          confirm_template=f"{self._TPL}/campo_nome_social.png")

    # ----------------------------------------------------------------
    # Steps CP04-CP18: Formulario principal
    # ----------------------------------------------------------------

    def _step_nome_social(self, ctx, dados: dict, observer=None) -> StepResult:
        _ocr = [None]
        def fn():
            valor = dados.get("nome_social", "") or dados.get("nome", "")
            self._preencher_template(ctx, "campo_nome_social.png",
                                     "campo_nome_social", valor)
            pyautogui.press("tab")
            time.sleep(0.3)
            # verify_lov: confirma que o campo nao ficou vazio e lê o valor real
            # Uso verify_lov (nao verify_fill) porque o valor aceito pelo Oracle Forms
            # pode ter formatacao diferente do dado gerado pelo Faker
            ok, valor_lido = ctx.runner.verify_lov(
                "nome_social",
                region=(18, 148, 350, 162),
                timeout=3.0,
            )
            _ocr[0] = valor_lido
            if not ok:
                print(f"[CP04] AVISO: campo Nome Social ficou vazio apos digitacao")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP04_social.png")
        step = self._step("CP04", "Nome Social", fn, observer, validated=True)
        if step.success and _ocr[0]:
            step.ocr_lido = _ocr[0]
        return step

    def _step_data_nascimento(self, ctx, dados: dict, observer=None) -> StepResult:
     def fn():
        data = dados["data_nascimento"]
        hora = dados.get("hora", "00:00")

        # Campo de data com máscara Oracle Forms: Ctrl+A não funciona.
        # Digitar só os dígitos (sem /) — o Forms preenche os separadores.
        x, y = self._coord(ctx, "campo_data_nascimento")
        pyautogui.click(x, y); time.sleep(0.3)
        pyautogui.press("backspace", presses=10, interval=0.02)
        digitos_data = data.replace("/", "")   # "02/03/1966" → "02031966"
        ctx.runner.type_text(digitos_data)
        time.sleep(0.3)

        # Campo hora: mesmo padrão
        x, y = self._coord(ctx, "campo_hora")
        pyautogui.click(x, y); time.sleep(0.3)
        pyautogui.press("backspace", presses=6, interval=0.02)
        digitos_hora = hora.replace(":", "")   # "00:00" → "0000"
        ctx.runner.type_text(digitos_hora)
        time.sleep(0.3)

        self._verify_campo(ctx, "data_nascimento", data, "CP05", obrigatorio=True)
        return ctx.runner.screenshot(f"{ctx.evidence_dir}CP05_data.png")
     return self._step("CP05", "Data Nascimento + Hora", fn, observer, validated=True)
    def _step_sexo(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            valor = dados.get("sexo", "M")
            self._preencher_coord(ctx, "campo_sexo", valor)
            self._verify_campo(ctx, "sexo", valor, "CP06", obrigatorio=True)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP06_sexo.png")
        return self._step("CP06", f"Sexo: {dados.get('sexo', 'M')}", fn, observer,
                          validated=True)

    def _step_nacionalidade(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_nacionalidade",
                                  dados.get("nacionalidade", "BRASILEIRA"))
            pyautogui.press("tab")
            time.sleep(2.0)
            encontrou = ctx.runner.wait_template(f"{self._TPL}/btn_ok.png",
                                                  timeout=8.0, threshold=0.6)
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(1.5)
            ctx.runner.type_text("SP")
            pyautogui.press("tab")
            time.sleep(0.5)
            ctx.runner.type_text("SAO PAULO")
            time.sleep(0.3)
            encontrou2 = ctx.runner.wait_template(f"{self._TPL}/btn_ok_nacion.png",
                                                   timeout=8.0, threshold=0.6)
            if encontrou2:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok_nacion.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP07_nacion.png")
        return self._step("CP07", "Nacionalidade", fn, observer)

    def _step_mae(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            valor = dados["mae"]
            self._preencher_coord(ctx, "campo_mae", valor)
            self._verify_campo(ctx, "nome_mae", valor, "CP08", obrigatorio=True)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP08_mae.png")
        return self._step("CP08", "Mae", fn, observer, validated=True)

    def _step_pai(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_pai", dados["pai"])
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP09_pai.png")
        return self._step("CP09", "Pai", fn, observer)

    def _step_conjuge(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_conjuge", dados.get("conjuge", ""))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP10_conjuge.png")
        return self._step("CP10", "Conjuge", fn, observer)

    def _step_responsavel(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_responsavel", dados.get("responsavel", ""))
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP11_responsavel.png")
        return self._step("CP11", "Responsavel", fn, observer)

    def _step_cor_etnia(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            valor = dados.get("cor_etnia", "PARDA")
            self._preencher_coord(ctx, "campo_cor_etnia", valor)
            pyautogui.press("tab")
            time.sleep(0.3)
            self._verify_campo(ctx, "cor_etnia", valor, "CP12", obrigatorio=True)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP12_cor.png")
        return self._step("CP12", "Cor/Etnia", fn, observer, validated=True)

    def _step_religiao(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_religiao", dados.get("religiao", "CATOLICA"))
            pyautogui.press("tab")
            time.sleep(1.5)
            encontrou = ctx.runner.wait_template(
                f"{self._TPL}/btn_ok.png", timeout=8.0, threshold=0.6,
            )
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP13_religiao.png")
        return self._step("CP13", "Religiao", fn, observer)

    def _step_estado_civil(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            valor = dados.get("estado_civil", "SOLTEIRO")
            self._preencher_coord(ctx, "campo_estado_civil", valor)
            pyautogui.press("tab")
            time.sleep(0.3)
            self._verify_campo(ctx, "estado_civil", valor, "CP14", obrigatorio=True)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP14_civil.png")
        return self._step("CP14", "Estado Civil", fn, observer, validated=True)

    def _step_ocupacao(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            valor = dados.get("ocupacao", "ESTUDANTE")
            self._preencher_coord(ctx, "campo_ocupacao", valor)
            pyautogui.press("tab")
            time.sleep(0.3)
            self._verify_campo(ctx, "ocupacao", valor, "CP15", obrigatorio=True)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP15_ocupacao.png")
        return self._step("CP15", "Ocupacao", fn, observer, validated=True)

    def _step_situacao_familiar(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_situacao_familiar",
                                  dados.get("situacao_familiar", "SEM INFORMACAO"))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP16_sit_familiar.png")
        return self._step("CP16", "Situacao Familiar", fn, observer)

    def _step_tipo_deficiencia(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_tipo_deficiencia",
                                  dados.get("tipo_deficiencia", ""))
            pyautogui.press("tab")
            time.sleep(0.3)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP17_defic.png")
        return self._step("CP17", "Tipo de Deficiencia", fn, observer)

    def _step_escolaridade(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._preencher_coord(ctx, "campo_escolaridade",
                                  dados.get("escolaridade", "SUPERIOR INCOMPLETO"))
            pyautogui.press("tab")
            time.sleep(1.5)
            encontrou = ctx.runner.wait_template(
                f"{self._TPL}/btn_ok.png", timeout=8.0, threshold=0.6,
            )
            if encontrou:
                ctx.runner.safe_click(f"{self._TPL}/btn_ok.png", threshold=0.6)
            else:
                pyautogui.press("enter")
            time.sleep(0.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP18_escolar.png")
        return self._step("CP18", "Escolaridade", fn, observer)

    # ----------------------------------------------------------------
    # Steps CP19-CP21: Abas
    # ----------------------------------------------------------------

    def _step_documentos(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._clicar_aba(ctx, "aba_documentos.png", "aba_documentos")
            time.sleep(0.5)
            # confirm_template: aba Documentos deve estar visível
            apareceu = ctx.runner.wait_template(f"{self._TPL}/aba_documentos.png",
                                                timeout=8.0, threshold=0.7)
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: aba_documentos.png nao visivel apos clicar na aba. "
                    "Aba Documentos pode nao ter sido ativada."
                )

            pyperclip.copy(dados.get("rg", "44643579X"))
            pyautogui.click(262, 424); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(637, 427); time.sleep(0.3)
            pyperclip.copy("SSP")
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(780, 426); time.sleep(0.3)
            pyperclip.copy("SP")
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(868, 424); time.sleep(0.3)
            # sempre 30 dias atras — nunca anterior ao nascimento, nunca futuro
            data_emissao = (date.today() - timedelta(days=30)).strftime("%d/%m/%Y")
            pyperclip.copy(data_emissao)
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            cpf = dados["cpf"].replace(".", "").replace("-", "")
            pyautogui.click(262, 450); time.sleep(0.3)
            pyperclip.copy(cpf)
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            pyautogui.click(257, 476); time.sleep(0.3)
            pyperclip.copy("726337961670004")
            pyautogui.hotkey("ctrl", "v"); time.sleep(0.2)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP19_docs.png")
        return self._step("CP19", "Aba Documentos: RG + CPF + CNS", fn, observer,
                          confirm_template=f"{self._TPL}/aba_documentos.png")

    def _step_enderecos(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._clicar_aba(ctx, "aba_enderecos.png", "aba_enderecos")
            time.sleep(0.5)
            # confirm_template: aba Enderecos deve estar visível
            apareceu = ctx.runner.wait_template(f"{self._TPL}/aba_enderecos.png",
                                                timeout=8.0, threshold=0.7)
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: aba_enderecos.png nao visivel apos clicar na aba. "
                    "Aba Enderecos pode nao ter sido ativada."
                )
            end = dados.get("endereco", {})

            self._preencher_coord(ctx, "campo_cep", end.get("cep", "01310100"))
            pyautogui.press("tab"); time.sleep(2.5)

            screenshot_cep = ctx.runner.screenshot(f"{ctx.evidence_dir}CP20_cep_check.png")
            logradouro_lido = OcrHelper.ler_regiao(screenshot_cep, (214, 424, 528, 444)).strip()
            print(f"[CP20] Logradouro apos CEP: '{logradouro_lido}'")

            if logradouro_lido:
                print("[CP20] Auto-preenchimento OK - preenchendo apenas Numero e Complemento")
                self._preencher_coord(ctx, "campo_numero_endereco",      end.get("numero",      "44"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_complemento_endereco", end.get("complemento", "CADASTRO DE TESTE"))
                pyautogui.press("tab"); time.sleep(0.3)
            else:
                print("[CP20] Auto-preenchimento falhou - preenchendo todos os campos")
                self._preencher_coord(ctx, "campo_tipo_endereco",        end.get("tipo",        "AVENIDA"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_logradouro",           end.get("logradouro",  "DR. ENEAS CARVALHO DE AGUIAR"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_numero_endereco",      end.get("numero",      "44"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_complemento_endereco", end.get("complemento", "CADASTRO DE TESTE"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_pais_endereco",        end.get("pais",        "BRASIL"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_uf_endereco",          end.get("uf",          "SP"))
                pyautogui.press("tab"); time.sleep(0.3)
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_municipio_endereco",   end.get("municipio",   "SAO PAULO"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_bairro",               end.get("bairro",      "BELA VISTA"))
                pyautogui.press("tab"); time.sleep(0.3)
                self._preencher_coord(ctx, "campo_referencia_endereco",  end.get("referencia",  "PROXIMO AO CENTRO"))
                pyautogui.press("tab"); time.sleep(0.3)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP20_endereco.png")
        return self._step("CP20", "Aba Enderecos", fn, observer,
                          confirm_template=f"{self._TPL}/aba_enderecos.png")

    def _step_comunicacao(self, ctx, dados: dict, observer=None) -> StepResult:
        def fn():
            self._clicar_aba(ctx, "aba_comunicacao.png", "aba_comunicacao")
            time.sleep(0.5)
            # confirm_template: aba Comunicacao deve estar visível
            apareceu = ctx.runner.wait_template(f"{self._TPL}/aba_comunicacao.png",
                                                timeout=8.0, threshold=0.7)
            if not apareceu:
                raise AssertionError(
                    "Falha de Observabilidade: aba_comunicacao.png nao visivel apos clicar na aba. "
                    "Aba Comunicacao pode nao ter sido ativada."
                )

            com = dados.get("comunicacao", {})

            # Linha 1 - celular
            self._preencher_coord(ctx, "campo_comunicacao_prioridade_l1", "1")
            pyautogui.press("tab"); time.sleep(0.2)
            pyautogui.click(*self._coord(ctx, "campo_comunicacao_lov_l1")); time.sleep(1.5)
            pyautogui.click(82, 142); time.sleep(0.3)
            ctx.runner.type_text("CELULAR")
            pyautogui.click(113, 354); time.sleep(1.0)
            pyautogui.click(221, 355); time.sleep(0.5)
            self._preencher_coord(ctx, "campo_comunicacao_numero_l1",
                                  com.get("celular", dados.get("celular", "")))
            pyautogui.press("tab"); time.sleep(0.3)

            # Linha 2 - e-mail
            self._preencher_coord(ctx, "campo_comunicacao_prioridade_l2", "2")
            pyautogui.press("tab"); time.sleep(0.2)
            pyautogui.click(*self._coord(ctx, "campo_comunicacao_lov_l2")); time.sleep(1.5)
            pyautogui.click(82, 142); time.sleep(0.3)
            ctx.runner.type_text("E-MAIL")
            pyautogui.click(113, 354); time.sleep(1.0)
            pyautogui.click(221, 355); time.sleep(0.5)
            self._preencher_coord(ctx, "campo_comunicacao_numero_l2", "teste@teste.com")
            pyautogui.press("tab"); time.sleep(0.3)

            # Salvar antes de gerar matricula
            pyautogui.click(58, 66); time.sleep(2.5)

            # Popup apos salvar e comportamento esperado no SI3 — fechar silenciosamente
            if self._fechar_popups_oracle(ctx):
                print("[CP21] Popup Oracle Forms fechado apos salvar — comportamento esperado")

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP21_comunicacao.png")
        return self._step("CP21", "Aba Comunicacao: celular + e-mail", fn, observer,
                          confirm_template=f"{self._TPL}/aba_comunicacao.png")

    # ----------------------------------------------------------------
    # Step CP22: Gerar Matricula + Salvar + OCR + estado_jornada.json
    # ----------------------------------------------------------------

    def _step_gerar_matricula_salvar(self, ctx, observer=None) -> StepResult:
        def fn():
            # 1. Clicar em Gerar Matricula
            try:
                ctx.runner.safe_click(f"{self._TPL}/btn_gerar_matricula.png", threshold=0.7)
            except Exception:
                self._clicar_coord(ctx, "btn_gerar_matricula")
            time.sleep(2.0)

            # 2. Salvar
            pyautogui.click(58, 66); time.sleep(3.0)

            # Popup apos salvar e comportamento esperado — fechar silenciosamente
            if self._fechar_popups_oracle(ctx):
                print("[CP22] Popup Oracle Forms fechado apos salvar — comportamento esperado")

            # 3. Screenshot para OCR
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}CP22_matricula.png")

            # 4. Le regioes OCR do config.yaml
            r_mat = ctx.config.regioes_ocr["matricula"]
            regiao_matricula = (r_mat["x1"], r_mat["y1"], r_mat["x2"], r_mat["y2"])

            # 5. OCR — Matricula (validacao de que foi gerada)
            OcrHelper.salvar_debug(screenshot_path, regiao_matricula,
                                   f"{ctx.evidence_dir}CP22_ocr_debug.png")
            texto_mat = OcrHelper.ler_regiao(screenshot_path, regiao_matricula)
            numeros_mat = re.findall(r"\d+", texto_mat)
            if not numeros_mat:
                raise AssertionError(
                    f"Matricula nao gerada ou OCR nao leu.\n"
                    f"Texto lido: '{texto_mat}'\n"
                    f"Regiao usada: {regiao_matricula}\n"
                    f"Veja CP22_ocr_debug.png e ajuste regioes_ocr.matricula no config.yaml."
                )
            matricula = numeros_mat[0]
            print(f"[CP22] Matricula gerada: {matricula}")

            # 6. OCR — Identificador (usado como paciente_id no AB02)
            # O Identificador fica no topo da tela, campo fixo, so digitos
            # Regiao calibravel em regioes_ocr.identificador no config.yaml
            # Fallback: usa a matricula se a regiao nao estiver configurada
            paciente_id = matricula  # fallback padrao
            if "identificador" in ctx.config.regioes_ocr:
                r_id = ctx.config.regioes_ocr["identificador"]
                regiao_id = (r_id["x1"], r_id["y1"], r_id["x2"], r_id["y2"])
                OcrHelper.salvar_debug(screenshot_path, regiao_id,
                                       f"{ctx.evidence_dir}CP22_ocr_id_debug.png")
                texto_id = OcrHelper.ler_regiao(screenshot_path, regiao_id)
                numeros_id = re.findall(r"\d+", texto_id)
                if numeros_id:
                    paciente_id = numeros_id[0]
                    print(f"[CP22] Identificador lido: {paciente_id}")
                else:
                    print(f"[CP22] AVISO: OCR nao leu Identificador (texto='{texto_id}') "
                          f"— usando matricula '{matricula}' como fallback. "
                          f"Ajuste regioes_ocr.identificador no config.yaml.")
            else:
                print(f"[CP22] regioes_ocr.identificador nao configurado — "
                      f"usando matricula '{matricula}' como paciente_id. "
                      f"Adicione ao config.yaml para usar o Identificador.")

            # 7. Salva Identificador como paciente_id — usado pelo AB02 na admissao
            _salvar_estado_jornada("paciente_id", paciente_id)
            _salvar_estado_jornada("matricula", matricula)  # mantém matricula separada

            return screenshot_path
        return self._step("CP22", "Gerar Matricula + Salvar + OCR", fn, observer,
                          confirm_template="ocr:matricula")

    # ----------------------------------------------------------------
    # Step CP23: Sair
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None) -> StepResult:
        def fn():
            self._clicar_coord(ctx, "btn_sair_1")
            time.sleep(1.5)
            self._clicar_coord(ctx, "btn_sair_2")
            time.sleep(1.5)
            self._clicar_coord(ctx, "btn_sair_menu")
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CP23_menu.png")
        return self._step("CP23", "sair para o Menu Principal", fn, observer)