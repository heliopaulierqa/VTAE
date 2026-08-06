# VTAE — Manual Técnico (documento vivo)

**Versão do documento:** v0.1 · **Atualizado em:** 05/08/2026 (em tempo real durante as sessões)
**Substitui:** VTAE_Manual_Tecnico_v1.md (29/07) e VTAE_documentacao_tecnica_v.0.md — versões antigas podem ser apagadas.
**Público:** quem precisa entender o que o framework FAZ e ONDE cada coisa mora.

> **REGRA DE USO (inegociável):** este manual e o `VTAE_Projeto_v0.1.md` DEVEM
> ser consultados no início de qualquer sessão e atualizados EM TEMPO REAL.
> O histórico feito/fazendo/a fazer vive no Projeto §2; este manual descreve o
> código como ele É hoje. Convenção de honestidade: o que está aqui existe no
> código; meta futura ou coisa quebrada está marcada **[ALVO]**, **[PARCIAL]**,
> **[QUEBRADO]** ou **[MORTO — remover]**. Nada é maquiado.

---

## 1. O que é

Framework de automação de testes para Oracle Forms legado (SI3, SisLab), Oracle
APEX (MSI3) e futuro Citrix. Princípio: teste que executa sem validar resultado
é script. Tudo existe para responder as 5 perguntas de observabilidade:
o que executou? o que digitou/clicou? o sistema respondeu certo? se falhou,
por quê? é estável ao longo do tempo?

## 2. O mapa — um lugar por papel

```
VTAE/
├── vtae/                    código do framework (não existe mais src/)
│   ├── core/
│   │   ├── motor/           ★ O MOTOR (Fase 2) — ver §4
│   │   ├── context.py       FlowContext — a mochila entre steps
│   │   ├── result.py        StepResult / FlowResult / CausaFalha
│   │   ├── object_repository.py  adapter do YAML de objetos
│   │   ├── estado_jornada.py     estado entre flows de jornada (JSON)
│   │   ├── texto.py         _normalizar / _similar (tolerância OCR)
│   │   └── health_check.py  pré-condições de ambiente
│   ├── vision/              template matching (diagnose!) + EasyOCR
│   ├── runners/
│   │   ├── opencv_runner.py     desktop: template, pyautogui, verify_lov
│   │   ├── playwright_runner.py web: seletores CSS
│   │   ├── jab_reader.py        ★ LeitorJab — leitura exata via Access Bridge
│   │   ├── browser_launcher.py  abre Edge e dispara o SI3
│   │   └── database_runner.py   [CONGELADO — InCor]
│   ├── flows/               flows Python legados por sistema (geração 1)
│   │   └── si3/cadastro_min/steps.py  steps nomeados usados pelo motor
│   ├── config/              ConfigLoader + SystemConfig (schema)
│   ├── cli/                 vtae run / send / summary
│   └── report/              observer, report.html, summary, metrics
├── flows/                   ★ YAMLs de flow (roteiros do motor)
│   └── si3/cadastro_min.yaml    38 linhas — o cadastro inteiro
├── objects/                 ★ YAMLs de objetos (Modelo de Elemento)
│   └── si3/cadastro_min.yaml    atual (tipo/criticidade/locators)
├── configs/                 dados por teste (YAML + .env; credencial nunca no YAML)
├── templates/               PNGs dos locators de template
├── tests/                   unit/ (fakes) e integration/ (tela real)
├── scripts/                 mapear JAB, calibrar OCR, diagnose contra arquivo
├── evidence/                saída por execução: screenshots, execution.json, report.html
└── docs/                    Projeto v0.1, este manual, prompts de instrução
```

Regra de organização: cada informação tem UM lugar. Locator → `objects/`.
Dado de teste → `configs/`. Roteiro → `flows/*.yaml`. Mesma informação em dois
lugares = bug de arquitetura.

## 3. Conceitos essenciais

- **Step** — ação com identidade (S01...), screenshot, resultado próprio;
  abort-on-failure sempre.
- **Runner** — quem toca a tela; contrato em `base_runner.py` (`click_template`,
  `type_text`, `wait_template`, `safe_click`, `verify_lov`...).
- **FlowContext** — runner, config, evidence_dir, objects, jab (lazy), db
  (congelado), resultados acumulados.
- **Observer** — produz execution.log/json, report.html, screenshots por step.
- **Flow Python (geração 1)** — classe com steps codificados; legado, será
  substituído pela reescrita da Fase 3.
- **YAML de flow + motor (geração 3)** — o caminho atual: roteiro declarado,
  motor executa.

## 4. O MOTOR (`vtae/core/motor/`) — como um teste roda hoje

Comando: `vtae run --test cadastro_paciente_min` (atalho para
`pytest tests/integration/si3/test_cadastro_min_motor.py -s`) ou o pytest direto.

Peças (cada uma com unitário próprio em `tests/unit/`):

| Módulo | Papel |
|---|---|
| `plano.py` | lê o YAML de flow e monta o plano de steps |
| `validacao.py` | valida a declaração (campo sem objeto, tipo desconhecido...) |
| `interpolacao.py` | resolve `{faker:...}` e `{sorteio:...}` com os dados do config |
| `resolvedor.py` | decide o locator por elemento: jab → template → coordenada → seletor; loga qual resolveu |
| `acoes.py` | mecânica por `tipo`: texto/data digitam; lov = F9→digitar→ENTER→OK; lov_lista = F9→PAUSA→Localizar→ENTER→OK (regra 70: LOV é janela interna, sem HWND — nunca esperar janela do Windows) |
| `verificacao.py` | Verificador por tipo — ver matriz §5; produz OK/DIVERGENTE/VAZIO/NAO_VERIFICAVEL, camada decisora, divergência entre camadas |
| `executor.py` | orquestra: passo a passo, `_verificar_estavel` (3 releituras — só DIVERGENTE repete), observer, evidências |
| `passo.py` | representação de um passo executável |
| `esperas.py` | espera por condição (título de janela, template) — nunca sleep cego |

