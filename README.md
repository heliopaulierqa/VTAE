# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.3.0-purple)
![Testes](https://img.shields.io/badge/testes-32%20unitários-green)
![MSI3](https://img.shields.io/badge/MSI3-10%20execuções%20✅-brightgreen)

---

## O que é o VTAE

O VTAE é um framework híbrido de automação de testes que combina visão computacional, controle de browser e OCR para interagir com qualquer sistema — como um usuário humano faria. Ele localiza elementos por imagem, seletor CSS ou leitura de texto, executa ações e captura evidências automaticamente em cada etapa.

**O diferencial:** onde ferramentas puramente web (Playwright, Cypress, Selenium) não chegam, o VTAE chega. E onde ferramentas puramente desktop falham em aplicações web modernas, o VTAE também resolve.

Ideal para:
- Sistemas web modernos (Oracle APEX, React, Angular)
- Sistemas legados desktop sem API de automação (Oracle Forms, Citrix)
- Ambientes híbridos onde Playwright e OpenCV precisam trabalhar juntos

---

## Instalação

```bash
# dependências
pip install -r requirements.txt

# instalar o projeto
pip install -e .

# instalar o browser (só na primeira vez)
playwright install chromium

# OCR — Tesseract (Windows)
# Baixar em: https://github.com/UB-Mannheim/tesseract/wiki
# Marcar "Portuguese" durante a instalação
# Verificar:
python -c "from vtae.core.ocr_helper import OcrHelper; OcrHelper.verificar_instalacao()"
```

> **Windows (PowerShell):** use `$env:PYTHONPATH="."` no lugar de `PYTHONPATH=.`

---

## Estrutura do projeto

```
vtae/
├── core/
│   ├── base_runner.py       # contrato abstrato do runner
│   ├── context.py           # FlowContext — contexto compartilhado
│   ├── result.py            # StepResult e FlowResult
│   ├── observer.py          # logs, evidências e relatório HTML
│   ├── report_generator.py  # gerador de relatório HTML
│   ├── ocr_helper.py        # OCR centralizado (Tesseract)
│   └── apex_helper.py       # helpers para Oracle APEX (MSI3)
├── flows/                   # lógica dos fluxos de teste
│   ├── login_flow_msi3.py
│   ├── frequencia_aplicacao_flow.py
│   └── cadastro_funcionario_flow_sislab.py
├── runners/
│   ├── opencv_runner.py     # runner desktop (visão computacional)
│   └── playwright_runner.py # runner web (browser)
├── configs/                 # credenciais por sistema
├── tests/
│   ├── unit/                # testes sem tela real (32 testes)
│   └── integration/
│       ├── sislab/
│       └── msi3/
templates/                   # recortes de tela por sistema
evidence/                    # screenshots e relatórios por execução
```

---

## Como usar

### Testes unitários (sem tela real)

```bash
python -m pytest vtae/tests/unit/ -v
```

### Testes de integração (com sistema real)

```bash
# MSI3 — Frequência de Aplicação
python -m pytest vtae/tests/integration/test_frequencia_aplicacao.py -v -s

# SisLab — Cadastro de Funcionário
python -m pytest vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py -v -s

# todos
python -m pytest vtae/tests/integration/ -v -s
```

---

## Runners disponíveis

### OpenCVRunner — desktop

Usa visão computacional para encontrar e clicar em elementos na tela.
O parâmetro `template` é um caminho para uma imagem `.png` recortada do elemento.

```python
from vtae.runners.opencv_runner import OpenCVRunner

runner = OpenCVRunner(confidence=0.8)
ctx = FlowContext(runner=runner, config=LoginConfigSisLab)
LoginFlow().execute(ctx, observer=observer)
```

**Templates** — salve os recortes em `templates/sistema/modulo/`:

```
templates/
└── sislab/
    └── login/
        ├── campo_usuario.png
        ├── campo_senha.png
        └── btn_entrar.png
```

> **Dica:** recorte com bordas e contexto ao redor. Quanto mais único o recorte, menos falsos positivos.

### PlaywrightRunner — web

Usa seletores CSS para interagir com sistemas no browser.

```python
from vtae.runners.playwright_runner import PlaywrightRunner

runner = PlaywrightRunner(url="https://sistema.interno/login", headless=False)
ctx = FlowContext(runner=runner, config=LoginConfigMsi3)
LoginFlowMsi3().execute(ctx, observer=observer)
```

### Modo híbrido — Playwright + OpenCV

Para sistemas como Oracle APEX que misturam HTML acessível com elementos
renderizados que o Playwright não acessa, os dois runners trabalham juntos
no mesmo flow. Exemplo real no `FrequenciaAplicacaoFlow`:

```python
# Playwright — navegação e formulários via seletor CSS
ctx.runner._page.get_by_role("link", name="Sistema de Pacientes").click()
frame.locator("#P17_FRAP_CD").fill(dados["codigo"])

# OpenCV — card sem href CSS acessível
cv = OpenCVRunner(confidence=0.7)
cv.safe_click("templates/msi3/cadastros_basicos/frequencia_aplicacao.png")

# Playwright retoma para verificar resultado
ctx.runner.wait_template("text=Novo Cadastro", timeout=20.0)
```

---

## Helpers centralizados

### OcrHelper — leitura de texto em interfaces nativas

Para grades e tabelas do Oracle Forms que não são acessíveis via seletor CSS.

```python
from vtae.core.ocr_helper import OcrHelper

# lê texto de uma região específica da tela
texto = OcrHelper.ler_regiao(screenshot_path, regiao=(x1, y1, x2, y2))

# verifica nome na grade (tolerante a erros de OCR)
encontrado, token = OcrHelper.contem_qualquer_token(
    screenshot_path,
    tokens=nome.split(),
    regiao=(0, 320, 950, 620),
)

# debug — salva imagem pré-processada
OcrHelper.salvar_debug(screenshot_path, regiao=(0, 320, 950, 620))
```

> **Regra:** sistemas web → Playwright lê o texto diretamente. OCR é reservado
> para interfaces nativas desktop (Oracle Forms, SisLab, SI3).

### ApexHelper — interações com Oracle APEX

```python
from vtae.core.apex_helper import ApexHelper

# após salvar — detecta erro antes de continuar
ApexHelper.verificar_sem_erro(ctx.runner)

# após ação AJAX — aguarda spinner sumir
ApexHelper.aguardar_spinner(ctx.runner)

# verifica registro na grade sem OCR
ApexHelper.verificar_registro_na_grade(ctx.runner, texto=dados["codigo"])

# debug quando um step falha
info = ApexHelper.inspecionar_pagina(ctx.runner)
# retorna: url, titulo, erro, sucesso, frames
```

Seletores validados no ambiente MSI3 (APEX 23.1 / Universal Theme 42).
Busca automaticamente na página principal e dentro de iframes.

---

## Observabilidade

Cada execução gera automaticamente três arquivos em `evidence/YYYY-MM-DD/nome_teste/`:

| Arquivo | Conteúdo |
|---|---|
| `execution.log` | Log estruturado com timestamps |
| `execution.json` | Dados estruturados de todos os steps |
| `report.html` | Relatório visual com screenshots — abra no browser |

O relatório HTML inclui métricas, barra de progresso, detalhamento por flow
e screenshots clicáveis com lightbox.

---

## Dados dinâmicos com Faker

Para evitar registros duplicados em testes de cadastro:

```python
from faker import Faker
fake = Faker("pt_BR")

dados = {
    "sequencia": str(fake.random_int(min=100, max=9999)),
    "codigo":    fake.bothify(text="??##").upper(),
    "descricao": f"TESTE VTAE {fake.bothify(text='????####').upper()}",
    "nome":      fake.name().upper(),
    "cpf":       fake.cpf(),
}
```

---

## Mapa de navegação MSI3

Confirmado em 27/04/2026. Navegação obrigatória via cliques — URL direta invalida sessão APEX.

| Tela | URL | Como chegar |
|---|---|---|
| Home | `/home?p1_modu_nr=` | após login |
| Sistema de Pacientes | `/home?p1_modu_nr=337` | sidebar → "Sistema de Pacientes" |
| Apoio à Assistência | `/home?p1_modu_nr=401` | sidebar → "Apoio" |
| Cadastros Básicos | `/sec_menu?p2_modu_nr=402` | sidebar → "Cadastros" |
| Frequência de Aplicação | `/sec_menu?p2_modu_nr=405` | OpenCV → card |

IDs dos campos do formulário (iframe `title='Cadastro de Frequência de Aplicação'`):

| Campo | ID |
|---|---|
| Sequência | `#P17_FRAP_SQ_EXIBICAO` |
| Código | `#P17_FRAP_CD` |
| Descrição | `#P17_FRAP_NM` |
| Tipo de Aplicação | `#P17_FRAP_TP_CONTAINER` |
| Frequência Tipo Única | `#P17_FRAP_CK_USO_FLUXO_0` |
| Qtd dias da semana | `#P17_FRAP_QT_DIAS_SEMANA` |
| Qtd em 24 horas | `#P17_FRAP_QT_24HS` |
| Intervalo em horas | `#P17_FRAP_INTERVAL_MIN_CONF_HORARIO` |
| Hora | `#P17_HORA` |
| Unidade Funcional | `#P17_UNFU_DS` |

---

## Convenção de IDs de steps

| Prefixo | Flow | Sistema |
|---|---|---|
| `L01`, `L02`... | `LoginFlow` | SisLab / SI3 desktop |
| `MW01`, `MW02`... | `LoginFlowMsi3` | MSI3 web Oracle APEX |
| `CF01`, `CF02`... | `CadastroFuncionarioFlow` | SisLab Oracle Forms |
| `FA01`, `FA02`... | `FrequenciaAplicacaoFlow` | MSI3 Oracle APEX |
| `A01`, `A02`... | `AdmissaoFlow` | Qualquer sistema |

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows ativos | Status |
|---|---|---|---|---|
| SisLab | Desktop — Oracle Forms | OpenCV | Login, CadastroFuncionario | ✅ |
| SI3 | Desktop — Oracle Forms | OpenCV | Login, CadastroPaciente | ✅ |
| MSI3 | Web — Oracle APEX 23.1 | Playwright + OpenCV | Login, FrequenciaAplicacao | ✅ |

---

## Fases do projeto

| # | Fase | Descrição | Status |
|---|---|---|---|
| 1 | Base de IA aplicada | Python, NumPy, OpenCV, noções de ML | ✅ |
| 2 | Automação inteligente | Playwright, OpenCV, OCR, híbrido web+desktop | 🔵 Em andamento |
| 3 | Arquitetura de engenharia | Clean Architecture, CLI, plugins | 🔜 |
| 4 | IA em produção | Docker, MLflow, Jenkins, CI/CD | 🔜 |
| 5 | Portfólio profissional | Documentação, cases reais, repositório | 🔜 |

---

## Changelog

### v0.3.0 — 2026-04-27
- `FrequenciaAplicacaoFlow` reescrito — Playwright puro para navegação e formulário, OpenCV cirúrgico para card sem CSS acessível. Validado em 10+ execuções consecutivas
- `ApexHelper` centralizado em `vtae/core/` — seletores validados no APEX 23.1 do ambiente real (MSI3). Suporte automático a iframes
- `LoginFlowMsi3` atualizado — detecta erro de credencial via `ApexHelper.verificar_sem_erro` no MW04; `inspecionar_pagina` no except do MW05
- `OcrHelper` centralizado em `vtae/core/` — pré-processamento otimizado para Oracle Forms (escala 2x + threshold adaptativo)
- `CadastroFuncionarioFlowSislab` — flow completo com verificação de grade via OCR no CF09
- Mapa de navegação do MSI3 documentado — URLs, módulos e IDs de campos confirmados no ambiente

### v0.2.0
- `OpenCVRunner` — runner desktop com visão computacional
- `PlaywrightRunner` — runner web com browser maximizado
- `ExecutionObserver` — logs, JSON e relatório HTML automático
- `report_generator.py` — relatório HTML com screenshots e lightbox
- `FrequenciaAplicacaoFlow` — fluxo completo MSI3 com Playwright + OpenCV
- `LoginFlowMsi3` — login web Oracle APEX
- Integração com **Faker** para dados únicos
- 32 testes unitários passando

### v0.1.0
- Estrutura inicial de pastas
- `LoginFlow`, `AdmissaoFlow`, `SuprimentosFlow` (esqueletos)
- `LoginConfigSisLab`

---

## Documentação

- `VTAE_Documentacao.docx` — documentação completa do projeto
- `VTAE_Manualv2.docx` — manual do desenvolvedor para criar novos testes

---

## Próximos passos

- [ ] Fase 2 — YOLO para detecção de componentes de UI
- [ ] Fase 2 — heurísticas de confiança visual
- [ ] Fase 3 — Clean Architecture e CLI funcional
- [ ] Suporte mobile — PlaywrightRunner com emulação de dispositivo
- [ ] Novos flows — `AdmissaoFlow` e `SuprimentosFlow` com templates reais
