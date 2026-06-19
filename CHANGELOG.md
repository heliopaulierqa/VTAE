# Changelog — VTAE

Todas as mudanças significativas do projeto são documentadas aqui.

---

## [0.5.16] — 2026-06-12

### Corrigido — Bugs críticos de infraestrutura
- **`src/config/loader.py`**: `_parsear_env_file` cortava valores por `#` inline (`value.split("#", 1)[0]`) — quebrava qualquer senha/valor contendo `#` (ex: `teste#1906` → `teste`). Revertido. Nova regra: `.env` nunca tem comentário na mesma linha de `VAR=valor` — comentários sempre em linha separada acima.
- **`src/config/loader.py`** e **`src/runners/opencv_runner.py`**: default `ocr_engine: "tesseract"` corrigido para `"easyocr"` em `ConfigLoader._construir` e `OpenCVRunner.__init__` (o `__init__` não repassava `config.ocr_engine`).
- **`src/flows/si3/cadastro_paciente_flow.py`**: CP05 `_step_data_nascimento` — `Ctrl+A` não seleciona corretamente em campo de data com máscara Oracle Forms (`02/03/1966` virava `12/03/1966`); trocado por `backspace(10x) + type_text` (mesmo padrão aplicado ao campo de hora).

### Corrigido — AdmissaoComAgendamentoFlow (AB05)
- Fluxo real de 3 telas mapeado: Cadastro de Pacientes → Verificar Agendamento → AMBULATORIO.
- `wait_template` em `campo_unidade_funcional.png` / `label_ambulatorio.png` / `btn_guia_tiss.png` dava score 1.0 mesmo com a tela "Verificar Agendamento" ainda aberta (Oracle Forms renderiza elementos de telas adjacentes simultaneamente). Substituído por guard `_titulo_janela_contem("AMBULAT", excluir="VERIFICAR")` via `pygetwindow`.
- Novo template `btn_admitir_verificar_ag.png` (botão "Admitir" da tela Verificar Agendamento) + coordenada `primeira_linha_grade_ag` (seleção da linha do agendamento na grade) calibrados.

### Adicionado
- **`src/flows/si3/admissao_ambulatorio_flow.py`** AB02: contrato `paciente_id` — `.env` (`SI3_PACIENTE_ID`) preenchido = teste standalone; vazio = lê `estado_jornada.json` (fluxo de jornada completa). Permite `vtae run --test admissao_com_agendamento_jornada` isolado.
- **`scripts/testar_regiao_ocr.py`**: testa região OCR isolada (salva `_crop_raw.png` + `_crop_proc.png` com upscale 3x + grayscale), sem rodar a jornada inteira (~90s economizados por ciclo de calibração).
- `VTAE_Roadmap_Observabilidade_v0_5_16.docx` — roadmap consolidado com Fase 1 (gate) de observabilidade real por campo.
- `VTAE_Prompt_Instrucao_Geral_v0.5.16.md` — instrução geral do projeto atualizada (substitui a v0.5.12).

### Descoberto — não corrigido ainda
- Jornada `ambulatorio`: AB06–AB12 não verificam via OCR se o valor digitado foi aceito pelo sistema ("testes cegos"). Causou AB15 (Nr. Admissão) lendo vazio após 14 steps "OK". Vira **Fase 1 (gate)** — escopo travado na jornada `ambulatorio` até validação 3x consecutivas; nenhuma outra jornada recebe os novos guards antes disso.

---

## [0.5.15] — 2026-06-11

### Validado
- Jornada `ambulatorio` (sem agendamento): 3x consecutivas (pacientes 49976892/94/95).
  - AB04: campo Tipo = RUA via `backspace×20 + digitar + Tab + Ctrl+S`
  - AB12: profissional do procedimento selecionado via Tab
  - AB14: salvar via F10
  - AB15: `regioes_ocr.nr_admissao_amb` calibrado no `config.yaml` — `ocr_lido='00234746'`

### Adicionado
- `scripts/testar_regiao_ocr.py` criado nesta sessão (ver detalhe completo em 0.5.16).

---

## [0.5.14] — 2026-06-10