**Fluxo:** teste (boot) → `Executor(ctx, observer, leitor_exato).executar("flows/...yaml")`
→ plano → para cada step: ação por tipo → verificação por tipo → StepResult com
`ocr_lido`/`jab_lido`/avisos → FlowResult + report.

**LeitorJab (`runners/jab_reader.py`):** adaptador `.ler(nome) -> str|None`
entre pyjab e o Verificador. JAVA_HOME "de mentira" do config ANTES do import;
conexão cacheada; `TIMEOUT_CONEXAO=10` (regra 71: camada de verificação nunca
segura a jornada); falha degrada para OCR com aviso. **[PARCIAL]** sem unitário
ainda (pendência aberta).

**Boot provisório:** `tests/integration/si3/test_cadastro_min_motor.py` abre o
SI3 (browser_launcher), espera `popup_conexao.png`, roda `LoginFlow` (por
TEMPLATE — nunca LoginSi3Flow por coordenada, regra 75) e chama o Executor.
Morre quando a fixture `si3` (peça 5) nascer.

## 5. Camadas de verificação — o coração

| Camada | Prova | Quando decide |
|---|---|---|
| pyjab (LeitorJab) | o valor que o componente TEM (exato) | lov / lov_lista — pega match parcial silencioso (caso ALLIANZ) |
| OCR (EasyOCR) | o que o usuário VÊ | texto livre (Levenshtein ~30%); data/máscara por ESTRUTURA (mín. dígitos); resultado por polling |
| Template/OpenCV | a TELA reagiu | navegação, confirmação de tela |
| Playwright | DOM | web (MSI3) |
| Banco | persistência | [CONGELADO] |

Camadas são PARALELAS: pyjab prova o que o sistema tem, screenshot prova o que
o usuário vê — ambos ficam no StepResult. `criticidade` decide falha × aviso.
Divergência entre camadas: passa com aviso registrado (não some).

**Estado por campo do cadastro_min (medido 05/08):** nome=OCR ·
data_nascimento=OCR estrutura · hora=**nenhum** (aviso permanente) ·
sexo/nacionalidade/cor_etnia=**pyjab exato** · matricula/identificador=OCR polling.

## 6. Regras operacionais que mais queimam na prática

1. Medir antes de confiar — `diagnose()` contra arquivo real; sensibilidade E
   especificidade. Template via `pyautogui.screenshot()` + `PIL.crop()`, nunca Win+Shift+S.
2. Evidência PRIMEIRO (`evidence/<data>/<teste>/`, `*_auto_diag_*.png`) — abrir
   o print antes de qualquer hipótese (regra 8/36).
3. Durante execução em tela real, o SI3 é dono da tela — NADA pode cobrir o
   formulário; OCR lê a tela inteira, quem está na frente vence (regra 78).
   Rodar de PowerShell avulso, minimizado.
4. LOV do Forms é janela interna — pygetwindow não vê (regra 70). Título de
   janela só para telas com handle (`Form_Pac0010`, `Cadastro De Pacientes`).
5. Toda conexão externa com timeout explícito e degradação para aviso (regra 71).
6. Região OCR não pode alcançar o campo vizinho (regra 73 — caso cor_etnia).
7. Âncora por template tem que ser específica da TELA (regra 74 — caso nome_social).
8. `sys.executable` nos subprocess, nunca `"python"` (regra 30 — corrigido no
   run.py em 05/08: antes disso o CLI rodava pytest no Python GLOBAL, fora do venv).
9. JAVA_HOME do pyjab via config/código, nunca setx (regra 31).
10. Dado de teste via `_dado()`/config — default escondido proibido (regra 19).
11. F10 salva (não Ctrl+S); TAB não fecha LOV (clicar OK); janela pode abrir
    reduzida — maximizar antes do primeiro clique.
12. Gate 3x consecutivas antes de considerar qualquer coisa validada.

## 7. Testes

- **`tests/unit/`** — baseline atual: **967 passed / 86 failed**. As 86 são
  dívida antiga; triagem agendada (Projeto §2.3 item 3). Convenção: um arquivo
  de teste por módulo; FAKES em vez de MagicMock (fake devolve o programado e
  registra a FORMA da chamada — mock passaria sem provar nada, regra 42).
- **`tests/integration/`** — contra sistema real; componente (1 flow) ou
  jornada (flows encadeados com `estado_jornada.json`).
- Debug de verify_lov vai para `/tmp/...png` **[QUEBRADO no Windows — cai na
  raiz do drive; mover para evidence/]**.

## 8. Scripts de apoio

| Script | Uso |
|---|---|
| `posicao_mouse.py` | coordenada de um ponto da tela |
| `testar_regiao_ocr.py` | calibrar região OCR |
| `diagnose_contra_arquivo.py` | score de template contra screenshot salvo |
| `mapear_names_jab.py` | listar names JAB (dump `scripts/jab_dump.txt`) |
| `testar_conexao_db.py` | [CONGELADO] |

## 9. Glossário

**LOV** lista de valores do Forms · **Match parcial silencioso** texto inválido
que casa com o item mais próximo sem erro visível (só pyjab pega) · **Gate 3x**
3 execuções consecutivas sem falha · **Bootstrap** recurso não calibrado gera
aviso, não quebra · **Jornada** flows encadeados com estado · **Modelo de
Elemento** um registro por objeto de tela com todos os locators · **Geração 1**
flows Python legados · **Geração 2** [REMOVIDA na limpeza de 06/08]
dsl_interpreter/components · **Geração 3** o motor.
