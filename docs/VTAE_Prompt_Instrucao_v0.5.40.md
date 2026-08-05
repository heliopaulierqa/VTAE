# VTAE — Prompt de Instrução Geral do Projeto

**Data:** 31/07/2026 (4ª sessão do dia) | **Versão:** v0.5.40
Use este documento como primeira mensagem no próximo chat.
Referência acima deste documento: **VTAE_Projeto_v1.md** — a "constituição" do projeto.
Este prompt é registro operacional: onde paramos e o que fazer a seguir. Para visão, fases e método, consultar o Projeto v1.

---

## 0. REGRAS DE TRABALHO — LEIA PRIMEIRO

**ESTAS REGRAS SÃO INEGOCIÁVEIS E NUNCA PODEM SER QUEBRADAS:**

1. NUNCA criar ou alterar arquivo sem que Helio veja o conteúdo atual primeiro.
2. NUNCA gerar arquivo completo sem receber o upload / ler o arquivo atual.
3. AGUARDAR O UPLOAD (ou ler o arquivo real) antes de gerar qualquer código — jamais antecipar ou assumir conteúdo.
4. Para alterações pontuais: informar exatamente ONDE e O QUE mudar — não gerar arquivo completo.
5. NUNCA romper ou alterar nenhum contrato/padrão estabelecido sem que Helio saiba e aprove.
6. NUNCA reescrever lógica de negócio de um flow — apenas as linhas explicitamente solicitadas.
7. Quando um flow está validado e funcionando, qualquer mudança é CIRÚRGICA: confirmar com diff antes de entregar; zero alteração em qualquer step, helper ou lógica não solicitada.
8. Antes de responder sobre qualquer falha: pesquisar o histórico de chats — o padrão pode já ter sido resolvido antes.
9. Não propor soluções cosméticas — cada mudança responde uma das 5 perguntas de observabilidade. Testes veem o que acontece de verdade; nunca ancorar continuidade num elemento visual específico sem medir.
10. Não circular — se uma abordagem falhou 2x, propor alternativa diferente, não insistir.
11. Medir antes de confiar — `diagnose()` contra arquivo real (nunca tela ao vivo por engano) antes de rodar a jornada inteira.
12. Medir sensibilidade E especificidade — não só "o template acha o popup", mas "o template NÃO acha nada numa tela sem popup".
13. Gerar arquivo completo SOMENTE quando Helio pedir expressamente.
14. Nenhum `.env` pode ter comentário na mesma linha de um `VAR=valor` — comentário em linha separada, acima.
15. Mudanças de observabilidade são GATE: uma jornada de cada vez, 3x consecutivas antes de propagar.
16. Subprocessos do CLI sempre usam `sys.executable`, nunca a string `"python"` — EXCETO onde já documentado como dívida pré-existente.
17. `pyperclip.copy()` + Ctrl+V precisa de delay mínimo (≥0.15s) entre as duas chamadas, e 0.5s entre clique em campo e ação seguinte.
18. Templates SEMPRE via `pyautogui.screenshot()` + `PIL.crop()` — nunca Win+Shift+S nem recorte colado no chat.
19. `diagnose()`: template primeiro, screenshot depois. O nativo sempre captura a tela ao vivo — para arquivo, sobrescrever `matcher._capture_screen` (`scripts/diagnose_contra_arquivo.py`).
20. `regioes_ocr` no YAML exige espaço após dois pontos: `{ x1: 27, y1: 145 }`.
21. Coordenadas com janela maximizada. Preferir clique via template quando o elemento pode se deslocar.
22. Dois `FlowContext` separados quando dois flows têm configs diferentes.
23. `_verify_campo_obrigatorio` / `_verify_campo_opcional` exigem `ocr_holder: list` como último argumento.
24. Campos com reformatação automática (data, CPF, telefone) NÃO usam valor exato via OCR — verificação por estrutura (mínimo de dígitos), padrão CM05.
25. `ocr_lido` propagado ao StepResult: `step.ocr_lido = _ocr[0] if _ocr[0] is not None else ''`.
26. Popups são âncoras frágeis para GUARDS GENÉRICOS — mas templates apertados de um ELEMENTO ESPECÍFICO E JÁ CONHECIDO continuam confiáveis quando medidos.
27. Campo Profissional em lista de procedimentos SI3: não aceita digitação direta — `_selecionar_via_lov`.
28. `max(numeros, key=len)` no OCR de campos com múltiplos números.
29. Cenário negativo em Oracle Forms tem DUAS formas de falha silenciosa: (a) com popup específico e conhecido; (b) sem popup, match parcial em LOV → verificação estrutural via pyjab.
30. Verificação estrutural via pyjab é uma segunda camada, PARALELA ao OCR — comparação exata, sem tolerância Levenshtein. `JABDriver` conecta sob demanda, cacheado em `ctx.jab`.
31. `JAVA_HOME` do pyjab é setado programaticamente no código, lido do config (`.env`), NUNCA via `setx`.
32. pyjab não substitui OCR/OpenCV/Playwright — complementa.
33. `AdmissaoAmbulatorioFlow` é o flow-modelo do projeto para padrões de verificação e observabilidade. Padrões estruturais novos (Modelo de Elemento, ObjectRepository) estreiam no `CadastroPacienteMinFlow` na Fase 0.
34. `DatabaseRunner`: CONGELADO por decisão de segurança do InCor até liberação. Nada nas Fases 0–5 depende de banco.
35. **Padrão de aprendizado:** nenhum código entra sem que Helio explique o que faz e por quê. Todo diff vem com (a) o que muda, (b) por que muda, (c) qual conceito Python está em jogo. Helio digita diffs pequenos; colar é reservado para blocos mecânicos.
36. Regra de disciplina anti-especulação: diante de uma falha, medir e reverter empiricamente ANTES de gerar hipóteses.
37. Ambiente: o sandbox Linux pode ficar indisponível em algumas sessões — trabalho continua via leitura/edição direta na pasta conectada do Windows. Quando indisponível, `git` e `pytest` ficam com Helio. **O terminal é PowerShell: `grep` não existe — usar `Select-String`, e envolver em `(...).Count` para que "zero ocorrências" imprima `0` em vez de nada.**
38. Prompts operacionais podem ficar atrasados em relação ao código. Antes de aceitar como verdade uma pendência marcada "a fazer" num prompt antigo, ler o arquivo real no repositório — **o registro escrito não é a fonte de verdade, o disco é.**
39. Argumento posicional casa por posição, não por nome — remover um parâmetro do meio de uma assinatura reordena silenciosamente os que vêm depois em toda chamada posicional. Verificar com grep após qualquer edição desse tipo, não só reler o diff.
40. Separação de dado por natureza, não por conveniência: **locator** (coordenada/regiao_ocr/template/jab_name) vive em `objects/*.yaml` porque muda quando a TELA muda; **dado de teste** (dados_faker, listas, cenário) vive em `config.yaml` porque muda quando o CENÁRIO muda; **segredo** vive em `.env` porque muda quando a MÁQUINA muda. Teste mental: *"se o SI3 mudar de layout amanhã, o que preciso reabrir?"*
41. **Gate fechado termina em commit.** A sequência é: diff → grep de verificação → `pytest unit` contra baseline → 3x na tela real → **commit**. Sem o commit, a próxima sessão herda working tree suja e não distingue o que foi validado do que era rascunho. A mensagem registra o número do gate (unit passed/failed e quantas execuções reais), não só o que mudou.
42. **Mock mente sobre o que tem.** `MagicMock` responde truthy a qualquer atributo e a qualquer chamada. Todo código novo em `BaseFlow` que leia um atributo opcional de `ctx` precisa validar a **FORMA do valor recebido** (`isinstance`, `len`, conteúdo), não apenas a existência do atributo (`getattr`/`is not None`).
43. **Fontes idênticas não provam precedência.** Quando uma migração troca a origem de um dado e as duas origens têm valores iguais, execuções verdes provam ausência de regressão, não que a nova origem está no comando. A prova positiva exige perturbar deliberadamente a nova fonte, ver o efeito, e desfazer. **Executada e confirmada em 31/07 — ver v0.5.39 §3.1.** Corolário aprendido na 0.2c-2: quando a fonte antiga é **removida**, a perturbação deixa de ser necessária — passar já prova que só existe uma fonte.
44. **Centralizar a decisão não migra quem já decidia sozinho.** Criar um resolvedor no `BaseFlow` só muda o comportamento de quem o chama. Um flow que lê a fonte antiga na mão continua lendo a fonte antiga, e nenhum grep pelo *consumidor* revela isso. Ao centralizar acesso a um dado, o grep obrigatório é pela **FONTE** (`ctx.config.<secao>`) em todo o projeto, não pelo helper — e ele só está fechado quando o resultado é zero.
45. **Tolerante embaixo, estrito em cima.** Um resolvedor de locator devolve `None` para ausência e não decide se aquilo é fatal — quem chama decide, campo a campo, porque a criticidade é do campo e não do mecanismo. Corolário: ao migrar um acesso que hoje levanta exceção (`dict[chave]`) para um resolvedor tolerante, é obrigatório reintroduzir a explosão explícita no ponto de chamada.
46. **[NOVA v0.5.40] Guard nunca executado não é robustez — é decoração.** Um `if self._tpl_existe(tpl):` cujo arquivo nunca esteve no disco torna o ramo do template código morto permanente, e o `else` (coordenada) vira o único caminho real. Nada falha, nada avisa, e quem lê o arquivo acredita que existe proteção onde não existe. **Ao mapear qualquer locator baseado em arquivo, conferir que o arquivo EXISTE na pasta** — comparar as chaves do `objects/*.yaml` com o conteúdo real de `templates/<sistema>/<tela>/`. Encontrado no CM06 em 31/07: a f-string apontava para `btn_ok_lov.png`, e o que existe na pasta é `btn_ok_lov_generico.png`.
47. **[NOVA v0.5.40] Fonte única dispensa a perturbação, mas exige o inventário.** Depois que a fonte redundante sai (0.2c-2), um verde já prova precedência. O que *não* fica provado por execução verde é o **inverso**: chaves presentes no `objects/` que nenhum código consome. Não há grep que pegue isso automaticamente — só o inventário manual objeto-por-objeto, que fica para a Fase 5 (tooling).

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor (São Paulo). Combina OpenCV, Playwright, EasyOCR, pyjab/Java Access Bridge e oracledb (DatabaseRunner) para automatizar sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — Oracle APEX).

