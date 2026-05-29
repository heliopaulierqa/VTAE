# Changelog — VTAE

Todas as mudanças significativas do projeto são documentadas aqui.

---

## [0.5.9d] — 2026-05-29

### Adicionado — Fase 5f: AdmissaoInternacaoFlow validado

**`src/flows/si3/admissao_internacao_flow.py`** (novo, validado)
- AdmissaoInternacaoFlow — AI01–AI18 passando — validado em 29/05/2026
- Jornada completa: `vtae run --jornada internacao` ✅ (cadastro + admissão)
- Navegação via "Localizar no Menu" — padrão consolidado para todos os módulos SI3
- Cenário SUS validado — estrutura `cenarios_provedor` suporta sus/particular/incor_sis/convenio
- AI05: OCR condicional no campo Tipo — preenche RUA só se vazio; default seguro = assume preenchido
- AI12: LOV Profissional Responsável — popup abre com resultado único → OK direto
- AI14: campo Número=1 + TAB abre popup automaticamente → digita %medico → double_click no médico de informatica
- AI15: botão Leito → confirm_template `btn_alocar_leito.png` (aparece na mesma tela)
- AI16: Alocar Leito → popup "não existe reserva" → OK → Consultar Leito → LOV unidade
- AI17: seleciona leito + popup "especialidade diferente" → Sim (condicional, `_tpl_existe`)
- AI18: 3x `safe_click(btn_sair.png)` para retornar ao menu principal
- AI19: OCR valida Nr Admissão (modo bootstrap até calibrar `regioes_ocr.nr_admissao`)

**`configs/si3/si3_internacao/config.yaml`** (novo)
- Estrutura completa com `dados:`, `coordenadas:`, `regioes_ocr:`
- `cenarios_provedor`: sus, particular, incor_sis, convenio — alterar `cenario_provedor` para mudar cenário
- `termo_menu_int: 'INTERNACAO'` — padrão Localizar no Menu
- `credenciais.paciente_id: ${SI3_PACIENTE_ID:-}` — vazio=lê estado_jornada.json; preenchido=reutiliza

**`templates/si3/admissao_internacao/`** (novos templates capturados)
- `aba_endereco.png`, `btn_admitir_paciente.png`, `btn_alocar_leito.png`
- `btn_consultar_leito.png`, `btn_info_compl.png`, `btn_leito.png`
- `btn_nao_popup.png`, `btn_ok_popup.png`, `btn_pesquisar.png`, `btn_pesquisar_menu.png`
- `btn_retornar.png`, `btn_sair.png`, `btn_sim_popup.png`
- `campo_identificado.png`, `campo_matricula_responsavel.png`, `campo_nr_admissao.png`
- `campo_numero.png`, `item_medico_informatica.png`, `menu_internacao.png`

### Corrigido

- **AI05 default seguro**: `campo_vazio = False` por padrão — sem OCR calibrado, não preenche (evita sobrescrever campo já preenchido)
- **AI15 confirm_template**: corrigido de `btn_consultar_leito.png` para `btn_alocar_leito.png` — "Alocar Leito" aparece na tela que abre após clicar em "Leito"; "Consultar Leito" só aparece após clicar em "Alocar Leito"
- **AI16 popup "já possui leito"**: fechado com OK antes de continuar
- **AI14 LOV**: removido clique na LOV — `campo_numero=1 + TAB` abre o popup automaticamente (padrão Oracle Forms)
- **AI12 LOV**: removida busca desnecessária — popup abre com resultado único, basta OK direto
- **`_ler_estado()`**: corrigido para passar a chave como argumento: `_ler_estado("paciente_id")`
- **`result.add()`**: corrigido para `result.steps.append(sr)` — API correta do FlowResult
- **`ctx_ref`**: removido resquício de closure — `_step()` recebe `ctx=ctx` como parâmetro
- **YAML `???`**: valores placeholder substituídos por `{ x: 0, y: 0 }` — YAML não aceita `?` em flow nodes

### Padrões consolidados nesta sessão

- **Navegação de módulo SI3**: digita no "Localizar no Menu" → Pesquisar → Não (popup) → double_click no item
- **Template = menor elemento único**: nunca capturar tela inteira; usar label fixo ou botão de texto estático
- **LOV com resultado único**: só OK, sem busca
- **LOV com lista**: digita termo → Localizar → double_click (dispensa OK)
- **TAB abre popup LOV em Oracle Forms**: `campo_numero=1 + TAB` é mais estável que clicar na LOV
- **3x btn_sair.png**: padrão para retornar ao menu principal após admissão internação
- **confirm_template por tela**: AI15→`btn_alocar_leito.png`, AI16→`btn_consultar_leito.png`
- **Popup condicional**: sempre `_tpl_existe()` + `is_visible()` — nunca assumir que aparece

### Validado
- Jornada internação completa: cadastro_paciente + admissao_internacao ✅ 29/05/2026

---

## [0.5.9c] — 2026-05-28

### Adicionado — Fase 5e: AdmissaoComAgendamentoFlow + reorganização jornadas

- `AdmissaoComAgendamentoFlow` criado — herda 90% do AdmissaoAmbulatorioFlow
- Reorganização de jornadas em `tests/integration/si3/jornadas/`
- `vtae run --jornada internacao` registrado no CLI
- Pendente: calibrar `btn_admitir_com_agendamento.png` e coordenadas

