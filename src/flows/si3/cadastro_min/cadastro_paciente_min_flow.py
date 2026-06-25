# src/flows/si3/cadastro_min/cadastro_paciente_min_flow.py
"""
CadastroPacienteMinFlow — Cadastro minimo de paciente no SI3 (Oracle Forms).

Presupoe que o login ja foi executado via LoginSi3Flow.

Steps:
    CM01  Abrir modulo via Localizar no Menu
    CM02  Pesquisar nome (tela Parametros de Pesquisa)
    CM03  Clicar Novo (tela Pacientes — lista)
    CM04  Preencher Nome (formulario)
    CM05  Preencher Data Nascimento + Hora
    CM06  Preencher Sexo (LOV — selecao aleatoria)
    CM07  Preencher Nacionalidade (LOV — selecao aleatoria, 3 caminhos)
    CM08  Preencher Cor/Etnia (LOV — selecao aleatoria)
    CM09  Gerar Matricula + Salvar (F10) + OCR matricula/identificador
    CM10  Sair para o Menu Principal

Padrao LOV com lista (Pais/Estado/Cidade) — CM07:
    1. Clicar campo -> F9 -> LOV abre
    2. Clicar campo Localizar da LOV (campo_localizar_lov)
    3. Limpar + digitar valor sorteado -> LOV filtra para 1 resultado
    4. Clicar OK da LOV
    Este padrao garante selecao aleatoria real e elimina dependencia
    do primeiro item da lista. Mesma logica para todos os 3 popups.

Cenario negativo (observabilidade):
    config.yaml: cenario: negativo
    Listas de valores invalidos comentadas no config — descomentar para ativar.
    O flow digita o valor invalido -> Oracle Forms mostra HC-INCOR ->
    _verificar_popup_erro_incor() detecta via template e falha com AssertionError.

Contrato de classificacao de campo (Fase 1):
    CM04 Nome          — Obrigatorio (_verify_campo_obrigatorio)
    CM05 Data Nasc     — Obrigatorio (verificacao por estrutura — min 6 digitos)
    CM06 Sexo          — Obrigatorio (_verify_campo_obrigatorio)
    CM07 Nacionalidade — Obrigatorio (_verify_campo_obrigatorio)
    CM08 Cor/Etnia     — Opcional    (_verify_campo_opcional)
    CM09 Matricula     — Obrigatorio (OCR direto — AssertionError se vazio)
    CM10 Sair          — sem verificacao OCR
"""

import random
import re
import time

import pyautogui
from faker import Faker

from src.core.estado_jornada import salvar as _salvar_estado_jornada
from src.core.result import FlowResult, StepResult
from src.flows.base_flow import BaseFlow
from src.vision.ocr import OcrHelper

_fake_br = Faker("pt_BR")

# Template do popup HC-INCOR — modal interno Oracle Forms sem handle proprio
# Deteccao via is_visible — pygetwindow nao enxerga este popup
_TPL_ERRO_INCOR = "templates/si3/cadastro_paciente_min/popup_erro_incor.png"