- **Versão atual:** v0.5.40
- **Python:** 3.13+
- **Fase atual (Projeto v1):** Fase 0 — Modelo de Elemento. **Fases 0.1, 0.2, 0.2c-1, 0.2c-2 e 0.2b concluídas e commitadas.** Resta a **0.3** (conftest de integração) para fechar a Fase 0.
- **Banco:** congelado por segurança.
- **Documento de referência:** VTAE_Projeto_v1.md

O `objects/cadastro_min.yaml` é hoje a **fonte única** de coordenada, região OCR, caminho de template, `jab_name` e `tela.titulo_jab` do `CadastroPacienteMinFlow`. Não sobrou locator no `config.yaml` nem hardcoded no Python.

---

## 2. Estado atual dos flows — inalterado desde v0.5.32

Ver tabela completa no Projeto v1. Nenhum flow mudou de status nesta sessão.

As fases 0.2c-2 e 0.2b tocaram **apenas** `cadastro_paciente_min_flow.py`, `objects/cadastro_min.yaml` e o `config.yaml` do CadastroMin. Nenhum outro flow foi lido, editado ou executado. Os flows com gate fechado (AdmissaoAmbulatorio, AdmissaoInternacao, Agendamento) seguem lendo `ctx.config.regioes_ocr` dos **seus próprios** configs pelo caminho de fallback do `BaseFlow`, sem alteração de comportamento.

