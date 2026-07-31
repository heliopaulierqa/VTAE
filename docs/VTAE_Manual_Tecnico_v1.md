# VTAE — Manual Técnico do Framework

**Versão do manual:** 1.0 · **Data:** 29/07/2026
**Base:** código real do repositório, verificado arquivo a arquivo nesta data
**Público:** quem precisa entender o que o framework FAZ e ONDE cada coisa mora — sem precisar ler o código inteiro

Convenção de honestidade deste manual: tudo que está descrito aqui existe no código
hoje. Quando algo é meta futura ou está quebrado/incompleto, está marcado
explicitamente como **[ALVO]**, **[PARCIAL]** ou **[QUEBRADO]**. Nada é maquiado.

---

## 1. O que é o VTAE

O VTAE (Visual Test Automation Engine) é um framework de automação de testes para
aplicações que ferramentas comuns não alcançam: sistemas legados Oracle Forms
(SI3, SisLab), web moderna Oracle APEX (MSI3) e, no futuro, Citrix e desktop
genérico.

O princípio central, registrado no Projeto v1: **teste que executa sem validar
resultado é script, não teste.** Tudo no framework existe para responder 5
perguntas de observabilidade sobre cada execução:

1. O que executou?
2. O que digitou/clicou?
3. O sistema respondeu certo?
4. Se falhou, por quê?
5. O sistema é estável ao longo do tempo?

## 2. O mapa — um lugar por papel

```
VTAE/
├── vtae/            O MOTOR — código genérico do framework
│   ├── core/        contexto, resultados, exceções, estado entre testes, DSL
│   ├── vision/      visão computacional: template matching + OCR
│   ├── runners/     quem toca a tela: OpenCV (desktop), Playwright (web)
│   ├── flows/       BaseFlow (helpers genéricos) + flows por sistema/domínio
│   └── report/      observabilidade: logs, evidências, report.html, métricas
│
├── objects/         O QUE EXISTE NAS TELAS — Modelo de Elemento (YAML)
│                    cada objeto: coordenada, região OCR, template, jab_name
│
├── configs/         O QUE CADA TESTE USA — dados, cenário, credenciais (YAML+.env)
├── templates/       as imagens PNG que os locators de template apontam
├── tests/           unit/ (com mock) e integration/ (contra sistema real)
├── scripts/         ferramentas de apoio (mapear JAB, calibrar OCR, diagnosticar)
├── docs/            Projeto v1/v1.1, este manual, manuais de uso
│
└── src/             [LEGADO EM ESVAZIAMENTO] restam: config/ (loader), cli/,
                     components/, core/object_repository.py, runners/database_runner.py
```

A regra de organização: **cada tipo de informação tem UM lugar.** Se a mesma
informação aparecer em dois lugares, é bug de arquitetura, não opção.

| Pergunta | Onde está a resposta |
|---|---|
| Onde fica o campo X na tela? | `objects/<tela>.yaml` |
| Que valor digitar no campo X? | `configs/<sistema>/<funcionalidade>/config.yaml` |
| Como clicar/esperar/ler? | `vtae/runners/` + `vtae/vision/` |
| Que passos o teste executa? | `vtae/flows/<sistema>/<domínio>/<flow>.py` |
| O que aconteceu na execução? | `evidence/<data>/<teste>/` (screenshots + execution.json + report.html) |

## 3. Os conceitos essenciais

**Flow** — uma classe Python que representa uma funcionalidade testável (ex:
`CadastroPacienteMinFlow`). Um flow é uma sequência de **steps**.

**Step** — uma ação com identidade (`CM01`, `AB07`...), descrição legível,
screenshot de evidência e resultado próprio. Se um step falha, o flow aborta
(abort-on-failure, sempre).

**Runner** — quem efetivamente toca a tela. O flow nunca sabe COMO clicar; ele
pede ao runner. `OpenCVRunner` (desktop, por imagem), `PlaywrightRunner` (web,
por seletor CSS). Contrato comum em `vtae/runners/base_runner.py`:
`click_template`, `type_text`, `screenshot`, `wait_template`, `safe_click`.

**FlowContext** (`vtae/core/context.py`) — a mochila que passa de step em step.
Carrega: `runner`, `config`, `evidence_dir`, `objects` (ObjectRepository),
`jab` (conexão Access Bridge, lazy), `db` (congelado), e os resultados acumulados.

