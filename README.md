# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA  
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.12-purple)
![Testes](https://img.shields.io/badge/testes-297%20unitários-green)
![Fase](https://img.shields.io/badge/fase-5f%20concluída-brightgreen)

---

## O que é o VTAE

O VTAE é um framework híbrido de automação de testes que combina visão computacional (OpenCV), controle de browser (Playwright) e OCR (EasyOCR) para interagir com qualquer sistema — como um usuário humano faria.

**O diferencial:** onde ferramentas puramente web (Playwright, Cypress, Selenium) não chegam, o VTAE chega. E onde ferramentas puramente desktop falham em aplicações web modernas, o VTAE também resolve.

Ideal para:
- Sistemas web modernos (Oracle APEX, React, Angular)
- Sistemas legados desktop sem API de automação (Oracle Forms, Citrix)
- Ambientes híbridos onde Playwright e OpenCV precisam trabalhar juntos

---

## Instalação e Configuração

### 1. Pré-requisito do sistema operacional

**Python 3.13+** — única dependência de SO necessária.
```bash
python --version  # deve retornar 3.13.x
```

> ✅ **Tesseract removido na v0.5.11** — o VTAE usa EasyOCR (instalado via pip, sem dependência de SO).

---

### 2. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd VTAE
```

---

### 3. Criar e ativar ambiente virtual (.venv)

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

> ✅ **Sempre use .venv** — o `.venv` está no `.gitignore` — nunca commitar.

---

### 4. Instalar dependências Python

```bash
pip install -r requirements.txt
pip install -e .
playwright install chromium
```

> ⚠️ O EasyOCR baixa modelos (~200MB) na primeira execução. A partir da segunda, usa cache local.

---

### 5. Configurar credenciais

Cada jornada tem seu próprio `.env` isolado. **Nunca commitar no Git.**

```bash
# configs/si3/si3_cadastro_paciente/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=   # vazio = cadastra novo; preenchido = reutiliza

# configs/si3/si3_internacao/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=
```

---

### 6. Verificar instalação

```bash
python -c "from src.vision.ocr import OcrHelper; OcrHelper.verificar_instalacao()"
python -m pytest tests/unit/ -v
vtae systems
```

---

### 7. Executar o primeiro teste

Pré-requisitos:
- SI3 aberto e **maximizado** na tela principal
- Credenciais configuradas no `.env`
- Resolução 1920x1080

```bash
vtae run --jornada internacao
```

---

## Estrutura do projeto

```
VTAE/
├── src/
│   ├── core/           # FlowContext, result, observer, types, estado_jornada
│   ├── vision/         # TemplateMatcher (multi-scale), OcrHelper, OcrEngine
│   ├── runners/        # OpenCVRunner, PlaywrightRunner
│   ├── flows/
│   │   ├── base_flow.py       # ← BaseFlow: _step, _dado, _coord, _tpl_existe,
│   │   │                      #             _focar_si3, _clicar_aguardar (v0.5.12)
│   │   ├── si3/
│   │   │   ├── login_flow.py
│   │   │   ├── cadastro_paciente_flow.py    (CP01–CP23) ✅ 3x
│   │   │   ├── admissao_internacao_flow.py  (AI01–AI19) ✅ validado 08/06
│   │   │   ├── admissao_ambulatorio_flow.py (AB01–AB15) ✅ 3x
│   │   │   ├── agendamento_flow.py          (AG01–AG13) ✅ 3x
│   │   │   └── admissao_com_agendamento_flow.py         🔜 aguarda calibração
│   │   ├── sislab/
│   │   │   ├── login_flow.py
│   │   │   └── cadastro_funcionario_flow.py (CF01–CF10) ✅
│   │   └── msi3/
│   │       ├── login_flow.py
│   │       ├── apex_helper.py
│   │       ├── frequencia_aplicacao_flow.py (FA01–FA10) ✅
│   │       └── tipo_anestesia_flow.py       (TA01–TA09) ✅
│   ├── config/         # ConfigLoader + schema.py
│   └── cli/            # run.py, send.py
├── configs/
│   └── si3/
│       ├── si3_cadastro_paciente/  config.yaml + .env
│       ├── si3_internacao/         config.yaml + .env
│       ├── si3_ambulatorio/        config.yaml + .env
│       └── si3_agendamento/        config.yaml + .env
├── templates/si3/
│   ├── cadastro_paciente/
│   │   └── titulo_menu_principal.png        # novo v0.5.12
│   ├── admissao_internacao/
│   │   ├── btn_selecionar_leito.png         # novo v0.5.12
│   │   ├── btn_ok_reserva_popup.png         # novo v0.5.12
│   │   ├── titulo_internacao.png            # novo v0.5.12
│   │   └── titulo_menu_principal.png        # novo v0.5.12
│   ├── admissao_ambulatorio/
│   └── agendamento/
├── tests/
│   ├── unit/
│   └── integration/
│       └── si3/
│           ├── components/
│           │   └── cadastro_paciente_fixture.py  ← única fonte da lógica de cadastro
│           └── jornadas/
│               ├── internacao/
│               ├── ambulatorio/sem_agendamento/
│               └── ambulatorio/com_agendamento/
├── scripts/
│   └── posicao_mouse.py
└── evidence/
    ├── flakiness.json
    ├── estado_jornada.json
    └── YYYY-MM-DD/
        ├── <teste>/
        │   ├── execution.log
        │   ├── execution.json
        │   └── report.html
        └── summary/
```

---

## CLI

```bash
# ── Jornadas completas ──────────────────────────────────────────────
vtae run --jornada internacao
vtae run --jornada ambulatorio
vtae run --jornada ambulatorio_com_agendamento
vtae run --jornada internacao --repeat 3

# ── Testes individuais ──────────────────────────────────────────────
vtae run --test cadastro_paciente_jornada
vtae run --test admissao_internacao_jornada
vtae run --test admissao_ambulatorio_jornada
vtae run --test agendamento_jornada
vtae run --test cadastro_funcionario
tae run --jornada ambulatorio_com_agendamento

# ── Utilitários ─────────────────────────────────────────────────────
vtae systems
vtae flakiness --top 5
vtae clean --days 7
vtae summary
vtae metrics
```

---

## Sistemas automatizados

| Sistema | Tipo | Runner | Flows validados | Steps |
|---|---|---|---|---|
| SI3 | Desktop Oracle Forms | OpenCV | Login, CadastroPaciente (3×), AdmissaoInternacao ✅ 08/06, AdmissaoAmbulatorio (3×), Agendamento (3×) | 3+23+19+15+13 |
| SisLab | Desktop Oracle Forms | OpenCV | Login, CadastroFuncionario | 3+10 |
| MSI3 | Web Oracle APEX 23.1 | Playwright+OpenCV | Login, FrequenciaAplicacao, TipoAnestesia | 5+10+9 |

---

## BaseFlow — padrão centralizado (v0.5.10+)

Todos os flows herdam `BaseFlow` (`src/flows/base_flow.py`).

```python
class MeuFlow(BaseFlow):
    def execute(self, ctx, dados, observer=None) -> FlowResult:
        ...
    def _step_xx01(self, ctx, observer=None):
        def fn():
            valor = self._dado(dados, "chave", "XX01")
            x, y  = self._coord(coords, "campo_x")
            self._clicar_aguardar(
                ctx,
                acao=lambda: ctx.runner.safe_click(f"{self._TPL}/btn.png"),
                confirmacao=f"{self._TPL}/tela_destino.png",
                label="XX01 transicao",
            )
        return self._step("XX01", "descricao", fn, observer, ctx=ctx)
```

**Helpers disponíveis:**
- `_step()` — wrapper com observabilidade completa
- `_dado()` — leitura segura de dado obrigatório
- `_coord()` — leitura de coordenada com erro claro
- `_tpl_existe()` — verifica existência de template antes de usar
- `_focar_si3()` — reativa janela Oracle Forms
- `_clicar_aguardar()` — clique com confirmação visual e retry automático *(novo v0.5.12)*

---

## `_clicar_aguardar` — transições robustas (v0.5.12)

Substitui o padrão `safe_click + time.sleep` fixo em todas as transições críticas.

```python
self._clicar_aguardar(
    ctx,
    acao=lambda: ctx.runner.safe_click(f"{self._TPL}/btn.png", threshold=0.7),
    confirmacao=f"{self._TPL}/tela_destino.png",
    timeout=12,    # segundos por tentativa
    threshold=0.7,
    retries=2,     # recliques se não confirmou
    label="AI06 admitir paciente",
)
```

**Comportamento:**
- Executa `acao()` → aguarda `confirmacao` via `wait_template`
- Se não apareceu → reclica até `retries` vezes
- Se template não existe → avisa no log e usa sleep fixo (bootstrap seguro)
- Funciona para desktop e web com o mesmo contrato

---

## Observabilidade

| Arquivo | Conteúdo |
|---|---|
| `execution.log` | Log estruturado com timestamps |
| `execution.json` | Dados estruturados por step (CI/CD) |
| `report.html` | Relatório técnico com screenshots |
| `summary/*.html` | Relatório gerencial (Onda 2) |
| `flakiness.json` | Histórico global de pass/fail |
| `estado_jornada.json` | paciente_id compartilhado entre steps |

### Três validações obrigatórias

| Situação | Validação |
|---|---|
| Digitação em campo | `verify_fill(valor, regiao_ocr)` — EasyOCR confirma |
| Seleção via LOV | `verify_lov(campo, regiao_ocr)` — EasyOCR confirma e loga valor lido |
| Navegação de tela | `_clicar_aguardar` ou `confirm_template` |

---

## OcrEngine — engine OCR centralizado (v0.5.11)

```yaml
# config.yaml de qualquer jornada
ocr_engine: easyocr   # padrão — pip puro, sem instalação no SO
```

| Altura do campo | Escala | Uso típico |
|---|---|---|
| < 20px | 4x | Campos numéricos Oracle Forms |
| < 35px | 3x | Nr. Leito, Nr. Admissão |
| < 60px | 2x | Campos médios |
| ≥ 60px | 1x | Campos grandes |

---

## Padrões consolidados

### Oracle Forms (SI3 / SisLab)
- `type_text()` obrigatório para campos com acentos
- `double_click` para menus Oracle Forms
- **LOV resultado único:** OK direto (sem busca)
- **LOV com lista:** digita → Localizar → `double_click`
- **TAB abre popup LOV:** mais estável que clicar na LOV
- **Popup condicional:** `_tpl_existe()` + `is_visible(threshold=0.80)`
- **Popup janela Forms flutuante:** template separado `btn_ok_reserva_popup.png`
- **Transição de tela:** `_clicar_aguardar` — nunca sleep fixo
- **Foco perdido:** `_focar_si3()` antes de steps críticos
- Salvar: **F10**
- Sair: **`_clicar_aguardar` com template de confirmação da tela seguinte**
- Navegação: **Localizar no Menu**

### Oracle APEX / MSI3
- Nunca navegar por URL direta — invalida a sessão APEX
- Cards sem href CSS — OpenCV obrigatório
- Formulários dialog — `ApexHelper` abstrai frames separados

---

## Fases do projeto

| Fase | Descrição | Status |
|---|---|---|
| 1–4c | Base, Clean Architecture, DSL | ✅ |
| 5a | CadastroPacienteFlow 23 steps, 3x | ✅ |
| 5b | Observabilidade básica | ✅ |
| 5c | Jornada ambulatório 3x | ✅ 26/05/2026 |
| 5d | AgendamentoFlow 13 steps, 3x | ✅ 27/05/2026 |
| Onda 1 | confirm_template + validated + _focar_si3 | ✅ 27/05/2026 |
| 5e | AdmissaoComAgendamento + reorganização | ✅ 28/05/2026 |
| 5f | AdmissaoInternacaoFlow AI01–AI19 | ✅ 08/06/2026 |
| v0.5.11 | EasyOCR + ocr_lido no report | ✅ 03/06/2026 |
| **v0.5.12** | **`_clicar_aguardar` + templates comuns + popup flutuante** | ✅ 08/06/2026 |
| 5g | Calibrar AdmissaoComAgendamento | 🔜 próximo |
| 6 | YOLO fine-tuning | 🔜 |
| 7 | CI/CD Jenkins + RDP | 🔜 |
| 8 | Portfólio profissional | 🔜 |

---

## Pendências ativas

| # | Pendência | Prioridade |
|---|---|---|
| 1 | Validar jornada internacao 3x consecutivas | 🔴 |
| 2 | `self._tpl()` no BaseFlow + pasta `templates/si3/common/` | 🔴 |
| 3 | Calibrar AdmissaoComAgendamento (Fase 5g) | 🔴 |
| 4 | Calibrar `regioes_ocr` si3_internacao (nr_admissao) | 🟡 |
| 5 | Validar jornadas ambulatorio/agendamento após v0.5.12 | 🟡 |
| 6 | Alertas automáticos de regressão (Onda 3) | 🟢 |

---

## Documentação

| Arquivo | Descrição |
|---|---|
| `docs/VTAE_Prompt_Instrucao_Geral_v0.5.12.md` | Estado atual — usar como contexto em novo chat |
| `docs/VTAE_Documentacao_Tecnica.docx` | Arquitetura, runners, matchers, exceções |
| `docs/VTAE_Manual_Criacao_Testes.docx` | Passo a passo para criar novos testes |
| `CHANGELOG.md` | Histórico de mudanças |

---

## Ambiente virtual (.venv)

```bash
# Criar (uma vez)
python -m venv .venv

# Ativar (sempre antes de trabalhar)
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # Linux/Mac

# Instalar dependências
pip install -r requirements.txt
pip install -e .
playwright install chromium

# Verificar EasyOCR
python -c "from src.vision.ocr import OcrHelper; OcrHelper.verificar_instalacao()"

# Desativar
deactivate
```

**O `.venv` está no `.gitignore`** — nunca commitar.