---

## 3. O que foi feito na sessão de 31/07/2026 — 4ª sessão (v0.5.39 → v0.5.40)

### 3.1 [FEITO] Fase 0.2c-2 — `regioes_ocr` sai do `config.yaml` do CadastroMin

Medição antes do diff (regra 11), toda ela contra o disco (regra 38):

| Checagem | Resultado |
|---|---|
| 7 chaves existem em `objects/cadastro_min.yaml`? | ✅ todas, com os 28 números idênticos |
| `ctx.config.regioes_ocr` no flow? | ✅ 0 — a 0.2c-1 já tinha fechado |
| Loader quebra sem a seção? | ❌ não — `loader.py:248` usa `.get("regioes_ocr", {})`, `schema.py:173` tem `default_factory=dict` |
| Algum teste **unitário** carrega esse config? | ❌ nenhum — só integração |

Removida a seção `regioes_ocr:` inteira (7 chaves + cabeçalho), substituída por duas linhas de comentário que apontam para o `objects/`. Corrigidas duas strings que a remoção tornaria falsas: a mensagem do `AssertionError` do CM09 e o cabeçalho do `_step_cm09`, que **duplicava os números das regiões em comentário** — uma terceira cópia que ninguém atualizaria.

**Gate:** `pytest tests/unit` 799/89 idêntico ao baseline · 3x na tela real (126s/127s/115s) · `paciente_id ≠ matricula` nas três · commit.

