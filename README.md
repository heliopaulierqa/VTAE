# VTAE — Visual Test Automation Engine

> Framework híbrido de automação inteligente baseado em Visão Computacional + IA
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.3.1-purple)
![Testes Unitários](https://img.shields.io/badge/testes%20unitários-32%20passando-green)
![SI3](https://img.shields.io/badge/SI3%20CadastroPaciente-14%2F14%20✅-brightgreen)
![MSI3](https://img.shields.io/badge/MSI3%20FrequenciaAplicacao-10%2B%20execuções%20✅-brightgreen)

---

## O que é o VTAE

O VTAE é um framework híbrido de automação de testes que combina visão computacional,
controle de browser e OCR para interagir com qualquer sistema — como um usuário humano faria.
Ele localiza elementos por imagem, seletor CSS ou leitura de texto, executa ações e captura
evidências automaticamente em cada etapa.

**O diferencial:** onde ferramentas puramente web (Playwright, Cypress, Selenium) não chegam,
o VTAE chega. E onde ferramentas puramente desktop falham em aplicações web modernas,
o VTAE também resolve.

Ideal para:
- Sistemas legados desktop sem API de automação (Oracle Forms, Citrix, VDI)
- Sistemas web complexos como Oracle APEX
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
# Verificar instalação:
python -c "from vtae.core.ocr_helper import OcrHelper; OcrHelper.verificar_instalacao()"

# pytest-repeat — para rodar o mesmo teste N vezes
pip install pytest-repeat
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
├── flows/
│   ├── login_flow.py
│   ├── login_flow_msi3.py
│   ├── cadastro_paciente_flow.py
│   ├── cadastro_funcionario_flow_sislab.py
│   └── frequencia_aplicacao_flow.py
├── runners/
│   ├── opencv_runner.py     # runner desktop (visão computacional)
│   └── playwright_runner.py # runner web (browser)
├── configs/                 # credenciais por sistema
│   ├── si3/
│   ├── sislab/
│   └── msi3/
└── tests/
    ├── unit/                # testes sem tela real (32 testes)
    └── integration/
        ├── si3/             # Oracle Forms desktop
        ├── sislab/          # Oracle Forms desktop
        └── msi3/            # Oracle APEX web
templates/                   # recortes de tela por sistema
evidence/                    # screenshots e relatórios por execução
scripts/                     # posicao_mouse.py e utilitários
```

---

## Como usar

### Testes unitários (sem tela real)

```bash
python -m pytest vtae/tests/unit/ -v
```

### Testes de integração (sistema aberto e maximizado)

```bash
# sistema específico
python -m pytest vtae/tests/integration/si3/ -v -s
python -m pytest vtae/tests/integration/msi3/ -v -s

# teste específico
python -m pytest vtae/tests/integration/si3/test_cadastro_paciente.py -v -s

# múltiplos testes separados por espaço
python -m pytest vtae/tests/integration/si3/test_cadastro_paciente.py vtae/tests/integration/msi3/test_frequencia_aplicacao.py -v -s

# todos os testes de integração
python -m pytest vtae/tests/integration/ -v -s

# repetir o mesmo teste N vezes (valida estabilidade)
python -m pytest vtae/tests/integration/si3/test_cadastro_paciente.py -v -s --count=5
```

### Via CLI (Fase 3)

```bash
python -m vtae.cli.run run --all
python -m vtae.cli.run run --module si3
python -m vtae.cli.run run --test cadastro_paciente
```

---

## Runners disponíveis

### OpenCVRunner — desktop

Usa visão computacional para encontrar e clicar em elementos na tela.

```python
from vtae.runners.opencv_runner import OpenCVRunner

runner = OpenCVRunner(confidence=0.8)
ctx = FlowContext(runner=runner, config=LoginConfigSi3,
                  evidence_dir=observer.evidence_dir)
LoginFlow().execute(ctx, observer=observer)
```

**Templates** — salve os recortes em `templates/sistema/modulo/`:

```
templates/
└── si3/
    └── paciente/
        ├── menu_cadastro_paciente.png
        ├── campo_nome_social.png
        └── btn_salvar.png
```

> **Dica:** recorte o label do campo, não o campo em branco — o label é único na tela.
> Nomes sem acentos e sem espaços — use underline. Ex: `campo_mae.png`

### PlaywrightRunner — web

Usa seletores CSS ou texto para interagir com sistemas no browser.

```python
from vtae.runners.playwright_runner import PlaywrightRunner

runner = PlaywrightRunner(url="https://sistema.interno/login", headless=False)
ctx = FlowContext(runner=runner, config=LoginConfigMsi3,
                  evidence_dir=observer.evidence_dir)
LoginFlowMsi3().execute(ctx, observer=observer)
```

### Modo híbrido — Playwright + OpenCV

Para sistemas como Oracle APEX onde alguns elementos não têm seletor CSS acessível:

```python
# Playwright — navegação via sidebar (normaliza acentos automaticamente)
ctx.runner._page.get_by_role("link", name="Sistema de Pacientes").first.click()
ApexHelper.aguardar_spinner(ctx.runner)

# OpenCV — card sem href CSS acessível
from vtae.runners.opencv_runner import OpenCVRunner
cv = OpenCVRunner(confidence=0.7)
cv.safe_click("templates/msi3/cadastros_basicos/frequencia_aplicacao.png")

# Playwright retoma para verificar resultado
ctx.runner.wait_template("text=Novo Cadastro", timeout=20.0)
```

---

## Helpers centralizados

### OcrHelper — leitura de texto em interfaces nativas

Para grades e tabelas do Oracle Forms que não são HTML:

```python
from vtae.core.ocr_helper import OcrHelper

# lê texto de uma região específica (x1, y1, x2, y2)
texto = OcrHelper.ler_regiao(screenshot_path, regiao=(507, 139, 667, 169))

# busca tolerante a erros do OCR
encontrou, token = OcrHelper.contem_qualquer_token(
    screenshot_path, tokens=nome.split(), regiao=(0, 320, 950, 620)
)

# salva imagem pré-processada para debug
OcrHelper.salvar_debug(screenshot_path, regiao=(507, 139, 667, 169),
                       output="debug_matricula.png")
```

> **Regra:** sistemas web → Playwright lê o texto diretamente.
> OCR é reservado para interfaces nativas desktop (Oracle Forms).

### ApexHelper — interações com Oracle APEX

```python
from vtae.core.apex_helper import ApexHelper

ApexHelper.aguardar_spinner(ctx.runner)          # após ações AJAX
ApexHelper.verificar_sem_erro(ctx.runner)        # após salvar
ApexHelper.verificar_registro_na_grade(          # valida cadastro sem OCR
    ctx.runner, texto=dados["codigo"]
)
info = ApexHelper.inspecionar_pagina(ctx.runner) # debug: url, título, erro
```

> **IMPORTANTE:** nunca navegue por URL direta no APEX — invalida a sessão.
> Sempre clique nos menus. Use `get_by_role("link", name="...")` para o sidebar.

---

## Observabilidade

Cada execução gera automaticamente três arquivos em `evidence/YYYY-MM-DD/nome_teste/`:

| Arquivo | Conteúdo |
|---|---|
| `execution.log` | Log estruturado com timestamps de cada step |
| `execution.json` | Dados estruturados de todos os steps |
| `report.html` | Relatório visual com screenshots — abra no browser |

---

## Dados dinâmicos com Faker

```python
from faker import Faker
fake = Faker("pt_BR")

dados = {
    "nome":            fake.name().upper(),
    "nome_social":     "",   # vazio = usa o nome do paciente
    "data_nascimento": fake.date_of_birth(minimum_age=18).strftime("%d/%m/%Y"),
    "sexo":            fake.random_element(["M", "F"]),
    "mae":             fake.name_female().upper(),
    "pai":             fake.name_male().upper(),
    "cpf":             fake.cpf().replace(".", "").replace("-", ""),
    "codigo":          fake.bothify(text="??##").upper(),
    "descricao":       f"TESTE VTAE {fake.bothify(text='????####').upper()}",
}
```

> **Atenção:** use sempre `ctx.runner.type_text()` para campos com acentos.
> `pyautogui.typewrite()` perde `Í`, `Ã`, `Ç` no Windows.

---

## FlowContext — conceito central

```python
ctx = FlowContext(
    runner=runner,
    config=LoginConfigSi3,
    evidence_dir=observer.evidence_dir,
)

# ctx.user         → vem do config automaticamente
# ctx.password     → vem do config automaticamente
# ctx.runner       → instância do runner
# ctx.evidence_dir → onde salvar screenshots
```

---

## Convenção de IDs de steps

| Prefixo | Flow | Sistema |
|---|---|---|
| `L01`, `L02`... | `LoginFlow` | SisLab / SI3 desktop |
| `MW01`, `MW02`... | `LoginFlowMsi3` | MSI3 Oracle APEX web |
| `CP01`, `CP02`... | `CadastroPacienteFlow` | SI3 Oracle Forms |
| `CF01`, `CF02`... | `CadastroFuncionarioFlow` | SisLab Oracle Forms |
| `FA01`, `FA02`... | `FrequenciaAplicacaoFlow` | MSI3 Oracle APEX |
| `A01`, `A02`... | `AdmissaoFlow` | Qualquer sistema |
| `XX01`, `XX02`... | Novo flow | Definir prefixo único |

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows ativos | Status |
|---|---|---|---|---|
| SisLab | Desktop — Oracle Forms | OpenCV | Login, CadastroFuncionario | ✅ |
| SI3 | Desktop — Oracle Forms | OpenCV | Login, CadastroPaciente | ✅ |
| MSI3 | Web — Oracle APEX 23.1 | Playwright + OpenCV | Login, FrequenciaAplicacao | ✅ |

---

## Mapa de navegação MSI3

Confirmado no ambiente. Navegação obrigatória via cliques — URL direta invalida sessão APEX.

| Step | Ação | URL resultante |
|---|---|---|
| FA01 | sidebar → "Sistema de Pacientes" | `/home?p1_modu_nr=337` |
| FA02 | sidebar → "Apoio" | `/home?p1_modu_nr=401` |
| FA03 | sidebar → "Cadastros" | `/sec_menu?p2_modu_nr=402` |
| FA04 | OpenCV → card Frequência de Aplicação | `/sec_menu?p2_modu_nr=405` |
| FA05 | clica "Novo Cadastro" | abre iframe formulário |

---

## Fases do projeto

| # | Fase | Descrição | Status |
|---|---|---|---|
| 1 | Base de IA aplicada | Python, NumPy, OpenCV, noções de ML | ✅ |
| 2 | Automação inteligente | Playwright, OpenCV, OCR, híbrido web+desktop | 🔵 Em andamento |
| 3 | Arquitetura de engenharia | Clean Architecture, CLI, migração vtae/ → src/ | 🔜 |
| 4 | IA em produção | Docker, MLflow, Jenkins, CI/CD | 🔜 |
| 5 | Portfólio profissional | Documentação, cases reais, repositório | 🔜 |

---

## Documentação

- `VTAE_Manualv3.docx` — manual do desenvolvedor para criar novos testes
- `VTAE_Documentacao_v031.docx` — documentação completa do projeto
- `CHANGELOG.md` — histórico de versões

---

## Changelog

### v0.3.1 — 2026-04-28
- `CadastroPacienteFlow` SI3 — 14/14 steps OK, validado com Faker e OCR de matrícula
- Estratégia de coordenadas diretas para Oracle Forms — resolve foco errático
- CP07 Nacionalidade — dois popups em sequência com fallback Enter
- CP13 Gerar matrícula — OCR confirma persistência do cadastro
- CP14 Sair 3x — retorno completo ao Menu Principal

### v0.3.0 — 2026-04-27
- `FrequenciaAplicacaoFlow` MSI3 — validado em 10+ execuções consecutivas
- `ApexHelper` centralizado — seletores validados no APEX 23.1
- `LoginFlowMsi3` — detecção de erro de credencial
- `OcrHelper` centralizado — pré-processamento otimizado para Oracle Forms
- Mapa de navegação MSI3 documentado

### v0.2.0
- `OpenCVRunner` — runner desktop com visão computacional
- `PlaywrightRunner` — runner web com browser maximizado
- `ExecutionObserver` — logs, JSON e relatório HTML automático
- `FrequenciaAplicacaoFlow` — fluxo completo MSI3 com Playwright + OpenCV
- `LoginFlowMsi3` — login web Oracle APEX
- Integração com **Faker** para dados únicos
- 32 testes unitários passando

### v0.1.0
- Estrutura inicial de pastas
- `LoginFlow`, `AdmissaoFlow`, `SuprimentosFlow` (esqueletos)
- `LoginConfigSisLab`

---

## Próximos passos

- [ ] Fase 2 — YOLO para detecção de componentes de UI
- [ ] Fase 2 — validar `CadastroFuncionarioFlow` no SisLab
- [ ] Fase 3 — Clean Architecture e CLI funcional
- [ ] Fase 3 — migração `vtae/` → `src/`
- [ ] Suporte mobile — PlaywrightRunner com emulação de dispositivo
