# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.4.3-purple)
![Testes](https://img.shields.io/badge/testes-70%20unitários-green)
![Cobertura](https://img.shields.io/badge/cobertura%20vision-89%25-brightgreen)
![Fase](https://img.shields.io/badge/fase%203-concluída-brightgreen)
![Sistemas](https://img.shields.io/badge/sistemas-3%20automatizados-blue)

---

## Por que VTAE?

A maioria das ferramentas de automação resolve apenas parte do problema. O VTAE resolve tudo.

| Cenário | Selenium / Playwright | PyAutoGUI | **VTAE** |
|---|---|---|---|
| Oracle APEX (web moderno) | ✅ | ❌ | ✅ |
| Oracle Forms (desktop legado) | ❌ | ⚠️ frágil | ✅ robusto |
| Canvas / iframe sem DOM | ❌ | ❌ | ✅ OpenCV |
| Template falha por zoom/DPI | ❌ falha | ❌ falha | ✅ multi-scale |
| Template com contraste diferente | ❌ falha | ❌ falha | ✅ heurísticas |
| Múltiplos ambientes (dev/hom/prod) | configuração manual | não suporta | ✅ YAML nativo |
| Relatório visual com evidências | plugin externo | não suporta | ✅ HTML nativo |
| Detecção de componentes por imagem | não suporta | básico | ✅ TemplateMatcher |

**O diferencial real:** o VTAE combina Playwright para HTML e OpenCV para o resto — no mesmo flow, de forma transparente. É o único framework que automatiza Oracle Forms, Oracle APEX e sistemas híbridos com a mesma base de código.

---

## Casos reais automatizados

### InCor — Instituto do Coração

**CadastroPacienteFlow — SI3 (Oracle Forms)**
Automatiza o cadastro completo de pacientes no sistema hospitalar legado SI3: nome, data de nascimento, CPF, filiação, cor/etnia, nacionalidade e geração de matrícula via OCR. 14 steps, validado em produção.

**CadastroFuncionarioFlow — SisLab (Oracle Forms)**
Cadastro end-to-end de funcionários no SisLab: login, preenchimento de dados pessoais e contratuais, seleção de cargo/departamento por dropdown, salvamento e verificação na grade via OCR. 10 steps, validado em produção.

**TipoAnestesiaFlow — MSI3 (Oracle APEX)**
Navegação por 4 níveis de menus do MSI3 — combinando Playwright para sidebar e OpenCV para cards sem href CSS — até o formulário de cadastro de tipo de anestesia em iframe de dialog. 9 steps, validado em produção.

**FrequenciaAplicacaoFlow — MSI3 (Oracle APEX)**
Cadastro de frequência de aplicação com preenchimento de 8 campos em iframe APEX. Validado em 10+ execuções consecutivas sem falha.

---

## O que é o VTAE

Framework híbrido de automação de testes que combina visão computacional, controle de browser e OCR para interagir com qualquer sistema — como um usuário humano faria. Ele localiza elementos por imagem, seletor CSS ou leitura de texto, executa ações e captura evidências automaticamente em cada etapa.

---

## Instalação

```bash
pip install -r requirements.txt
pip install -e .
playwright install chromium

# OCR — Tesseract (Windows)
# Baixar: https://github.com/UB-Mannheim/tesseract/wiki
# Marcar "Portuguese" durante a instalação
python -c "from src.vision.ocr import OcrHelper; OcrHelper.verificar_instalacao()"
```

> **Windows:** após `pip install -e .` o comando `vtae` fica disponível no PATH.

---

## CLI — Como usar

```bash
# listar sistemas disponíveis
vtae systems

# listar ambientes de um sistema
vtae systems --sistema sislab

# executar módulo completo (dev por padrão)
vtae run --module sislab
vtae run --module msi3

# executar em ambiente específico
vtae run --module sislab --env homologacao
vtae run --module sislab --env producao

# executar teste específico
vtae run --test cadastro_funcionario
vtae run --test tipo_anestesia --env homologacao

# re-executar testes que falharam automaticamente
vtae run --module sislab --retry 2

# executar tudo
vtae run --all
vtae run --all --env homologacao

# limpar evidências antigas
vtae clean --days 7
vtae clean --days 30 --dry-run
```

Ao final de cada execução, relatório unificado salvo em:
```
evidence/YYYY-MM-DD/summary/<modulo>_<ambiente>.html
```

---

## Estrutura do projeto

```
VTAE/
├── src/                         ← Clean Architecture
│   ├── core/                    # context, result, observer, types
│   ├── vision/                  # TemplateMatcher (89% cobertura), OcrHelper
│   ├── runners/                 # OpenCVRunner, PlaywrightRunner
│   ├── flows/
│   │   ├── si3/                 # Oracle Forms — SI3
│   │   ├── sislab/              # Oracle Forms — SisLab
│   │   └── msi3/                # Oracle APEX + apex_helper
│   ├── config/                  # ConfigLoader + schema YAML
│   └── cli/                     # vtae run, systems, clean + summary report
│
├── vtae/                        ← aliases para src/ (retrocompatibilidade)
├── configs/                     ← config.yaml + .env por sistema
├── templates/                   ← recortes de tela por sistema
└── evidence/                    ← screenshots e relatórios por execução
```

---

## Visão computacional — diferenciais técnicos

### Multi-scale matching (F2-A)
Testa o template em 5 escalas `(1.0, 0.9, 1.1, 0.8, 1.2)` automaticamente. Resolve falhas causadas por diferença de zoom ou DPI entre a captura e a execução — sem recapturar o template.

### Heurísticas de confiança visual (F2-B)
Quando multi-scale falha, aplica sequencialmente: contraste +30%, brilho +20, equalização de histograma e escala de cinza. Compensa renderização inconsistente de Oracle Forms sem configuração adicional.

```
[TemplateMatcher] match via 'contrast' (score=0.812, scale=1.0x)
```

Quando tudo falha, exibe diagnóstico detalhado:
```
Template não encontrado: 'templates/sislab/btn_salvar.png'
  ✗ original (multi-scale)    score=0.581
  ✗ contrast                  score=0.623
  ✗ equalize                  score=0.612
```

### Anchor-based clicking (F2-C)
```python
# encontra label "Nome:" e clica 200px à direita — no campo
runner.click_near("templates/si3/label_nome.png", offset_x=200)
```

---

## Configuração por YAML

```yaml
# configs/sislab/config.yaml
sistema: sislab
tipo: desktop
runner: opencv

ambientes:
  dev:
    url: http://127.0.0.1:5000
    confidence: 0.8
  homologacao:
    url: http://sislab.hom.interno
    headless: true

credenciais:
  usuario: ${SISLAB_USER:-admin}
  senha: ${SISLAB_PASS}

dados_faker:
  - campo: nome
    tipo: faker
    metodo: name
    transformacao: sem_prefixo_upper
  - campo: cargo
    tipo: fixo
    valor: "ANALISTA DE RH"
```

Credenciais em `configs/<sistema>/.env` (gitignore):
```
SISLAB_USER=admin
SISLAB_PASS=admin123
```

Uso nos testes:
```python
from src.config import ConfigLoader

config = ConfigLoader.carregar("sislab")
config = ConfigLoader.carregar("sislab", "homologacao")
```

---

## Runners

### OpenCVRunner — desktop
```python
runner = OpenCVRunner(confidence=0.8)
runner.safe_click("templates/sislab/btn_salvar.png")
runner.click_near("templates/si3/label_nome.png", offset_x=200)
runner.double_click("templates/si3/menu_cadastros.png")
```

### PlaywrightRunner — web
```python
runner = PlaywrightRunner(url="https://sistema/login", headless=False)
```

### Modo híbrido — Playwright + OpenCV
```python
# Playwright para navegação e formulários CSS
page.get_by_role("link", name="Sistema de Pacientes").click()
frame.locator("#P17_FRAP_CD").fill(dados["codigo"])

# OpenCV para cards sem href CSS
cv = OpenCVRunner(confidence=0.7)
cv.safe_click("templates/msi3/card_frequencia.png")
```

---

## Testes

```bash
# unitários — 70 testes, sem tela real
python -m pytest vtae/tests/unit/ -v

# cobertura
python -m pytest vtae/tests/unit/ --cov=src --cov-report=term-missing

# integração — com sistema real aberto
vtae run --module sislab
vtae run --test tipo_anestesia
```

---

## Observabilidade

Cada execução gera em `evidence/YYYY-MM-DD/<teste>/`:

| Arquivo | Conteúdo |
|---|---|
| `execution.log` | Log com timestamps de cada step |
| `execution.json` | Dados estruturados para CI/CD |
| `report.html` | Screenshots clicáveis com lightbox |

A CLI gera adicionalmente em `evidence/YYYY-MM-DD/summary/`:

| Arquivo | Conteúdo |
|---|---|
| `<modulo>_<ambiente>.html` | Métricas globais + tabela de resultados + erros |

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows | Status |
|---|---|---|---|---|
| SisLab | Desktop — Oracle Forms | OpenCV | Login, CadastroFuncionario | ✅ |
| SI3 | Desktop — Oracle Forms | OpenCV | Login, CadastroPaciente | ✅ |
| MSI3 | Web — Oracle APEX 23.1 | Playwright + OpenCV | Login, FrequenciaAplicacao, TipoAnestesia | ✅ |

---

## Fases do projeto

| # | Fase | Descrição | Status |
|---|---|---|---|
| 1 | Base de IA aplicada | Python, NumPy, OpenCV, noções de ML | ✅ |
| 2 | Automação inteligente | Playwright, OpenCV, OCR, multi-scale, heurísticas | ✅ |
| 3 | Arquitetura de engenharia | Clean Architecture, ConfigLoader YAML, CLI, relatório | ✅ |
| 4 | IA em produção | Docker, FastAPI, MLflow, Jenkins, YOLO | 🔜 |
| 5 | Portfólio profissional | Documentação, cases reais, repositório público | 🔜 |

---

## Próximos passos (Fase 4)

- [ ] YOLO — detecção de componentes de UI (treinado com screenshots reais do projeto)
- [ ] Docker + FastAPI para servir modelos
- [ ] MLflow — versionamento de modelos com métricas de flakiness
- [ ] Jenkins / GitLab CI — `vtae run --all` integrado ao pipeline
- [ ] Métricas: flakiness rate e drift visual por flow

---

## Documentação

- `VTAE_Documentacao.docx` — documentação completa v0.4.3
- `VTAE_Manual.docx` — manual do desenvolvedor v0.4.3
- `CHANGELOG.md` — histórico completo de versões
