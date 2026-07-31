# VTAE — Prompt de Instrução Geral do Projeto

Data: 30/07/2026 | Versão: v0.5.34 | Cole este documento como primeira mensagem no próximo chat.

Hierarquia: **VTAE_Projeto_v1.md** (constituição) → **VTAE_Projeto_v1.1_PROPOSTA.md** (revisão, formalização pendente) → **VTAE_Manual_Tecnico_v1.md** (referência técnica) → **docs/mapear_names_jab.md** (procedimento JAB, novo 30/07) → este prompt (registro operacional).

---

## 0. REGRAS DE TRABALHO — LEIA PRIMEIRO

Regras 1-14 do v0.5.33 permanecem válidas. As essenciais, resumidas, mais as novas de 30/07:

1. NUNCA criar/alterar arquivo sem Helio ver o conteúdo atual primeiro.
2. Mudança em flow validado é CIRÚRGICA — diff aprovado antes, zero alteração fora do pedido.
3. Gerar arquivo completo SOMENTE quando pedido expressamente.
4. Gate: 3x consecutivas antes de considerar validado.
5. Regra 19: `dados.get(x, default)` PROIBIDO em flow — todo dado passa por `_dado()`.
6. Templates sempre medidos (diagnose) antes de confiar; sensibilidade E especificidade.
7. pyjab LÊ, não escreve. Leitura exata, sem Levenshtein. JAVA_HOME de mentira em código, nunca `setx`.
8. Banco CONGELADO (segurança InCor).
9. Regra 43 (aprendizado): desenho em português antes de código; diff explicado (o que / por quê / conceito Python); "não entendi" bloqueia merge.
10. **UMA FRENTE POR VEZ** — fechada por completo, com registro escrito, antes de qualquer outra existir.
11. **VALIDAÇÃO DOCUMENTAL ANTES DE EXECUÇÃO.**
12. **SEM ESCOPO NOVO POR RESPOSTA** — lista fechada; item fora dela é decisão de Helio, nunca iniciativa de Claude.
13. **VERIFICAÇÃO COM CAMINHO ABSOLUTO** em toda busca de arquivo.
14. **A RÉGUA DO PROJETO**: (a) teste novo cabe em poucas linhas; (b) manual cabe em 1 página; (c) segundo flow sai MENOR que o primeiro.
15. **[NOVA 30/07] Terminal NUNCA elevado para qualquer coisa que toque JAB.** O UIPI do Windows bloqueia o handshake com a JVM e o `isJavaWindow` retorna falso. O erro que aparece mente: diz `no java window found by title` como se o título estivesse errado. Medido e confirmado nesta sessão. Vale para `scripts/mapear_names_jab.py` e para `vtae run`.
16. **[NOVA 30/07] Título de janela no pyjab é `fnmatch`, não substring** (`pyjab/common/win32utils.py:240`). Precisa casar por INTEIRO ou usar curinga (`"*Pac0010*"`).
17. **[NOVA 30/07] Evidência tem que ser do momento da leitura.** Salvar uma captura posterior, ou de escopo diferente do que foi lido, não é evidência — é ilustração. Vale para OCR, template e pyjab.
18. **[NOVA 30/07] "Passou" não prova que uma camada tolerante rodou.** Camada que pula em silêncio e camada que teve sucesso em silêncio são indistinguíveis. Se não há linha no log, não há prova.

---

## 1. CONTEXTO DE RELACIONAMENTO

A crise de confiança de 29/07 foi endereçada. Helio pediu desculpas pela rispidez em 30/07 e trouxe um plano de 8 itens; Claude respondeu que o plano não era escopo novo, e sim reordenação do que já estava registrado. A sessão de 30/07 correu bem: medição antes de afirmação, erros de Claude admitidos na hora (duas hipóteses erradas foram descartadas por medição, não defendidas). Manter esse padrão.

---

## 2. O que é o VTAE

Framework híbrido de automação de testes (InCor): OpenCV + EasyOCR + pyjab + Playwright para Oracle Forms (SI3, SisLab) e APEX (MSI3). Python 3.13. Detalhes técnicos: `docs/VTAE_Manual_Tecnico_v1.md`.

---

## 3. O que foi feito em 30/07 (v0.5.33 → v0.5.34)

### 3.1 [FECHADO] Fase 0 — gate 3x cumprido

Os três `jab_name` do CadastroMin foram mapeados, escritos no YAML e validados com 3 rodadas verdes.

| Objeto | `jab_name` | Observação |
|---|---|---|
| `campo_sexo` | `Descrição do Sexo.` | name único no dump |
| `campo_cor_etnia` | `Descrição da Cor/Raça.` | cuidado: existe também `Identificação da Cor/Raça.` (código, `text: '2'`) |
| `campo_nacionalidade` | `Tipo de naturalidade` | **name ambíguo** — aparece 2x (role `text` e role `combo box`). Medido: `find_elements_by_name` devolve `0 text 'BRASILEIRO'`, `1 combo box None`. O índice 0 é o certo, mas isso é ordem de árvore, não garantia. Se um dia CM07 falhar com valor lido vazio, é aqui. |