**Observer** (`vtae/report/observer.py`) — escuta cada step e produz os artefatos
de observabilidade: `execution.log`, `execution.json`, `report.html`, screenshots
nomeados por step.

**Teste** — um arquivo em `tests/integration/` que monta o contexto (config +
runner + observer + objects), executa um ou mais flows e faz `assert` no
resultado. Testes de **jornada** encadeiam flows (ex: cadastro → agendamento →
admissão), passando estado via `estado_jornada.json`.

## 4. Anatomia de uma execução

Comando: `vtae run --test cadastro_paciente_min` (CLI em `src/cli/run.py`).

1. O CLI localiza o(s) arquivo(s) de teste e dispara o pytest.
2. O teste carrega o config (`ConfigLoader.carregar(...)`), cria o runner,
   o observer e o `FlowContext`. Para o CadastroMin, carrega também o
   `ObjectRepository` de `objects/cadastro_min.yaml`.
3. O flow executa step a step. Cada step passa pelo `BaseFlow._step()`, que:
   - loga o início no observer;
   - executa a ação (função `fn` do step);
   - se houver `confirm_template`, espera a tela destino aparecer (8s) —
     achou → step marcado `validated=True`; não achou → falha;
   - cronometra, captura screenshot, classifica a causa em caso de erro
     (`CausaFalha`: template não encontrado, timeout, OCR, coordenada,
     configuração, sistema, estado ausente, desconhecida);
   - em falha: tira screenshot automático de diagnóstico.
4. Ao final: `FlowResult` (sucesso = todos os steps ok), report.html gerado,
   evidências salvas em `evidence/<data>/<teste>/`.

## 5. As camadas de verificação — o coração do framework

Um clique pode "funcionar" e o sistema ainda assim gravar coisa errada. Por isso
existem camadas paralelas, cada uma provando uma coisa diferente:

| Camada | Onde vive | O que prova | Quando usar |
|---|---|---|---|
| **OpenCV / template matching** | `vtae/vision/template.py` + `OpenCVRunner` | a TELA reagiu (botão sumiu, tela nova apareceu) | navegação, cliques, confirmação de tela |
| **OCR (EasyOCR)** | `vtae/vision/ocr*.py` | o que o usuário VÊ escrito no campo | campos de texto livre; tolerância Levenshtein 20-23% para ruído de fonte |
| **pyjab (Java Access Bridge)** | helper `_verify_campo_via_jab` no BaseFlow | o valor REAL que o componente TEM (leitura exata, sem ruído) | campos de lista/LOV em Oracle Forms — pega o "match parcial silencioso" que nenhuma camada visual pega (caso ALLIANZ/PALMEIRAS) |
| **Playwright** | `PlaywrightRunner` | DOM da página web | sistemas web (MSI3) — OCR/pyjab não se aplicam |
| **Banco (DatabaseRunner)** | `src/runners/database_runner.py` | o registro foi PERSISTIDO | **[CONGELADO]** por decisão de segurança do InCor |

Matriz de decisão por tipo de campo (a regra que decide qual camada verifica o quê):

| Tipo de campo | Verificação |
|---|---|
| Lista/LOV (Sexo, Provedor, Unidade...) | pyjab (exato) + OCR em paralelo |
| Texto livre (Nome, Observação) | OCR com tolerância |
| Com máscara/reformatação (data, CPF) | verificação por ESTRUTURA (mín. de dígitos), nunca valor exato via OCR |
| Resultado gerado pelo sistema (matrícula, nº admissão) | OCR da região + obrigatório não-vazio |
| Navegação/clique | template matching (`confirm_template`) |
| Web | seletor Playwright |

Ponto essencial: **as camadas são PARALELAS, não substitutas.** O pyjab prova o
que o sistema tem; o screenshot+OCR prova o que o usuário vê. Ambos ficam no
resultado.

## 6. Componentes, um a um

### 6.1 `vtae/core/`

- **`context.py` — FlowContext.** Dataclass com runner, config, credenciais,
  evidence_dir, objects, jab, db. Propriedades `user`/`password` resolvem
  credencial do dict ou do config. Métodos: `add_result`, `all_passed`,
  `print_summary`.
- **`result.py` — StepResult / FlowResult / CausaFalha.** O StepResult carrega:
  sucesso, duração, screenshot, erro, causa classificada, `validated`
  (True = houve verificação real, não só execução), `description` e `ocr_lido`
  (o valor que a verificação leu — rastreabilidade no report).