### 3.2 [FEITO] Fase 0.2b — templates migram para o ObjectRepository

Três chaves `template:` novas no `objects/cadastro_min.yaml`:

```yaml
  campo_nome_pesquisa:            # já existia — ganhou template
    coordenada: { x: 172, y: 259 }
    template: templates/si3/cadastro_paciente_min/campo_nome_pesquisa.png

  campo_nome_social:              # objeto novo — só template
    template: templates/si3/cadastro_paciente_min/campo_nome_social.png

  popup_erro_incor:               # objeto novo — só template
    template: templates/si3/cadastro_paciente_min/popup_erro_incor.png
```

Dois deles não têm `coordenada`, e está certo: um objeto do repositório é um **elemento da tela**, não um clique. `campo_nome_social` só confirma que o formulário abriu; `popup_erro_incor` só é procurado — quem se clica é o `btn_ok_erro_incor`.

No flow: CM01 e CM03 passam `ctx.objects.template(...)` no `confirm_template`; `_verificar_popup_erro_incor` resolve pelo repo e **mantém** o `_tpl_existe`, porque os dois guards respondem perguntas diferentes — *"o objeto declara template?"* (estrito, `KeyError`) e *"o arquivo está no disco?"* (tolerante, bootstrap). As constantes `_TPL` e `_TPL_ERRO_INCOR` ficaram órfãs e saíram.

**Gate:** `pytest tests/unit` 799/89 idêntico · 3x na tela real · `paciente_id`/`matricula` = 51512545/55679398 → 51512546/55679399 → 51512547/55679400, delta constante de 4.166.853 · commit.

### 3.3 [FEITO] Ramo morto removido no CM06 — achado da medição da 0.2b

O CM06 tinha:

```python
ok_tpl = f"{self._TPL}/btn_ok_lov.png"
if self._tpl_existe(ok_tpl):
    ctx.runner.safe_click(ok_tpl, threshold=0.75)
else:
    x, y = ctx.objects.coord("btn_ok_lov")
    pyautogui.click(x, y)
```

**`btn_ok_lov.png` nunca existiu na pasta** — o arquivo lá é `btn_ok_lov_generico.png`. O `if` sempre deu falso; o clique sempre foi por coordenada. Todas as execuções históricas do CadastroMin passaram por baixo desse ramo sem nunca entrar nele.

Não quebrou nada porque o LOV de Sexo não se desloca. Mas o código afirmava uma robustez (regra 21) que a execução nunca teve. Helio decidiu **remover o ramo**, deixando só o clique por coordenada — que é o comportamento real. Virou a **regra 46**.

Se algum dia o CM06 precisar de clique por template de verdade, o caminho é o da regra 18 + regras 11 e 12: recortar, medir sensibilidade **e** especificidade, mapear no YAML — e isso é gate próprio, não emenda de outra fase.

