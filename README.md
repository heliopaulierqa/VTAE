# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA  
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.3-purple)
![Testes](https://img.shields.io/badge/testes-314%20unitários-green)
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
│   │   ├── si3/             # cadastro_paciente_flow, admissao_internacao_flow
│   │   ├── sislab/
│   │   └── msi3/
│   ├── config/              # ConfigLoader + schema YAML
│   └── cli/                 # vtae run, systems, clean, send
├── vtae/                    ← aliases retrocompatibilidade
│   ├── configs/             # config.yaml + .env por sistema/funcionalidade
│   │   ├── si3/
│   │   │   ├── config.yaml            # cadastro paciente
│   │   │   ├── si3_internacao/        # admissão internação
│   │   │   │   ├── config.yaml
│   │   │   │   └── .env
│   │   ├── msi3/
│   │   └── sislab/
│   └── tests/               # unit (314) + integration
├── templates/               # recortes de tela por sistema
│   └── si3/
│       └── admissao_internacao/   # templates do fluxo de internação
├── scripts/
│   └── posicao_mouse.py     # utilitário para capturar coordenadas
└── evidence/                # screenshots e relatórios por execução
```

---

## Credenciais

Credenciais em `vtae/configs/<sistema>/.env` — **nunca no código nem no Git**.

```bash
# vtae/configs/si3/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha

# vtae/configs/si3/si3_internacao/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=7029594   # ID do paciente de teste — LGPD

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
# 314 testes — ~2s
```

---

## CLI — Executar testes

```bash
# teste específico
vtae run --test cadastro_paciente
vtae run --test admissao_internacao
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

## Utilitário — Captura de coordenadas

Para capturar coordenadas de elementos na tela (necessário na criação de novos testes desktop):

```bash
python scripts/posicao_mouse.py
```

O script captura até 4 coordenadas com contagem regressiva de 5 segundos cada. Útil para identificar campos pequenos que exigem coordenada direta no Oracle Forms.

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

## DSL Expandida (v0.5.1 — v0.5.3)

O VTAE possui uma DSL YAML que permite criar testes sem escrever Python:

```yaml
flow: cadastro_paciente
sistema: si3
steps:
  - action: fill_field
    template: templates/si3/label_nome.png
    offset_x: 200
    value: <<DADOS.nome>>

  - action: assert_visible
    template: templates/si3/btn_salvar.png

  - action: loop
    count: 3
    steps:
      - action: fill_field
        template: templates/si3/campo.png
        value: <<LOOP.index>>

  - action: if
    condition: {type: assert_visible, target: templates/si3/msg_erro.png}
    then:
      - action: click
        template: templates/si3/btn_ok.png
    else:
      - action: assert_text
        selector: "#resultado"
        text: "Sucesso"
```

**Ações disponíveis:** `fill_field`, `assert_visible`, `assert_text`, `select_dropdown`, `run_component`, `loop`, `if/else`

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows | Steps | Status |
|---|---|---|---|---|---|
| SisLab | Desktop Oracle Forms | OpenCV | Login, CadastroFuncionario | 3 + 10 | ✅ |
| SI3 | Desktop Oracle Forms | OpenCV | Login, CadastroPaciente, AdmissaoInternacao | 3 + 14 + 18 | ✅ |
| MSI3 | Web Oracle APEX 23.1 | Playwright + OpenCV | Login, FrequenciaAplicacao, TipoAnestesia | 5 + 10 + 9 | ✅ |

---

## Padrões consolidados

### Oracle Forms (SI3 / SisLab)
- `type_text()` obrigatório para campos com acentos
- `double_click` para menus
- `click_near` apenas para campos grandes e únicos — campos pequenos na mesma linha usam coordenada direta
- Campos de LOV — clicar no botão `[...]`, buscar, OK
- Dropdowns com animação — `time.sleep(1.5)` antes de clicar na opção + template OpenCV para a opção
- Popups que abrem em posição variável — usar template OpenCV para o botão OK
- URL vazia válida no `AmbienteConfig` para sistemas desktop
- ID do paciente sempre via `.env` (LGPD — nunca hardcoded)

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

Cada sistema tem sua pasta de config. Funcionalidades dentro de um mesmo sistema ficam em subpastas:

```
vtae/configs/
├── si3/
│   ├── config.yaml            # cadastro paciente
│   ├── .env
│   └── si3_internacao/        # admissão internação
│       ├── config.yaml
│       └── .env               # contém SI3_PACIENTE_ID
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
    "si3_internacao",
    configs_dir=pathlib.Path("vtae/configs/si3")
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
| 5 | YOLO dataset + fine-tuning | 🔵 Em andamento |
| 6 | CI/CD Jenkins + RDP | 🔜 |
| 7 | Portfólio profissional | 🔜 |

---

## Changelog

### v0.5.3 — 2026-05-08
- `AdmissaoInternacaoFlow` — 18 steps, 21/21 passando
- ID do paciente via `.env` (conformidade LGPD)
- Padrão de subpasta de config por funcionalidade (`vtae/configs/si3/si3_internacao/`)
- `scripts/posicao_mouse.py` — captura até 4 coordenadas com contagem regressiva
- DSL: `loop` (count/items, `<<LOOP.item>>`, `<<LOOP.index>>`), `if/else`
- 314 testes unitários verdes em 2s

### v0.5.2 — 2026-05-07
- DSL: `select_dropdown`, `run_component`
- 3 componentes reutilizáveis: `cadastro_paciente_component`, `cadastro_funcionario_component`, `apex_form_component`

### v0.5.1 — 2026-05-07
- DSL expandida: `fill_field`, `assert_visible`, `assert_text`, interpolação `<<DADOS.campo>>`

### v0.5.0 — 2026-05-06
- Débito técnico concluído
- 189 → 314 testes unitários
- `mock_sleep` autouse fixture — suite unitária: 206s → 2s

### v0.4.5
- `vtae send` — envio de relatório HTML por e-mail

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
| `VTAE_Manual_Criacao_Testes.docx` | Passo a passo detalhado para criar novos testes do zero |
| `VTAE_Manual.docx` | Manual do desenvolvedor |
| `VTAE_Roadmap_fases_4_5.docx` | Roadmap com ordem revisada |