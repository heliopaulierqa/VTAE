# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA  
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.13-purple)
![Testes](https://img.shields.io/badge/testes-297%20unitários-green)
![Fase](https://img.shields.io/badge/fase-B%20—%20Observabilidade%20campos%20texto-brightgreen)

---

## O que é o VTAE

Framework híbrido de automação de testes que combina visão computacional (OpenCV),
controle de browser (Playwright) e OCR (EasyOCR) para interagir com qualquer sistema
como um usuário humano faria.

**Palavra-chave: CONFIANÇA.** Teste que executa sem validar resultado é script, não teste.

Ideal para:
- Sistemas legados desktop sem API de automação (Oracle Forms, Citrix)
- Sistemas web modernos (Oracle APEX, React, Angular)
- Ambientes híbridos onde Playwright e OpenCV precisam trabalhar juntos

---

## Pré-requisitos

| Requisito | Versão | Observação |
|---|---|---|
| Python | 3.13+ | Única dependência de SO |
| Git | qualquer | Para clonar o repositório |
| Resolução | 1920x1080 | Coordenadas calibradas nessa resolução |
| SI3 | aberto e maximizado | Antes de rodar testes desktop |

> ✅ **Tesseract removido na v0.5.11** — EasyOCR instalado via pip, sem dependência de SO.

---

## Instalação em máquina nova

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd VTAE
```

### 2. Criar e ativar o ambiente virtual

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv .venv
source .venv/bin/activate
```

> O `.venv` está no `.gitignore` — **nunca commitar**. Sempre ativar antes de trabalhar.

### 3. Instalar dependências

```bash
pip install -r requirements.txt
pip install -e .
playwright install chromium
```

> ⚠️ EasyOCR baixa modelos (~200MB) na primeira execução. Segunda execução usa cache.

### 4. Configurar credenciais

Cada jornada tem seu próprio `.env`. **Nunca commitar no Git.**

```bash
# configs/si3/si3_cadastro_paciente/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=        # vazio = cadastra novo; preenchido = reutiliza

# configs/si3/si3_internacao/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=

# configs/si3/si3_ambulatorio/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=

# configs/msi3/.env
MSI3_USER=seu_usuario
MSI3_PASS=sua_senha

# .env na raiz (pyjab — JAVA_HOME de mentira para Access Bridge)
SI3_JAB_HOME_FAKE=C:\jab_home
```

> Comentários no .env sempre em linha separada — **nunca na mesma linha do VAR=valor**.

### 5. Verificar instalação

```bash
# EasyOCR
python -c "from src.vision.ocr import OcrHelper; print('EasyOCR OK')"

# Testes unitários (deve passar 297, 76 falhas conhecidas pré-existentes)
python -m pytest tests/unit/ -v

# CLI
vtae systems
```

### 6. Primeiro teste

Abra o SI3 maximizado na tela principal e execute:

```bash
vtae run --test cadastro_paciente_jornada
```

---

## CLI — comandos disponíveis

```bash
# Jornadas completas
vtae run --jornada internacao
vtae run --jornada ambulatorio
vtae run --jornada ambulatorio_com_agendamento
vtae run --jornada internacao --repeat 3

# Testes individuais
vtae run --test cadastro_paciente_jornada
vtae run --test admissao_internacao_jornada
vtae run --test admissao_ambulatorio_jornada
vtae run --test agendamento_jornada
vtae run --test cadastro_funcionario

# Utilitários
vtae systems          # lista sistemas detectados
vtae flakiness --top 5  # top steps mais flaky
vtae clean --days 7   # limpa evidências antigas
vtae summary          # relatório gerencial
vtae metrics          # métricas de cobertura
```

---

## Estrutura do projeto

```
VTAE/
├── vtae/                    O MOTOR — código genérico do framework
│   ├── core/                FlowContext, StepResult, Observer, estado_jornada
│   ├── vision/              TemplateMatcher (multi-scale) + OcrEngine (EasyOCR)
│   ├── runners/             OpenCVRunner, PlaywrightRunner
│   ├── flows/               BaseFlow + flows por sistema
│   └── report/              observer.py, report_generator.py, summary_generator.py
│
├── objects/                 Modelo de Elemento — YAML por tela (ObjectRepository)
├── configs/                 Dados de teste por funcionalidade (config.yaml + .env)
├── templates/               PNGs para template matching
├── tests/
│   ├── unit/                297 testes com mock — rodam sem SI3 aberto
│   └── integration/
│       └── si3/jornadas/    testes contra o sistema real
├── scripts/
│   ├── posicao_mouse.py     capturar coordenadas x,y na tela
│   ├── testar_regiao_ocr.py calibrar região OCR — ver o que o EasyOCR lê
│   └── diagnose_contra_arquivo.py  medir score de template vs screenshot
├── docs/                    documentação do projeto
│   ├── VTAE_Projeto_v1.docx       o leme — visão total e fases
│   ├── VTAE_Manual_Tecnico_v1.md  como cada arquivo funciona
│   ├── VTAE_Roadmap_v0.1.md       checklist de direção
│   └── VTAE_Manual_Criacao_Testes_v0.1.md  passo a passo
├── VTAE_Prompt_Instrucao_v0.5.13.md  registro operacional de sessão
├── README.md                este arquivo
└── evidence/                gerado automaticamente ao rodar testes
    ├── flakiness.json       histórico pass/fail por step
    ├── estado_jornada.json  paciente_id entre steps da jornada
    └── YYYY-MM-DD/
        └── <teste>/
            ├── execution.log    log estruturado
            ├── execution.json   dados por step (CI/CD)
            └── report.html      relatório visual com screenshots
```

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Status |
|---|---|---|---|
| SI3 | Desktop Oracle Forms | OpenCVRunner | ✅ Login, CadastroPaciente, AdmissaoInternacao, AdmissaoAmbulatorio, Agendamento |
| SisLab | Desktop Oracle Forms | OpenCVRunner | ✅ Login, CadastroFuncionario |
| MSI3 | Web Oracle APEX 23.1 | Playwright+OpenCV | ✅ Login, FrequenciaAplicacao, TipoAnestesia |

---

## Padrão de validação por tipo de campo

| Tipo | Método | O que prova |
|---|---|---|
| Texto livre (nome, data, etnia) | `verify_lov` com região calibrada | Campo não ficou vazio + valor lido aparece no report |
| Numérico (matrícula, leito) | `verify_fill` com região calibrada | Valor exato conferido |
| LOV (seleção de lista) | `verify_lov` com região calibrada | Seleção não ficou vazia |
| Navegação / clique | `confirm_template` | Tela destino apareceu |
| Web (APEX/MSI3) | `verify_fill_web` via DOM | Sem OCR — lê direto do DOM |

### Como calibrar uma região OCR

1. Rodar o teste — abrir o screenshot do step no Paint
2. Cursor no canto **superior-esquerdo** do campo preenchido → anotar x1, y1
3. Cursor no canto **inferior-direito** do campo preenchido → anotar x2, y2
4. Atualizar `regioes_ocr` no `config.yaml`
5. Rodar — verificar `[verify_lov] OK — campo preenchido: 'VALOR'` no log
6. Abrir `report.html` — confirmar `OCR leu: VALOR` no badge do step

```yaml
# config.yaml — regioes_ocr
regioes_ocr:
  nome_social: { x1: 18, y1: 148, x2: 350, y2: 162 }  # habilitado ✅
  nr_admissao: { x1: 0, y1: 0, x2: 0, y2: 0 }          # bootstrap — desabilitado
```

---

## Padrões Oracle Forms

| Situação | Estratégia |
|---|---|
| Transição de tela crítica | `_clicar_aguardar(acao, confirmacao)` — nunca sleep fixo |
| Campo texto livre | `verify_lov` com região calibrada |
| Campo numérico | `verify_fill` com região calibrada |
| LOV resultado único | OK direto (sem busca) |
| LOV com lista | digita → Localizar → `double_click` |
| Campo com acento | `type_text()` obrigatório |
| Salvar | **F10** (nunca Ctrl+S) |
| Navegar módulo | Localizar no Menu → Pesquisar → Não → `double_click` |
| Popup variável | `_tpl_existe()` + `is_visible(threshold=0.80)` |

---

## Observabilidade — o que cada execução gera

| Arquivo | Para quem | Conteúdo |
|---|---|---|
| `report.html` | Dev / QA | Screenshots por step, badge ✔ VALIDADO, OCR leu: valor, histórico flakiness |
| `execution.json` | CI/CD | Dados estruturados — step_id, duration_ms, ocr_lido, causa_falha |
| `execution.log` | Dev | Log com timestamps — inclui [verify_lov] e [verify_fill] |
| `summary/summary_*.html` | Gestor | Verde/vermelho por jornada, sem ruído técnico |
| `flakiness.json` | QA | Histórico acumulado — taxa de falha e duração por step |

---

## Documentação

| Documento | Localização | Papel |
|---|---|---|
| VTAE_Projeto_v1.docx | docs/ | O leme — visão total, todas as fases A→H |
| VTAE_Manual_Tecnico_v1.md | docs/ | Como cada arquivo funciona, linha a linha |
| VTAE_Roadmap_v0.1.md | docs/ | Checklist de direção — evolui a cada fase |
| VTAE_Manual_Criacao_Testes_v0.1.md | docs/ | Passo a passo para criar novos testes |
| VTAE_Prompt_Instrucao_v0.5.13.md | raiz | Registro operacional — contexto para novo chat |

---

## Ambiente virtual — referência rápida

```bash
# Criar (uma vez por máquina)
python -m venv .venv

# Ativar (sempre antes de trabalhar)
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Linux/Mac

# Instalar
pip install -r requirements.txt && pip install -e . && playwright install chromium

# Desativar
deactivate
```