### 3.4 [CONTEXTO] Por que a perturbação da 0.2c-2 foi dispensada

Helio perguntou se era necessária. Não era, e a razão importa: na §3.1 do v0.5.39 as duas fontes existiam com valores iguais, então "passou" não dizia quem mandava. Depois da remoção, só sobrou uma fonte — se o `objects/` não estivesse alimentando as regiões, o CM09 não teria lido matrícula nenhuma. O verde já é a prova. Registrado como corolário da **regra 43**.

O que a perturbação testaria de fato seria outra coisa — se o `raise AssertionError` do CM09 dispara mesmo. Esse caminho fica melhor coberto pelo teste unitário da pendência #4, que roda em milissegundos e fica no repositório.

### 3.5 [ACHADO] `estado_jornada.json` guarda só a última execução

Descoberto ao coletar as evidências do gate: o arquivo é sobrescrito a cada rodada, por design (é handoff para os flows de admissão, não log). Helio precisou copiar os valores manualmente entre as três execuções.

Isso reforça a pendência #3 (`ocr_lido` perdido em falha): se o valor lido fosse ao `StepResult`, ficaria no `execution.json` de cada execução, com histórico por data, sem coleta manual.

### 3.6 [AMBIENTE] Sandbox Linux indisponível pela segunda sessão seguida

VHDX ausente. Todo o trabalho por leitura/edição direta na pasta conectada do Windows; `git` e `pytest` com Helio (regra 37). **Consequência registrada:** o `objects/cadastro_min.yaml` da 0.2b não foi validado com `yaml.safe_load` — só relido. Quem provou a sintaxe foram as 3 execuções reais (uma indentação errada quebraria o `from_yaml` na primeira).

---

## 4. Pendências imediatas (ordem de execução)

| # | Pendência | Prioridade | Depende de |
|---|---|---|---|
| 1 | **Fase 0.3 — fecha a Fase 0.** Criar `tests/integration/conftest.py` com fixture(s) canônica(s) de boot do SI3 (login + observer + runner + ObjectRepository), aposentando `login_si3_fixture.py` e `cadastro_paciente_fixture.py` órfãos e o boot manual duplicado em `test_cadastro_paciente_min.py` e nos demais 13 arquivos de integração. Agora desbloqueada: o contrato do ObjectRepository (`coord`/`regiao_ocr`/`template`/`jab_name`) está estável e exercitado em tela real. | 🔴 próxima | — |
| 2 | **`causa_falha` classifica erro de automação como `SISTEMA`** — locator errado, template desatualizado e região descalibrada são falhas do teste, não do sistema sob teste. Num relatório gerencial vira acusação falsa contra o SI3. Decidir entre causa nova (`LOCATOR`/`AUTOMACAO`) ou heurística no classificador. | 🟡 | — |
| 3 | **`ocr_lido` perdido quando o step falha** — o padrão `if step.success and _ocr[0]` descarta o valor lido exatamente no caso em que ele é diagnóstico. Ver §3.5: também resolveria a coleta manual de evidência entre execuções. Vale revisar em todos os flows. | 🟡 | — |
| 4 | **`CadastroPacienteMinFlow` não tem teste unitário** — o flow-piloto da Fase 0 é o único coberto só por integração (~2 min por execução). Todo gate dele custa tela real. Candidato a `test_cadastro_paciente_min_flow.py` com `ctx` falso que devolva tuplas de verdade (regra 42) e cubra os `raise` do CM09 e os `KeyError` do `template()`. | 🟡 dívida visível | — |
| 5 | **CM06 sem clique por template** — decorrência consciente da §3.3. Se o LOV de Sexo passar a se deslocar, o caminho é capturar `btn_ok_lov.png` (regra 18), medir (regras 11 e 12) e mapear. Gate próprio. Hoje não incomoda. | 🟢 monitorar | — |
| 6 | CM06 (Sexo) roda sem verificação pyjab real por race condition de startup do Java Access Bridge (herdado de v0.5.35). | 🟡 conhecido, não bloqueia | — |
| 7 | Mapear names pyjab restantes (AB06, AB09, AB10, AB11, AB12). | 🟡 paralelo | — |
| 8 | `test_cadastro_paciente_flow.py` desatualizado — 27 steps esperados vs 4 reais, responsável pela maior parte das 89 falhas do baseline. Decidir: atualizar ou marcar `xfail` com justificativa. | 🟡 dívida visível | — |
| 9 | `test_config_loader.py::test_arquivo_nao_encontrado` — o teste espera `"não encontrado"` com til, o loader emite `"nao encontrado"` sem. Uma linha; reduz o ruído do baseline em 1. | 🟢 trivial | — |
| 10 | `tests/integration/msi3/jornadas/anestesia_pre_operatorio/test_frequencia_aplicacao.py` importa caminho `src.flows.msi3...` que nunca existiu (pré-existente, fora de `tests/unit`). | 🟡 conhecido, não bloqueia | — |
| 11 | Observação não investigada: falha isolada em CM07/BRASILEIRO por popup HC-INCOR (09:34 de 31/07) — não se repetiu em 16 execuções desde então. Revisitar só se voltar. | 🟢 monitorar | — |
| 12 | Escolher aplicação Citrix candidata a cliente 2 (Fase 3). | 🟡 a definir | Helio |
| 13 | Todos os itens de banco suspensos até liberação do InCor. | ⏸ congelado | Liberação segurança |

