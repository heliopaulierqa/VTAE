# src/flows/si3/admissao/base_admissao_flow.py
"""
BaseAdmissaoFlow — Classe base para flows de admissao SI3 (Ambulatorio,
Internacao, e futuros SADT/Pronto-Socorro).

Versao: 0.5.25 — nasce com o guard Fail Fast (_assert_tela_limpa).

Contexto (ver prompt de instrucao geral v0.5.25, secoes 3.1-3.4):
    O Passo E (cenario negativo) expos que o Oracle Forms tem DUAS formas
    de falha silenciosa em campos LOV:
      (a) COM popup — campo obrigatorio vazio no F10, erro de procedure,
          validacao de negocio. Gera popup 'HC - INCOR' visivel.
      (b) SEM popup — match parcial em LOV (ex: 'PROVEDOR_INVALIDO_XYZ'
          vira 'PALMEIRAS'). Tela permanece limpa, campo aparenta
          preenchido corretamente. Esta classe NAO cobre esse caso —
          ver _verify_campo_via_jab em base_flow.py (segunda camada,
          verificacao estrutural via pyjab).

Este arquivo resolve exclusivamente o caso (a): guard entre steps que
detecta popup de erro ANTES do proximo clique, evitando o padrao
"cliques cegos dentro do popup, OCR le conteudo do popup, falha na
razao errada" observado na sessao de 01-03/07/2026.

Medicao dos templates (03/07/2026, regra 11 — diagnose() contra 4
screenshots reais de popups distintos, script scripts/diagnose_contra_arquivo.py):

    Template                              Teto medido   Threshold usado
    -----------------------------------   -----------   ----------------
    titulo_hc_incor.png (faixa de titulo)     ~0.887          0.83
    btn_ok_popup.png (botao OK generico)      ~0.837          0.80

    Titulo: score consistente nos 4 popups catalogados (ORA-20002,
    'Transacao nao efetivada!', 'Preenchimento obrigatorio do Tipo',
    'E necessario incluir procedimentos na Fila'), alcancado via ajuste
    'equalize' (4a tentativa da cascata do TemplateMatcher — nao bate
    na 1a tentativa 'original', que fica em ~0.648. Isso e absorvido
    automaticamente por wait_template()/safe_click(), que ja rodam a
    cascata completa).

    Botao: score consistente nos mesmos 4 popups + mais 3 catalogados
    depois (7 no total), melhor resultado via 'original' (sem ajuste).
    Template recortado de UM popup ('Plano NAO esta Contratado') e
    validado contra os outros 6 — serve como detector/clicavel
    universal, nao precisa de 1 template por popup.

Ordem de operacao do guard (confirmada com Helio 03/07):
    1. Detecta popup (retry ate 'tentativas' vezes, 'intervalo' entre elas)
    2. Screenshot IMEDIATO — evidencia capturada ANTES de qualquer clique
    3. OCR da mensagem — BOOTSTRAP: sem regiao calibrada ainda, pulado
       silenciosamente (mesmo espirito do bootstrap em regioes_ocr)
    4. Fecha o popup (safe_click no botao OK generico) — devolve o
       Oracle Forms a estado limpo para a proxima execucao
    5. Levanta AssertionError — com step_id, screenshot, mensagem OCR
       (se capturada) e se o fechamento automatico funcionou

Pendencia conhecida, documentada e nao escondida:
    OCR da mensagem do popup (passo 3) ainda nao tem regiao calibrada —
    a mensagem varia de tamanho/posicao entre os 7 popups catalogados.
    Ate calibrar, o guard funciona sem a mensagem no erro (screenshot
    ainda serve de evidencia). Calibrar quando houver prioridade —
    nao bloqueia o guard em si.
"""

import time

from vtae.flows.base_flow import BaseFlow


