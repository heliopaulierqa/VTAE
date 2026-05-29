# configs/si3/si3_internacao/config.yaml
# AdmissaoInternacaoFlow — v0.5.9d
#
# CONTRATO: todos os dados de teste ficam aqui.
# O flow nao tem nenhum valor default — se um campo faltar aqui,
# o step falha com mensagem clara indicando qual chave esta ausente.
#
# CENARIOS NEGATIVOS: basta alterar o valor do campo.
# Exemplo: termo_medico_responsavel: 'MEDICO INEXISTENTE'
#          unidade_funcional: 'UNIDADE INVALIDA'
#
# Como carregar:
#   config = ConfigLoader.carregar(
#       "si3_internacao",
#       configs_dir=pathlib.Path("configs/si3"),
#   )

sistema: si3_internacao
tipo: desktop
runner: opencv

ambientes:
  dev:
    url: ''
    confidence: 0.75
    headless: false
    timeout: 30

credenciais:
  usuario:     ${SI3_USER}
  senha:       ${SI3_PASS}
  paciente_id: ${SI3_PACIENTE_ID:-}   # vazio=le do estado_jornada.json

dados_faker: []   # internacao nao usa faker — dados sao fixos por natureza

dados:
  # ── AI01: Navegacao via Localizar no Menu ─────────────────────────────
  # Termo digitado no campo "Localizar no Menu" para encontrar o modulo
  # Igual ao padrao do ambulatorio (termo_menu_ag no agendamento)
  termo_menu_int: 'INTERNACAO'

  # ── AI07: Unidade Funcional ───────────────────────────────────────────
  # Digitar + TAB — Oracle Forms carrega a sigla automaticamente
  # REGRA: campo fixo mas alteravel para testar outra unidade
  # CENARIO NEGATIVO: trocar para 'UNIDADE INVALIDA' para testar erro
  unidade_funcional: 'SC AMBULATORIO'

  # ── AI08: Provedor e Plano ────────────────────────────────────────────
  # cenario_provedor define qual bloco abaixo sera usado pelo flow
  # Valores possiveis: sus | particular | incor_sis | convenio
  cenario_provedor: 'sus'

  cenarios_provedor:
    sus:
      provedor:    'SUS'
      plano:       'SUS'
      carteirinha: ''
      validade:    ''
    particular:
      provedor:    'PARTICULAR'
      plano:       'PARTICULAR'
      carteirinha: ''
      validade:    ''
    incor_sis:
      provedor:    'INCOR SIS'
      plano:       'INCOR - SIS'
      carteirinha: '12345678'       # trocar por faker se necessario
      validade:    '30/12/2028'
    convenio:
      provedor:    'CONVENIO'
      plano:       'EXCELLENCE'
      carteirinha: '123456789012'   # trocar por faker se necessario
      validade:    '30/12/2028'

  # ── AI08b: Declarante/Acompanhantes e Especialidade ──────────────────
  declarante:    'TESTE DE FERRAMENTA DE AUTOMACAO'
  especialidade: 'ANGIO - ANGIOLOGIA'

  # ── AI09: Observacao ──────────────────────────────────────────────────
  obs: 'TESTE DE FERRAMENTA DE AUTOMACAO'

  # ── AI10: Origem do Paciente ──────────────────────────────────────────
  # Digitar + TAB — campo Entidade preenche automaticamente
  # CENARIO NEGATIVO: trocar para 'ORIGEM INVALIDA'
  origem_tipo: 'RESIDENCIA'

  # ── AI11: Origem da Solicitacao de Internacao (dropdown) ─────────────
  # Valor exato do item no dropdown — alterar para testar outro cenario
  # Opcoes visiveis no sistema: Consultorio Interno, Consultorio Externo,
  #   Pronto Socorro, Transferencia Hospitalar
  origem_solicitacao: 'Consultorio Interno'

  # ── AI12: Profissional Responsavel pela Internacao (LOV) ─────────────
  # Termo digitado no campo Localizar da LOV — usar % como wildcard
  # CENARIO NEGATIVO: trocar para 'MEDICO INEXISTENTE' para testar erro
  #termo_medico_responsavel: '%medico'

  # ── AI14: Profissional do Info. Compl. de Internacao (LOV) ───────────
  # Pode ser o mesmo medico ou outro — campo independente de AI12
  # CENARIO NEGATIVO: trocar para nome que nao existe
  termo_medico_compl: '%medico'

  # ── AI-Leito: Alocar Leito ────────────────────────────────────────────
  # Termo digitado no campo Localizar da LOV de unidade funcional do leito
  # Digitar 'UM' ja retorna resultados — alterar para outra unidade se necessario
  termo_unidade_leito: 'UM'