### Corrigido
- **AI18** (saída multi-tela, `admissao_internacao_flow.py`): reescrito com template por tela + confirmação por elemento único + coordenada na borda + confirmar antes de reclicar — padrão reaproveitável para saídas multi-tela.
- **AB01** (`admissao_ambulatorio_flow.py`): migrado para "Localizar no Menu" (`menu_ambulatorio.png` + `btn_pesquisar_menu.png` + `titulo_ambulatorio.png`).
- `ocr_engine: easyocr` adicionado aos configs `si3_ambulatorio` e `si3_agendamento`.

### Validado
- Jornada `internacao`: 3x consecutivas (pacientes 49976883/84/85).

---

## [0.5.12] — 2026-06-08

### Adicionado — Robustez de transições + templates comuns

**`src/flows/base_flow.py`**
- `_clicar_aguardar(ctx, acao, confirmacao, timeout, threshold, retries, label)` — helper universal para transições de tela
  - Executa `acao()` → aguarda `confirmacao` aparecer via `wait_template`
  - Se não confirmou → reclica até `retries` vezes com log de tentativa
  - Se template não existe em disco → fallback com `time.sleep` e aviso no log (nunca quebra)
  - Funciona para desktop (template PNG) e web (seletor CSS) — mesmo contrato

**`templates/si3/admissao_internacao/`** (novos)
- `btn_selecionar_leito.png` — botão "Selecionar" na tela Lista de Leitos Livres
- `btn_ok_reserva_popup.png` — botão OK da janela Forms flutuante ("Não existe reserva para o paciente")
- `titulo_internacao.png` — título da janela INTERNACAO (confirmação do 1º Sair)
- `titulo_menu_principal.png` — título da janela Menu Principal (confirmação do 2º Sair)

**`templates/si3/cadastro_paciente/`** (novo)
- `titulo_menu_principal.png` — título da janela Menu Principal (confirmação do CP23)

**`tests/integration/si3/components/cadastro_paciente_fixture.py`**
- `observer.inject_logger(ctx)` adicionado antes dos flows — logs do runner chegam ao `execution.log`
- Import corrigido: `_salvar_estado` importado de `src.core.estado_jornada`

### Corrigido

**`src/flows/si3/admissao_internacao_flow.py`**
- **AI06**: `safe_click + time.sleep(2.0)` → `_clicar_aguardar` aguardando `campo_identificado.png`
- **AI16 fluxo LOV corrigido**: `_clicar_aguardar` movido para após OK da LOV de unidades (não antes de Consultar Leito)
- **AI16 popups**: loop fecha todos os popups pós-Alocar Leito — tenta `btn_ok_reserva_popup.png` (janela flutuante) e `btn_ok_popup.png` (janela principal) em sequência, até 3 vezes cada
- **AI18**: reescrito com `_clicar_aguardar` nos dois saídas principais (`titulo_internacao.png` e `titulo_menu_principal.png`); 3º sair condicional
- **verify_fill/verify_lov**: todos desempacotando `ok, _ =` corretamente (tupla v0.5.11)

**`src/flows/si3/cadastro_paciente_flow.py`**
- **CP02**: `safe_click + time.sleep(3.0)` → `_clicar_aguardar` aguardando `btn_novo.png` — resolve falha por delay variável do sistema
- **CP23**: reescrito com `_clicar_aguardar` no último sair confirmando `titulo_menu_principal.png`; saídas 1 e 2 com `time.sleep(2.5)` aumentado

### Padrões consolidados nesta sessão

- **`_clicar_aguardar` como padrão de transição**: substitui `safe_click + time.sleep` fixo em todas as transições críticas — desktop e web
- **Popup janela Forms flutuante**: requer template separado (`btn_ok_reserva_popup.png`) — aparência diferente do popup principal
- **Fluxo AI16**: Consultar Leito → LOV unidades → OK → `_clicar_aguardar(btn_selecionar_leito)` — o `_clicar_aguardar` vai no OK da LOV, não no Consultar Leito
- **Closure problem**: ao usar `_clicar_aguardar` com coordenadas em lambda, usar variáveis `x_ok, y_ok` distintas
- **`inject_logger` obrigatório**: `observer.inject_logger(ctx)` antes de qualquer flow no fixture/teste
- **Template comum**: `titulo_menu_principal.png` reutilizado em cadastro e internação — base para pasta `common/` futura

### Validado
- Jornada internação completa: cadastro_paciente + admissao_internacao ✅ 08/06/2026 (1/3 — aguarda mais 2)