---

## 5. Padrões consolidados de código

Inalterados desde v0.5.32, exceto os itens abaixo. Principais: `_verify_campo_obrigatorio`/`_verify_campo_opcional`, `_verify_campo_via_jab`, fallback banco→YAML (congelado), `diagnose_contra_arquivo`, guard genérico revogado, `_db_assert_admissao` (esqueleto preservado, congelado).

### 5.x `_resolver_regiao_ocr` — resolução de locator com fallback

```python
def _resolver_regiao_ocr(self, ctx, regiao_key: str):
    repo = getattr(ctx, "objects", None)
    if repo is not None:
        r = repo.regiao_ocr(regiao_key)
        if isinstance(r, tuple) and len(r) == 4 and any(r):
            return r
    regiao = ctx.config.regioes_ocr.get(regiao_key)
    if regiao and (regiao["x1"] or regiao["y1"]
                   or regiao["x2"] or regiao["y2"]):
        return (regiao["x1"], regiao["y1"], regiao["x2"], regiao["y2"])
    return None
```

**Padrão de referência para qualquer futura migração de locator.** Quatro propriedades a preservar:

1. `getattr` cobre "o atributo pode não existir"; `isinstance` cobre "o atributo existe mas mente sobre o que é" (regra 42).
2. Bootstrap zerado equivale a ausente — nas duas fontes.
3. Sem `try/except`: ausência esperada devolve `None`, erro de programador explode.
4. Criar o resolvedor é metade do trabalho — a outra metade é o grep pela fonte antiga até dar zero (regra 44).

O ramo de fallback ao `config` continua vivo e é usado pelos outros flows. Para o CadastroMin ele agora é inalcançável (a seção não existe mais), o que é o objetivo: fonte única sem quebrar quem ainda não migrou.

### 5.y Consumo do resolvedor no ponto de chamada

Três formas, escolhidas pela criticidade do campo (regra 45):

```python
# Campo obrigatório com bootstrap tolerado (CM05):
regiao_tupla = self._resolver_regiao_ocr(ctx, "campo_data_nasc")
if regiao_tupla is not None:
    ...verifica...
else:
    print("[CM05] AVISO: regiao nao calibrada — verificacao pulada (bootstrap).")

# Campo cuja ausência é fatal (CM09 matrícula):
regiao_mat = self._resolver_regiao_ocr(ctx, "matricula")
if regiao_mat is None:
    raise AssertionError("[CM09] Regiao 'matricula' nao calibrada ...")

# Campo opcional com fallback (CM09 identificador):
regiao_id = self._resolver_regiao_ocr(ctx, "identificador")
if regiao_id is not None:
    ...lê e sobrescreve o default...
```

