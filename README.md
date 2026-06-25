# VTAE — Visual Test Automation Engine

> Framework híbrido de automação de testes baseado em Visão Computacional + IA  
> para sistemas web modernos, legados desktop e ambientes híbridos.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![Versão](https://img.shields.io/badge/versão-0.5.20-purple)
![Testes](https://img.shields.io/badge/testes-282%20unitários-green)
![Fase](https://img.shields.io/badge/fase-1%20(gate)%20em%20curso-orange)

---

## O que é o VTAE

Framework híbrido de automação de testes que combina visão computacional (OpenCV), controle de browser (Playwright) e OCR (EasyOCR) para interagir com qualquer sistema — como um usuário humano faria.

Ideal para:
- Sistemas web modernos (Oracle APEX, React, Angular)
- Sistemas legados desktop sem API de automação (Oracle Forms, Citrix)
- Ambientes híbridos onde Playwright e OpenCV precisam trabalhar juntos

---

## Instalação

### 1. Pré-requisito

**Python 3.13+** — única dependência de SO. Sem Java/JDK nem Tesseract.

```bash
python --version  # deve retornar 3.13.x
```

> ⚠️ **Resolução de tela: 1920x1080.** Coordenadas absolutas quebram silenciosamente em outras resoluções.

### 2. Instalar (recomendado)

```bash
instalar.bat   # cria .venv, instala dependências, valida EasyOCR
```

**Manual:**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
playwright install chromium
```

### 3. Credenciais

Cada funcionalidade tem seu próprio `.env`. **Nunca commitar no Git.**

```bash
# configs/si3/si3_login/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha

# configs/si3/si3_cadastro_paciente/.env
SI3_USER=seu_usuario
SI3_PASS=sua_senha
SI3_PACIENTE_ID=   # vazio = cadastra novo; preenchido = reutiliza
```

> **Regra:** nenhum comentário na mesma linha de `VAR=valor`. Comentários sempre em linha separada acima.

### 4. Verificar instalação

```bash
python -c "from src.vision.ocr import OcrHelper; OcrHelper.verificar_instalacao()"
python -m pytest tests/unit/ -v
vtae systems
```

---

## CLI — Comandos principais

```bash
# ── Jornadas completas ──────────────────────────────────────────────
vtae run --jornada internacao
vtae run --jornada ambulatorio
vtae run --jornada ambulatorio_com_agendamento
vtae run --jornada internacao --repeat 3

# ── Testes individuais ──────────────────────────────────────────────
vtae run --test login_si3_novo
vtae run --test cadastro_paciente_min
vtae run --test cadastro_paciente_jornada
vtae run --test admissao_internacao_jornada
vtae run --test admissao_ambulatorio_jornada

# ── Utilitários ─────────────────────────────────────────────────────
vtae systems          # lista sistemas disponíveis
vtae flakiness --top 5  # campos mais instáveis
vtae clean --days 7   # limpa evidências antigas
vtae summary          # relatório gerencial
vtae metrics          # métricas de execução
```

---

## Debug e calibração — Comandos do terminal

### Capturar screenshot e identificar coordenadas

```bash
# Tirar screenshot com 3s de delay (tempo para clicar na janela do sistema)
python -c "import pyautogui, time; time.sleep(3); pyautogui.screenshot('screenshot_sistema.png'); print('salvo')"

# Abrir no Paint para identificar coordenadas (x,y na barra de status)
python -c "import subprocess; subprocess.Popen(['mspaint', 'screenshot_sistema.png'])"
```

### Capturar template a partir do screenshot

```bash
# Recortar template com coordenadas identificadas no Paint
python -c "
from PIL import Image
img = Image.open('screenshot_sistema.png')
x1, y1, x2, y2 = 288, 224, 509, 358   # suas coordenadas
recorte = img.crop((x1, y1, x2, y2))
recorte.save('templates/si3/meu_modulo/meu_template.png')
print('Tamanho:', recorte.size)
recorte.show()
"
```

### Validar score de template (diagnose)

```bash
# ATENÇÃO: template PRIMEIRO, screenshot DEPOIS — inversão retorna 0.0 sempre
python -c "
from src.vision.template import TemplateMatcher
print(TemplateMatcher().diagnose(
    'templates/si3/meu_modulo/meu_template.png',
    'screenshot_sistema.png'
))"
```

| Score | Diagnóstico | Ação |
|---|---|---|
| ≥ 0.88 | Aprovado | Prosseguir |
| 0.75–0.87 | Aceitável | Documentar threshold no código |
| 0.50–0.74 | Problema estrutural | Recapturar |
| < 0.50 | Escala errada | Verificar método de captura |

> ⚠️ Oracle Forms via Edge tem teto real ~0.79. Documentar e justificar quando abaixo de 0.88.

### Capturar coordenada de campo

```bash
# Abre contador regressivo — posicionar mouse no campo durante a contagem
python scripts/posicao_mouse.py
```

### Testar região OCR isolada

```bash
# Testa leitura de uma região específica — salva _crop_raw.png e _crop_proc.png
python scripts/testar_regiao_ocr.py screenshot_sistema.png x1 y1 x2 y2

# Exemplos reais:
python scripts/testar_regiao_ocr.py screenshot_cadastro.png 27 145 447 168    # campo nome
python scripts/testar_regiao_ocr.py screenshot_cadastro.png 363 195 463 207   # data nasc
python scripts/testar_regiao_ocr.py screenshot_cadastro.png 543 192 633 212   # sexo
python scripts/testar_regiao_ocr.py screenshot_cadastro.png 565 148 662 166   # matricula
```

### Verificar config carregado (debug de dados)

```bash
# Confirma que o config.yaml e .env foram carregados corretamente
python -c "
from src.config import ConfigLoader
import pathlib
c = ConfigLoader.carregar('si3_cadastro_paciente_min', configs_dir=pathlib.Path('configs/si3'))
print('DADOS:', c.DADOS)
print('URL:', c.url)
print('OCR ENGINE:', c.ocr_engine)
"
```

### Testar _normalizar e _similar manualmente

```bash
python -c "
import sys; sys.path.insert(0, '.')
from src.flows.base_flow import _normalizar, _similar
# Testar normalizacao
print(_normalizar('CÂMARA'))           # CAMARA
print(_normalizar('04/11/2023'))       # 04112023
# Testar similaridade
print(_similar('3RUNA', 'BRUNA'))      # True  (B/3 — 1 erro em 5)
print(_similar('DLIIA', 'OLIVIA'))     # True  (O/D, V/I — 2 erros em 6)
print(_similar('TESTE ERRO', 'BRUNA')) # False (muito diferente)
"
```

### Ler arquivo completo pelo terminal

```bash
# Ler qualquer arquivo do projeto sem editor
cat src/flows/si3/cadastro_min/cadastro_paciente_min_flow.py
cat configs/si3/si3_cadastro_paciente_min/config.yaml
cat src/flows/base_flow.py

# Com numeração de linhas (útil para identificar onde editar)
cat -n src/flows/base_flow.py

# Filtrar linhas com palavra-chave
cat src/flows/base_flow.py | grep -n "_verify_campo"
cat src/flows/base_flow.py | grep -n "def _"

# Ver apenas parte do arquivo (linhas 50 a 100)
sed -n '50,100p' src/flows/base_flow.py
```

### Ver evidências de execução

```bash
# Listar execuções do dia
ls evidence/2026-06-25/

# Ver log de execução
cat evidence/2026-06-25/test_cadastro_paciente_min_flow/execution.log

# Abrir relatório HTML no browser
start evidence/2026-06-25/test_cadastro_paciente_min_flow/report.html

# Ver estado da jornada (paciente_id compartilhado)
cat evidence/estado_jornada.json

# Ver histórico de flakiness
cat evidence/flakiness.json
```

---

## Estrutura do projeto

```
VTAE/
├── instalar.bat                         # instalação do zero
├── vtae.bat                             # wrapper que ativa .venv
├── src/
│   ├── core/           # FlowContext, result, observer, types, estado_jornada
│   ├── vision/         # TemplateMatcher (multi-scale), OcrHelper, OcrEngine
│   ├── runners/
│   │   ├── opencv_runner.py
│   │   ├── playwright_runner.py
│   │   └── browser_launcher.py          # subprocess — não Playwright
│   ├── flows/
│   │   ├── base_flow.py                 # v0.5.20: _normalizar + _similar + verify com comparação
│   │   ├── si3/
│   │   │   ├── login/
│   │   │   │   └── login_si3_flow.py    # LoginSi3Flow ✅ 3x
│   │   │   ├── cadastro_min/
│   │   │   │   └── cadastro_paciente_min_flow.py  # CadastroPacienteMinFlow ✅ 3x
│   │   │   ├── cadastro_paciente_flow.py    (CP01–CP23) ✅ 3x
│   │   │   ├── admissao_internacao_flow.py  (AI01–AI19) ✅ 3x
│   │   │   ├── admissao_ambulatorio_flow.py (AB01–AB16) ✅ 3x — guards Fase 1 pendentes
│   │   │   ├── agendamento_flow.py          (AG01–AG13) ✅ 3x
│   │   │   └── admissao_com_agendamento_flow.py   🔜 3x pendente pós-gate
│   │   ├── sislab/
│   │   │   └── cadastro_funcionario_flow.py (CF01–CF10) ✅
│   │   └── msi3/
│   │       ├── frequencia_aplicacao_flow.py (FA01–FA10) ✅
│   │       └── tipo_anestesia_flow.py       (TA01–TA09) ✅
│   ├── config/         # ConfigLoader + schema.py
│   └── cli/            # run.py, send.py
├── configs/
│   └── si3/
│       ├── si3_login/
│       ├── si3_cadastro_paciente_min/
│       ├── si3_cadastro_paciente/
│       ├── si3_internacao/
│       ├── si3_ambulatorio/
│       └── si3_agendamento/
├── templates/si3/
│   ├── login/
│   ├── cadastro_paciente_min/
│   ├── cadastro_paciente/
│   ├── admissao_internacao/
│   ├── admissao_ambulatorio/
│   ├── agendamento/
│   └── common/                          # 🔜 Fase 1 Passo B
├── tests/
│   ├── unit/
│   └── integration/si3/
│       ├── components/
│       │   ├── login_si3_fixture.py          # ✅ 3x
│       │   └── test_cadastro_paciente_min.py # ✅ 3x
│       └── jornadas/
├── scripts/
│   ├── posicao_mouse.py       # captura coordenadas
│   └── testar_regiao_ocr.py   # calibra regioes OCR
└── evidence/
    ├── flakiness.json
    ├── estado_jornada.json
    └── YYYY-MM-DD/
        └── <teste>/
            ├── execution.log
            ├── execution.json
            └── report.html
```

---

## BaseFlow — helpers disponíveis (v0.5.20)

```python
# Wrapper canônico com observabilidade
self._step(step_id, descricao, fn, observer, confirm_template, validated, ctx)

# Leitura segura de dados e coordenadas
self._dado(dados, chave, step_id)
self._coord(coords, nome)
self._tpl_existe(path)

# Foco de janela
self._focar_si3()
self._focar_navegador_sislab(titulo_parcial)

# Ação com confirmação visual
self._clicar_aguardar(ctx, acao, confirmacao, timeout, threshold, retries, label)

# Verificação OCR de campo (v0.5.20 — compara valor lido vs esperado)
self._verify_campo_obrigatorio(ctx, nome, valor_esperado, step_id, regiao_key, ocr_holder)
self._verify_campo_opcional(ctx, nome, valor_esperado, step_id, regiao_key, ocr_holder)
```

**Funções auxiliares (módulo, fora da classe):**
```python
_normalizar(texto)                        # remove acentos + separadores
_similar(lido, esperado, tolerancia=0.30) # Levenshtein 30%
```

---

## Observabilidade

| Arquivo | Conteúdo |
|---|---|
| `execution.log` | Log estruturado com timestamps |
| `execution.json` | Dados por step para CI/CD |
| `report.html` | Relatório com screenshots de cada step |
| `summary/*.html` | Relatório gerencial |
| `flakiness.json` | Histórico global de pass/fail |
| `estado_jornada.json` | `paciente_id` compartilhado entre flows |

---

## Sistemas automatizados

| Sistema | Tipo | Flows validados |
|---|---|---|
| SI3 | Desktop Oracle Forms | Login ✅, CadastroPacienteMin ✅, CadastroPaciente ✅, AdmissaoInternacao ✅, AdmissaoAmbulatorio ✅, Agendamento ✅ |
| SisLab | Desktop Oracle Forms | Login, CadastroFuncionario ✅ |
| MSI3 | Web Oracle APEX 23.1 | Login, FrequenciaAplicacao ✅, TipoAnestesia ✅ |

---

## Documentação

| Arquivo | Descrição |
|---|---|
| `docs/VTAE_Prompt_Instrucao_Geral_v0_5_20.md` | Estado atual — usar como contexto em novo chat |
| `docs/VTAE_Manual_Criacao_Testes_v0_5_18.docx` | Manual completo de criação de testes |
| `VTAE_Roadmap_Observabilidade_v0_5_17.docx` | Roadmap Fase 1 detalhado |
| `docs/VTAE_Documentacao_Tecnica.docx` | Arquitetura, runners, matchers |
| `CHANGELOG.md` | Histórico de mudanças |