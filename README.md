# VTAE — Visual Test Automation Engine

> Framework de automação de testes baseado em Visão Computacional + OCR,
> genérico para qualquer sistema com tela: desktop, legado, Citrix e web.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.49-purple)
![Testes](https://img.shields.io/badge/testes-952%20unitários-green)
![Fase](https://img.shields.io/badge/fase-2%20—%20Formato%20declarativo-brightgreen)

---

## O que é o VTAE

Framework de automação de testes que combina visão computacional (OpenCV),
controle de browser (Playwright) e OCR (EasyOCR) para interagir com qualquer sistema
como um usuário humano faria.

**Palavra-chave: CONFIANÇA.** Teste que executa sem validar resultado é script, não teste.

**Independente de sistema.** Nada no núcleo depende de um sistema específico.
SI3, SisLab e MSI3 são campos de prova reais, não referência de design.

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
| Sistema sob teste | aberto e maximizado | Antes de mapear ou executar |

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

> ⚠️ `pip install -e .` e o `.venv` **guardam o caminho absoluto da pasta**.
> Se a pasta do projeto for movida ou renomeada, veja
> [Problemas comuns](#problemas-comuns).

### 4. Configurar credenciais

Cada teste tem seu `.env` na pasta de dados (`configs/<sistema>/<funcionalidade>/`).
**Nunca commitar no Git.**

```bash
# configs/si3/si3_cadastro_paciente/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=        # vazio = cadastra novo; preenchido = reutiliza

# configs/msi3/.env
MSI3_USER=seu_usuario
MSI3_PASS=sua_senha

# .env na raiz (opcional — pyjab, JAVA_HOME de mentira para Access Bridge)
SI3_JAB_HOME_FAKE=C:\jab_home
```

> Comentários no .env sempre em linha separada — **nunca na mesma linha do VAR=valor**.

### 5. Verificar instalação

```bash
# Pacote instalado e apontando para ESTA pasta
python -c "import vtae; print(vtae.__file__)"

# Testes unitários (952 passando em 25/09/2026)
python -m pytest tests/unit/

# CLI
vtae systems
```

O caminho impresso pelo primeiro comando precisa ser o da pasta atual do projeto.

---

## Criar um teste — caminho atual

Passo a passo completo: **VTAE_Manual_Criacao_Testes, §0** (do zero ao gate).

```bash
# 1. Mapear os elementos da tela (5 s para deixar a tela na frente)
vtae mapear objects/<sistema>/<funcionalidade>.yaml

# 2. Escrever o roteiro em flows/<sistema>/<funcionalidade>.yaml
#    com os verbos genéricos: abrir, esperar, clicar, teclar,
#    preencher, verificar, salvar, ler_resultado

# 3. Executar uma vez
vtae executar flows/<sistema>/<funcionalidade>.yaml

# 4. Gate: 3 execuções seguidas, para na primeira falha
vtae executar flows/<sistema>/<funcionalidade>.yaml --vezes 3
```

Regras:
- Uma pasta por sistema, um arquivo por funcionalidade (em `objects/` e em `flows/`).
- Elementos do caminho até a tela (menu, busca, popup) vão no arquivo de objetos do próprio roteiro.
- A prova de cada passo tem que ser **exclusiva da tela depois da ação** — o recorte não pode aparecer na tela anterior.
- O gate não fecha com degradação (template caiu para coordenada).

---

## CLI — comandos disponíveis

```bash
# Caminho atual (decisão 26)
vtae mapear objects/<sistema>/<tela>.yaml       # mapear elementos de uma tela
vtae executar flows/<sistema>/<roteiro>.yaml    # rodar qualquer roteiro
vtae executar flows/<sistema>/<roteiro>.yaml --vezes 3   # gate

# Utilitários
vtae systems            # lista sistemas detectados
vtae flakiness --top 5  # top steps mais flaky
vtae clean --days 7     # limpa evidências antigas
vtae summary            # relatório gerencial
vtae metrics            # métricas de cobertura

# Acervo histórico (testes em Python — só consulta, sem gate)
vtae run --test cadastro_paciente_jornada
vtae run --jornada internacao
```

---

## Problemas comuns

### `ModuleNotFoundError: No module named 'vtae'` ou `Fatal error in launcher: Unable to create process` depois de mover/renomear a pasta

**Causa:** `pip install -e .` não copia o código — registra o caminho da pasta.
O `.venv` também guarda o caminho absoluto de onde foi criado. Movendo ou
renomeando qualquer pasta do caminho, os dois passam a apontar para um lugar
que não existe.

**Correção** (na pasta nova):

```powershell
# 1. Sair do .venv antigo e apagá-lo (o pip.exe dele aponta para a pasta velha)
deactivate
Remove-Item -Recurse -Force .venv

# 2. Recriar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install -e .
playwright install chromium
```

> Use `python -m pip` em vez de `pip`: o `pip.exe` grava o caminho do Python
> de onde foi criado; `python -m pip` usa sempre o Python ativo.

**Conferir:**

```powershell
python -c "import sys; print(sys.prefix)"        # deve mostrar ...\VTAE\.venv da pasta nova
python -c "import vtae; print(vtae.__file__)"    # deve mostrar ...\VTAE\vtae\__init__.py da pasta nova
```

> O prompt mostrar `(.venv)` não garante nada: o `activate` de um `.venv`
> antigo ativa o caminho velho. Confie no `sys.prefix`.

---

## Estrutura do projeto

```
VTAE/
├── vtae/                    O MOTOR — código genérico do framework
│   ├── cli/                 vtae mapear, vtae executar, vtae run...
│   ├── core/                FlowContext, ObjectRepository, motor declarativo
│   ├── vision/              TemplateMatcher (multi-scale) + OcrEngine (EasyOCR)
│   ├── runners/             OpenCVRunner, PlaywrightRunner, DatabaseRunner, jab_reader
│   ├── flows/               flows Python do acervo histórico
│   └── report/              observer.py, report_generator.py, summary_generator.py
│
├── flows/                   Roteiros YAML — um arquivo por funcionalidade
├── objects/                 Modelo de Elemento — YAML por tela (gerado pelo vtae mapear)
├── configs/                 Dados de teste por funcionalidade (config.yaml + .env)
├── templates/               PNGs para template matching (gerados pelo vtae mapear)
├── tests/
│   ├── unit/                testes com mock — rodam sem sistema aberto
│   └── integration/         testes do acervo histórico contra o sistema real
├── scripts/
│   ├── posicao_mouse.py     capturar coordenadas x,y na tela
│   ├── testar_regiao_ocr.py calibrar região OCR — ver o que o EasyOCR lê
│   └── diagnose_contra_arquivo.py  medir score de template vs screenshot
├── docs/                    os quatro documentos do projeto (ver abaixo)
├── README.md                este arquivo
└── evidence/                gerado automaticamente ao rodar testes
    ├── flakiness.json       histórico pass/fail por step
    └── YYYY-MM-DD/
        └── <teste>/
            ├── execution.log    log estruturado
            ├── execution.json   dados por step (CI/CD)
            └── report.html      relatório visual com screenshots
```

---

## Campos de prova

| Sistema | Tipo | Estado |
|---|---|---|
| SI3 | Oracle Forms → login migrado para APEX (10/2026) | Login: gate 3/3 em 25/09 (Forms); refazendo no APEX. Próximo: cadastro |
| SauceDemo | Web | Bancada web — a montar |
| SisLab | Desktop Oracle Forms | Exploração (trilha paralela, sem gate) |
| MSI3 | Web Oracle APEX | Candidata a terceira bancada (decisão 21) |

> Os testes estão sendo refeitos do zero (10/2026) com `vtae mapear` + roteiro YAML.
> O piloto CadastroMin foi removido.
>
> Os testes em Python de SI3, SisLab e MSI3 (cadastro de paciente, admissões,
> agendamento, cadastro de funcionário, frequência de aplicação, tipo de anestesia)
> são **acervo histórico**: ficam para consulta, sem calibração nem gate.

---

## Referência — padrões do acervo histórico

Usados nos flows Python antigos. Ficam como consulta; testes novos usam os
verbos genéricos do roteiro YAML.

### Validação por tipo de campo

| Tipo | Método | O que prova |
|---|---|---|
| Texto livre (nome, data, etnia) | `verify_lov` com região calibrada | Campo não ficou vazio + valor lido aparece no report |
| Numérico (matrícula, leito) | `verify_fill` com região calibrada | Valor exato conferido |
| LOV (seleção de lista) | `verify_lov` com região calibrada | Seleção não ficou vazia |
| Navegação / clique | `confirm_template` | Tela destino apareceu |
| Web (APEX/MSI3) | `verify_fill_web` via DOM | Sem OCR — lê direto do DOM |

### Padrões Oracle Forms

| Situação | Estratégia |
|---|---|
| Transição de tela crítica | `_clicar_aguardar(acao, confirmacao)` — nunca sleep fixo |
| Campo com acento | `type_text()` obrigatório |
| Salvar | **F10** (nunca Ctrl+S) |
| Navegar módulo | Localizar no Menu → Pesquisar → Não → `double_click` |
| Popup variável | `_tpl_existe()` + `is_visible(threshold=0.80)` |

---

## Observabilidade — o que cada execução gera

| Arquivo | Para quem | Conteúdo |
|---|---|---|
| `report.html` | Dev / QA | Screenshots por step, badge ✔ VALIDADO, OCR leu: valor |
| `execution.json` | CI/CD | Dados estruturados — step_id, duration_ms, ocr_lido, causa_falha, avisos de degradação |
| `execution.log` | Dev | Log com timestamps — inclui avisos de degradação |
| `summary/summary_*.html` | Gestor | Verde/vermelho por jornada, sem ruído técnico |
| `flakiness.json` | QA | Histórico acumulado — taxa de falha e duração por step |

> ⚠️ Dívida conhecida: avisos de degradação ainda **não** aparecem no `report.html` —
> conferir no `execution.log` ou no `execution.json`.

---

## Documentação

Fonte da verdade: os quatro documentos em `docs/`. Em conflito, o Projeto vence.

| Documento | Papel |
|---|---|
| VTAE_Roadmap.docx | **Ler primeiro** — onde o trabalho parou e o próximo passo |
| VTAE_Projeto.docx | O leme — visão total, fases 1–6, decisões |
| VTAE_Manual_Criacao_Testes.docx | Passo a passo para criar testes (§0: do zero ao gate) |
| VTAE_Manual_Tecnico.docx | Como cada parte do framework funciona |

A versão de cada documento vive dentro dele, nunca no nome do arquivo.

---

## Ambiente virtual — referência rápida

```bash
# Criar (uma vez por máquina — e de novo se a pasta for movida)
python -m venv .venv

# Ativar (sempre antes de trabalhar)
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Linux/Mac

# Instalar
pip install -r requirements.txt && pip install -e . && playwright install chromium

# Conferir qual Python está em uso
python -c "import sys; print(sys.prefix)"

# Desativar
deactivate
```
