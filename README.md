# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA  
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.9d-purple)
![Testes](https://img.shields.io/badge/testes-297%20unitários-green)
![Fase](https://img.shields.io/badge/fase-5e%20AdmissaoComAgendamento-blue)

---

## O que é o VTAE

O VTAE é um framework híbrido de automação de testes que combina visão computacional (OpenCV), controle de browser (Playwright) e OCR (Tesseract) para interagir com qualquer sistema — como um usuário humano faria.

**O diferencial:** onde ferramentas puramente web (Playwright, Cypress, Selenium) não chegam, o VTAE chega. E onde ferramentas puramente desktop falham em aplicações web modernas, o VTAE também resolve.

Ideal para:
- Sistemas web modernos (Oracle APEX, React, Angular)
- Sistemas legados desktop sem API de automação (Oracle Forms, Citrix)
- Ambientes híbridos onde Playwright e OpenCV precisam trabalhar juntos

---

## Instalação e Configuração

### 1. Pré-requisitos do sistema operacional

**Python 3.13+**
```bash
python --version  # deve retornar 3.13.x
```

**Tesseract OCR** (obrigatório para leitura de campos via OCR)
- Windows: baixar em https://github.com/UB-Mannheim/tesseract/wiki
  - Durante a instalação, marcar o pacote de idioma **"Portuguese"**
  - Caminho padrão após instalação: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Verificar: `tesseract --version`

**pygetwindow** (obrigatório para controle de foco no Oracle Forms)
```bash
pip install pygetwindow
```

---

### 2. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd VTAE
```

---

### 3. Instalar dependências Python

```bash
pip install -r requirements.txt
pip install -e .
playwright install chromium
```

---

### 4. Configurar credenciais

Cada jornada tem seu próprio `.env` isolado. **Nunca commitar no Git.**

```bash
# configs/si3/si3_cadastro_paciente/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
# Deixe vazio para cadastrar novo automaticamente.
# Preencha para reutilizar paciente existente.
# ATENÇÃO: limpe após o teste para não afetar outras execuções.
SI3_PACIENTE_ID=

# configs/si3/si3_ambulatorio/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=

# configs/si3/si3_agendamento/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
```

---

### 5. Verificar instalação

```bash
# Testes unitários
python -m pytest tests/unit/ -v

# Verificar CLI
vtae systems
```

---

### 6. Executar o primeiro teste

Pré-requisitos:
- SI3 aberto e **maximizado** na tela principal
- Credenciais configuradas no `.env`
- Resolução 1920x1080

```bash
vtae run --test cadastro_paciente_jornada
```

---

## Estrutura do projeto

```
VTAE/
├── src/
│   ├── core/           # FlowContext, result, observer, types, estado_jornada
│   ├── vision/         # TemplateMatcher (multi-scale), OcrHelper
│   ├── runners/        # OpenCVRunner, PlaywrightRunner
│   ├── flows/
│   │   ├── si3/        # login, cadastro_paciente (23), admissao_internacao (18)
│   │   │               # admissao_ambulatorio (15), agendamento (13)
│   │   │               # admissao_com_agendamento ✅ criado
│   │   ├── sislab/     # login, cadastro_funcionario
│   │   └── msi3/       # login, frequencia_aplicacao, tipo_anestesia
│   ├── config/         # ConfigLoader + schema.py
│   └── cli/            # run.py, summary.py, send.py
├── configs/
│   └── si3/
│       ├── si3_cadastro_paciente/  config.yaml + .env
│       ├── si3_internacao/         config.yaml + .env
│       ├── si3_ambulatorio/        config.yaml + .env
│       └── si3_agendamento/        config.yaml + .env
├── templates/si3/
│   ├── cadastro_paciente/
│   ├── admissao_internacao/
│   ├── admissao_ambulatorio/
│   └── agendamento/
├── tests/
│   ├── unit/
│   │   ├── conftest.py      # mock_sleep autouse — SOMENTE aqui
│   │   └── test_*.py
│   └── integration/
│       ├── si3/
│       │   ├── test_login_real.py
│       │   ├── components/
│       │   │   └── cadastro_paciente_fixture.py  ← única fonte da lógica de cadastro
│       │   └── jornadas/
│       │       ├── ambulatorio/
│       │       │   ├── sem_agendamento/
│       │       │   │   ├── test_01_cadastro_paciente.py
│       │       │   │   └── test_02_admissao_ambulatorio.py
│       │       │   └── com_agendamento/
│       │       │       ├── test_01_cadastro_paciente.py
│       │       │       ├── test_02_agendamento.py
│       │       │       └── test_03_admissao_com_agendamento.py
│       │       └── internacao/
│       │           ├── test_01_cadastro_paciente.py
│       │           └── test_02_admissao_internacao.py
│       ├── msi3/
│       │   └── jornadas/intra_operatorio/
│       │       ├── test_frequencia_aplicacao.py
│       │       └── test_tipo_anestesia.py
│       └── sislab/
│           └── jornadas/cadastros/
│               └── test_01_cadastro_funcionario.py
├── scripts/
│   └── posicao_mouse.py
└── evidence/
    ├── flakiness.json
    ├── estado_jornada.json
    └── YYYY-MM-DD/<teste>/
```

---

## CLI

```bash
# Testes individuais
vtae run --test login_si3 - NÃO FUNCIONOU
vtae run --test cadastro_paciente_jornada - OK
vtae run --test admissao_ambulatorio_jornada : AJUSTAR
vtae run --test agendamento_jornada - ok
vtae run --test admissao_com_agendamento_jornada - AJUSTAR
vtae run --test admissao_internacao_jornada - AJUSTAR
vtae run --test frequencia_aplicacao - OK
vtae run --test tipo_anestesia - NÃO FUNCIONOU

# Jornadas completas (encadeadas — para se um step falhar)
vtae run --jornada ambulatorio                  # cadastro → admissão - AJUSTAR A ADMISSÃO
vtae run --jornada ambulatorio_com_agendamento  # cadastro → agendamento → admissão
vtae run --jornada internacao                   # cadastro → admissão internação

# Com repetição (valida estabilidade)
vtae run --jornada ambulatorio --repeat 3

# Observabilidade
vtae flakiness --top 5
vtae systems
vtae clean --days 7
```

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows | Status |
|---|---|---|---|---|
| SI3 | Desktop Oracle Forms | OpenCV | Login, CadastroPaciente (23), AdmissaoInternacao (18), AdmissaoAmbulatorio (15), Agendamento (13), AdmissaoComAgendamento | ✅ |
| SisLab | Desktop Oracle Forms | OpenCV | Login, CadastroFuncionario | ✅ |
| MSI3 | Web Oracle APEX 23.1 | Playwright + OpenCV | Login, FrequenciaAplicacao, TipoAnestesia | ✅ |

---

## Padrão SI3_PACIENTE_ID — isolamento por jornada

Cada jornada tem seu próprio `.env` com `SI3_PACIENTE_ID`:

```bash
SI3_PACIENTE_ID=        # vazio = cadastra novo paciente automaticamente
# SI3_PACIENTE_ID=505050  # preenchido = reutiliza paciente, pula o cadastro
```

Isso garante que jornadas diferentes não interferem entre si — especialmente importante com a regra de admissão aberta do SI3.

---

## Padrões consolidados

### Oracle Forms (SI3 / SisLab)
- `type_text()` obrigatório para campos com acentos
- `double_click` para menus
- `click_near` para campos grandes; coordenada direta para campos pequenos
- **LOV:** `_selecionar_via_lov()` + `verify_lov()` obrigatório após
- **LOV em grade:** `_lov_linha_tab()` — Tab Navigation, sem offset_y calculado
- **Campos de grade:** `pyperclip.copy() + ctrl+v`
- **Popup Editor (bug Oracle Forms):** 2x Escape antes de clicar em botões críticos
- **Foco perdido:** `_focar_si3()` — reativa janela Oracle Forms via pygetwindow
- **Template ausente:** `_tpl_existe()` — fallback com timeout, nunca quebra por PNG ausente
- Salvar: **F10** (não Ctrl+S)
- Navegação: **Localizar no Menu** (mais estável que Favoritos)

### Oracle APEX / MSI3
- Nunca navegar por URL direta — invalida a sessão APEX
- Cards sem href CSS — OpenCV obrigatório
- `networkidle` não funciona após cliques OpenCV — usar polling de URL

---

## Observabilidade

Cada execução gera em `evidence/YYYY-MM-DD/<teste>/`:

| Arquivo | Conteúdo |
|---|---|
| `execution.log` | Log estruturado com todos os prints do runner |
| `execution.json` | confidence_score e template_path por step |
| `report.html` | Relatório visual offline — série temporal + badges |
| `flakiness.json` | Histórico global de pass/fail por step |
| `estado_jornada.json` | paciente_id compartilhado entre steps da jornada |

**CausaFalha** classificada automaticamente:
`TEMPLATE_NAO_ENCONTRADO | TIMEOUT | OCR_LEITURA | COORDENADA | ESTADO_AUSENTE | SISTEMA | DESCONHECIDA`

---

## Fases do projeto

| Fase | Descrição | Status |
|---|---|---|
| 1–4c | Base, Clean Architecture, DSL | ✅ |
| 5a | CadastroPacienteFlow 23 steps, 3x | ✅ |
| 5b | Observabilidade básica | ✅ |
| 5c | Jornada ambulatório 3x | ✅ 26/05/2026 |
| Obs-Fase1 | verify_lov + verify_fill + score + logger + report.html | ✅ 26/05/2026 |
| 5d | AgendamentoFlow 13 steps, 3x | ✅ 27/05/2026 |
| Onda 1 | confirm_template + _focar_si3 + _tpl_existe + SI3_PACIENTE_ID | ✅ 27/05/2026 |
| **5e** | **AdmissaoComAgendamento + reorganização jornadas** | 🔵 28/05/2026 |
| Onda 2 | summary_generator.py gerencial | 🔜 |
| Onda 3 | Métricas + alertas regressão | 🔜 |
| 6 | YOLO fine-tuning | 🔜 |
| 7 | CI/CD Jenkins + RDP | 🔜 |
| 8 | Portfólio profissional | 🔜 |

---

## Documentação

| Arquivo | Descrição |
|---|---|
| `docs/VTAE_Prompt_Instrucao_Geral.md` | Estado atual — usar como contexto em novo chat |
| `docs/VTAE_Documentacao_Tecnica.docx` | Arquitetura, runners, matchers, exceções |
| `docs/VTAE_Manual_Criacao_Testes.docx` | Passo a passo para criar novos testes |
| `CHANGELOG.md` | Histórico de mudanças |