---

## [0.5.9b] — 2026-05-27

### Adicionado — Onda 1: Observabilidade real

- `confirm_template` em todos os steps de navegação
- `validated=True` propagado no `_step()` wrapper
- `_focar_si3()` antes de steps críticos em Oracle Forms
- `_tpl_existe()` — fallback gracioso para templates ausentes
- `verify_lov` em AG07, AB11, AB12

### Adicionado — Fase 5d: AgendamentoFlow

- AgendamentoFlow — AG01–AG13 passando — validado 3x em 27/05/2026
- `vtae run --jornada ambulatorio_com_agendamento` funcionando

---

## [0.5.9a] — 2026-05-26

### Adicionado — Obs-Fase1b: verify_lov + verify_fill + _dado + set_logger

- `verify_lov()` — OCR confirma campo LOV não ficou vazio após seleção
- `verify_fill()` — OCR confirma campo preenchido após digitação
- `_dado()` — dado ausente = erro imediato com mensagem clara
- `PlaywrightRunner.set_logger()` — logs web chegam ao execution.log

### Adicionado — Fase 5c: Jornada ambulatório

- AdmissaoAmbulatorioFlow — AB01–AB15 validado 3x em 26/05/2026
- `vtae run --jornada ambulatorio` funcionando

---

## [0.4.0] — 2026-05-02

### Adicionado — Fase 3 E1: Clean Architecture

**Estrutura `src/` com separação por sistema**
- Criada estrutura Clean Architecture em `src/` mantendo `vtae/` funcionando via aliases
- Separação por sistema em `src/flows/`: `si3/`, `sislab/`, `msi3/`
- `apex_helper.py` movido para `src/flows/msi3/` — helper específico junto aos flows que o usam
- Camadas genéricas sem separação: `src/core/`, `src/vision/`, `src/runners/`
- Regra de dependência: `core ← vision ← runners ← flows` (nunca o contrário)

**Arquivos novos**
- `src/core/types.py` — exceções centralizadas: `VtaeError`, `StepError`, `TemplateNotFoundError`, `ConfigError`, `RunnerError`
- `src/vision/template.py` — `TemplateMatcher` isolado do `OpenCVRunner`
- `pyproject.toml` v0.4.0 — registra `src*` e `vtae*` no editable install

**Aliases em `vtae/`** — todos os módulos redirecionam para `src/` via re-export de uma linha.

**Padrão para novos sistemas** — adicionar sistema = criar 4 pastas: `src/flows/<sistema>/`, `configs/<sistema>/`, `templates/<sistema>/`, `tests/integration/<sistema>/`

### Validado
- 32 testes unitários verdes após migração

---

## [0.3.5] — 2026-05-02

### Adicionado — F2-C: Anchor-based Clicking

**`src/runners/opencv_runner.py`**
- `click_near(template, offset_x, offset_y)` — encontra o template âncora e clica na posição deslocada
- Útil para Oracle Forms onde o label é estável mas o campo fica a distância fixa do label

**`src/vision/template.py`**
- `find_anchor(anchor_path, offset_x, offset_y)` — implementação do anchor no `TemplateMatcher`

---

## [0.3.4] — 2026-05-02

### Adicionado — F2-B: Heurísticas de Confiança Visual

**`src/vision/template.py`**
- Pipeline de 5 estratégias de matching antes de concluir não encontrado
- `DiagnosticReport` — score de cada estratégia quando tudo falha
- `diagnose(template_path)` — executa todas as estratégias para debug

---

## [0.3.3] — 2026-05-02

### Adicionado — F2-A: Multi-scale Template Matching

**`src/vision/template.py`**
- `TemplateMatcher` isolado — instanciável independente do runner
- Multi-scale: testa escalas `(1.0, 0.9, 1.1, 0.8, 1.2)` e retorna melhor match
- Otimização: score >= 0.9 em escala 1.0 → retorna imediatamente

---

## [0.3.2] — 2026-05-02

### Adicionado

- `CadastroPacienteFlow` — 14/14 steps — validado 28/04/2026
- `TipoAnestesiaFlow` — 9/9 steps — validado 30/04/2026
- `CadastroFuncionarioFlow` (SisLab) — 10/10 steps — validado 02/05/2026

### Padrões consolidados
- Tab para navegar entre campos após clicar em Novo
- CPF sem pontuação para campos com máscara
- Validação por template preferível a OCR para mensagens de sucesso/erro
- Formulários APEX em dialog — acesso via `page.frames`
- Polling de URL após cliques OpenCV no MSI3

---

## [0.3.0] — 2026-04-27

### Adicionado

- `apex_helper.py` — helper centralizado Oracle APEX
- `ocr_helper.py` — helper centralizado OCR desktop
- `FrequenciaAplicacaoFlow` — reescrito, validado 10+ execuções
- `LoginFlowMsi3` — detecção de erro de credencial

---

## [0.2.0] — 2026

### Adicionado
- `OpenCVRunner`, `PlaywrightRunner`, `ExecutionObserver`
- Integração com Faker para dados únicos
- 32 testes unitários passando

---

## [0.1.0] — 2026

### Adicionado
- Estrutura inicial de pastas
- `LoginFlow`, `AdmissaoFlow`, `SuprimentosFlow` (esqueletos)