class BaseAdmissaoFlow(BaseFlow):
    """
    Classe base para flows de admissao SI3.
    Ambulatorio, Internacao e futuros SADT/Pronto-Socorro herdam daqui.

    Nesta versao (v0.5.25): contem apenas o guard _assert_tela_limpa.
    Extracao dos steps comuns AB06-AB11/AI06-AI12 fica para um proximo
    passo do roadmap (item 8) — nao antecipado aqui (regra 6: nao
    reescrever logica de negocio sem pedido explicito).
    """

    # ----------------------------------------------------------------
    # Templates e thresholds — medidos 03/07/2026 (regra 11)
    # ----------------------------------------------------------------

    _TITULO_POPUP = "templates/si3/common/titulo_hc_incor.png"
    _THRESHOLD_TITULO_POPUP = 0.83

    _BTN_OK_POPUP = "templates/si3/common/btn_ok_popup.png"
    _THRESHOLD_BTN_OK_POPUP = 0.80

    # ----------------------------------------------------------------
    # _assert_tela_limpa() — Guard Fail Fast entre steps de admissao
    # ----------------------------------------------------------------

    def _assert_tela_limpa(
        self,
        ctx,
        step_id: str,
        tela_esperada: str = None,
        tentativas: int = 2,
        intervalo: float = 0.4,
    ) -> None:
        """
        Confirma que NAO ha popup de erro 'HC - INCOR' bloqueando a tela
        antes do proximo step executar. Chamar no INICIO de cada step de
        admissao, antes de qualquer clique — nao depois.

        Se detectar popup:
            1. Screenshot imediato (evidencia antes de fechar)
            2. Tenta fechar automaticamente (safe_click no botao OK)
            3. Levanta AssertionError — nunca deixa o flow continuar
               com popup aberto na tela

        Se nao detectar popup mas 'tela_esperada' foi informado:
            Confirma que o template da tela esperada esta visivel.
            Se nao estiver, levanta AssertionError — o foco pode estar
            em uma tela diferente da que o flow assume (ex: tela nao
            trocou apos o clique anterior).

        Retry (tentativas/intervalo): protege contra falso negativo por
        timing — popup ainda renderizando no instante da checagem.
        Cada tentativa usa timeout curto (nao espera o popup aparecer,
        so confirma se ja esta la); o espaco entre tentativas e dado
        por 'intervalo'.

        Args:
            ctx:            FlowContext
            step_id:        ID do step que vai executar a seguir
                            (aparece na mensagem de erro caso falhe)
            tela_esperada:  template PNG opcional — confirma que a tela
                            correta esta visivel, alem de confirmar
                            ausencia de popup. None = pula essa checagem.
            tentativas:     numero de checagens de popup antes de
                            concluir "tela limpa" (default 2)
            intervalo:      segundos entre tentativas (default 0.4)

        Raises:
            AssertionError: popup detectado (fechado automaticamente
                            antes de levantar), ou tela_esperada nao
                            confirmada.
        """
        popup_detectado = False
        for tentativa in range(1, tentativas + 1):
            popup_detectado = ctx.runner.wait_template(
                self._TITULO_POPUP,
                timeout=0.3,
                threshold=self._THRESHOLD_TITULO_POPUP,
            )
            if popup_detectado:
                break
            if tentativa < tentativas:
                time.sleep(intervalo)

        if popup_detectado:
            # 1. Screenshot IMEDIATO — evidencia antes de qualquer clique
            screenshot_path = None
            try:
                screenshot_path = ctx.runner.screenshot(
                    f"{ctx.evidence_dir}{step_id}_popup_detectado.png"
                )
            except Exception:
                pass

            # 2. OCR da mensagem — BOOTSTRAP: regiao ainda nao calibrada
            # (mensagem varia de posicao/tamanho entre os popups catalogados).
            # Pulado silenciosamente ate haver prioridade de calibrar,
            # mesmo espirito do bootstrap em regioes_ocr nao calibradas.
            mensagem_lida = None

            # 3. Fecha o popup — devolve o Oracle Forms a estado limpo
            fechado = False
            try:
                fechado = ctx.runner.safe_click(self._BTN_OK_POPUP)
                time.sleep(0.5)
            except Exception as e:
                print(f"[{step_id}] AVISO: falha ao tentar fechar popup "
                      f"automaticamente: {e}")

            # 4. Falha SEMPRE — popup nunca deveria estar presente aqui
            raise AssertionError(
                f"[{step_id}] Guard Fail Fast: popup 'HC - INCOR' detectado "
                f"antes deste step executar.\n"
                f"Screenshot: {screenshot_path}\n"
                f"Mensagem do popup: "
                f"{'nao calibrada (bootstrap)' if mensagem_lida is None else mensagem_lida!r}\n"
                f"Fechado automaticamente: {fechado}\n"
                f"Causa provavel: match parcial em LOV do step anterior, "
                f"dado invalido aceito silenciosamente, ou validacao de "
                f"negocio (campo obrigatorio vazio, procedure Oracle)."
            )

        # Sem popup — confirma tela esperada, se informada
        if tela_esperada:
            tela_ok = ctx.runner.wait_template(
                tela_esperada, timeout=2.0, threshold=0.7
            )
            if not tela_ok:
                raise AssertionError(
                    f"[{step_id}] Guard Fail Fast: tela esperada nao "
                    f"confirmada — '{tela_esperada}' nao encontrado na "
                    f"tela atual.\n"
                    f"O foco pode estar em uma tela diferente da que o "
                    f"flow assume neste ponto."
                )