- **`exceptions.py`** — exceções tipadas (StepError, ConfigError...).
- **`estado_jornada.py`** — persistência simples (JSON) de valores entre flows
  de uma jornada (ex: `paciente_id` gerado no cadastro e usado na admissão).
- **`dsl_interpreter.py`** — interpretador de testes declarados em YAML (DSL).
  Executa ações como `login`, `click`, `type` a partir de um YAML de steps.
  **[PARCIAL]** — funcional para casos simples; os flows Python são o caminho
  principal hoje.
- **`health_check.py`** — verificação de pré-condições de ambiente.

### 6.2 `vtae/vision/`

- **`template.py` — TemplateMatcher.** Localiza imagens na tela (OpenCV):
  `find`, `find_or_none`, `find_all`, `find_best`, multi-escala, âncora com
  offset, e o **`diagnose()`** — relatório de score com heurísticas (equalize
  etc.), usado para medir template antes de confiar (regra do projeto: medir
  antes de confiar; `scripts/diagnose_contra_arquivo.py` roda contra screenshot
  salvo).
- **`ocr.py` / `ocr_engine.py` / `ocr_helper.py`** — leitura de texto por região
  da tela via EasyOCR. `OcrHelper.ler_regiao`, `contem_qualquer_token`,
  `salvar_debug` (recorte da região para calibração).

### 6.3 `vtae/runners/`

- **`base_runner.py`** — o contrato (ABC): `click_template`, `type_text`,
  `screenshot`, `wait_template`, `safe_click` (retry). Qualquer runner novo
  (Citrix, por exemplo) implementa este contrato — os flows não mudam.
- **`opencv_runner.py`** — desktop. Clica por template, digita via pyautogui,
  lê por OCR (`verify_lov(nome, region, timeout)` retorna `(ok, texto_lido)`),
  `is_visible`, `click_near` (âncora + offset).
- **`playwright_runner.py`** — web. Mesmos métodos com seletores CSS;
  `navigate`, `fill`; expõe `_page` para casos avançados (frames APEX).
- **`browser_launcher.py`** — abre o Edge e dispara o SI3 (Oracle Forms via
  browser) — usado no bootstrap do teste do CadastroMin.

### 6.4 `vtae/flows/` — o BaseFlow e os flows

**`base_flow.py`** é o helper central. Todo flow herda dele e ganha:

| Helper | O que faz |
|---|---|
| `_step(id, descricao, fn, observer, confirm_template, validated, ctx)` | wrapper canônico de step: cronometra, confirma tela, classifica falha, screenshot automático |
| `_dado(dados, chave, step_id)` | leitura OBRIGATÓRIA de dado do config — falha com mensagem clara se ausente. Regra 19: `dados.get(x, default)` é PROIBIDO nos flows |
| `_coord(coords, nome)` | coordenada do config **[EM EXTINÇÃO — substituída por `ctx.objects.coord()`]** |
| `_tpl_existe(path)` | template existe? (bootstrap de templates ainda não capturados) |
| `_focar_si3()` / `_focar_navegador_sislab()` | foco de janela, tolerante |
| `_clicar_aguardar(ctx, acao, confirmacao, ...)` | clique com confirmação visual + retry; fallback com aviso se template não capturado |
| `_verify_campo_obrigatorio(...)` | OCR da região: campo vazio ou valor incompatível → falha |
| `_verify_campo_opcional(...)` | idem, mas só avisa (não bloqueia) |
| `_verify_campo_via_jab(ctx, jab_name, valor, step_id, holder)` | leitura EXATA via Access Bridge; comparação sem tolerância |
| `_conectar_db` / `_obter_via_banco_ou_yaml` | **[CONGELADO]** fallback banco→YAML preservado |

Funções de módulo: `_normalizar` (remove acentos/separadores — OCR perde
acentos em fonte Oracle Forms) e `_similar` (distância de edição com tolerância
— aceita ruído B/3, O/D sem aceitar valor errado).

**Flows por sistema** (estado em 29/07/2026):

