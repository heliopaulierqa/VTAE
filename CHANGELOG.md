# Changelog — VTAE

Todas as mudanças significativas do projeto são documentadas aqui.

---

## [0.3.0] — 2026-04-27

### Adicionado

**`vtae/core/apex_helper.py`**
- Helper centralizado para interações com Oracle APEX (MSI3)
- Seletores validados no ambiente real: APEX 23.1 / Universal Theme 42
- Suporte automático a iframes — busca em página principal e frames
- `verificar_sem_erro()` — detecta mensagem de erro do APEX após ações críticas
- `verificar_sucesso()` — aguarda confirmação de sucesso
- `aguardar_spinner()` — substitui `time.sleep` fixo após ações AJAX
- `verificar_registro_na_grade()` — lê grade via Playwright (sem OCR em sistemas web)
- `inspecionar_pagina()` — snapshot do estado da página para debug (inclui frames)
- `obter_titulo_pagina()` — confirma navegação na tela certa

**`vtae/core/ocr_helper.py`**
- Helper centralizado de OCR para sistemas desktop (Oracle Forms)
- Pré-processamento otimizado: escala de cinza → 2x → threshold adaptativo gaussiano
- `ler_regiao()` — lê texto de área específica da tela
- `ler_tela_inteira()` — leitura completa para debug
- `contem_qualquer_token()` — validação tolerante a erros do Tesseract
- `salvar_debug()` — salva imagem pré-processada para inspeção visual
- `verificar_instalacao()` — confirma Tesseract configurado corretamente

**`vtae/flows/frequencia_aplicacao_flow.py`** (reescrito)
- Navegação 100% via sidebar do Playwright — estável e sem dependência de encoding
- FA01–FA03: `get_by_role("link")` no sidebar — normaliza acentos automaticamente
- FA04: OpenCV cirúrgico para card sem href CSS acessível
- FA05–FA10: Playwright puro via iframe com IDs confirmados no DevTools
- Verificação final via `ApexHelper.verificar_registro_na_grade`
- Validado em 10+ execuções consecutivas no ambiente MSI3

**`vtae/flows/login_flow_msi3.py`** (atualizado)
- MW04: `ApexHelper.verificar_sem_erro` após submeter — credencial inválida vira mensagem clara em vez de timeout de 15s
- MW05: `ApexHelper.inspecionar_pagina` no except — URL, título e erro no log

**`vtae/flows/cadastro_funcionario_flow_sislab.py`** (novo)
- Flow completo para cadastro de funcionário no SisLab (Oracle Forms desktop)
- CF01–CF08: OpenCV com fallback de coordenadas
- CF09: verificação da grade via OCR (`OcrHelper.contem_qualquer_token`)

**`vtae/configs/sislab/cadastro_funcionario_config.py`** (novo)
- Credenciais e dados dinâmicos com Faker para cadastro de funcionário

**`vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py`** (novo)
- Arquivo de teste para o `CadastroFuncionarioFlow`

### Mapa de navegação MSI3 documentado

Confirmado em 27/04/2026 — navegação obrigatória via cliques (URL direta invalida sessão APEX):

```
Home → sidebar "Sistema de Pacientes" → p1_modu_nr=337
     → sidebar "Apoio"                → p1_modu_nr=401
     → sidebar "Cadastros"            → sec_menu?p2_modu_nr=402
     → OpenCV card                    → sec_menu?p2_modu_nr=405
     → Novo Cadastro → iframe formulário
```

IDs dos campos do formulário de Frequência de Aplicação (iframe APEX 23.1):
- `#P17_FRAP_SQ_EXIBICAO`, `#P17_FRAP_CD`, `#P17_FRAP_NM`
- `#P17_FRAP_TP_CONTAINER`, `#P17_FRAP_CK_USO_FLUXO_0`
- `#P17_FRAP_QT_DIAS_SEMANA`, `#P17_FRAP_QT_24HS`
- `#P17_FRAP_INTERVAL_MIN_CONF_HORARIO`, `#P17_HORA`, `#P17_UNFU_DS`

### Corrigido

- Problema de encoding com acentos no Windows/Python 3.13 — resolvido usando `get_by_role("link")` no sidebar em vez de `has_text` com caracteres especiais
- Sessão APEX invalidada por navegação direta via URL — corrigido usando cliques no menu em vez de `navigate()` com módulo direto
- Indentação corrompida em múltiplas iterações do flow — arquivo reescrito do zero com verificação de sintaxe

---

## [0.2.0] — 2026

### Adicionado
- `OpenCVRunner` — runner desktop com visão computacional
- `PlaywrightRunner` — runner web com browser maximizado
- `ExecutionObserver` — logs, JSON e relatório HTML automático
- `report_generator.py` — relatório HTML com screenshots e lightbox
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