# ─────────────────────────────────────────────────────────────────────────────
# coordenadas — capturar com: python scripts/posicao_mouse.py
#
# QUANDO usar coordenada vs template:
#   Campo pequeno / na mesma posicao sempre  → coordenada direta (aqui)
#   Botao unico e estavel                    → template OpenCV
#   Label de campo grande                    → template OpenCV (click_near)
#
# STATUS: { x: 0, y: 0 } = ainda nao capturado — substituir apos calibracao
# ─────────────────────────────────────────────────────────────────────────────
coordenadas:

  # ── Menu Principal (AI01) — mesma coordenada do ambulatorio ──────────
  campo_localizar_menu:         { x: 624, y: 578 }  # reutilizar do si3_agendamento

  # ── Tela Pesquisa de Pacientes (AI02) ────────────────────────────────
  # Campo "Identificador" — dois tabs a partir do foco inicial
  # Usar coordenada direta pois click_near no label e instavel aqui
  campo_identificador:          { x: 523, y: 180 }  # calibrado 29/05/2026

  # ── Tela de Admissao principal ────────────────────────────────────────

  # AI07 — campo Unidade Funcional (cursor ja esta aqui ao abrir a tela)
  # Manter como fallback caso o foco nao esteja no campo
  campo_unidade_funcional:      { x: 122, y: 204 }   # capturar

  # AI08 — Provedor e Plano
  campo_provedor:               { x: 63, y: 242  }   # capturar
  campo_plano:                  { x: 354, y: 241 }   # capturar
  campo_carteirinha:            { x: 671, y: 239 }   # capturar (so para incor_sis e convenio)
  campo_validade_carteirinha:   { x: 742, y: 280 }   # capturar (so para incor_sis e convenio)

  # AI08b — Declarante e Especialidade
  campo_declarante:             { x: 44, y: 279 }   # capturar
  campo_especialidade:          { x: 335, y: 281 }   # capturar

  # AI09 — Obs
  campo_obs:                    { x: 77, y: 345 }   # capturar

  # AI10 — Origem do Paciente (campo Tipo)
  campo_origem_tipo:            { x: 65, y: 409 }   # capturar

  # AI11 — Dropdown Origem da Solicitacao
  dropdown_origem_solicitacao:  { x: 638, y: 460 }   # capturar

  # AI12 — LOV Profissional Responsavel pela Internacao
  btn_lov_medico_responsavel:   { x: 830, y: 529 }   # capturar (botao [...] ao lado do campo)
  btn_ok_medico_resp:           { x: 641, y: 816 }   # capturar (botao OK no popup)

  # AI13 — Botao Info. Compl. de Internacao
  # Usar template btn_info_compl.png — nao precisa de coordenada

  # AI14 — Campo Numero no popup Info. Compl.
  campo_numero_compl:           { x: 0, y: 0 }   # capturar

  # AI15 — Botao Retornar (popup Info. Compl.)
  btn_retornar_compl:           { x: 0, y: 0 }   # capturar

  # AI16 — Botao LEITO (tela principal)
  # Usar template btn_leito.png — nao precisa de coordenada

  # AI17 — Tela Alocar Leito
  btn_alocar_leito:             { x: 0, y: 0 }   # capturar
  btn_consultar_leito:          { x: 0, y: 0 }   # capturar
  campo_busca_unidade_leito:    { x: 0, y: 0 }   # capturar (campo Localizar no popup)
  btn_localizar_unidade_leito:  { x: 0, y: 0 }   # capturar
  btn_ok_unidade_leito:         { x: 0, y: 0 }   # capturar

  # AI18 — Lista de leitos — clicar na primeira linha
  primeira_linha_leitos:        { x: 0, y: 0 }   # capturar
  btn_selecionar_leito:         { x: 0, y: 0 }   # capturar

  # AI19 — Botao OK + Sair na tela Alocar Leito
  btn_ok_alocar:                { x: 0, y: 0 }   # capturar
  btn_sair_alocar:              { x: 0, y: 0 }   # capturar

# ─────────────────────────────────────────────────────────────────────────────
# regioes_ocr — calibrar com Paint apos primeira execucao
#
# COMO CALIBRAR:
#   1. Rodar o teste — steps com WARNING "Regiao nao calibrada" = ainda pendente
#   2. Abrir o screenshot do step em evidence/ no Paint
#   3. Cursor no canto superior-esquerdo do campo → x1, y1
#   4. Cursor no canto inferior-direito do campo  → x2, y2
#   5. Substituir { x1: 0, y1: 0, x2: 0, y2: 0 } pelos valores reais
#
# Quando (0,0,0,0): assert pulado com WARNING — nao falha (modo bootstrap).
# Quando calibrado: assert ativo — step falha se valor nao for encontrado.
# ─────────────────────────────────────────────────────────────────────────────
regioes_ocr:

  # AI05 — Campo Tipo na aba Endereco
  # OCR condicional: verifica se esta vazio antes de preencher
  campo_tipo_endereco:
    x1: 0
    y1: 0
    x2: 0
    y2: 0

  # AI12 — Campo do medico responsavel (apos LOV fechar)
  # Confirma que o campo nao ficou vazio — verify_lov obrigatorio
  campo_medico_responsavel:
    x1: 0
    y1: 0
    x2: 0
    y2: 0

  # AI21 — Nr Admissao (tela principal apos alocar leito)
  # CALIBRAR PRIMEIRO: obrigatorio para validar que a admissao foi salva
  nr_admissao:
    x1: 0
    y1: 0
    x2: 0
    y2: 0