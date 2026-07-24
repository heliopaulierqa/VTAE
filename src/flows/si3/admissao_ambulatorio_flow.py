# src/flows/si3/admissao_ambulatorio_flow.py
"""
AdmissaoAmbulatorioFlow — SI3 Oracle Forms
v0.5.15: AB02 corrigido — restaurado clique+digitacao perdidos em edicao anterior.

Mudancas vs v0.5.10:
  - herda BaseFlow — _step(), _dado(), _coord(), _tpl_existe(), _focar_si3() removidos
  - dados.get("chave", "DEFAULT") em campos obrigatorios substituidos por _dado()
  - campos opcionais (obs, declarante, especialidade) mantidos com .get() + default
  - ctx=ctx adicionado em todos os _step() calls
  - description propagada automaticamente pelo BaseFlow._step()

v0.5.15 — AB02 (12/06/2026):
  - Contrato paciente_id seguindo o mesmo padrao de si3_internacao:
    ${SI3_PACIENTE_ID:-} preenchido no .env -> usa ctx.config.PACIENTE_ID
    (permite rodar admissao standalone sem depender de estado_jornada.json)
    vazio -> le _ler_estado("paciente_id") (fluxo normal da jornada completa)
  - BUGFIX: uma edicao anterior havia removido o bloco de clique+type_text
    do AB02, fazendo o step "passar" em ~70ms sem digitar nada no campo
    Identificador — falso positivo corrigido restaurando o bloco.

v0.5.22 — ocr_lido (01/07/2026):
  - _ocr = [None] movido para escopo do metodo em AB06-AB11
  - step.ocr_lido = _ocr[0] apos _step() retornar — padrao AB15 propagado

v0.5.23 — LOV aleatorio (item 3 do roadmap, 01/07/2026):
  - cenario_provedor: 'aleatorio' — escolhe aleatoriamente de cenarios_validos
  - AB06: random.choice(dados['unidades_validas']) em vez de valor unico fixo
  - AB12: random.choice(procedimentos) — 1 procedimento por execucao
  - Interface identica ao definitivo (DatabaseRunner) — so muda a fonte dos dados
  - Nenhum valor unico de dominio de LOV fixo neste flow

v0.5.25 — pyjab no AB07 (03/07/2026):
  - Guard de popup (_assert_tela_limpa) TENTADO e ABANDONADO nesta sessao —
    deu falso positivo numa tela sem popup nenhum (score 0.886 no titulo
    'HC - INCOR' contra uma tela normal do SI3). Template de baixa textura
    + ajuste 'equalize' e instavel demais para servir de guard estrutural.
    NENHUMA chamada de guard neste arquivo — decisao explicita, nao
    esquecimento (ver regra 25: popups sao ancoragens frageis).
  - AB07 (Provedor/Plano) ganha verificacao estrutural via pyjab, EM
    PARALELO ao OCR ja existente (_verify_campo_obrigatorio/_opcional).
    Le o valor REAL do campo via Java Access Bridge — pega o caso de
    match parcial silencioso em LOV (ex: 'PROVEDOR_INVALIDO_XYZ' virar
    'PALMEIRAS' sem popup nenhum, tela aparentando limpa). Conexao do
    JABDriver e sob demanda (primeira vez que o AB07 precisar), cacheada
    em ctx.jab — nao reconecta a cada verificacao.

v0.5.25 — fix _fechar_popups_convenio (03/07/2026):
  - BUGFIX real, nao cosmetico: btn_ok_convenio.png (350x100px) incluia
    a mensagem do popup no recorte — quebra quando a mensagem muda
    ("Webservice nao cadastrado" vs "Neste momento nao foi possivel
    verificar"). Score medido contra popup real: 0.4969 (bem abaixo do
    threshold 0.75) — falha silenciosa que deixou popup aberto por
    varios steps, contaminando AB08/AB09/AB10 com OCR lendo o texto
    do popup em vez dos campos reais.
  - Corrigido com btn_sim_convenio.png — recorte apertado (52x24px, so
    o botao). Score medido: 0.816, estavel em 5/5 metodos de
    pre-processamento, mesma posicao (1030,585) em todos.
  - Clique trocado de coordenada absoluta fixa para clique via template
    (safe_click) — elimina dependencia de posicao fixa, que poderia
    desalinhar se o dialog do Windows redimensionar conforme o tamanho
    da mensagem (regra 20).
"""

import os
import random
import re
import time

import pyautogui