| Sistema | Flow | Steps | Estado |
|---|---|---|---|
| SI3 | `LoginFlow` (template) e `LoginSi3Flow` (coordenada) | 3 | validados |
| SI3 | `CadastroPacienteMinFlow` | CM01-CM10 | **PILOTO da Fase 0** — ObjectRepository ligado, pyjab em bootstrap (names sendo mapeados) |
| SI3 | `CadastroPacienteFlow` | CP01-CP27 | **[QUEBRADO]** bug real no CP04 + defaults em código que violam a regra 19 |
| SI3 | `AdmissaoAmbulatorioFlow` | AB01-AB16 | referência técnica do pyjab (validado 3x) |
| SI3 | `AdmissaoInternacaoFlow`, `AdmissaoComAgendamentoFlow`, `AgendamentoFlow` | — | validados, aguardam propagação do padrão |
| SisLab | `LoginFlowSisLab`, `CadastroFuncionarioFlowSislab` | 3 + CF01-CF10 | validados; coordenadas hardcoded em constantes (dívida registrada) |
| MSI3 | `LoginFlowMsi3`, `TipoAnestesiaFlow` | MW01-05, TA01-08 | validados (web) |
| MSI3 | `CadastrarOrientacaoFlow` | OR01 | esqueleto intencional (aguarda acesso ao sistema) |

### 6.5 `vtae/report/`

- **`observer.py` — ExecutionObserver.** Cria a pasta de evidência do teste,
  loga início/fim de cada step, injeta logger no runner, grava
  `execution.json` e gera `report.html` ao final (`observer.report(ctx)`).
- **`report_generator.py` / `summary_generator.py` / `metrics.py`** — o HTML
  por execução, o consolidado de várias execuções e as métricas (cobertura de
  validação: quantos steps têm `validated=True`).

### 6.6 `objects/` — o Modelo de Elemento

`objects/cadastro_min.yaml` (único até agora — piloto):

```yaml
tela:
  titulo_jab: "Form_Pac0010"        # título da janela Java (JABDriver)

objetos:
  campo_sexo_lov:
    coordenada: { x: 648, y: 200 }   # onde clicar
  campo_sexo:
    regiao_ocr: { x1: 543, y1: 192, x2: 633, y2: 212 }   # onde ler
    jab_name: 'Descrição do Sexo.'   # locator de acessibilidade (exato)
```

Cada objeto de tela é UM registro com MÚLTIPLOS locators — coordenada (clique),
região OCR (leitura visual), template (imagem) e jab_name (leitura exata).
Este é o embrião da visão do Projeto v1 §4. O adapter que lê este YAML é o
`ObjectRepository` (**[ATENÇÃO]** ainda em `src/core/object_repository.py` —
migração para `vtae/core/` pendente de decisão): `coord()`, `regiao_ocr()`,
`template()`, `jab_name()` (tolerante — None se não mapeado), `titulo_jab()`.

**[ALVO]** Fase 2 do Projeto v1: um resolvedor `self.obj(ctx, "campo_x")` que
tenta jab → template → coordenada automaticamente, logando qual locator resolveu.

### 6.7 `configs/` — dados do teste

Estrutura: `configs/<sistema>/<funcionalidade>/config.yaml` + `.env` (credenciais
e segredos — nunca no YAML; comentários SEMPRE em linha própria no .env).

O `ConfigLoader` (`src/config/loader.py`) monta um `SystemConfig`
(`src/config/schema.py`) que expõe `DADOS` — e aqui mora um comportamento que
precisa estar claro:

**`DADOS` = seção `dados:` (valores fixos) + seção `dados_faker:` (REGRAS de
geração).** O `dados_faker` não guarda valores — guarda instruções ("nome = Faker
gera nome novo"). A cada execução o valor é inventado na hora (decisão de
projeto: LGPD, nunca dado real de paciente). Em conflito de chave, o Faker
sobrescreve o fixo. Consequência prática: apagar um valor do YAML NÃO esvazia o
campo se existir regra `dados_faker` para ele — a regra continua gerando.
O valor usado em cada execução fica registrado no `execution.json`/report.

### 6.8 `tests/`

- **`tests/unit/`** — ~890 testes com runner mockado (MagicMock). Rodam em
  segundos, sem sistema aberto. Padrão: classe por step, caminho de sucesso E
  de falha, `TestAbortOnFailure`. Baseline conhecido: 89 falhas pré-existentes
  (82 do CadastroPacienteFlow quebrado + 7 menores) — mapeadas na proposta v1.1.
