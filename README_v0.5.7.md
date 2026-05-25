# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA  
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.7c-purple)
![Testes](https://img.shields.io/badge/testes-372%20unitários-green)
![Fase](https://img.shields.io/badge/fase-5c%20jornada%20ambulatório-blue)

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

# configs/si3/si3_ambulatorio/.env
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
├── src/                          ← Clean Architecture
│   ├── core/                     # FlowContext, result, observer, types,
│   │                             # estado_jornada, health_check
│   ├── vision/                   # TemplateMatcher (multi-scale), OcrHelper
│   ├── runners/                  # OpenCVRunner, PlaywrightRunner
│   ├── flows/
│   │   ├── si3/                  # login_flow, cadastro_paciente_flow (CP01-CP23)
│   │   │                         # admissao_internacao_flow (AI01-AI18)
│   │   │                         # admissao_ambulatorio_flow (AB01-AB15)
│   │   ├── sislab/               # login_flow, cadastro_funcionario_flow
│   │   └── msi3/                 # login_flow, frequencia_aplicacao_flow,
│   │                             # tipo_anestesia_flow, apex_helper
│   ├── config/                   # ConfigLoader (loader.py) + schema.py
│   └── cli/                      # vtae run, systems, clean, send, flakiness
├── configs/
│   └── si3/
│       ├── si3_cadastro_paciente/
│       │   ├── config.yaml       # coordenadas, regioes_ocr, dados_faker
│       │   └── .env              # SI3_USER, SI3_PASS (LGPD)
│       ├── si3_internacao/
│       │   ├── config.yaml
│       │   └── .env              # SI3_PACIENTE_ID (LGPD)
│       └── si3_ambulatorio/
│           ├── config.yaml       # coordenadas, dados, cenarios_provedor,
│           │                     # procedimentos
│           └── .env              # SI3_USER, SI3_PASS (LGPD)
├── templates/
│   └── si3/
│       ├── cadastro_paciente/
│       ├── admissao_internacao/
│       └── admissao_ambulatorio/
├── tests/
│   ├── unit/
│   │   ├── conftest.py           # mock_sleep autouse — SOMENTE aqui
│   │   └── test_*.py
│   └── integration/
│       └── jornadas/
│           └── ambulatorio/
│               ├── test_01_cadastro_paciente.py     ✅ Fase 5a
│               └── test_02_admissao_ambulatorio.py  🔵 Fase 5c
├── scripts/
│   └── posicao_mouse.py          # captura coordenadas com contagem regressiva
└── evidence/
    ├── flakiness.json            # histórico global de pass/fail por step
    ├── estado_jornada.json       # compartilhado entre testes da jornada
    └── YYYY-MM-DD/<teste>/       # screenshots + logs + report.html
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
# teste isolado
vtae run --test cadastro_paciente_jornada

# teste isolado com repetição (valida estabilidade)
vtae run --test cadastro_paciente_jornada --repeat 3

# jornada encadeada (test_01 → test_02 → ...)
vtae run --jornada ambulatorio

# módulo completo
vtae run --module si3

# todos os sistemas
vtae run --all

# ambiente e retry
vtae run --module si3 --env homologacao --retry 2

# observabilidade — análise de flakiness
vtae flakiness --top 5          # top 5 steps mais instáveis
vtae flakiness --min-falhas 1   # steps que falharam ao menos 1x

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

Captura até 4 coordenadas com contagem regressiva de 5 segundos cada.  
Sempre usar com o sistema **maximizado** e na **mesma resolução** de produção (1920x1080).

---

## Runners

### OpenCVRunner — desktop

```python
from src.runners.opencv_runner import OpenCVRunner
from src.config.loader import ConfigLoader
import pathlib

config = ConfigLoader.carregar(
    "si3_cadastro_paciente",
    configs_dir=pathlib.Path("configs/si3")
)
runner = OpenCVRunner(confidence=config.confidence)
```

### PlaywrightRunner — web

```python
from src.runners.playwright_runner import PlaywrightRunner
from src.config.loader import ConfigLoader
import pathlib

config = ConfigLoader.carregar("msi3", configs_dir=pathlib.Path("configs"))
runner = PlaywrightRunner(url=config.url, headless=False)
```

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows | Status |
|---|---|---|---|---|
| SisLab | Desktop Oracle Forms | OpenCV | Login, CadastroFuncionario | ✅ |
| SI3 | Desktop Oracle Forms | OpenCV | Login, CadastroPaciente (23 steps), AdmissaoInternacao (18 steps), AdmissaoAmbulatorio (15 steps) | ✅ / 🔵 |
| MSI3 | Web Oracle APEX 23.1 | Playwright + OpenCV | Login, FrequenciaAplicacao, TipoAnestesia | ✅ |

---

## config.yaml — estrutura completa (v0.5.7c)

A partir da v0.5.7c o config.yaml suporta a seção `dados:` para dados fixos e estruturados,
além da `dados_faker:` para dados gerados dinamicamente. Ambas são acessíveis via `config.DADOS`.

```yaml
sistema: si3_ambulatorio
tipo: desktop
runner: opencv

ambientes:
  dev:
    url: ''
    confidence: 0.75

credenciais:
  usuario: ${SI3_USER}
  senha: ${SI3_PASS}

dados_faker:
  - campo: nome
    tipo: faker
    metodo: name
    transformacao: sem_prefixo_upper

# Dados fixos — strings, listas, dicts aninhados
# Acessíveis via config.DADOS no flow
dados:
  unidade_funcional: 'SC MONITORIZACAO AMBULATORIAL'
  cenario_provedor: 'sus'   # sus | convenio_allianz | convenio_unimed | ...
  cenarios_provedor:
    sus:
      provedor: 'SUS'
      plano: 'SUS'
      numero_carteirinha: ''
      validade_carteirinha: ''
    convenio_allianz:
      provedor: 'ALLIANZ'
      plano: 'EXCELLENCE'
      numero_carteirinha: '54354354353'
      validade_carteirinha: '30/07/2028'
  procedimentos:
    - { codigo: 'SCF-CONS', complemento: 'CASO NOVO', area_executora: '', profissional: 'MEDICO' }
    - { codigo: 'ECG', complemento: 'SEGUIMENTO', area_executora: 'COMISSAO CIENTIFICA', profissional: 'MEDICO' }

coordenadas:
  campo_identificador_amb:  { x: 530, y: 180 }
  campo_medico_nome:        { x: 235, y: 471 }

regioes_ocr:
  nr_admissao_amb: { x1: 10, y1: 40, x2: 200, y2: 70 }
```

**Regras:** `coordenadas`, `regioes_ocr` e `dados` ficam SEMPRE no config.yaml — nunca no flow.

---

## Padrões consolidados

### Oracle Forms (SI3 / SisLab)

- `type_text()` obrigatório para campos com acentos
- `double_click` para menus
- `click_near` para campos grandes e únicos — campos pequenos usam coordenada direta
- **Campos de grade** (aba Documentos): usar `pyperclip.copy() + ctrl+v` — `pyautogui.write()` é ignorado
- **LOV (botão `[...]`):** `_selecionar_via_lov()` — helper padrão com popup + Localizar + OK
- Unidade Funcional: `type_text` + 2x TAB (sigla carrega automaticamente)
- Médico Responsável: LOV com `%medico` → duplo clique em MEDICO (SOH PARA USO DA INFORMATICA)
- Popups de erro aleatórios (FRM-*, HC-INCOR): `_fechar_popups_oracle()` — fecha se aparecer, ignora se não
- ID do paciente sempre via `.env` (LGPD — nunca hardcoded)
- Coordenadas TODAS no `config.yaml` — nunca hardcoded no flow

### Oracle APEX / MSI3

- Nunca navegar por URL direta — invalida a sessão APEX
- Cards sem href CSS — OpenCV obrigatório
- `networkidle` não funciona após cliques OpenCV — usar polling de URL
- Formulários dialog abrem em frame separado — acessar via `page.frames`

---

## Observabilidade (v0.5.7c)

Cada execução gera em `evidence/YYYY-MM-DD/<teste>/`:

| Arquivo | Conteúdo |
|---|---|
| `execution.log` | Log estruturado com timestamps e causa de falha |
| `execution.json` | Dados com `execution_id` UUID, ambiente (OS, hostname, resolução) |
| `report.html` | Relatório visual com screenshots clicáveis |
| `flakiness.json` | Global em `evidence/` — histórico de pass/fail/duração por step |
| `estado_jornada.json` | Compartilhado entre testes — `paciente_id`, `nr_admissao_amb` |

**CausaFalha** classificada automaticamente:
`TEMPLATE_NAO_ENCONTRADO | TIMEOUT | OCR_LEITURA | COORDENADA | ESTADO_AUSENTE | SISTEMA | DESCONHECIDA`

---

## Roadmap de Observabilidade

O projeto identificou falso positivo crítico (teste reporta PASSOU mas sistema ficou em tela errada).
Detalhes completos em `Roadmap_VTAE_Observabilidade_v057.docx`.

| Fase | Descrição | Status |
|---|---|---|
| **Obs-A** | `confirm_template` no `_step()` + `verify_fill` + `validated` no StepResult | 🔴 Fazer agora |
| **Obs-B** | Badge integridade no report.html + screenshot before/after + resumo executivo | 🔜 |
| **Obs-C** | `expect_error` no DSL + testes negativos + detecção OCR de erro | 🔜 |
| **Obs-D** | CadastroPacienteFlow com observabilidade real — validar 3x | 🔜 |
| **Obs-E** | Jornada ambulatório completa com observabilidade real | 🔜 |

---

## Convenção de IDs de steps

| Prefixo | Flow | Sistema | Status |
|---|---|---|---|
| `L01`... | `LoginFlow` | SI3 / SisLab | ✅ |
| `MW01`... | `LoginFlowMsi3` | MSI3 | ✅ |
| `CF01`... | `CadastroFuncionarioFlow` | SisLab | ✅ |
| `CP01`... | `CadastroPacienteFlow` | SI3 | ✅ 23 steps |
| `AI01`... | `AdmissaoInternacaoFlow` | SI3 | ✅ 18 steps |
| `FA01`... | `FrequenciaAplicacaoFlow` | MSI3 | ✅ |
| `TA01`... | `TipoAnestesiaFlow` | MSI3 | ✅ |
| `AB01`... | `AdmissaoAmbulatorioFlow` | SI3 | 🔵 15 steps, calibrando |
| `AT01`... | `AtendimentoMedicoFlow` | SI3 | 🔜 Fase 5c |
| `AA01`... | `AltaAmbulatorioFlow` | SI3 | 🔜 Fase 5c |

---

## Fases do projeto

| Fase | Descrição | Status |
|---|---|---|
| 1–4c | Base, Clean Architecture, DSL, migração estrutural | ✅ |
| 5a | CadastroPacienteFlow 23 steps, 3x seguidas | ✅ |
| 5b | Observabilidade básica (CausaFalha, flakiness, execution_id, health check) | ✅ |
| 5c | Jornada ambulatório completa (test_01–test_04) | 🔵 Em andamento |
| Obs-A | confirm_template + verify_fill + validated (fim do falso positivo) | 🔴 Fazer agora |
| Obs-B | report.html com valor para gestão | 🔜 |
| Obs-C | Caminhos negativos (expect_error) | 🔜 |
| Obs-D | CadastroPacienteFlow com observabilidade real | 🔜 |
| Obs-E | Jornada ambulatório com observabilidade real | 🔜 |
| 6 | YOLO fine-tuning + integração OpenCVRunner | 🔜 |
| 7 | CI/CD Jenkins + RDP | 🔜 |
| 8 | Portfólio profissional | 🔜 |

---

## Changelog

### v0.5.7c — 2026-05-22
- `AdmissaoAmbulatorioFlow` — 15 steps AB01-AB15, AB01-AB11 passando
- `_selecionar_via_lov()` — helper reutilizável para LOV (AB11, AB12)
- `_resolver_cenario_provedor()` — cenários de provedor configuráveis no config.yaml
- `dados:` no config.yaml — seção de dados fixos exposta via `config.DADOS`
- `schema.py` atualizado — `dados_fixos` no `SystemConfig`, `DADOS` mescla fixos + Faker
- `loader.py` atualizado — lê seção `dados:` e passa como `dados_fixos`
- `observer.py` corrigido — `setdefault` fora do `if` (fix `KeyError: total_execucoes`)
- AB04 com OCR — só digita RUA se campo Tipo estiver vazio
- AB11 via LOV — `%medico` → duplo clique em MEDICO (SOH PARA USO DA INFORMATICA)
- AB12 com lista de procedimentos configurável — cada item com código, complemento, área executora e profissional

### v0.5.6c — 2026-05-21
- `CadastroPacienteFlow` **23/23 steps passando 3x seguidas** — Fase 5a concluída ✅
- `regioes_ocr` migrado para `config.yaml` — região OCR da matrícula configurável
- `_fechar_popups_oracle()` — fecha popups FRM-*/HC-INCOR sem falhar o teste
- `--repeat N` adicionado ao CLI
- Aba Documentos com `pyperclip` — RG + Emissor + UF + Data + CPF + CNS via `ctrl+v`

### v0.5.3 — 2026-05-08
- `AdmissaoInternacaoFlow` — 18 steps, 21/21 passando
- ID do paciente via `.env` (conformidade LGPD)
- `scripts/posicao_mouse.py` — captura até 4 coordenadas com contagem regressiva
- DSL: `loop`, `if/else`
- 314 testes unitários verdes em 2s

### v0.5.0 — 2026-05-06
- Débito técnico concluído — 189 → 314 testes unitários
- `mock_sleep` autouse fixture — suite unitária: 206s → 2s

---

## Documentação

| Arquivo | Descrição |
|---|---|
| `VTAE_Prompt_Instrucao_Geral.md` | Prompt de instrução geral — estado atual do projeto |
| `Roadmap_VTAE_Observabilidade_v057.docx` | Roadmap detalhado de observabilidade e evolução |
| `VTAE_Documentacao_Tecnica.docx` | Arquitetura, runners, matchers, exceções, padrões |
| `VTAE_Manual_Criacao_Testes.docx` | Passo a passo detalhado para criar novos testes |