Janela JAB: `Form_Pac0010` (exato).

Gate: rodadas #1 (09:32:35), #3 (09:47:54) e #4 (09:49:58), todas PASSOU. A execução #2 (09:46:13) morreu em CM07 sem registro de fim — Helio confirmou interrupção por motivo externo, não falha do teste. As três contam.

Comprovação de que a camada pyjab realmente rodou (antes da observabilidade existir, foi por aritmética de tempo): CM06 saltou de 3.4s para ~22s (custo de conectar o JABDriver + varrer árvore de 2734 elementos), CM07 de ~17s para ~23s, CM08 de ~5.6s para ~11s. Cenário de falha descartado: se o JABDriver não tivesse conectado, `ctx.jab` ficaria `None` e cada step pagaria 30s de timeout.

### 3.2 [NOVO] `docs/mapear_names_jab.md`

Procedimento completo de como descobrir um `jab_name`, com os erros que custaram tempo hoje. Ponto central: **buscar pelo VALOR visível na tela, não pelo rótulo do campo**. "Nacionalidade" não tem nenhum name contendo "nacional"; foi buscando `BRASILEIRO` que apareceu `Tipo de naturalidade`.

### 3.3 [DESCOBERTA GRANDE] Nenhum flow do VTAE registrava valor lido no `execution.log`

Medido: `ocr_lido` aparece **zero vezes** em todos os `execution.log` do projeto (~50 arquivos, junho e julho). O código do observer que loga `ocr_lido` (`observer.py:125-126`) **nunca executou**.

Causa: ordem. O `_step()` loga na linha 254 e retorna na 255; todos os flows atribuem `step.ocr_lido = ...` **depois** do return — 14 pontos em 5 flows, documentado como "padrão AB15 propagado". No instante do log o campo é sempre `None`. O `execution.json` e o `report.html` são montados no fim, por isso têm o valor.

### 3.4 [FEITO, GATE ABERTO] Observabilidade da camada pyjab — 5 edições aplicadas

Decisões de Helio: campo novo `jab_lido`; log no observer; e `jab_name` mapeado + JABDriver que não conecta passa a **falhar o step** (bootstrap tolerante vale só para objeto SEM `jab_name`).

1. `vtae/core/result.py` — campo `jab_lido: str | None = None`.
2. `vtae/flows/base_flow.py` `_step()` — parâmetros `ocr_holder: list = None` e `jab_holder: list = None`; holders lidos depois do `fn()` e antes de montar o `StepResult`. O parâmetro antigo `ocr_lido` foi mantido.
3. `vtae/report/observer.py` — `ocr_lido` e `jab_lido` logados fora do `if validated`.
4. `cadastro_paciente_min_flow.py` — helper `_verificar_via_jab_se_mapeado` recebe `jab_holder` (antes criava e descartava a leitura); skips com `jab_name` mapeado viram `AssertionError`; skip de bootstrap vira log de aviso.
5. `tests/integration/si3/components/test_cadastro_paciente_min.py` — `observer.inject_logger(ctx)` no ctx do cadastro (só o `ctx_login` recebia, apesar do comentário "obrigatorio desde v0.5.12").

Suíte unitária: **799 passed / 89 failed** antes e depois. Zero regressão, confirmado 3x.

### 3.5 [FALHA ABERTA] A rodada de validação falhou em CM04

`vtae run --test cadastro_paciente_min` às 11:32 falhou: `[CM04] Campo OBRIGATORIO 'nome' ficou vazio apos digitacao. Esperado: 'ANA JÚLIA VASCONCELOS' | OCR leu: ''`.

Não foi causado pelas 5 edições — CM04 é OCR puro, não tem camada pyjab, e seu `_step` não foi tocado. O mesmo CM04 passou 4x de manhã.

O que foi descartado por medição: janela não maximizada (a captura de debug prova 1920x1080 e a `regiao_ocr (27,145,447,168)` cai exatamente no campo); exceção engolida no `ler_regiao` (o código não tem try/except).

O que sobrou: o screenshot lido pelo OCR naquele instante não tinha o texto, ou o EasyOCR falhou nele. **Medição pendente** — ver §4.

Bug independente que apareceu: o campo mostra `ANA JLIA VASCONCELOS`. **O `Ú` sumiu na digitação.** Caractere acentuado não chegou ao SI3.

Defeito de observabilidade encontrado no caminho: `verify_lov` (opencv_runner.py:326-327) salva como debug uma captura da **tela inteira tirada depois do timeout**, não o recorte que foi lido. Mesma família do problema que acabamos de corrigir no pyjab.

