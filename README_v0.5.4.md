# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA  
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.6-purple)
![Testes](https://img.shields.io/badge/testes-372%20unitários-green)
![Fase](https://img.shields.io/badge/fase-5a%20em%20andamento-orange)

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

**Git**
```bash
git --version
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

Verificar instalação do OCR:
```bash
python -c "from src.vision.ocr import OcrHelper; print('OCR OK')"
```

---

### 4. Configurar credenciais

Crie os arquivos `.env` nas pastas de config. **Nunca commitar no Git.**

```bash
# configs/si3/si3_cadastro_paciente/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
```

Para outros sistemas:
```bash
# configs/sislab/.env
SISLAB_USER=seu_usuario
SISLAB_PASS=sua_senha

# configs/msi3/.env
MSI3_USER=seu_usuario
MSI3_PASS=sua_senha
MSI3_URL=https://seu-servidor/apex/login
```

---

### 5. Verificar instalação

```bash
# Testes unitários — devem passar todos em ~8s
python -m pytest tests/unit/ -v

# Verificar CLI
vtae systems
```

---

### 6. Executar o primeiro teste de integração

Pré-requisitos antes de rodar:
- SI3 aberto e **maximizado** na tela principal (Menu Principal)
- Credenciais configuradas no `.env`
- Tesseract instalado com pacote Portuguese

```bash
vtae run --test cadastro_paciente_jornada
```

Evidências salvas em: `evidence/<data>/test_cadastro_paciente_jornada/`

---

### Observações para outro computador

- **Coordenadas dependem de resolução**: se a resolução da tela for diferente, as coordenadas no `config.yaml` precisarão ser recalibradas com `python scripts/posicao_mouse.py`
- **Templates dependem de zoom**: se o Oracle Forms estiver com zoom diferente, recapturar os templates em `templates/si3/cadastro_paciente/`
- **Tesseract path**: se instalado em caminho diferente do padrão, configurar a variável de ambiente `TESSDATA_PREFIX`

---

## Estrutura do projeto

```
VTAE/
├── src/                     ← Clean Architecture
│   ├── core/                # FlowContext, result, observer, types, exceções
│   ├── vision/              # TemplateMatcher (multi-scale), OcrHelper
│   ├── runners/             # OpenCVRunner, PlaywrightRunner
│   ├── flows/               # flows por sistema (si3, sislab, msi3)
│   │   ├── si3/             # cadastro_paciente_flow, login_flow
│   │   ├── sislab/
│   │   └── msi3/
│   ├── config/              # ConfigLoader + schema YAML
│   └── cli/                 # vtae run, systems, clean, send
├── configs/                 ← configs por sistema (configs_dir padrão)
│   ├── si3/
│   │   └── si3_cadastro_paciente/
│   │       ├── config.yaml  # coordenadas, dados_faker, credenciais
│   │       └── .env         # SI3_USER, SI3_PASS
│   ├── msi3/
│   └── sislab/
├── templates/               # recortes de tela por sistema
│   └── si3/
│       └── cadastro_paciente/
├── tests/
│   ├── unit/
│   │   ├── conftest.py      # mock_sleep autouse — SOMENTE aqui
│   │   └── test_cadastro_paciente_flow.py
│   └── integration/
│       └── jornadas/
│           └── ambulatorio/
│               └── test_01_cadastro_paciente.py
├── scripts/
│   └── posicao_mouse.py     # captura coordenadas com contagem regressiva
└── evidence/                # screenshots e relatórios por execução
    └── estado_jornada.json  # paciente_id gerado — compartilhado entre testes
```

---

## Credenciais

Credenciais em `configs/<sistema>/<subpasta>/.env` — **nunca no código nem no Git**.

```bash
# configs/si3/si3_cadastro_paciente/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
```

---

## Testes unitários

```bash
python -m pytest tests/unit/ -v
# 372 testes — ~8s
```

> ⚠️ O `conftest.py` com `mock_sleep autouse` deve estar em `tests/unit/conftest.py`.  
> Não coloque em `tests/conftest.py` — isso aplicaria o mock nos testes de integração e  
> mascararia problemas reais de timing no Oracle Forms.

---

## CLI — Executar testes

```bash
# jornada completa
vtae run --test cadastro_paciente_jornada

# módulo completo
vtae run --module si3

# todos os sistemas
vtae run --all

# ambiente e retry
vtae run --module si3 --env homologacao --retry 2

# utilitários
vtae systems
vtae clean --days 7
vtae send --module si3 --to gestor@incor.org.br
```

---

## Utilitário — Captura de coordenadas

Para capturar coordenadas de elementos na tela (necessário na criação de novos testes desktop):

```bash
python scripts/posicao_mouse.py
```

Captura até 4 coordenadas com contagem regressiva de 5 segundos cada. Útil para identificar campos pequenos que exigem coordenada direta no Oracle Forms.

---

## Runners

### OpenCVRunner — desktop

```python
from src.runners.opencv_runner import OpenCVRunner
from src.config import ConfigLoader

config = ConfigLoader.carregar(
    "si3_cadastro_paciente",
    configs_dir=pathlib.Path("configs/si3")
)
runner = OpenCVRunner(confidence=config.confidence)
```

### PlaywrightRunner — web

```python
from src.runners.playwright_runner import PlaywrightRunner

config = ConfigLoader.carregar("msi3", configs_dir=pathlib.Path("configs"))
runner = PlaywrightRunner(url=config.url, headless=False)
```

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows | Status |
|---|---|---|---|---|
| SisLab | Desktop Oracle Forms | OpenCV | Login, CadastroFuncionario | ✅ |
| SI3 | Desktop Oracle Forms | OpenCV | Login, CadastroPaciente | ✅ 21/22 steps |
| MSI3 | Web Oracle APEX 23.1 | Playwright + OpenCV | Login, FrequenciaAplicacao, TipoAnestesia | ✅ |

---

## Padrões consolidados

### Oracle Forms (SI3 / SisLab)

- `type_text()` obrigatório para campos com acentos
- `double_click` para menus
- `click_near` para campos grandes e únicos — campos pequenos usam coordenada direta
- **Campos de grade** (aba Documentos): usar `pyperclip.copy() + ctrl+v` — `pyautogui.write()` é ignorado
- Campos de LOV: clicar no botão `[...]`, buscar no popup, OK
- Dropdowns de escolha (ex: Frequenta Escola): clicar no campo para abrir + clicar na opção
- Popups de posição variável: usar template OpenCV para o botão OK com threshold 0.55
- URL vazia válida no `AmbienteConfig` para sistemas desktop
- ID do paciente sempre via `.env` (LGPD — nunca hardcoded)
- Coordenadas TODAS no `config.yaml` — nunca hardcoded no flow

### Oracle APEX / MSI3

- Nunca navegar por URL direta — invalida a sessão APEX
- Cards sem href CSS — OpenCV obrigatório
- `networkidle` não funciona após cliques OpenCV — usar polling de URL
- Formulários dialog abrem em frame separado — acessar via `page.frames`

---

## Convenção de IDs de steps

| Prefixo | Flow | Sistema |
|---|---|---|
| `L01`... | `LoginFlow` | SisLab / SI3 desktop |
| `MW01`... | `LoginFlowMsi3` | MSI3 Oracle APEX |
| `CF01`... | `CadastroFuncionarioFlow` | SisLab |
| `CP01`... | `CadastroPacienteFlow` | SI3 |
| `AI01`... | `AdmissaoInternacaoFlow` | SI3 |
| `FA01`... | `FrequenciaAplicacaoFlow` | MSI3 |
| `TA01`... | `TipoAnestesiaFlow` | MSI3 |

---

## Organização de configs por sistema

```
configs/
├── si3/
│   └── si3_cadastro_paciente/
│       ├── config.yaml   # coordenadas, dados_faker
│       └── .env          # SI3_USER, SI3_PASS
├── msi3/
│   ├── config.yaml
│   └── .env
└── sislab/
    ├── config.yaml
    └── .env
```

No teste, aponte `configs_dir` para a pasta do sistema:

```python
config = ConfigLoader.carregar(
    "si3_cadastro_paciente",
    configs_dir=pathlib.Path("configs/si3")
)
```

---

## Fases do projeto

| # | Fase | Status |
|---|---|---|
| 1 | Base de IA aplicada | ✅ |
| 2 | Automação inteligente (web, desktop, híbrido) | ✅ |
| 3 | Arquitetura de engenharia (Clean Arch, CLI, ConfigLoader) | ✅ |
| 4 | DSL expandida (fill_field, assert, loop, if/else) | ✅ |
| 4b | Admissão de Internação SI3 (18 steps, LGPD) | ✅ |
| 5a | CadastroPacienteFlow integração real — 21/22 steps | 🔵 Em andamento |
| 5b | Observabilidade (enum CausaFalha, flakiness.json, health check) | 🔜 |
| 6 | CI/CD Jenkins + RDP | 🔜 |
| 7 | Portfólio profissional | 🔜 |

---

## Changelog

### v0.5.6 — 2026-05-19
- `CadastroPacienteFlow` 21/22 steps passando em integração real
- Jornada completa: Login → Dados gerais → Endereço → Comunicação → Documentos → Gerar Matrícula
- `pyperclip` para campos de grade Oracle Forms (aba Documentos)
- CEP com auto-preenchimento via OCR: só preenche Número+Complemento quando logradouro vem preenchido
- LOV de Comunicação com popup próprio (coordenadas específicas)
- Frequenta Escola: clique direto no dropdown (seta do teclado não funciona no Oracle Forms)
- `mock_sleep` autouse movido para `tests/unit/conftest.py` (não afeta mais integração)
- 372 testes unitários verdes em ~8s

### v0.5.3 — 2026-05-08
- `AdmissaoInternacaoFlow` — 18 steps, 21/21 passando
- ID do paciente via `.env` (conformidade LGPD)
- Padrão de subpasta de config por funcionalidade
- `scripts/posicao_mouse.py` — captura até 4 coordenadas com contagem regressiva
- DSL: `loop`, `if/else`
- 314 testes unitários verdes em 2s

### v0.5.2 — 2026-05-07
- DSL: `select_dropdown`, `run_component`
- 3 componentes reutilizáveis

### v0.5.1 — 2026-05-07
- DSL expandida: `fill_field`, `assert_visible`, `assert_text`

### v0.5.0 — 2026-05-06
- Débito técnico concluído
- 189 → 314 testes unitários
- `mock_sleep` autouse fixture — suite unitária: 206s → 2s

---

## Documentação

| Arquivo | Descrição |
|---|---|
| `VTAE_Documentacao_Tecnica.docx` | Arquitetura, runners, matchers, exceções, padrões |
| `VTAE_Manual_Criacao_Testes.docx` | Passo a passo detalhado para criar novos testes |
| `VTAE_Continuacao_5a_v2.docx` | Prompt de continuação — estado atual da Fase 5a |
| `VTAE_Roadmap_v055.docx` | Roadmap com fases e prioridades |