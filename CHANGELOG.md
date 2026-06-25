# Changelog — VTAE

Todas as mudanças significativas do projeto são documentadas aqui.

---

## [0.5.20] — 2026-06-25

### Adicionado — Comparação OCR robusta + verificação por estrutura

**`src/flows/base_flow.py`** (atualizado)
- `_normalizar(texto)` — remove acentos E separadores de data (`/`, `-`, `.`) antes de comparar. Resolve `CÂMARA→CMARA` e `04/11/2023→04112023` ao mesmo tempo
- `_similar(lido, esperado, tolerancia=0.30)` — distância de edição Levenshtein com 30% de tolerância. Aceita ruído de OCR em fontes Oracle Forms (`B→3`, `O→D`, `V→I`) sem abaixar o rigor para valores genuinamente errados
- `_verify_campo_obrigatorio` atualizado — agora compara valor lido vs esperado via `_similar()`, não apenas verifica se está vazio. Falha se vazio OU se valor for incompatível
- `_verify_campo_opcional` atualizado — mesma lógica, não-bloqueante. Adicionado parâmetro `valor_esperado` à assinatura

**`src/flows/si3/cadastro_min/cadastro_paciente_min_flow.py`** (atualizado)
- CM05 `_step_cm05_data_nascimento` reescrito com **verificação por estrutura** — não compara valor digitado vs exibido (Oracle Forms reformata DDMMYYYY→DD/MM/YYYY). Verifica que OCR leu pelo menos 6 dígitos no campo. Padrão de referência para todos os campos com máscara
- CM08 `_step_cm08_cor_etnia` — `_verify_campo_opcional` agora recebe `cor_etnia` como `valor_esperado`

### Padrões consolidados nesta sessão

- **Comparação OCR não pode ser literal** — EasyOCR em fontes Oracle Forms perde acentos e confunde caracteres similares. Sempre usar `_normalizar()` + `_similar()` antes de comparar
- **Campos com máscara: verificação por estrutura** — datas, CPFs, telefones têm reformatação automática. Verificar dígitos mínimos, não valor exato. Padrão documentado em CM05
- **Valor residual é falso sucesso** — campo preenchido com valor de execução anterior passa OCR mas tem valor errado. `_similar()` detecta isso com rigor proporcional
- **Cenário negativo via YAML funciona** — substituir lista por valor inválido (`TESTE ERRO`) → sistema rejeita → campo fica com valor residual diferente do esperado → `_similar()` detecta → AssertionError correto

### Validado
- `CadastroPacienteMinFlow` — 3x consecutivas ✅ (25/06/2026) com observabilidade completa
- Cenário negativo Sexo (`TESTE ERRO`) — detectado e reportado corretamente ✅
- Cenário negativo Cor/Etnia (`TESTE ERRO`) — AVISO não-bloqueante correto ✅

---

## [0.5.19] — 2026-06-25

### Adicionado — CadastroPacienteMinFlow completo + _selecionar_em_lov + OCR matrícula

**`src/flows/si3/cadastro_min/cadastro_paciente_min_flow.py`** (expandido)
- CM05: Data Nascimento + Hora — `_verify_campo_obrigatorio`
- CM06: Sexo via LOV aleatório — `_selecionar_em_lov` + `_verify_campo_obrigatorio`
- CM07: Nacionalidade — 3 caminhos (Brasileiro/Estrangeiro/Naturalizado), LOV aleatória por caminho, `_verificar_popup_erro_incor()` após cada OK
- CM08: Cor/Etnia via LOV aleatória — `_verify_campo_opcional`
- CM09: Gerar Matrícula + F10 + OCR matrícula/identificador + `_salvar_estado_jornada`
- CM10: Sair para Menu Principal
- Helper `_selecionar_em_lov()` — padrão universal: F9 → campo Localizar → digitar → OK
- Helper `_verificar_popup_erro_incor()` — detecção via `is_visible` (não pygetwindow)
- Helper `_aguardar_popup_fechar()` — polling por título via pygetwindow
- Helper `_aguardar_titulo_janela()` — para telas sem template (fundo variável)

**`configs/si3/si3_cadastro_paciente_min/config.yaml`** (expandido)
- `dados:` com listas sorteáveis: `sexo_opcoes`, `cor_etnia_opcoes`, `nacionalidade_opcoes`
- `estados_brasileiro` + `cidades_por_estado` (pares vinculados)
- `paises_estrangeiro`, `paises_naturalizado` + versões `_negativo`
- `dados_faker:` com `data_entrada_brasil`, `data_naturalizacao`, `nr_portaria`
- `regioes_ocr` calibradas: `campo_sexo`, `campo_nacionalidade`, `campo_cor_etnia`, `matricula`, `identificador`
- `coordenadas` para todos os popups (Brasileiro, Estrangeiro, Naturalizado, HC-INCOR)