from src.core.context import FlowContext
from src.core.estado_jornada import ler as _ler_estado, salvar as _salvar_estado
from src.core.result import FlowResult
from src.flows.base_flow import BaseFlow
from src.vision.ocr import OcrHelper


class AdmissaoAmbulatorioFlow(BaseFlow):

    FLOW_NAME = "AdmissaoAmbulatorioFlow"
    _TPL = "templates/si3/admissao_ambulatorio"
    # Regiao do Nr Admissao agora vem do config (regioes_ocr.nr_admissao_amb),
    # nao mais hardcoded — padrao do projeto: coordenadas no YAML.

    # ----------------------------------------------------------------
    # execute
    # ----------------------------------------------------------------

    def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas
        dados  = self._resolver_cenario_provedor(ctx, dados)

        steps = [
            lambda: self._step_abrir_ambulatorio(ctx, observer),
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
            lambda: self._step_salvar(ctx, observer),
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
    # Helpers privados especificos deste flow
    # ----------------------------------------------------------------

    def _obter_provedores_validos(self, ctx) -> dict | None:
        """
        EXCECAO DOCUMENTADA ao padrao generico _obter_via_banco_ou_yaml
        (BaseFlow): provedor nao e uma lista simples de valores — e um
        PAR provedor+plano, e o cenario correspondente no YAML carrega
        alem disso carteirinha/validade (dado de teste, nao existe nas
        tabelas de dominio do SI3). Por isso tem logica propria aqui,
        em vez de usar o helper generico.

        Retorna {provedor: plano} vindos do banco, ou None se o banco
        nao conectou/nao retornou nada (quem chama decide o fallback
        para cenarios_provedor do YAML — regra 34, WARNING explicito).
        Nome de tabela/coluna provisorio (SI3_PROVEDORES/PRV_NOME/
        PRV_PLANO/PRV_ATIVO) — ajustar quando confirmado.
        """
        self._conectar_db(ctx)
        if getattr(ctx, "db", None):
            try:
                linhas = ctx.db.query(
                    "SELECT PRV_NOME, PRV_PLANO FROM SI3_PROVEDORES WHERE PRV_ATIVO = 1"
                )
                pares = {l["PRV_NOME"]: l["PRV_PLANO"] for l in linhas}
                if pares:
                    print(f"[AB07] provedores via DatabaseRunner ({len(pares)} opcoes)")
                    return pares
                print("[AB07] WARNING: DatabaseRunner retornou lista vazia — usando fallback YAML.")
            except Exception as e:
                print(f"[AB07] WARNING: DatabaseRunner indisponivel ({e}) — usando fallback YAML.")
        return None

    def _resolver_cenario_provedor(self, ctx, dados: dict) -> dict:
        """Resolve o cenario ativo de provedor — sobrescreve provedor/plano/carteirinha.

        cenario_provedor: 'aleatorio' -> banco decide QUAL provedor/plano
        usar (fonte de verdade de dominio), localizando depois o cenario
        do YAML com o MESMO provedor — para herdar carteirinha/validade
        corretas (dado de teste que nao existe no banco de provedores
        ativos). Se o banco nao conectar, ou o provedor sorteado nao
        tiver cenario YAML correspondente (sem carteirinha/validade),
        cai para o fallback aleatorio original (sorteio direto de
        cenarios_validos) — sempre com WARNING explicito (regra 34).
        """
        cenario_key = dados.get("cenario_provedor", "convenio_allianz")
        cenarios    = dados.get("cenarios_provedor", {})

        if cenario_key == "aleatorio":
            pares_db = self._obter_provedores_validos(ctx)
            cenario_key = None
            if pares_db:
                provedor_escolhido = random.choice(list(pares_db.keys()))
                cenario_key = next(
                    (k for k, v in cenarios.items()
                     if v.get("provedor") == provedor_escolhido),
                    None,
                )
                if cenario_key:
                    print(f"[AB] provedor via banco: '{provedor_escolhido}' "
                          f"-> cenario YAML correspondente: '{cenario_key}'")
                else:
                    print(f"[AB] WARNING: provedor '{provedor_escolhido}' do banco "
                          f"nao tem cenario correspondente no YAML (sem carteirinha/"
                          f"validade) — usando fallback aleatorio do YAML.")

            if not cenario_key:
                # Rotaciona entre os cenarios listados em cenarios_validos.
                # Fallback: todos os cenarios definidos em cenarios_provedor.
                cenarios_validos = dados.get("cenarios_validos") or list(cenarios.keys())
                cenario_key = random.choice(cenarios_validos)
                print(f"[AB] cenario_provedor: 'aleatorio' (fallback YAML) → escolhido: '{cenario_key}'")

        cenario = cenarios.get(cenario_key, {})
        if not cenario:
            print(f"[WARNING] cenario_provedor '{cenario_key}' nao encontrado — usando dados base")
        merged = {**dados, **cenario}
        print(f"[AB] cenario_provedor ativo: '{cenario_key}' — provedor: {merged.get('provedor')}")
        return merged

    def _fechar_popups_convenio(self, ctx) -> bool:
        """
        Detecta popup de elegibilidade de convenio e clica em Sim.

        v0.5.25 (03/07): template trocado de btn_ok_convenio.png (350x100px —
        pegava icone + mensagem + os 2 botoes juntos, score medido 0.4969
        contra popup real, MUITO abaixo do threshold) para btn_sim_convenio.png
        (recorte apertado 52x24px, so o botao — score medido 0.816, estavel
        em 5/5 metodos de pre-processamento, mesma posicao em todos).
        Causa raiz do score baixo do template antigo: a mensagem do popup
        muda conforme o motivo da falha de elegibilidade ("Webservice nao
        cadastrado" vs "Neste momento nao foi possivel verificar"), e o
        template antigo incluia esse texto — quebra quando a mensagem muda,
        mesmo padrao ja visto e corrigido no titulo HC-INCOR e no botao OK
        generico dos popups internos.

        Clique agora via TEMPLATE (safe_click), nao mais via coordenada
        absoluta fixa — o botao pode deslocar de posicao se o dialog do
        Windows redimensionar conforme o tamanho da mensagem. Clicar onde
        o template foi de fato encontrado elimina essa dependencia de
        coordenada (regra 20 — evitar coordenada fixa quando ha alternativa).

        Retorna True se encontrou e fechou o popup.
        """
        encontrou = False
        for _ in range(3):
            try:
                achou = ctx.runner.wait_template(
                    f"{self._TPL}/btn_sim_convenio.png", timeout=2.0, threshold=0.75,
                )
                if achou:
                    ctx.runner.safe_click(f"{self._TPL}/btn_sim_convenio.png", threshold=0.75)
                    time.sleep(0.5)
                    encontrou = True
                else:
                    break
            except Exception:
                break
        return encontrou

    def _selecionar_via_lov(self, ctx, coords,
                             btn_lov: str, campo_localizar: str, termo: str,
                             btn_localizar: str, btn_ok: str,
                             duplo_clique_item: str = None) -> None:
        """Fluxo padrao de LOV."""
        x, y = self._coord(coords, btn_lov)
        pyautogui.click(x, y); time.sleep(1.5)
        x, y = self._coord(coords, campo_localizar)
        pyautogui.click(x, y); time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(termo); time.sleep(0.3)
        x, y = self._coord(coords, btn_localizar)
        pyautogui.click(x, y); time.sleep(1.5)
        if duplo_clique_item:
            x, y = self._coord(coords, duplo_clique_item)
            pyautogui.doubleClick(x, y); time.sleep(1.0)
        else:
            x, y = self._coord(coords, btn_ok)
            pyautogui.click(x, y); time.sleep(0.5)

    # ----------------------------------------------------------------
    # AB01 — Abrir modulo Ambulatorio
    # ----------------------------------------------------------------

    def _step_abrir_ambulatorio(self, ctx, observer=None):
        """
        Navegacao via 'Localizar no Menu' (padrao AI01 validado).
        Localizar no Menu -> digita AMBULATORIO -> Pesquisar -> Nao -> double_click.
        Confirma chegada pela tela de admissao (titulo_ambulatorio.png, unico).
        """
        def fn():
            termo = self._dado(ctx.config.DADOS, "termo_menu_amb", "AB01")
            self._focar_si3()

            coords = ctx.config.coordenadas
            x, y = self._coord(coords, "campo_localizar_menu")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(termo); time.sleep(0.3)

            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar_menu.png", threshold=0.7)
            time.sleep(1.0)

            # Popup "Continuar Busca?" -> Nao (condicional)
            tpl_nao = f"{self._TPL}/btn_nao_popup.png"
            if self._tpl_existe(tpl_nao) and ctx.runner.is_visible(tpl_nao, threshold=0.80):
                ctx.runner.safe_click(tpl_nao, threshold=0.80)
                time.sleep(0.5)

            # Double click no item Ambulatorio na arvore
            ctx.runner.double_click(f"{self._TPL}/menu_ambulatorio.png", threshold=0.7)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB01_ambulatorio.png")
        return self._step("AB01", "abrir modulo Ambulatorio via Localizar no Menu",
                          fn, observer,
                          confirm_template=f"{self._TPL}/titulo_ambulatorio.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB02 — Informar Identificador
    # ----------------------------------------------------------------

    def _step_informar_identificador(self, ctx, coords, observer=None):
        """
        Contrato paciente_id (v0.5.15, alinhado com si3_internacao):
          ${SI3_PACIENTE_ID:-} preenchido no .env -> usa ctx.config.PACIENTE_ID
            (permite rodar a admissao standalone, sem depender de
             estado_jornada.json — util para `vtae run --test
             admissao_com_agendamento_jornada` isolado)
          vazio -> le _ler_estado("paciente_id") (fluxo normal da jornada
            completa: cadastro -> agendamento -> admissao)
        """
        def fn():
            paciente_id_env = ctx.config.PACIENTE_ID
            if paciente_id_env:
                paciente_id = paciente_id_env
                print(f"[AB02] paciente_id via .env (SI3_PACIENTE_ID): {paciente_id}")
            else:
                paciente_id = _ler_estado("paciente_id")
                print(f"[AB02] paciente_id via estado_jornada.json: {paciente_id}")

            x, y = self._coord(coords, "campo_identificador_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(paciente_id); time.sleep(0.3)
            print(f"[AB02] Identificador digitado: {paciente_id}")
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB02_identificador.png")
        return self._step("AB02", "informar identificador do paciente", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB03 — Pesquisar
    # ----------------------------------------------------------------

    def _step_pesquisar(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_pesquisar.png", threshold=0.7)
            ctx.runner.wait_template(
                f"{self._TPL}/btn_admitir_paciente.png", timeout=10, threshold=0.7
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB03_pesquisa.png")
        return self._step("AB03", "pesquisar paciente",
                          fn, observer,
                          confirm_template=f"{self._TPL}/btn_admitir_paciente.png",
                          ctx=ctx)

    # ----------------------------------------------------------------
    # AB04 — Aba Enderecos: campo Tipo = RUA (sempre)
    # ----------------------------------------------------------------

    def _step_tipo_endereco(self, ctx, coords, observer=None):
        """
        Campo Tipo (RUA/AVENIDA) e obrigatorio para SUS — se ficar vazio, o SI3
        bloqueia a admissao com o popup da Portaria 257 no AB07.

        Estrategia: SEMPRE apagar o conteudo com BACKSPACE e digitar RUA. Este
        campo Tipo (com LOV anexado) NAO responde a selecao de texto — nem Ctrl+A
        nem Shift+Home limpam (geram concatenacao "RUARUA" e abrem o LOV de Tipos
        de Logradouro por valor invalido). O gesto correto, confirmado manualmente,
        e: clicar -> backspace ate limpar -> digitar -> Tab.
        Mandamos 20 backspaces (cobre qualquer Tipo; backspace em campo vazio nao
        faz nada, entao serve para os dois cenarios):
          - preenchido: backspace apaga o valor antigo, digita RUA
          - vazio: backspace nao tem efeito, digita RUA
        Sem OCR (que lia errado em campo de ~14px e gerava falso "ja preenchido").

        DIVIDA TECNICA CONSCIENTE (10/06/2026): preencher RUA fixo remove a
        variabilidade do Tipo. Para exercitar cenarios reais (viela/avenida/
        vazio->popup), promover para `tipo_endereco` no config.yaml ou um bloco
        `cenarios_endereco`. Deteccao robusta de campo virа com o YOLO (Fase 6).
        """
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/aba_enderecos.png", threshold=0.7)
            time.sleep(0.5)
            self._focar_si3()
            x, y = self._coord(coords, "campo_tipo_endereco_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.press("backspace", presses=20, interval=0.02)  # apaga conteudo
            ctx.runner.type_text("RUA")
            pyautogui.press("tab"); time.sleep(0.5)
            pyautogui.hotkey("ctrl", "s"); time.sleep(1.5)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB04_tipo_endereco.png")
        return self._step("AB04", "aba Enderecos — campo Tipo = RUA",
                          fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB05 — Admitir Paciente
    # ----------------------------------------------------------------

    def _step_admitir_paciente(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_admitir_paciente.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB05_admitir.png")
        return self._step("AB05", "clicar em Admitir Paciente", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB06 — Unidade Funcional
    # ----------------------------------------------------------------

    def _step_unidade_funcional(self, ctx, dados: dict, observer=None):
        _ocr = [None]
        def fn():
            # Padrao generico de fallback banco->YAML (BaseFlow) — mesmo
            # helper reutilizado por qualquer campo LOV com lista simples.
            # Nome de tabela/coluna provisorio (SI3_UNIDADES/UNI_NOME/
            # UNI_ATIVA) — ajustar quando confirmado.
            unidades = self._obter_via_banco_ou_yaml(
                ctx, dados, "AB06",
                sql="SELECT UNI_NOME FROM SI3_UNIDADES WHERE UNI_ATIVA = 1",
                coluna="UNI_NOME",
                chave_yaml="unidades_validas",
            )
            if not unidades:
                raise AssertionError(
                    "[AB06] Nenhuma unidade valida disponivel (banco e YAML "
                    "ambos vazios/indisponiveis). Adicionar lista em "
                    "dados.unidades_validas."
                )
            valor = random.choice(unidades)
            print(f"[AB06] unidade escolhida: '{valor}' (de {len(unidades)} opcoes)")
            ctx.runner.click_near(
                f"{self._TPL}/campo_unidade_funcional.png",
                offset_x=200, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(valor)
            pyautogui.press("tab"); time.sleep(0.5)
            pyautogui.press("tab"); time.sleep(0.5)
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB06_unidade.png")
            self._verify_campo_obrigatorio(ctx, "unidade_funcional", valor,
                                           "AB06", "campo_unidade_funcional", _ocr)
            return screenshot_path
        step = self._step("AB06", "preencher Unidade Funcional", fn, observer,
                          validated=True, ctx=ctx)
        if step.success:
            step.ocr_lido = _ocr[0] if _ocr[0] is not None else ''
        return step

    # ----------------------------------------------------------------
    # AB07 — Provedor / Plano
    # ----------------------------------------------------------------

    def _step_provedor_plano(self, ctx, dados: dict, observer=None):
        _ocr_prov  = [None]
        _ocr_plano = [None]
        def fn():
            provedor = self._dado(dados, "provedor", "AB07")
            plano    = self._dado(dados, "plano", "AB07")
            ctx.runner.click_near(
                f"{self._TPL}/campo_provedor.png", offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(provedor)
            pyautogui.press("tab"); time.sleep(0.5)
            ctx.runner.click_near(
                f"{self._TPL}/campo_plano.png", offset_x=150, offset_y=0, threshold=0.65
            )
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(plano)
            pyautogui.press("tab"); time.sleep(0.5)
            if self._fechar_popups_convenio(ctx):
                print("[AB07] Popup de convenio fechado")
            if provedor not in ("SUS", "PARTICULAR", "INCOR SIS"):
                carteirinha = dados.get("numero_carteirinha", "")
                validade    = dados.get("validade_carteirinha", "")
                if carteirinha:
                    ctx.runner.click_near(
                        f"{self._TPL}/campo_numero_carteirinha.png",
                        offset_x=100, offset_y=0, threshold=0.65
                    )
                    pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(carteirinha)
                    pyautogui.press("tab"); time.sleep(1.5)
                    if self._fechar_popups_convenio(ctx):
                        print("[AB07] Popup pos-carteirinha fechado")
                        time.sleep(1.0)  # aguarda popup fechar completamente
                if validade:
                    ctx.runner.click_near(
                        f"{self._TPL}/campo_validade_carteirinha.png",
                        offset_x=100, offset_y=0, threshold=0.65
                    )
                    pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(validade)
                    pyautogui.press("tab"); time.sleep(0.5)
                    # Popup pos-validade: SI3 dispara verificacao ao sair da validade.
                    if self._fechar_popups_convenio(ctx):
                        print("[AB07] Popup pos-validade fechado")
                        time.sleep(1.0)  # aguarda popup fechar completamente
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB07_provedor.png")
            self._verify_campo_obrigatorio(ctx, "provedor", provedor,
                                           "AB07", "campo_provedor", _ocr_prov)
            # Plano usa _opcional: nomes longos (ex: 'CORPORATIVO COMPLETO - APARTAMENTO')
            # excedem a capacidade de leitura confiavel do EasyOCR nessa regiao (242x20px).
            # Provedor ja valida que o preenchimento ocorreu — plano registra o lido sem parar.
            self._verify_campo_opcional(ctx, "plano", plano,
                                        "AB07", "campo_plano", _ocr_plano)

            # v0.5.25 — verificacao estrutural via pyjab (paralela ao OCR acima).
            # Pega match parcial silencioso em LOV que o OCR nao detecta
            # (Medicao 3, 03/07 — caso real PALMEIRAS/BASICO). Conexao sob
            # demanda, cacheada em ctx.jab — nao reconecta a cada verificacao.
            if not ctx.jab:
                try:
                    # JAVA_HOME de mentira (lado cliente pyjab) — vem do .env
                    # via config, nao de setx (setx exige terminal novo e some
                    # se o terminal ja estava aberto antes do comando). So
                    # localiza a WindowsAccessBridge-64.dll; nao toca no Java
                    # real do SI3 nem no JAVA_HOME do sistema. Precisa ser
                    # setado ANTES do import pyjab (a DLL e procurada no import).
                    _jab_home = ctx.config.DADOS.get("jab_home_fake")
                    if _jab_home:
                        os.environ["JAVA_HOME"] = _jab_home
                    from pyjab.jabdriver import JABDriver
                    ctx.jab = JABDriver(title='AMBULATÓRIO')
                except Exception as e:
                    print(f"[AB07] AVISO: JABDriver nao conectou — "
                          f"verificacao pyjab pulada nesta execucao: {e}")
            _jab_prov  = [None]
            _jab_plano = [None]
            self._verify_campo_via_jab(ctx, 'Descrição do provedor.', provedor,
                                       "AB07", _jab_prov)
            self._verify_campo_via_jab(ctx, 'Nome do Plano.', plano,
                                       "AB07", _jab_plano)

            return screenshot_path
        step = self._step("AB07", "preencher Provedor e Plano", fn, observer,
                          validated=True, ctx=ctx)
        if step.success:
            step.ocr_lido = (
                f"provedor={_ocr_prov[0] or ''} "
                f"plano={_ocr_plano[0] or ''}"
            )
        return step

    # ----------------------------------------------------------------
    # AB08 — Declarante / Especialidade
    # ----------------------------------------------------------------

    def _step_declarante_especialidade(self, ctx, dados: dict, coords, observer=None):
        _ocr_dec = [None]
        _ocr_esp = [None]
        def fn():
            # declarante e especialidade sao opcionais — fallback definido no config.yaml
            declarante    = dados.get("declarante",    "TESTE AUTOMATIZADO")
            especialidade = dados.get("especialidade", "CAR - CARDIO GERAL")
            x, y = self._coord(coords, "campo_declarante")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(declarante)
            pyautogui.press("tab"); time.sleep(0.3)
            x, y = self._coord(coords, "campo_especialidade")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(especialidade)
            pyautogui.press("tab"); time.sleep(0.3)
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB08_declarante.png")
            self._verify_campo_opcional(ctx, "declarante", declarante,
                                        "AB08", "campo_declarante_ocr", _ocr_dec)
            self._verify_campo_opcional(ctx, "especialidade", especialidade,
                                        "AB08", "campo_especialidade_ocr", _ocr_esp)
            return screenshot_path
        step = self._step("AB08", "preencher Declarante e Especialidade",
                          fn, observer, ctx=ctx)
        if step.success:
            step.ocr_lido = (
                f"declarante={_ocr_dec[0] or ''} "
                f"especialidade={_ocr_esp[0] or ''}"
            )
        return step

    # ----------------------------------------------------------------
    # AB09 — Obs
    # ----------------------------------------------------------------

    def _step_obs(self, ctx, dados: dict, coords, observer=None):
        _ocr_obs = [None]
        def fn():
            valor = dados.get("obs", "ADMISSAO REALIZADA COM FERRAMENTA DE AUTOMACAO DE TESTES")
            x, y = self._coord(coords, "campo_obs_amb")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(valor); time.sleep(0.3)
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB09_obs.png")
            self._verify_campo_opcional(ctx, "obs", valor,
                                        "AB09", "campo_obs_ocr", _ocr_obs)
            return screenshot_path
        step = self._step("AB09", "preencher campo Obs", fn, observer, ctx=ctx)
        if step.success:
            step.ocr_lido = _ocr_obs[0] if _ocr_obs[0] is not None else ''
        return step

    # ----------------------------------------------------------------
    # AB10 — Origem do Paciente
    # ----------------------------------------------------------------

    def _step_origem_paciente(self, ctx, dados: dict, coords, observer=None):
        _ocr_orig = [None]
        def fn():
            tipo = self._dado(dados, "origem_tipo", "AB10")
            x, y = self._coord(coords, "campo_origem_tipo")
            pyautogui.click(x, y); time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(tipo)
            pyautogui.press("tab"); time.sleep(1.0)
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB10_origem.png")
            self._verify_campo_obrigatorio(ctx, "origem_tipo", tipo,
                                           "AB10", "campo_origem_tipo_ocr", _ocr_orig)
            return screenshot_path
        step = self._step("AB10", "preencher Origem do Paciente", fn, observer,
                          validated=True, ctx=ctx)
        if step.success:
            step.ocr_lido = _ocr_orig[0] if _ocr_orig[0] is not None else ''
        return step

    # ----------------------------------------------------------------
    # AB11 — Medico Responsavel via LOV
    # ----------------------------------------------------------------

    def _step_medico_responsavel(self, ctx, coords, observer=None):
        _ocr_med = [None]
        def fn():
            self._selecionar_via_lov(
                ctx, coords,
                btn_lov="btn_lov_medico",
                campo_localizar="campo_localizar_medico",
                termo="%medico",
                btn_localizar="btn_localizar_medico",
                btn_ok="btn_localizar_medico",
                duplo_clique_item="item_profissional_proc",
            )
            time.sleep(1.5)
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB11_medico.png")
            self._verify_campo_obrigatorio(ctx, "medico_responsavel", "MEDICO",
                                           "AB11", "campo_medico_nome_ocr", _ocr_med)
            return screenshot_path
        step = self._step("AB11", "selecionar Medico Responsavel via LOV",
                          fn, observer, validated=True, ctx=ctx)
        if step.success:
            step.ocr_lido = _ocr_med[0] if _ocr_med[0] is not None else ''
        return step
    # ----------------------------------------------------------------
    # AB12 — Lista de Procedimentos
    # ----------------------------------------------------------------

    def _step_lista_procedimentos(self, ctx, dados: dict, coords, observer=None):
        def fn():
            procedimentos = self._dado(dados, "procedimentos", "AB12")
            if not procedimentos:
                raise AssertionError(
                    "Nenhum procedimento configurado em dados.procedimentos no config.yaml."
                )
            # Escolhe 1 procedimento aleatorio — explora diferentes codigos entre execucoes.
            # Transitorio: lista no YAML. Definitivo: db.query('SELECT PRO_CODIGO FROM ...')
            proc = random.choice(procedimentos)
            codigo         = proc.get("codigo", "")
            complemento    = proc.get("complemento", "")
            area_executora = proc.get("area_executora", "")
            profissional   = proc.get("profissional", "MEDICO")
            print(f"[AB12] procedimento escolhido: '{codigo}' / complemento: '{complemento}' "
                  f"(de {len(procedimentos)} opcoes)")

            ctx.runner.safe_click(f"{self._TPL}/btn_lista_procedimentos.png", threshold=0.7)
            time.sleep(1.5)

            self._selecionar_via_lov(
                ctx, coords,
                btn_lov="btn_lov_codigo_proc",
                campo_localizar="campo_localizar_proc",
                termo=codigo,
                btn_localizar="btn_localizar_proc",
                btn_ok="btn_ok_proc",
            )
            time.sleep(0.5)

            area_para_digitar = area_executora.strip()
            if area_para_digitar:
                x, y = self._coord(coords, "campo_localizar_area")
                pyautogui.click(x, y); time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a"); ctx.runner.type_text(area_para_digitar)
                x, y = self._coord(coords, "btn_localizar_area")
                pyautogui.click(x, y); time.sleep(1.0)
            x, y = self._coord(coords, "btn_ok_area_executora")
            pyautogui.click(x, y); time.sleep(0.5)
            pyautogui.press("tab"); time.sleep(0.3)
            pyautogui.press("tab"); time.sleep(0.3)

            if complemento:
                self._selecionar_via_lov(
                    ctx, coords,
                    btn_lov="btn_lov_complemento",
                    campo_localizar="campo_localizar_complemento",
                    termo=complemento,
                    btn_localizar="btn_localizar_complemento",
                    btn_ok="btn_ok_complemento",
                )
                time.sleep(0.5)

            # Profissional: seleciona via LOV — campo nao aceita digitacao direta
            self._selecionar_via_lov(
                ctx, coords,
                btn_lov="btn_lov_profissional_proc",
                campo_localizar="campo_localizar_profissional",
                termo=profissional,
                btn_localizar="btn_localizar_profissional",
                btn_ok="btn_ok_profissional",
            )
            time.sleep(0.5)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB12_procedimentos.png")
        return self._step("AB12", "preencher Lista de Procedimentos", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB13 — Voltar
    # ----------------------------------------------------------------

    def _step_voltar(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_voltar.png", threshold=0.7)
            time.sleep(2.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB13_voltar.png")
        return self._step("AB13", "clicar em Voltar", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB14 — Salvar admissao (F10)
    # ----------------------------------------------------------------

    def _step_salvar(self, ctx, observer=None):
        """
        Persiste a admissao na tela principal (apos Voltar) via F10.
        Sem este passo o Oracle Forms nao grava e o Nr. Admissao nao e gerado
        — era a causa do AB14 (agora AB15) ler ''.
        F10 confirmado manualmente (10/06/2026). Botao Salvar (disquete) e
        alternativa mais rapida — trocar por template no futuro se a latencia
        do F10 incomodar.
        """
        def fn():
            self._focar_si3()
            pyautogui.hotkey("f10"); time.sleep(3.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB14_salvar.png")
        return self._step("AB14", "salvar admissao (F10)", fn, observer, ctx=ctx)

    # ----------------------------------------------------------------
    # AB15 — Validar Nr Admissao via OCR
    # ----------------------------------------------------------------

    def _step_validar_admissao(self, ctx, observer=None):
        """
        Validacao final: OCR le o Nr Admissao na tela (apos salvar no AB14).
        Regiao vem do config (regioes_ocr.nr_admissao_amb) — nunca hardcoded,
        para o time calibrar sem tocar no codigo (padrao do projeto, igual AI19).
        Modo bootstrap: se a regiao estiver zerada {0,0,0,0}, avisa e passa.
        Calibrada: falha se nao encontrar numero.
        Regiao validada 11/06/2026: {x1:35,y1:131,x2:136,y2:155} le '00234746'.
        """
        _ocr = [None]
        def fn():
            regiao = ctx.config.regioes_ocr.get("nr_admissao_amb")
            # Aguarda tela carregar completamente antes de tirar screenshot
            # — evita OCR ler vazio quando servidor esta lento (bug 12/06/2026)
            ctx.runner.wait_template(
                f"{self._TPL}/titulo_ambulatorio.png",
                timeout=15,
                threshold=0.75,
            )
            screenshot_path = ctx.runner.screenshot(f"{ctx.evidence_dir}AB15_validacao.png")

            if not regiao or not (regiao["x1"] or regiao["y1"]
                                  or regiao["x2"] or regiao["y2"]):
                print("[AB15] AVISO: regioes_ocr.nr_admissao_amb nao calibrado — "
                      "validacao pulada (modo bootstrap). Calibrar apos 1a execucao.")
                return screenshot_path

            regiao_tupla = (regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"])
            OcrHelper.salvar_debug(
                screenshot_path, regiao_tupla,
                f"{ctx.evidence_dir}AB15_ocr_debug.png"
            )
            texto   = OcrHelper.ler_regiao(screenshot_path, regiao_tupla)
            numeros = re.findall(r"\d+", texto)
            if not numeros:
                raise AssertionError(
                    f"Nr Admissao nao encontrado — admissao pode ter falhado.\n"
                    f"Texto lido: '{texto}'\n"
                    f"Veja AB15_ocr_debug.png e ajuste regioes_ocr.nr_admissao_amb."
                )
            # pega o numero mais longo — evita capturar '2' ou '26' da mesma regiao
            nr_admissao = max(numeros, key=len)
            _ocr[0] = nr_admissao
            print(f"[AB15] Nr Admissao Ambulatorio: {nr_admissao}")
            _salvar_estado("nr_admissao_amb", nr_admissao)
            return screenshot_path
        step = self._step("AB15", "validar Nr Admissao via OCR",
                          fn, observer, validated=True, ctx=ctx)
        if step.success:
            step.ocr_lido = _ocr[0] if _ocr[0] is not None else ''
        return step

    # ----------------------------------------------------------------
    # AB16 — Sair
    # ----------------------------------------------------------------

    def _step_sair(self, ctx, observer=None):
        def fn():
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.5)
            ctx.runner.safe_click(f"{self._TPL}/btn_sair.png", threshold=0.7)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}AB16_sair.png")
        return self._step("AB16", "sair para Menu Principal", fn, observer, ctx=ctx)