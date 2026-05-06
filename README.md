# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA  
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.0-purple)
![Testes](https://img.shields.io/badge/testes-189%20unitários-green)
![DT](https://img.shields.io/badge/débito%20técnico-concluído-brightgreen)

---

## O que é o VTAE

O VTAE é um framework híbrido de automação de testes que combina visão computacional (OpenCV), controle de browser (Playwright) e OCR (Tesseract) para interagir com qualquer sistema — como um usuário humano faria.

**O diferencial:** onde ferramentas puramente web (Playwright, Cypress, Selenium) não chegam, o VTAE chega. E onde ferramentas puramente desktop falham em aplicações web modernas, o VTAE também resolve.

Ideal para:
- Sistemas web modernos (Oracle APEX, React, Angular)
- Sistemas legados desktop sem API de automação (Oracle Forms, Citrix)
- Ambientes híbridos onde Playwright e OpenCV precisam trabalhar juntos

---

## Instalação

```bash
pip install -r requirements.txt
pip install -e .
playwright install chromium

# OCR — Tesseract (Windows)
# Baixar em: https://github.com/UB-Mannheim/tesseract/wiki
# Marcar "Portuguese" durante a instalação
python -c "from vtae.core.ocr_helper import OcrHelper; OcrHelper.verificar_instalacao()"
```

---

## Estrutura do projeto

```
VTAE/
├── src/                     ← Clean Architecture
│   ├── core/                # FlowContext, result, observer, types, exceções
│   ├── vision/              # TemplateMatcher (multi-scale), OcrHelper
│   ├── runners/             # OpenCVRunner, PlaywrightRunner
│   ├── flows/               # flows por sistema (si3, sislab, msi3)
│   ├── config/              # ConfigLoader + schema YAML
│   └── cli/                 # vtae run, systems, clean, send
├── vtae/                    ← aliases retrocompatibilidade
│   ├── configs/             # config.yaml + .env por sistema
│   └── tests/               # unit (189) + integration
├── templates/               # recortes de tela por sistema
└── evidence/                # screenshots e relatórios por execução
```

---

## Credenciais

Credenciais em `vtae/configs/<sistema>/.env` — **nunca no código nem no Git**.

```bash
# vtae/configs/si3/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha

# vtae/configs/sislab/.env
SISLAB_USER=seu_usuario
SISLAB_PASS=sua_senha

# vtae/configs/msi3/.env
MSI3_USER=seu_usuario
MSI3_PASS=sua_senha
MSI3_URL=https://seu-servidor/apex/login
```

---

## Testes unitários

```bash
python -m pytest vtae/tests/unit/ -v
# 189 testes — ~1.3s
```

---

## CLI — Executar testes

```bash
# teste específico
vtae run --test cadastro_paciente
vtae run --test tipo_anestesia

# módulo completo
vtae run --module si3
vtae run --module msi3

# todos os sistemas
vtae run --all

# ambiente e retry
vtae run --module si3 --env homologacao --retry 2

# utilitários
vtae systems
vtae systems --sistema si3
vtae clean --days 7
vtae send --module si3 --to gestor@incor.org.br
vtae send --all --to a@x.com --to b@x.com
```

---

## Runners

### OpenCVRunner — desktop

```python
from vtae.runners.opencv_runner import OpenCVRunner
from src.config import ConfigLoader

config = ConfigLoader.carregar("si3",
    configs_dir=__import__('pathlib').Path("vtae/configs"))
runner = OpenCVRunner(confidence=config.confidence)
```

### PlaywrightRunner — web

```python
from vtae.runners.playwright_runner import PlaywrightRunner
from src.config import ConfigLoader

config = ConfigLoader.carregar("msi3",
    configs_dir=__import__('pathlib').Path("vtae/configs"))
runner = PlaywrightRunner(url=config.url, headless=False)
```

### Modo híbrido — Playwright + OpenCV

```python
# Playwright — seletores CSS normais
page.get_by_role("link", name="Sistema de Pacientes").click()
frame.locator("#P17_FRAP_CD").fill(dados["codigo"])

# OpenCV — elementos sem href CSS (cards, canvas, iframes)
cv = OpenCVRunner(confidence=0.7)
cv.safe_click("templates/msi3/card_frequencia.png")
```

---

## Exceções tipadas

```python
from src.core.types import (
    TemplateNotFoundError,  # template OpenCV não encontrado após retries
    RunnerError,            # erro no runner (Playwright ou OpenCV)
    ConfigError,            # YAML inválido ou campo ausente
    StepError,              # falha em step de execução
)
```

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows | Steps | Status |
|---|---|---|---|---|---|
| SisLab | Desktop Oracle Forms | OpenCV | Login, CadastroFuncionario | 3 + 10 | ✅ |
| SI3 | Desktop Oracle Forms | OpenCV | Login, CadastroPaciente | 3 + 14 | ✅ |
| MSI3 | Web Oracle APEX 23.1 | Playwright + OpenCV | Login, FrequenciaAplicacao, TipoAnestesia | 5 + 10 + 9 | ✅ |

---

## Padrões consolidados

### Oracle Forms (SI3 / SisLab)
- `type_text()` obrigatório para campos com acentos
- `double_click` para menus
- `click_near` apenas para campos grandes e únicos — campos pequenos na mesma linha usam coordenada direta
- URL vazia válida no `AmbienteConfig` para sistemas desktop

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
| `FA01`... | `FrequenciaAplicacaoFlow` | MSI3 |
| `TA01`... | `TipoAnestesiaFlow` | MSI3 |

---

## Fases do projeto

| # | Fase | Status |
|---|---|---|
| 1 | Base de IA aplicada | ✅ |
| 2 | Automação inteligente (web, desktop, híbrido) | ✅ |
| 3 | Arquitetura de engenharia (Clean Arch, CLI, ConfigLoader) | ✅ |
| 4 | DSL expandida + YOLO | 🔵 Em andamento |
| 5 | CI/CD Jenkins + RDP | 🔜 |
| 6 | Portfólio profissional | 🔜 |

---

## Changelog

### v0.5.0 — 2026-05-06
- **DT-1:** credenciais migradas para `.env` + histórico Git limpo com `git filter-repo`
- **DT-2:** `CadastroPacienteFlow` — estratégia híbrida `click_near` + coordenada direta
- **DT-4:** `RuntimeError` → `TemplateNotFoundError` e `RunnerError` em todos os runners
- **DT-5:** pastas `bkp/` removidas, flow com acento deletado
- `conftest.py` sem dependência de `login_config.py`
- 189 testes unitários verdes em 1.24s

### v0.4.5
- `vtae send` — envio de relatório HTML por e-mail (SMTP/TLS/SSL/Gmail)
- 31 testes unitários para o módulo send

### v0.3.1
- `CadastroPacienteFlow` 14/14, `TipoAnestesiaFlow` 9/9, `CadastroFuncionarioFlow` 10/10
- `ConfigLoader` com resolução de variáveis `${VAR}` e `${VAR:-default}`
- CLI `vtae run` com retry, summary e envio automático
- Clean Architecture `src/`

---

## Documentação

| Arquivo | Descrição |
|---|---|
| `VTAE_Documentacao_Tecnica.docx` | Arquitetura, runners, matchers, exceções, padrões |
| `VTAE_Manual_Criacao_Testes.docx` | Passo a passo para criar novos testes |
| `VTAE_Roadmap_Revisado.docx` | Roadmap com ordem revisada |