### Validado
- `CadastroPacienteMinFlow` CM01-CM10 — 3x consecutivas ✅ (25/06/2026)

---

## [0.5.18] — 2026-06-23

### Adicionado — LoginSi3Flow + CadastroPacienteMinFlow + browser_launcher + Passo A Fase 1

**`src/runners/browser_launcher.py`** (NOVO)
- `abrir_si3_navegador(url)` — abre Edge via `subprocess.Popen` (não Playwright)
- Playwright bloqueado pelo Oracle Forms (detecta depuração remota e recusa carregar)
- Sleep bootstrap de 10s logo após abrir — único sleep sem substituto possível

**`src/flows/si3/login/login_si3_flow.py`** (NOVO)
- `LoginSi3Flow` — L01 (Usuário), L02 (Senha), L03 (Conectar + confirmação via `menu_principal_login.png`)
- Validado 3x consecutivas (22/06/2026)

**`src/flows/base_flow.py`** (Passo A da Fase 1)
- `_focar_navegador_sislab(titulo_parcial)`
- `_verify_campo_obrigatorio(ctx, nome, valor, step_id, regiao_key, ocr_holder)`
- `_verify_campo_opcional(ctx, nome, step_id, regiao_key, ocr_holder)`
- `_focar_si3()` — adicionada busca por "Menu Principal"

### Padrões consolidados
- Playwright bloqueado para Oracle Forms — subprocess obrigatório
- Templates via `pyautogui.screenshot()` + `PIL.crop()` — Win+Shift+S captura em escala errada
- `diagnose()`: template primeiro, screenshot depois
- `regioes_ocr` no YAML: espaço obrigatório após dois pontos
- Dois FlowContext quando configs diferentes

### Validado
- `LoginSi3Flow` — 3x consecutivas ✅ (22/06/2026)
- `CadastroPacienteMinFlow` CM01-CM04 ✅

---

## [0.5.17] — 2026-06-19

### Adicionado — Portabilidade + instalar.bat + vtae.bat
- `instalar.bat` — instalação do zero
- `vtae.bat` — wrapper que ativa `.venv` automaticamente
- `pytest-repeat` adicionado ao `requirements.txt`

### Corrigido
- `run.py`: subprocess usava `"python"` fixo → `sys.executable`
- CP19: race condition de clipboard — delay 0.15s entre `copy()` e `Ctrl+V`

---

## [0.5.16] — 2026-06-12

### Corrigido
- `loader.py`: `_parsear_env_file` cortava valores por `#` inline
- `loader.py` e `opencv_runner.py`: default `ocr_engine` corrigido para `"easyocr"`
- CP05: `Ctrl+A` não funciona em campo de data com máscara → `backspace(10x) + type_text`
- AB05: Guard `_titulo_janela_contem("AMBULAT", excluir="VERIFICAR")`

### Adicionado
- `scripts/testar_regiao_ocr.py`
- Contrato `SI3_PACIENTE_ID` no `.env`

---

## [0.5.15] — 2026-06-11
### Validado
- Jornada `ambulatorio` 3x consecutivas

---

## [0.5.14] — 2026-06-10
### Corrigido
- AI18: saída multi-tela reescrita
- AB01: migrado para "Localizar no Menu"

### Validado
- Jornada `internacao` 3x consecutivas

---

## [0.5.12] — 2026-06-08
### Adicionado
- `_clicar_aguardar()` no BaseFlow
- `observer.inject_logger(ctx)` obrigatório nos fixtures

---

## [0.5.11] — 2026-06-03
### Adicionado
- Tesseract removido — EasyOCR via pip puro
- `verify_fill` e `verify_lov` retornam `(bool, str)`

---

## [0.5.9x] — 2026-05-26 a 29
- AdmissaoInternacaoFlow AI01–AI18 validado
- AdmissaoAmbulatorioFlow AB01–AB15 validado 3x
- AgendamentoFlow AG01–AG13 validado 3x

---

## [0.4.0] — 2026-05-02
- Clean Architecture: estrutura `src/`

## [0.3.x] — 2026-05-02
- `CadastroPacienteFlow`, `TipoAnestesiaFlow`, `CadastroFuncionarioFlow` validados
- `TemplateMatcher` multi-scale, pipeline 5 estratégias
- `click_near(template, offset_x, offset_y)`

## [0.2.0] — 2026
- `OpenCVRunner`, `PlaywrightRunner`, `ExecutionObserver`

## [0.1.0] — 2026
- Estrutura inicial