---

## 4. FRENTE ATUAL (única — regra 10): fechar o gate da observabilidade

| # | Item | Quem |
|---|---|---|
| 1 | Copiar o screenshot exato lido pelo OCR: `dir /o-d D:\tmp\verify_lov_attempt_*.png`, pegar o mais recente e copiar para `evidence\debug_attempt.png` | Helio roda, Claude analisa |
| 2 | Conforme o resultado: se o campo estiver VAZIO na imagem → causa é timing/digitação (investigar o `Ú`); se estiver PREENCHIDO → causa é o EasyOCR | Claude propõe, Helio decide |
| 3 | Corrigir CM04 e rodar 3x consecutivas verdes | Helio |
| 4 | Na 1ª verde, confirmar no `execution.log`: `\| ocr_lido: 'X' \| jab_lido: 'X'` em CM06/CM07/CM08 — primeira vez que o projeto registra valor lido no log | Claude confere |

O gate da observabilidade **recomeça do zero** — a rodada de 11:32 é vermelha, mesmo com a causa sendo anterior à camada nova.

---

## 5. Depois desta frente (ordem aprovada por Helio em 30/07 — NÃO iniciar sem ele abrir)

1. **Migração completa `src/` → `vtae/`** (item 1 do plano de 8 de Helio). Medido: **31 imports de `src.` em 24 arquivos**, sendo 18 em `tests/`. O que ainda vive em `src/`: `config/` (loader + schema, importado por 15 arquivos), `cli/` (run, summary, send), `core/object_repository.py`, `runners/database_runner.py`, `components/` (3). **Acoplamento invertido a quebrar:** `vtae/flows/base_flow.py` importa `from src.runners`.
2. **Manual `docs/criar_teste_novo.md` em 1 página** — escrito depois da migração, com os imports definitivos. Critério da régua.
3. Refatorar helpers bespoke → `BaseFlow` (item 4 do plano).
4. Bug CP04 do `CadastroPacienteFlow` + violações da regra 19 (defaults hardcoded "00:00" e "M"). São ~82 das 89 falhas do baseline.
5. Bootstrap dos testes de jornada; `pyproject.toml` vs `requirements.txt`; versionamento e README.
6. Fase 2 (resolvedor multi-locator) — decisão pendente: piloto Ambulatório vs CadastroMin.

Pendência de escopo pequeno, registrada e não executada: os `_step` de CM04 e CM05 (e os dos outros 4 flows) continuam sem `ocr_holder=`, então o valor de OCR deles segue fora do `execution.log`. É uma linha por step.

---

## 6. Fatos técnicos de referência rápida

- Suíte unit: **799 passando / 89 baseline**. As 89: ~82 do `CadastroPacienteFlow` quebrado, 3 `test_login_flow_msi3` (assinatura), 3 `test_send`, 1 `test_config_loader` (acento).
- Comando da suíte unitária: `.venv\Scripts\python -m pytest tests/unit -q`. O CLI **não** tem opção para unitários.
- **Bug do CLI confirmado**: `vtae run` dispara o pytest com o Python do SISTEMA, não o do venv (regra 24, `sys.executable`). Sintoma visível: `No module named 'vtae'` ao gerar o summary. Pertence à Fase 1.
- `_step()` do BaseFlow: `confirm_template` presente ⇒ `validated=True` automático.
- `ObjectRepository`: `coord()`, `regiao_ocr()`, `template()`, `jab_name()` (tolerante), `titulo_jab()`.
- YAML de configs está organizado (`configs/<sistema>/<funcionalidade>/config.yaml`, 8 arquivos consistentes). Fora do padrão: `config_notificacoes.yaml` na raiz e `objects/cadastro_min.yaml` (este é intencional — Modelo de Elemento).
- No `cmd`, `cd` sem `/d` não troca de unidade.
- Sandbox Linux de Claude esteve indisponível em 29/07 e 30/07 — verificações têm que ser feitas por leitura de arquivo, não por script.

---

## 7. Início do próximo chat

1. Helio cola este prompt.
2. Claude confirma a frente atual (§4) e NADA além dela.
3. Helio traz `evidence\debug_attempt.png` (item 1 da §4).

**Marco de 30/07 (v0.5.34):** Fase 0 encerrada com gate 3x e a camada pyjab comprovadamente ativa; 3 names mapeados e o procedimento documentado; descoberto e corrigido que nenhum flow do projeto registrava valor lido no log; observabilidade da camada pyjab implementada com 5 edições e zero regressão; gate da observabilidade aberto, bloqueado por uma falha de CM04 anterior à mudança; dois bugs novos registrados (o `Ú` que some na digitação e o `verify_lov` que salva evidência do momento errado).
