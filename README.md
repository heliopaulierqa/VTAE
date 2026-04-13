# VTAE — Visual Test Automation Engine

> Automação de testes via visão computacional para sistemas desktop e web.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.2.0-purple)
![Testes](https://img.shields.io/badge/testes-32%20passando-green)

---

## O que é o VTAE

O VTAE é um framework de automação de testes que combina visão computacional e controle de browser. Ele interage com sistemas como um usuário humano — localiza elementos por imagem ou seletor CSS, clica, digita e captura evidências em cada etapa.

Ideal para:
- Sistemas legados desktop sem API de automação
- Sistemas web complexos como Oracle APEX
- Ambientes onde Playwright e OpenCV precisam trabalhar juntos

---

## Instalação

```bash
# dependências
pip install -r requirements.txt

# instalar o projeto
pip install -e .

# instalar o browser (só na primeira vez)
playwright install chromium
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
│   └── report_generator.py  # gerador de relatório HTML
├── flows/                   # lógica dos fluxos de teste
├── runners/
│   ├── opencv_runner.py     # runner desktop (visão computacional)
│   └── playwright_runner.py # runner web (browser)
├── components/              # blocos reutilizáveis
├── configs/                 # credenciais por sistema
├── legacy/                  # código antigo isolado
├── dsl/                     # interpreter YAML (Fase 5)
├── cli/                     # linha de comando (Fase 6)
└── tests/
    ├── conftest.py          # fixtures compartilhadas
    ├── unit/                # testes sem tela real (32 testes)
    └── integration/         # testes com sistema real
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
# desktop
python -m pytest vtae/tests/integration/test_login_real.py -v -s

# web
python -m pytest vtae/tests/integration/test_msi3.py -v -s

# todos
python -m pytest vtae/tests/integration/ -v -s
```

### Via CLI

```bash
python -m vtae.cli.run run --all
python -m vtae.cli.run run --module admissao
python -m vtae.cli.run run --test login
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
        ├── campo_usuario.png   # recorte do campo usuário
        ├── campo_senha.png     # recorte do campo senha
        └── btn_entrar.png      # recorte do botão entrar
```

> **Dica:** recorte com bordas e contexto ao redor. Quanto mais único o recorte, menos falsos positivos.

### PlaywrightRunner — web

Usa seletores CSS para interagir com sistemas no browser.

```python
from vtae.runners.playwright_runner import PlaywrightRunner

runner = PlaywrightRunner(url="https://sistema.interno/login", headless=False)
ctx = FlowContext(runner=runner, config=LoginConfigWeb)
LoginFlowWeb().execute(ctx, observer=observer)
```

> **Oracle APEX:** para elementos problemáticos, combine Playwright (navegação) com OpenCV (cliques específicos).

---

## Observabilidade

Cada execução gera automaticamente três arquivos em `evidence/YYYY-MM-DD/nome_teste/`:

| Arquivo | Conteúdo |
|---|---|
| `execution.log` | Log estruturado com timestamps |
| `execution.json` | Dados estruturados de todos os steps |
| `report.html` | Relatório visual com screenshots — abra no browser |

O relatório HTML inclui métricas, barra de progresso, detalhamento por flow e screenshots clicáveis com lightbox.

---

## Dados dinâmicos com Faker

Para evitar registros duplicados em testes de cadastro:

```python
from faker import Faker
fake = Faker("pt_BR")

dados = {
    "sequencia": str(fake.random_int(min=100, max=9999)),
    "codigo": fake.bothify(text="??##").upper(),
    "descricao": f"TESTE VTAE {fake.bothify(text='????####').upper()}",
}
```

---

## FlowContext — conceito central

Em vez de passar `runner`, `config`, `user`, `password` separadamente, tudo fica em um único contexto:

```python
ctx = FlowContext(
    runner=runner,
    config=LoginConfigSisLab,
    evidence_dir=observer.evidence_dir,
)

# ctx.user       → vem do config automaticamente
# ctx.password   → vem do config automaticamente
# ctx.runner     → instância do runner
# ctx.evidence_dir → onde salvar screenshots
```

---

## Convenção de IDs de steps

| Prefixo | Flow |
|---|---|
| `L01`, `L02`... | `LoginFlow` (desktop) |
| `LW01`, `LW02`... | `LoginFlowWeb` |
| `MW01`, `MW02`... | `LoginFlowMsi3` |
| `A01`, `A02`... | `AdmissaoFlow` |
| `S01`, `S02`... | `SuprimentosFlow` |
| `FA01`, `FA02`... | `FrequenciaAplicacaoFlow` |

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Status |
|---|---|---|---|
| SisLab | Desktop | OpenCV | ✅ |
| SI3 | Desktop | OpenCV | ✅ |
| MSI3 | Web (Oracle APEX) | Playwright + OpenCV | ✅ |

---

## Status das fases

| # | Fase | Status |
|---|---|---|
| 1 | Consolidação | ✅ |
| 2 | Flows | ✅ |
| 3 | Robustez (retry, timeout) | ✅ |
| 4 | Observabilidade (logs, evidências, HTML) | ✅ |
| 5 | DSL — testes em YAML | 🟣 estrutura criada |
| 6 | CLI — execução por terminal | 🟣 estrutura criada |
| 7 | CI/CD — pipeline automático | 🔜 |
| 8 | Interface gráfica | 🔜 |

---

## Documentação

- `VTAE_Manual.docx` — manual completo para criar novos testes
- `CHANGELOG.md` — histórico de versões

---

## Changelog

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

## Próximos passos

- [ ] Fase 5 — DSL: executar testes definidos em YAML
- [ ] Fase 6 — CLI: `vtae run --all` funcional
- [ ] Fase 7 — CI/CD: pipeline automático
- [ ] Novos flows: `AdmissaoFlow` e `SuprimentosFlow` com templates reais
