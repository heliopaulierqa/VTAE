# Changelog — VTAE

Todas as mudanças significativas do projeto são documentadas aqui.

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

**Aliases em `vtae/`** — todos os módulos redirecionam para `src/` via re-export de uma linha. Testes existentes continuam funcionando sem alteração.

**Padrão para novos sistemas** — adicionar sistema = criar 4 pastas: `src/flows/<sistema>/`, `configs/<sistema>/`, `templates/<sistema>/`, `tests/integration/<sistema>/`

### Validado
- 32 testes unitários verdes após migração

---

## [0.3.5] — 2026-05-02

### Adicionado — F2-C: Anchor-based Clicking

**`src/runners/opencv_runner.py`**
- `click_near(template, offset_x, offset_y)` — encontra o template âncora e clica na posição deslocada
- Útil para Oracle Forms onde o label é estável mas o campo fica a distância fixa do label
- Exemplo: `runner.click_near("templates/si3/label_nome.png", offset_x=200)` encontra o label e clica no campo à direita

**`src/vision/template.py`**
- `find_anchor(anchor_path, offset_x, offset_y)` — implementação do anchor no `TemplateMatcher`

---

## [0.3.4] — 2026-05-02

### Adicionado — F2-B: Heurísticas de Confiança Visual

**`src/vision/template.py`**
- Pipeline de 5 estratégias de matching — tenta cada ajuste antes de concluir que não encontrou:
  1. Multi-scale sem ajuste (F2-A)
  2. Contraste +30%
  3. Brilho +20
  4. Equalização de histograma
  5. Escala de cinza
- `DiagnosticReport` — quando tudo falha, exibe score de cada estratégia tentada
- `diagnose(template_path)` — executa todas as estratégias e retorna relatório para debug
- Log automático quando ajuste é necessário: `[TemplateMatcher] match via 'contrast' (score=0.812, scale=1.0x)`

**Por que heurísticas:** Oracle Forms e sistemas legados têm renderização inconsistente — o mesmo botão pode aparecer com contraste diferente dependendo do tema Windows, DPI ou modo de compatibilidade. Os ajustes compensam essas variações sem recapturar o template.

**Exemplo de DiagnosticReport:**
```
Template não encontrado: 'templates/sislab/funcionario/btn_novo.png'
Threshold: 0.70
Scores por estratégia:
  ✗ original (multi-scale)    score=0.581
  ✗ contrast                  score=0.623
  ✗ brightness                score=0.598
  ✗ equalize                  score=0.612
  ✗ gray                      score=0.644
Dicas:
  - Reduza o confidence (ex: threshold=0.6)
  - Recapture o template com o sistema no mesmo estado
  - Verifique se a janela está maximizada
```

---

## [0.3.3] — 2026-05-02

### Adicionado — F2-A: Multi-scale Template Matching

**`src/vision/template.py`** (novo — extraído do OpenCVRunner)
- `TemplateMatcher` isolado — pode ser instanciado independente do runner
- Multi-scale matching: testa o template em escalas `(1.0, 0.9, 1.1, 0.8, 1.2)` e retorna o melhor match
- `MatchResult` dataclass — inclui posição `(x, y)`, `score`, `scale` e `adjustment`
- `find_best_score()` — retorna melhor score independente do threshold, usado pelo diagnóstico
- Otimização: score >= 0.9 em escala 1.0 → retorna imediatamente sem testar as outras escalas

**`src/runners/opencv_runner.py`** (atualizado)
- Delega todo o matching para `TemplateMatcher`
- `safe_click` loga score máximo quando falha: `score máximo: 0.63 (threshold: 0.70)`
- Loga escala usada quando diferente de 1.0: `match em escala 1.1x (score=0.847)`
- Aceita parâmetro `scales` para customizar escalas testadas por instância

**Por que multi-scale:** templates capturados em um browser/resolução podem não bater com a tela em outro momento se o zoom ou DPI for diferente.

### Validado
- 32 testes unitários verdes após F2-A, F2-B e F2-C

---

## [0.3.2] — 2026-05-02

### Adicionado