O `is not None` é obrigatório em vez de `if regiao:` — tupla `(0,0,0,0)` é falsy, e confundir "zerada" com "ausente" reintroduz o bug que o resolvedor existe para matar.

### 5.z [NOVO v0.5.40] Consumo de template via ObjectRepository

```python
# Template de confirmação — direto no _step (CM01, CM03):
confirm_template=ctx.objects.template("campo_nome_pesquisa"),

# Template de detecção com guard de bootstrap (CM07):
tpl = ctx.objects.template("popup_erro_incor")
if not self._tpl_existe(tpl):
    return  # bootstrap — template nao capturado ainda
if not ctx.runner.is_visible(tpl, threshold=0.75):
    return  # popup nao detectado — continuar normalmente
```

`template()` é **estrito** (`KeyError`), ao contrário de `regiao_ocr()` e `jab_name()`, que são tolerantes. Assimetria proposital, documentada no `object_repository.py`: template ausente vira espera ou clique em lugar nenhum, então tem que explodir. O `_tpl_existe` **não** é redundante com ele — responde "o arquivo está no disco?", que é a pergunta do bootstrap, e é o guard que precisa de atenção pela regra 46.

---

## 6. Matriz de decisão — qual camada verifica o quê

Inalterada — ver Projeto v1 §6 ou prompt v0.5.32.

---

## 7. Padrões Oracle Forms consolidados

Inalterados — ver Projeto v1 ou prompt v0.5.32.

---

## 8. Arquitetura atual — pasta única `vtae/`

```
vtae/
├── cli/          (run.py, send.py, summary.py)
├── components/   (si3/, msi3/)
├── config/       (loader.py, schema.py)
├── core/         (object_repository.py, context.py, result.py, ...)
├── flows/        (si3/, msi3/ — todo o código de negócio)
├── runners/      (database_runner.py, ...)
└── ...
```

`objects/cadastro_min.yaml` — **fonte única** de coordenada, `regiao_ocr`, `template`, `jab_name` e `tela.titulo_jab` do `CadastroPacienteMinFlow`.

`configs/si3/si3_cadastro_paciente_min/config.yaml` — sistema/tipo/runner/ocr_engine, credenciais (referência a `.env`), `dados_faker` e `dados:` (listas de cenário). **Nenhum locator.**

---

## 9. Próximo passo concreto (início do próximo chat)

1. **Pendência #1 — Fase 0.3**, que fecha a Fase 0. Ler `tests/integration/si3/components/test_cadastro_paciente_min.py`, `login_si3_fixture.py`, `cadastro_paciente_fixture.py` e os demais arquivos de integração **antes** de qualquer desenho (regra 3). Devolver o desenho da fixture em português, esperar o "faz sentido" de Helio, só então código (regra 35).
2. Gate da 0.3 é diferente das anteriores: mexe no boot de **todos** os testes de integração, não num flow. Rodar o CadastroMin 3x prova pouco — vale escolher pelo menos um segundo teste de integração que use a fixture nova.
3. As pendências #2, #3 e #4 (observabilidade e cobertura) não bloqueiam nada e podem entrar quando Helio quiser trocar de assunto. A #4 tem sinergia direta com a #1: fixture canônica facilita escrever o unitário que falta.

---

**Marco desta sessão (31/07, 4ª — v0.5.40):** o `config.yaml` do CadastroMin perdeu sua última coordenada e o `objects/cadastro_min.yaml` virou fonte única provada de todos os quatro tipos de locator; os templates saíram das f-strings e entraram no repositório, incluindo dois objetos que existem só como template (confirmação visual e popup de erro), o que forçou a distinção entre "objeto da tela" e "coisa que se clica"; a medição da 0.2b encontrou um ramo `if _tpl_existe` que nunca executou em nenhuma execução histórica — o arquivo apontado nunca esteve na pasta — e a remoção dele virou a regra 46; a regra 43 ganhou corolário (fonte única dispensa perturbação) e nasceu a 47 (o inverso — chaves órfãs no YAML — não tem grep, fica para a Fase 5); dois gates fechados com unit idêntico ao baseline e 3 execuções reais cada, e a Fase 0 fica a uma etapa do fim.