- **`tests/integration/`** — contra o sistema real. Os de **componente**
  (ex: `test_cadastro_paciente_min.py`) testam um flow; os de **jornada**
  (`tests/integration/si3/jornadas/...`) encadeiam flows com estado
  compartilhado. **[PARCIAL]** exigem sistema aberto manualmente (bootstrap
  automático é tarefa aberta; o teste do CadastroMin já abre o SI3 sozinho
  via `browser_launcher`).

### 6.9 `scripts/` — ferramentas

| Script | Uso |
|---|---|
| `posicao_mouse.py` | descobrir coordenada de um ponto da tela |
| `testar_regiao_ocr.py` | calibrar região OCR (ver o que o OCR lê) |
| `diagnose_contra_arquivo.py` | medir score de template contra screenshot salvo |
| `mapear_names_jab.py` | listar names JAB de uma janela (com filtro); dump em `scripts/jab_dump.txt` |
| `recortar_botao_ok.py` / `verificar_recorte_botao.py` | gerar/validar recortes de template |
| `testar_conexao_db.py` | **[CONGELADO]** teste isolado de conexão Oracle |

### 6.10 `src/` — o que resta do legado

| Item | Situação |
|---|---|
| `src/config/` (loader, schema) | ATIVO — usado por todos os testes; migração para `vtae/` prevista (Fase 1 restante) |
| `src/cli/` (run, send, summary) | ATIVO — `vtae run`; bug conhecido: subprocess usa Python do sistema, summary falha com "No module named vtae" |
| `src/core/object_repository.py` | ATIVO — peça central do Modelo de Elemento; migração pendente de decisão |
| `src/runners/database_runner.py` | **[CONGELADO]** por segurança InCor — intocado |
| `src/components/` (3 arquivos) | avaliar na Fase 1 restante (uso via DSL) |

## 7. Convenções que não se negocia (seleção das 43 regras)

1. Todo acesso a dado de teste passa por `_dado()` — default escondido é proibido (regra 19).
2. Template só entra depois de medido (`diagnose`); sensibilidade E especificidade.
3. Gate de 3 execuções consecutivas antes de considerar qualquer coisa validada.
4. Guard genérico de popup entre steps: REVOGADO — não recriar sem medir falso positivo.
5. pyjab lê, não escreve (escrita é spike futuro isolado).
6. JAVA_HOME do pyjab é setado em código, nunca via setx.
7. Campos com máscara nunca comparam valor exato via OCR — estrutura (mín. dígitos).
8. Mudança em flow validado é cirúrgica: diff aprovado antes, zero alteração fora do pedido.
9. Nenhum código entra sem explicação em português aprovada antes (regra 43 / método §6 do Projeto v1).

## 8. Estado atual — honesto, em uma tabela

| Área | Estado |
|---|---|
| Motor (core/vision/runners/report) em `vtae/` | ✅ migrado e coberto por testes |
| Flows migrados por domínio | ✅ todos; 799 unit tests passando, baseline 89 estável |
| Modelo de Elemento (objects YAML + ObjectRepository) | 🟡 piloto no CadastroMin; jab_names em mapeamento (Sexo já mapeado: `'Descrição do Sexo.'`; janela: `Form_Pac0010`) |
| Fase 0 (3 camadas no piloto + gate 3x) | 🟡 código pronto; faltam 2 names + 3 rodadas |
| Criar teste novo com pouco código | ❌ ainda não — é a promessa em aberto; critério de aceite: manual de 1 página + teste novo em poucas linhas |
| CadastroPacienteFlow (completo) | ❌ quebrado (CP04) + viola regra 19 — correção não agendada (decisão #8 da proposta v1.1) |
| Banco | ⏸ congelado (InCor) |
| Recorder, Citrix, tooling de objetos | ⏸ fases futuras (4, 3, 5) |

## 9. Glossário rápido

**LOV** — List of Values: campo Oracle Forms que abre lista de escolha.
**Match parcial silencioso** — defeito onde texto inválido digitado numa LOV
"casa" com o item mais parecido sem erro visível; só o pyjab detecta.
**Gate 3x** — critério de aceitação: 3 execuções consecutivas sem falha.
**Bootstrap** — modo tolerante: recurso não calibrado (região OCR, template,
jab_name) gera AVISO e é pulado, nunca quebra o flow.
**Evidência** — pasta por execução com screenshots por step + execution.json +
report.html.
**Jornada** — encadeamento de flows com estado compartilhado
(`estado_jornada.json`).
**Modelo de Elemento** — um registro por objeto de tela com todos os locators;
a base para criar testes declarando campos em vez de programando steps.