**`vtae/flows/cadastro_paciente_flow.py`** (validado)
- CadastroPacienteFlow — 14/14 steps passando — validado em 28/04/2026
- Estratégia de coordenadas diretas para todos os campos
- CP07 Nacionalidade: tratamento de 2 popups em sequência com Enter como fallback
- CP13: leitura da matrícula gerada via `OcrHelper.ler_regiao`
- CP14: sequência de saída em 3 etapas com coordenadas diretas

**`vtae/flows/tipo_anestesia_flow.py`** (novo, validado)
- TipoAnestesiaFlow — 9/9 steps passando — validado em 30/04/2026
- Navegação MSI3 via sidebar "Cirurgia (NOVO)" → cards → Tipo Anestesia
- TA04–TA06: OpenCV para cards sem href CSS, com confirmação por polling de URL
- TA08–TA09: Playwright via frame locator — formulário em dialog `f?p=152:19:...`

**`vtae/flows/cadastro_funcionario_flow_sislab.py`** (validado em 02/05/2026)
- CadastroFuncionarioFlow — 10/10 steps passando
- Login integrado no teste — fluxo end-to-end completo
- Navegação por Tab após clicar em Novo — padrão Oracle Forms
- Dropdowns Cargo e Departamento selecionados por seta (posição fixa)
- CF09: validação por template `msg_sucesso.png`
- CF10: verificação do nome na grade via OCR com `_REGIAO_GRADE = (0, 620, 1366, 660)`

**`vtae/configs/sislab/cadastro_funcionario_config.py`** (atualizado)
- CPF sem formatação — campo com máscara rejeita pontuação
- Cargo e Departamento fixos (dropdowns)

### Padrões consolidados

- **Tab para navegar entre campos** — após clicar em Novo, foco vai para o primeiro campo automaticamente
- **CPF sem pontuação** — enviar só dígitos para campos com máscara
- **Validação por template** preferível a OCR para mensagens de sucesso/erro
- **Formulários APEX em dialog** — acesso via `page.frames` iterando pelo ID do campo
- **Polling de URL após OpenCV** — `networkidle` não funciona após cliques OpenCV no MSI3

---

## [0.3.1] — 2026-04-28

> Versão de documentação — sem alterações de código.

### Atualizado

- `README.md` — v0.3.1
- `VTAE_Documentacao_v031.docx` — documentação completa do projeto
- `VTAE_Manualv3.docx` — manual do desenvolvedor v0.3.0

---

## [0.3.0] — 2026-04-27

### Adicionado

**`vtae/core/apex_helper.py`**
- Helper centralizado para interações com Oracle APEX (MSI3)
- Seletores validados: APEX 23.1 / Universal Theme 42
- `verificar_sem_erro()`, `verificar_sucesso()`, `aguardar_spinner()`
- `verificar_registro_na_grade()`, `inspecionar_pagina()`, `obter_titulo_pagina()`

**`vtae/core/ocr_helper.py`**
- Helper centralizado de OCR para sistemas desktop
- Pré-processamento: escala de cinza → 2x → threshold adaptativo gaussiano
- `ler_regiao()`, `ler_tela_inteira()`, `contem_qualquer_token()`, `salvar_debug()`

**`vtae/flows/frequencia_aplicacao_flow.py`** (reescrito)
- Validado em 10+ execuções consecutivas no ambiente MSI3

**`vtae/flows/login_flow_msi3.py`** (atualizado)
- Detecção de erro de credencial via `ApexHelper.verificar_sem_erro`

### Corrigido

- Encoding com acentos no Windows/Python 3.13 — `get_by_role("link")` no sidebar
- Sessão APEX invalidada por navegação direta via URL

---

## [0.2.0] — 2026

### Adicionado
- `OpenCVRunner` — runner desktop com visão computacional
- `PlaywrightRunner` — runner web com browser maximizado
- `ExecutionObserver` — logs, JSON e relatório HTML automático
- `FrequenciaAplicacaoFlow` — fluxo completo MSI3 com Playwright + OpenCV
- `LoginFlowMsi3` — login web Oracle APEX
- Integração com **Faker** para dados únicos
- 32 testes unitários passando

---

## [0.1.0] — 2026

### Adicionado
- Estrutura inicial de pastas
- `LoginFlow`, `AdmissaoFlow`, `SuprimentosFlow` (esqueletos)
- `LoginConfigSisLab`