class CadastroPacienteMinFlow(BaseFlow):
    FLOW_NAME = "CadastroPacienteMinFlow"
    _TPL = "templates/si3/cadastro_paciente_min"

    def execute(self, ctx, dados: dict = None, observer=None) -> FlowResult:
        result = FlowResult(flow_name=self.FLOW_NAME)
        coords = ctx.config.coordenadas

        for step_fn in [
            lambda: self._step_cm01_abrir(ctx, coords, observer),
            lambda: self._step_cm02_pesquisar(ctx, dados, coords, observer),
            lambda: self._step_cm03_novo(ctx, coords, observer),
            lambda: self._step_cm04_nome(ctx, dados, coords, observer),
            lambda: self._step_cm05_data_nascimento(ctx, dados, coords, observer),
            lambda: self._step_cm06_sexo(ctx, dados, coords, observer),
            lambda: self._step_cm07_nacionalidade(ctx, dados, coords, observer),
            lambda: self._step_cm08_cor_etnia(ctx, dados, coords, observer),
            lambda: self._step_cm09_gerar_matricula(ctx, observer),
            lambda: self._step_cm10_sair(ctx, coords, observer),
        ]:
            step = step_fn()
            result.steps.append(step)
            if not step.success:
                break  # abort-on-failure — sempre

        ctx.add_result(result)
        if observer:
            observer.log_flow_result(result)
        return result

    # ------------------------------------------------------------------
    # CM01 — Abrir modulo via Localizar no Menu
    # ------------------------------------------------------------------
    def _step_cm01_abrir(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            self._focar_si3()

            import pygetwindow as gw
            janelas = gw.getWindowsWithTitle("Menu Principal")
            if janelas:
                janelas[0].maximize()
                time.sleep(0.9)

            x, y = self._coord(coords, "campo_localizar_menu")
            pyautogui.click(x, y)
            time.sleep(1.5)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text("CADASTRO DE PACIENTE")
            time.sleep(0.9)

            x, y = self._coord(coords, "btn_pesquisar_menu")
            pyautogui.click(x, y)
            time.sleep(1.5)

            x, y = self._coord(coords, "btn_nao_popup")
            pyautogui.click(x, y)
            time.sleep(1.0)

            x, y = self._coord(coords, "menu_cadastro_paciente")
            pyautogui.doubleClick(x, y)
            time.sleep(1.0)

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CM01_abrir.png")

        return self._step(
            "CM01", "abrir Cadastro de Pacientes via Localizar no Menu",
            fn, observer,
            confirm_template=f"{self._TPL}/campo_nome_pesquisa.png",
            ctx=ctx,
        )

    # ------------------------------------------------------------------
    # CM02 — Pesquisar nome (tela Parametros de Pesquisa)
    # ------------------------------------------------------------------
    def _step_cm02_pesquisar(self, ctx, dados, coords, observer=None) -> StepResult:
        def fn():
            nome = self._dado(dados, "nome", "CM02")

            x, y = self._coord(coords, "campo_nome_pesquisa")
            pyautogui.click(x, y)
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")
            ctx.runner.type_text(nome)
            time.sleep(0.5)

            x, y = self._coord(coords, "btn_pesquisar_params")
            pyautogui.click(x, y)
            time.sleep(2.5)

            confirmado = self._aguardar_titulo_janela(
                "Cadastro De Pacientes", timeout=15.0
            )
            if not confirmado:
                raise AssertionError(
                    "[CM02] Tela de lista de pacientes nao carregou — "
                    "titulo 'Cadastro De Pacientes' nao encontrado em 15s."
                )

            return ctx.runner.screenshot(f"{ctx.evidence_dir}CM02_pesquisar.png")

        return self._step(
            "CM02", "pesquisar paciente na tela Parametros de Pesquisa",
            fn, observer, ctx=ctx,
        )

    # ------------------------------------------------------------------
    # CM03 — Clicar Novo (tela Pacientes — lista)
    # ------------------------------------------------------------------
    def _step_cm03_novo(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            x, y = self._coord(coords, "btn_novo_lista")
            pyautogui.click(x, y)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CM03_novo.png")

        return self._step(
            "CM03", "clicar em Novo na tela de lista de pacientes",
            fn, observer,
            confirm_template=f"{self._TPL}/campo_nome_social.png",
            ctx=ctx,
        )

    # ------------------------------------------------------------------
    # CM04 — Validar Nome (obrigatorio)
    # Calibrado: x1:27 y1:145 x2:447 y2:168
    # ------------------------------------------------------------------
    def _step_cm04_nome(self, ctx, dados, coords, observer=None) -> StepResult:
        _ocr = [None]

        def fn():
            nome = self._dado(dados, "nome", "CM04")
            time.sleep(0.3)
            self._verify_campo_obrigatorio(
                ctx, "nome", nome, "CM04", "campo_nome", _ocr
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CM04_nome.png")

        step = self._step(
            "CM04", "validar Nome pre-preenchido (obrigatorio)",
            fn, observer, validated=True, ctx=ctx,
        )
        if step.success and _ocr[0]:
            step.ocr_lido = _ocr[0]
        return step

    # ------------------------------------------------------------------
    # CM05 — Preencher Data Nascimento + Hora (obrigatorio)
    # Verificacao por estrutura, nao por valor exato:
    # O Oracle Forms reformata DDMMYYYY -> DD/MM/YYYY na exibicao.
    # O EasyOCR adiciona ruido nos digitos extremos (ex: 2->9, 2->7).
    # Comparar o valor digitado com o exibido e fragil por design —
    # campos com reformatacao automatica e mascara nunca devem usar
    # _verify_campo_obrigatorio com valor exato.
    # A prova correta e: o campo tem pelo menos 6 digitos apos o preenchimento.
    # Um campo vazio le '' ou ruido sem digitos. Uma data valida tem 8 digitos.
    # Calibrado: x1:363 y1:195 x2:463 y2:207
    # ------------------------------------------------------------------
    def _step_cm05_data_nascimento(self, ctx, dados, coords, observer=None) -> StepResult:
        _ocr = [None]

        def fn():
            data_raw = self._dado(dados, "data_nascimento", "CM05")

            if len(data_raw) == 8 and data_raw.isdigit():
                data_digitos = data_raw[6:8] + data_raw[4:6] + data_raw[0:4]
            else:
                data_digitos = data_raw.replace("/", "").replace("-", "")

            x, y = self._coord(coords, "campo_data_nasc")
            pyautogui.click(x, y)
            time.sleep(0.5)
            pyautogui.press("backspace", presses=10, interval=0.02)
            ctx.runner.type_text(data_digitos)
            time.sleep(0.3)

            x, y = self._coord(coords, "campo_hora")
            pyautogui.click(x, y)
            time.sleep(0.3)
            pyautogui.press("backspace", presses=6, interval=0.02)
            ctx.runner.type_text("0000")
            pyautogui.press("tab")
            time.sleep(0.3)

            # Verificacao por estrutura — nao compara valor digitado vs exibido.
            # Oracle Forms reformata a entrada (DDMMYYYY -> DD/MM/YYYY) e o
            # EasyOCR adiciona ruido nos digitos extremos. O que importa e que
            # o campo tenha pelo menos 6 digitos — prova que foi preenchido.
            screenshot_path = ctx.runner.screenshot(
                f"{ctx.evidence_dir}CM05_data.png"
            )
            regiao = ctx.config.regioes_ocr.get("campo_data_nasc")
            if regiao and (regiao["x1"] or regiao["y1"] or regiao["x2"] or regiao["y2"]):
                regiao_tupla = (regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"])
                ok, lido = ctx.runner.verify_lov(
                    "data_nascimento", region=regiao_tupla, timeout=3.0
                )
                _ocr[0] = lido
                digitos = re.findall(r"\d", lido)
                if not ok or len(digitos) < 6:
                    raise AssertionError(
                        f"[CM05] Campo OBRIGATORIO 'data_nascimento' ficou vazio "
                        f"ou sem formato de data reconhecivel.\n"
                        f"OCR leu: '{lido}' ({len(digitos)} digitos encontrados, minimo 6)\n"
                        f"Verifique se a data foi aceita pelo sistema."
                    )
                print(f"[CM05] OK — 'data_nascimento' = '{lido}' ({len(digitos)} digitos)")
            else:
                print(f"[CM05] AVISO: regiao 'campo_data_nasc' nao calibrada — "
                      f"verificacao OBRIGATORIA pulada (bootstrap).")
            return screenshot_path

        step = self._step(
            "CM05", "preencher Data Nascimento + Hora (obrigatorio)",
            fn, observer, validated=True, ctx=ctx,
        )
        if step.success and _ocr[0]:
            step.ocr_lido = _ocr[0]
        return step

    # ------------------------------------------------------------------
    # CM06 — Preencher Sexo via LOV (obrigatorio — selecao aleatoria)
    # Fluxo: clicar campo -> digitar -> TAB -> clicar OK
    # Calibrado: x1:543 y1:192 x2:633 y2:212
    # ------------------------------------------------------------------
    def _step_cm06_sexo(self, ctx, dados, coords, observer=None) -> StepResult:
        _ocr = [None]

        def fn():
            opcoes = self._dado(dados, "sexo_opcoes", "CM06")
            sexo = random.choice(opcoes)

            x, y = self._coord(coords, "campo_sexo_lov")
            pyautogui.click(x, y)
            time.sleep(0.5)
            pyautogui.press("backspace", presses=10, interval=0.02)
            ctx.runner.type_text(sexo)
            time.sleep(0.3)
            pyautogui.press("tab")
            time.sleep(0.5)

            ok_tpl = f"{self._TPL}/btn_ok_lov.png"
            if self._tpl_existe(ok_tpl):
                ctx.runner.safe_click(ok_tpl, threshold=0.75)
            else:
                x, y = self._coord(coords, "btn_ok_lov")
                pyautogui.click(x, y)
            time.sleep(0.5)

            self._verify_campo_obrigatorio(
                ctx, "sexo", sexo, "CM06", "campo_sexo", _ocr
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CM06_sexo.png")

        step = self._step(
            "CM06", "preencher Sexo via LOV (obrigatorio — aleatorio)",
            fn, observer, validated=True, ctx=ctx,
        )
        if step.success and _ocr[0]:
            step.ocr_lido = _ocr[0]
        return step

    # ------------------------------------------------------------------
    # CM07 — Preencher Nacionalidade via LOV (obrigatorio — selecao aleatoria)
    #
    # Fluxo:
    #   1. btn_lov_nacionalidade -> lista de tipos
    #   2. Clicar item da lista -> btn_ok_lista_nac -> popup secundario
    #   3. Preencher popup com _selecionar_em_lov() para cada campo de lista
    #   4. btn_ok_popup_<tipo> -> tenta fechar popup
    #   5. _verificar_popup_erro_incor() — template matching
    #   6. _aguardar_popup_fechar("Nacionalidade")
    # ------------------------------------------------------------------
    def _step_cm07_nacionalidade(self, ctx, dados, coords, observer=None) -> StepResult:
        _ocr = [None]

        def fn():
            opcoes = self._dado(dados, "nacionalidade_opcoes", "CM07")
            nacionalidade = random.choice(opcoes)

            # 1. Abrir lista de tipos
            x, y = self._coord(coords, "btn_lov_nacionalidade")
            pyautogui.click(x, y)
            time.sleep(1.0)

            # 2. Clicar item + OK da lista
            if nacionalidade == "BRASILEIRO":
                x, y = self._coord(coords, "item_lista_brasileiro")
            elif nacionalidade == "ESTRANGEIRO":
                x, y = self._coord(coords, "item_lista_estrangeiro")
            else:
                x, y = self._coord(coords, "item_lista_naturalizado")
            pyautogui.click(x, y)
            time.sleep(0.3)

            x, y = self._coord(coords, "btn_ok_lista_nac")
            pyautogui.click(x, y)
            time.sleep(1.0)

            # 3. Preencher popup + clicar OK
            if nacionalidade == "BRASILEIRO":
                self._preencher_popup_brasileiro(ctx, coords, dados)
                x, y = self._coord(coords, "btn_ok_popup_brasileiro")
            elif nacionalidade == "ESTRANGEIRO":
                self._preencher_popup_estrangeiro(ctx, coords, dados)
                x, y = self._coord(coords, "btn_ok_popup_estrangeiro")
            else:
                self._preencher_popup_naturalizado(ctx, coords, dados)
                x, y = self._coord(coords, "btn_ok_popup_naturalizado")
            pyautogui.click(x, y)
            time.sleep(0.8)

            # 4. Verificar popup HC-INCOR via template matching
            self._verificar_popup_erro_incor(ctx, coords, nacionalidade)

            # 5. Aguardar popup de Nacionalidade fechar
            self._aguardar_popup_fechar("Nacionalidade", timeout=5.0)
            time.sleep(0.5)

            self._verify_campo_obrigatorio(
                ctx, "nacionalidade", nacionalidade, "CM07", "campo_nacionalidade", _ocr
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CM07_nacionalidade.png")

        step = self._step(
            "CM07", "preencher Nacionalidade via LOV (obrigatorio — aleatorio)",
            fn, observer, validated=True, ctx=ctx,
        )
        if step.success and _ocr[0]:
            step.ocr_lido = _ocr[0]
        return step

    def _selecionar_em_lov(self, ctx, coords, campo_coord: str,
                           btn_ok_coord: str, valor: str) -> None:
        """
        Padrao universal para selecionar um valor em qualquer LOV de lista.

        Fluxo:
          1. Clicar no campo -> F9 -> LOV abre
          2. Clicar no campo Localizar da LOV
          3. Limpar + digitar o valor sorteado -> LOV filtra
          4. Clicar OK da LOV

        Este padrao garante selecao aleatoria real — nao depende do
        primeiro item da lista. Funciona para Pais, Estado e Cidade.
        O valor vem das listas do config.yaml, podendo incluir valores
        invalidos para cenario negativo (observabilidade).
        """
        # 1. Focar no campo e abrir a LOV
        x, y = self._coord(coords, campo_coord)
        pyautogui.click(x, y)
        time.sleep(0.5)
        pyautogui.press("f9")
        time.sleep(1.0)  # aguarda LOV abrir

        # 2. Clicar no campo Localizar e digitar o valor
        x, y = self._coord(coords, "campo_localizar_lov")
        pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        ctx.runner.type_text(valor)
        time.sleep(0.5)  # aguarda filtro aplicar

        # 3. Clicar OK — confirma o item filtrado
        x, y = self._coord(coords, btn_ok_coord)
        pyautogui.click(x, y)
        time.sleep(0.5)

        # 4. Aguardar LOV fechar via pygetwindow — polling por titulo
        # Cobre os titulos conhecidos das LOVs usadas neste flow
        for titulo in ("Grupo etnico", "Lista de Pa", "Lista de UF", "Lista de Ci"):
            self._aguardar_popup_fechar(titulo, timeout=3.0)
        time.sleep(0.3)

    def _preencher_popup_brasileiro(self, ctx, coords, dados) -> None:
        """
        Popup Brasileiro:
          - Estado: sorteia de estados_brasileiro + _selecionar_em_lov
          - Cidade: usa cidade correspondente do estado sorteado
        Pares Estado/Cidade definidos no config.yaml — adicionar novos sem
        alterar codigo.
        """
        estados = self._dado(dados, "estados_brasileiro", "CM07")
        cidades = self._dado(dados, "cidades_por_estado", "CM07")

        estado = random.choice(estados)
        cidade = cidades.get(estado, estado)  # fallback: usa a sigla se cidade nao mapeada

        self._selecionar_em_lov(
            ctx, coords,
            campo_coord="campo_estado_brasileiro",
            btn_ok_coord="btn_ok_lov_estado_brasileiro",
            valor=estado,
        )

        self._selecionar_em_lov(
            ctx, coords,
            campo_coord="campo_cidade_brasileiro",
            btn_ok_coord="btn_ok_lov_cidade_brasileiro",
            valor=cidade,
        )

    def _preencher_popup_estrangeiro(self, ctx, coords, dados) -> None:
        """
        Popup Estrangeiro:
          - Pais: sorteia de paises_estrangeiro + _selecionar_em_lov
          - Data Entrada Brasil: faker DDMMYYYY
          - Estado: faker sigla
          - Municipio: faker cidade
        """
        cenario = ctx.config.dados_fixos.get("cenario", "positivo")
        chave = "paises_estrangeiro_negativo" if cenario == "negativo" else "paises_estrangeiro"
        paises = self._dado(dados, chave, "CM07")
        pais = random.choice(paises)

        self._selecionar_em_lov(
            ctx, coords,
            campo_coord="campo_pais_estrangeiro",
            btn_ok_coord="btn_ok_lov_pais_estrangeiro",
            valor=pais,
        )

        data_entrada = _fake_br.date_of_birth().strftime("%d%m%Y")
        x, y = self._coord(coords, "campo_data_entrada_brasil")
        pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.press("backspace", presses=10, interval=0.02)
        ctx.runner.type_text(data_entrada)
        time.sleep(0.3)

        x, y = self._coord(coords, "campo_estado_estrangeiro")
        pyautogui.click(x, y)
        time.sleep(0.3)
        ctx.runner.type_text(_fake_br.state_abbr())
        time.sleep(0.3)

        x, y = self._coord(coords, "campo_municipio_estrangeiro")
        pyautogui.click(x, y)
        time.sleep(0.3)
        ctx.runner.type_text(_fake_br.city())
        time.sleep(0.3)

    def _preencher_popup_naturalizado(self, ctx, coords, dados) -> None:
        """
        Popup Naturalizado:
          - Pais: sorteia de paises_naturalizado + _selecionar_em_lov
          - Data Naturalizacao: faker DDMMYYYY
          - Nr Portaria: faker numerify "####/####"
        """
        cenario = ctx.config.dados_fixos.get("cenario", "positivo")
        chave = "paises_naturalizado_negativo" if cenario == "negativo" else "paises_naturalizado"
        paises = self._dado(dados, chave, "CM07")
        pais = random.choice(paises)

        self._selecionar_em_lov(
            ctx, coords,
            campo_coord="campo_pais_naturalizado",
            btn_ok_coord="btn_ok_lov_pais_naturalizado",
            valor=pais,
        )

        data_nat = _fake_br.date_of_birth().strftime("%d%m%Y")
        x, y = self._coord(coords, "campo_data_naturalizacao")
        pyautogui.click(x, y)
        time.sleep(0.3)
        pyautogui.press("backspace", presses=10, interval=0.02)
        ctx.runner.type_text(data_nat)
        time.sleep(0.3)

        nr_portaria = _fake_br.numerify("####/####")
        x, y = self._coord(coords, "campo_nr_portaria")
        pyautogui.click(x, y)
        time.sleep(0.3)
        ctx.runner.type_text(nr_portaria)
        time.sleep(0.3)

    def _verificar_popup_erro_incor(self, ctx, coords, nacionalidade: str) -> None:
        """
        Verifica se o popup HC-INCOR apareceu apos clicar OK no popup de Nacionalidade.

        Deteccao via template matching (is_visible) — NAO via pygetwindow.
        O popup HC-INCOR e um modal interno do Oracle Forms sem handle de janela
        proprio. pygetwindow.getAllTitles() nao o detecta.

        Se detectado:
          1. Screenshot de evidencia
          2. Fecha popup de erro (OK)
          3. Fecha popup de Nacionalidade (Cancelar)
          4. AssertionError com causa real

        Bootstrap: se template nao capturado, retorna silenciosamente.
        Cenario negativo: quando lista contem valor invalido, este metodo
        detecta e falha — validando a observabilidade do sistema.
        """
        if not self._tpl_existe(_TPL_ERRO_INCOR):
            return  # bootstrap — template nao capturado ainda

        # threshold=0.75: score maximo real = 0.785 (equalize)
        if not ctx.runner.is_visible(_TPL_ERRO_INCOR, threshold=0.75):
            return  # popup nao detectado — continuar normalmente

        # Popup detectado — registrar evidencia
        ctx.runner.screenshot(
            f"{ctx.evidence_dir}CM07_erro_incor_{nacionalidade}.png"
        )

        # Fechar popup de erro
        x, y = self._coord(ctx.config.coordenadas, "btn_ok_erro_incor")
        pyautogui.click(x, y)
        time.sleep(0.5)

        # Fechar popup de Nacionalidade
        x, y = self._coord(ctx.config.coordenadas, "btn_cancelar_popup_nac")
        pyautogui.click(x, y)
        time.sleep(0.5)

        raise AssertionError(
            f"[CM07] Popup HC-INCOR detectado apos preencher Nacionalidade "
            f"({nacionalidade}).\n"
            f"O sistema rejeitou os dados — campo obrigatorio ficou vazio "
            f"dentro do popup ou valor invalido foi digitado.\n"
            f"Screenshot: CM07_erro_incor_{nacionalidade}.png\n"
            f"Dica: verifique se o valor sorteado existe no SI3. "
            f"Para cenario negativo intencional, este comportamento e esperado."
        )

    # ------------------------------------------------------------------
    # CM08 — Preencher Cor/Etnia via LOV (opcional — selecao aleatoria)
    # Fluxo: clicar campo -> digitar -> TAB -> clicar OK
    # Calibrado: x1:22 y1:278 x2:200 y2:296
    # ------------------------------------------------------------------
    def _step_cm08_cor_etnia(self, ctx, dados, coords, observer=None) -> StepResult:
        _ocr = [None]

        def fn():
            opcoes = self._dado(dados, "cor_etnia_opcoes", "CM08")
            cor_etnia = random.choice(opcoes)

            self._selecionar_em_lov(
                ctx, coords,
                campo_coord="campo_cor_etnia_lov",
                btn_ok_coord="btn_ok_lov_cor_etnia",
                valor=cor_etnia,
            )

            self._verify_campo_opcional(
                ctx, "cor_etnia", cor_etnia, "CM08", "campo_cor_etnia", _ocr
            )
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CM08_cor_etnia.png")

        step = self._step(
            "CM08", "preencher Cor/Etnia via LOV (opcional — aleatorio)",
            fn, observer, validated=True, ctx=ctx,
        )
        if step.success and _ocr[0]:
            step.ocr_lido = _ocr[0]
        return step

    # ------------------------------------------------------------------
    # CM09 — Gerar Matricula + Salvar (F10) + OCR + estado_jornada.json
    # Fluxo:
    #   1. Salvar com F10
    #   2. Clicar btn_gerar_matricula
    #   3. OCR na regiao matricula — AssertionError se vazio (obrigatorio)
    #   4. OCR na regiao identificador — fallback para matricula se nao calibrado
    #   5. Salvar paciente_id e matricula em estado_jornada.json
    # Regioes OCR (config.yaml):
    #   matricula:     { x1: 565, y1: 148, x2: 662, y2: 166 }  calibrado
    #   identificador: { x1: 457, y1: 146, x2: 552, y2: 165 }  calibrado
    # ------------------------------------------------------------------
    def _step_cm09_gerar_matricula(self, ctx, observer=None) -> StepResult:
        def fn():
            self._focar_si3()

            # 1. Salvar com F10 primeiro
            pyautogui.press("f10")
            time.sleep(2.0)

            # 2. Clicar Gerar Matricula
            x, y = self._coord(ctx.config.coordenadas, "btn_gerar_matricula")
            pyautogui.click(x, y)
            time.sleep(2.0)

            # 3. Screenshot para OCR
            screenshot_path = ctx.runner.screenshot(
                f"{ctx.evidence_dir}CM09_matricula.png"
            )

            # 4. OCR — Matricula (obrigatorio — prova que o cadastro foi salvo)
            r_mat = ctx.config.regioes_ocr["matricula"]
            regiao_mat = (r_mat["x1"], r_mat["y1"], r_mat["x2"], r_mat["y2"])
            texto_mat = OcrHelper.ler_regiao(screenshot_path, regiao_mat)
            numeros_mat = re.findall(r"\d+", texto_mat)
            if not numeros_mat:
                raise AssertionError(
                    f"[CM09] Matricula nao gerada ou OCR nao leu.\n"
                    f"Texto lido: '{texto_mat}'\n"
                    f"Regiao usada: {regiao_mat}\n"
                    f"Verifique regioes_ocr.matricula no config.yaml."
                )
            matricula = numeros_mat[0]
            print(f"[CM09] Matricula gerada: {matricula}")

            # 5. OCR — Identificador (usado como paciente_id na jornada)
            paciente_id = matricula  # fallback padrao
            if "identificador" in ctx.config.regioes_ocr:
                r_id = ctx.config.regioes_ocr["identificador"]
                regiao_id = (r_id["x1"], r_id["y1"], r_id["x2"], r_id["y2"])
                texto_id = OcrHelper.ler_regiao(screenshot_path, regiao_id)
                numeros_id = re.findall(r"\d+", texto_id)
                if numeros_id:
                    paciente_id = numeros_id[0]
                    print(f"[CM09] Identificador lido: {paciente_id}")
                else:
                    print(
                        f"[CM09] AVISO: OCR nao leu Identificador "
                        f"(texto='{texto_id}') — usando matricula como fallback."
                    )

            # 6. Salvar em estado_jornada.json para uso nas admissoes
            _salvar_estado_jornada("paciente_id", paciente_id)
            _salvar_estado_jornada("matricula", matricula)
            print(f"[CM09] estado_jornada.json atualizado: "
                  f"paciente_id={paciente_id}, matricula={matricula}")

            return screenshot_path

        return self._step(
            "CM09", "gerar matricula + salvar + OCR",
            fn, observer, validated=True, ctx=ctx,
        )

    # ------------------------------------------------------------------
    # CM10 — Sair para o Menu Principal
    # ------------------------------------------------------------------
    def _step_cm10_sair(self, ctx, coords, observer=None) -> StepResult:
        def fn():
            self._focar_si3()
            x, y = self._coord(coords, "btn_sair_1")
            pyautogui.click(x, y)
            time.sleep(1.0)
            x, y = self._coord(coords, "btn_sair_2")
            pyautogui.click(x, y)
            time.sleep(1.0)
            x, y = self._coord(coords, "btn_sair_3")
            pyautogui.click(x, y)
            time.sleep(1.0)
            return ctx.runner.screenshot(f"{ctx.evidence_dir}CM10_sair.png")

        return self._step(
            "CM10", "sair para o Menu Principal",
            fn, observer, ctx=ctx,
        )

    # ------------------------------------------------------------------
    # Helper — aguarda popup fechar via pygetwindow
    # Util para popups COM handle proprio (popup Nacionalidade).
    # NAO funciona para modais internos Oracle Forms (HC-INCOR).
    # ------------------------------------------------------------------
    @staticmethod
    def _aguardar_popup_fechar(titulo_parcial: str, timeout: float = 5.0) -> None:
        import time as _time
        try:
            import pygetwindow as gw
        except ImportError:
            _time.sleep(timeout / 2)
            return

        inicio = _time.monotonic()
        while _time.monotonic() - inicio < timeout:
            titulos = gw.getAllTitles()
            if not any(titulo_parcial in t for t in titulos):
                return
            _time.sleep(0.3)

    # ------------------------------------------------------------------
    # Helper — aguarda titulo da janela via pygetwindow
    # Usado em CM02 (fundo variavel — templates nao funcionam)
    # ------------------------------------------------------------------
    @staticmethod
    def _aguardar_titulo_janela(titulo: str, timeout: float = 15.0) -> bool:
        import time as _time
        try:
            import pygetwindow as gw
        except ImportError:
            print("[_aguardar_titulo_janela] AVISO: pygetwindow nao instalado")
            _time.sleep(timeout / 3)
            return True

        inicio = _time.monotonic()
        while _time.monotonic() - inicio < timeout:
            titulos = gw.getAllTitles()
            if any(titulo in t for t in titulos):
                return True
            _time.sleep(0.5)
        return False