---

## [0.5.11] — 2026-06-03

### Adicionado — EasyOCR + ocr_lido no report

- **Tesseract removido** — `src/vision/ocr_engine.py` centraliza OCR via EasyOCR (pip puro)
- **`ocr_lido` no StepResult** — valor lido pelo OCR propagado até `report.html` como badge `✔ VALIDADO OCR leu: [valor]`
- **`verify_fill` e `verify_lov` retornam `(bool, str)`** — desempacotar sempre
- **Threshold 0.80** no AI17 — evita falso positivo do `btn_sim_popup.png` (score real > 0.85; falso = 0.702)
- **`.venv` obrigatório** — workflow estabelecido

---

## [0.5.9d] — 2026-05-29

### Adicionado — Fase 5f: AdmissaoInternacaoFlow validado

- AdmissaoInternacaoFlow — AI01–AI18 passando — validado em 29/05/2026
- Jornada completa: `vtae run --jornada internacao` ✅
- Navegação via "Localizar no Menu" — padrão consolidado
- Cenário SUS validado — estrutura `cenarios_provedor`
- AI12: LOV resultado único → OK direto
- AI14: `campo_numero=1 + TAB` abre popup automaticamente
- AI15/AI16/AI17: fluxo de leito completo
- AI18: 3x `safe_click(btn_sair.png)`
- AI19: OCR valida Nr Admissão (modo bootstrap)

---

## [0.5.9c] — 2026-05-28

### Adicionado — Fase 5e: AdmissaoComAgendamentoFlow + reorganização jornadas

- `AdmissaoComAgendamentoFlow` criado
- Reorganização de jornadas em `tests/integration/si3/jornadas/`
- `vtae run --jornada internacao` registrado no CLI

---

## [0.5.9b] — 2026-05-27

### Adicionado — Onda 1: Observabilidade real

- `confirm_template` em todos os steps de navegação
- `validated=True` propagado no `_step()` wrapper
- `_focar_si3()` antes de steps críticos
- `_tpl_existe()` — fallback gracioso para templates ausentes
- `verify_lov` em AG07, AB11, AB12

### Adicionado — Fase 5d: AgendamentoFlow

- AgendamentoFlow — AG01–AG13 passando — validado 3x em 27/05/2026

---

## [0.5.9a] — 2026-05-26

### Adicionado — Obs-Fase1b: verify_lov + verify_fill + _dado + set_logger

- `verify_lov()` — OCR confirma campo LOV não ficou vazio
- `verify_fill()` — OCR confirma campo preenchido
- `_dado()` — dado ausente = erro imediato
- `PlaywrightRunner.set_logger()`

### Adicionado — Fase 5c: Jornada ambulatório

- AdmissaoAmbulatorioFlow — AB01–AB15 validado 3x em 26/05/2026

---

## [0.4.0] — 2026-05-02

### Adicionado — Fase 3 E1: Clean Architecture

- Estrutura `src/` com separação por sistema
- `src/core/types.py` — exceções centralizadas
- `src/vision/template.py` — `TemplateMatcher` isolado
- `pyproject.toml` v0.4.0

---

## [0.3.5] — 2026-05-02

- `click_near(template, offset_x, offset_y)` — anchor-based clicking

## [0.3.4] — 2026-05-02

- Pipeline de 5 estratégias de matching + `DiagnosticReport`

## [0.3.3] — 2026-05-02

- `TemplateMatcher` multi-scale: testa escalas `(1.0, 0.9, 1.1, 0.8, 1.2)`

## [0.3.2] — 2026-05-02

- `CadastroPacienteFlow` — validado 28/04/2026
- `TipoAnestesiaFlow` — validado 30/04/2026
- `CadastroFuncionarioFlow` (SisLab) — validado 02/05/2026

## [0.3.0] — 2026-04-27

- `apex_helper.py`, `ocr_helper.py`
- `FrequenciaAplicacaoFlow` reescrito
- `LoginFlowMsi3` com detecção de erro

## [0.2.0] — 2026

- `OpenCVRunner`, `PlaywrightRunner`, `ExecutionObserver`
- Integração com Faker
- 32 testes unitários

## [0.1.0] — 2026

- Estrutura inicial: `LoginFlow`, `AdmissaoFlow`, `SuprimentosFlow` (esqueletos)