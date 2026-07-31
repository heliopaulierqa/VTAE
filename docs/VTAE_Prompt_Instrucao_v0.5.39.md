# VTAE — Prompt de Instrução Geral do Projeto

**Data:** 31/07/2026 (3ª sessão do dia) | **Versão:** v0.5.39
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
43. **Fontes idênticas não provam precedência.** Quando uma migração troca a origem de um dado e as duas origens têm valores iguais, execuções verdes provam ausência de regressão, não que a nova origem está no comando. A prova positiva exige perturbar deliberadamente a nova fonte, ver o efeito, e desfazer. **Executada e confirmada em 31/07 — ver §3.1.**
44. **[NOVA v0.5.39] Centralizar a decisão não migra quem já decidia sozinho.** Criar um resolvedor no `BaseFlow` só muda o comportamento de quem o chama. Um flow que lê a fonte antiga na mão continua lendo a fonte antiga, e nenhum grep pelo *consumidor* (`_verify_campo_*`) revela isso. Ao centralizar acesso a um dado, o grep obrigatório é pela **FONTE** (`ctx.config.<secao>`) em todo o projeto, não pelo helper — e ele só está fechado quando o resultado é zero.
45. **[NOVA v0.5.39] Tolerante embaixo, estrito em cima.** Um resolvedor de locator devolve `None` para ausência e não decide se aquilo é fatal — quem chama decide, campo a campo, porque a criticidade é do campo e não do mecanismo. Corolário: ao migrar um acesso que hoje levanta exceção (`dict[chave]`) para um resolvedor tolerante, é obrigatório reintroduzir a explosão explícita no ponto de chamada, senão a migração converte "quebra alto" em "segue com `None`" sem ninguém pedir.

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor (São Paulo). Combina OpenCV, Playwright, EasyOCR, pyjab/Java Access Bridge e oracledb (DatabaseRunner) para automatizar sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — Oracle APEX).

- **Versão atual:** v0.5.39
- **Python:** 3.13+
- **Fase atual (Projeto v1):** Fase 0 — Modelo de Elemento. **Fases 0.1, 0.2 e 0.2c-1 concluídas e commitadas.** A precedência do ObjectRepository sobre o config está **provada empiricamente**, não suposta.
- **Banco:** congelado por segurança.
- **Documento de referência:** VTAE_Projeto_v1.md

---

## 2. Estado atual dos flows — inalterado desde v0.5.32

Ver tabela completa no Projeto v1. Nenhum flow mudou de status nesta sessão.

A 0.2c-1 tocou **apenas** `cadastro_paciente_min_flow.py`. Nenhum outro flow foi lido, editado ou executado. Os flows com gate fechado (AdmissaoAmbulatorio, AdmissaoInternacao, Agendamento) seguem lendo `ctx.config.regioes_ocr` pelo caminho de fallback do `BaseFlow`, sem alteração de comportamento.

---

## 3. O que foi feito na sessão de 31/07/2026 — 3ª sessão (v0.5.38 → v0.5.39)

### 3.1 [FEITO] Pendência #1 — prova positiva de precedência (fecha a ressalva 3.7 do v0.5.38)

`campo_nome.regiao_ocr` deslocada 40px em y no `objects/cadastro_min.yaml` — de `{27,145,447,168}` para `{27,185,447,208}` — com o `config.yaml` mantido intacto e correto ao lado. Uma execução.

**Resultado:** CM04 falhou.

```
Esperado: 'MURILO FERNANDES' | OCR leu: '2UO 1  OOO'
```

O `2UO 1 OOO` é o EasyOCR raspando a linha da data/hora de nascimento — a faixa y 185-208 se sobrepõe ao `campo_data_nasc` (y 195-207). **Não é leitura vazia: é conteúdo de outro lugar da tela.** Isso descarta "falhou por acaso" e prova que a janela de OCR foi para onde o `objects` mandou, com o `config` sem conseguir vencer.

O deslocamento de 40px foi escolhido por isso, e não por ser um número redondo: uma região deslocada para área vazia produziria leitura em branco, indistinguível de falha de captura.

Linha revertida e confirmada por grep. Working tree limpa — perturbação medida e desfeita não é mudança, não gera commit.

### 3.2 [FEITO] Medição que redesenhou a Fase 0.2c

A 0.2c estava registrada como "remover as 7 `regioes_ocr` do `config.yaml`". A medição mostrou que isso teria quebrado o flow de três maneiras, duas delas silenciosas.

Das 7 regiões, apenas **4** estavam de fato atrás do `_resolver_regiao_ocr` (`campo_nome`/CM04, `campo_sexo`/CM06, `campo_nacionalidade`/CM07, `campo_cor_etnia`/CM08). As outras 3 o flow lia **direto** do `ctx.config.regioes_ocr`:

| Região | Como lia | O que aconteceria ao remover do config |
|---|---|---|
| `campo_data_nasc` (CM05) | `.get()` + guard de bootstrap | Cai no `else`: *"regiao nao calibrada — verificacao OBRIGATORIA pulada"*. **Step verde sem verificar nada.** |
| `matricula` (CM09) | `ctx.config.regioes_ocr["matricula"]` | `KeyError` — quebra alto |
| `identificador` (CM09) | `if "identificador" in ...` | Silenciosamente usa `paciente_id = matricula` como fallback |

Os dois casos silenciosos eram o problema, não o `KeyError`. O `identificador` errado vai para o `estado_jornada.json`, que alimenta os flows de admissão — a contaminação sairia do CadastroMin e entraria em outro flow.

Nesses 3 pontos, recalibrar no `objects` não tinha efeito nenhum: o mesmo bug de precedência da Fase 0.1, com outra roupa. Virou a **regra 44**.

### 3.3 [FEITO] Fase 0.2c-1 — três diffs em `cadastro_paciente_min_flow.py`

**CM05 (linha 252)** — três linhas viraram duas. A origem da região e o guard de bootstrap saíram; `if regiao_tupla is not None:` ocupa o mesmo nível do `if` antigo, então o corpo não mudou de indentação.

**CM09 matrícula (linha 670)** — duas linhas viraram seis. Troca de contrato consciente: o acesso por chave levantava `KeyError`, e o resolvedor é tolerante — devolveria `None` calado e `OcrHelper.ler_regiao(path, None)` faria algo imprevisível. A matrícula é a prova de que o cadastro salvou, então tem que explodir: `KeyError` virou `AssertionError` com mensagem legível. Virou a **regra 45**.

**CM09 identificador (linha 691)** — três linhas viraram duas. `"chave" in dicionario` testa só presença; o resolvedor testa presença **e** calibração **e** consulta as duas fontes. O `is not None` é proposital em vez de `if regiao_id:` — tupla `(0,0,0,0)` é falsy em Python, e o resolvedor já a converteu em `None`.

### 3.4 [FEITO] Gate da 0.2c-1

| Verificação | Resultado |
|---|---|
| `ctx.config.regioes_ocr` no flow | **0 ocorrências** ✅ |
| `pytest tests/unit -q` | **799 passed / 89 failed** — idêntico ao baseline ✅ |
| `tests/unit/test_base_flow.py` | 42/42 ✅ |
| `vtae run --test cadastro_paciente_min` | **PASSOU 3x** (128s / 144s / 116s) ✅ |
| `evidence/estado_jornada.json` | `paciente_id` ≠ `matricula` nas 3 execuções ✅ |

O `pytest` unitário aqui prova um negativo, não um positivo: **nenhum teste unitário importa o `CadastroPacienteMinFlow`** (ver pendência #6). O baseline idêntico mostra que os três diffs não vazaram para fora do flow — nada além disso.

A evidência positiva veio do `estado_jornada.json`: `paciente_id` e `matricula` saíram **diferentes** nas três execuções (`51512535`/`55679388` → `51512537`/`55679390`, avançando +2, consistente com dois cadastros a mais). Se o Diff 3 tivesse resolvido `None`, os dois campos sairiam idênticos pelo fallback. Como o pytest só mostra stdout em caso de falha, esse arquivo é a única evidência que sobra quando o teste passa.

### 3.5 [FEITO] Commit `ec07a57`

Regra 41 cumprida. Único arquivo: `vtae/flows/si3/cadastro_min/cadastro_paciente_min_flow.py`. Mensagem registra o gate (799/89 idêntico ao baseline, 3x na tela real, e a prova do `estado_jornada.json`).

### 3.6 [ACHADO, NÃO CORRIGIDO] Dois gaps de observabilidade expostos pela perturbação

A execução deliberadamente quebrada da §3.1 mostrou duas coisas que nenhuma execução verde mostraria:

1. **`causa_falha=CausaFalha.SISTEMA`** para uma falha que era de automação. A mensagem dizia *"Possivel valor residual de execucao anterior ou dado rejeitado pelo sistema"* — e a causa real era locator errado. O classificador não distingue "o SI3 recusou o dado" de "eu olhei para o pixel errado", e aponta o dedo para o sistema sob teste nos dois casos. Num relatório gerencial isso vira acusação falsa contra o SI3.
2. **`ocr_lido=None` no StepResult apesar do OCR ter lido `2UO 1 OOO`.** O flow só propaga com `if step.success and _ocr[0]` — em falha, o valor lido existe na mensagem de erro mas não no dado estruturado. É justamente na falha que ele mais serve.

Registrados como pendências #4 e #5. Nenhum foi tocado.

### 3.7 [AMBIENTE] Sandbox Linux indisponível

O ambiente Linux não subiu nesta sessão (VHDX ausente). Todo o trabalho foi feito por leitura/edição direta na pasta conectada do Windows; `git` e `pytest` ficaram com Helio (regra 37). Descoberto no caminho: `grep` não existe no PowerShell — incorporado à regra 37.

---

## 4. Pendências imediatas (ordem de execução)

| # | Pendência | Prioridade | Depende de |
|---|---|---|---|
| 1 | **Fase 0.2c-2** — remover as 7 `regioes_ocr` do `config.yaml` do CadastroMin, deixando fonte única. Inclui a string da linha ~684 (`Verifique regioes_ocr.matricula no config.yaml.`), que a remoção torna mentira. Diff mecânico; o custo é o gate (3x ≈ 6 min). | 🔴 próxima | 0.2c-1 (concluída) |
| 2 | **Fase 0.2b** — ligar `.template()` do ObjectRepository nos pontos onde o flow ainda monta caminho com `f"{self._TPL}/..."`. São 4 pontos no CadastroMin mais o `_TPL_ERRO_INCOR` no topo do módulo. `grep .template(` segue com zero chamadas. | 🟡 | #1 |
| 3 | **Fase 0.3** — criar `tests/integration/conftest.py` com fixture(s) canônica(s) de boot do SI3 (login + observer + runner), aposentando `login_si3_fixture.py` e `cadastro_paciente_fixture.py` órfãos e o boot manual duplicado em `test_cadastro_paciente_min.py` e nos demais 13 arquivos de integração. | 🟡 | #1, #2 (contrato do ObjectRepository estável) |
| 4 | **`causa_falha` classifica erro de automação como `SISTEMA`** — ver §3.6. Locator errado, template desatualizado e região descalibrada são falhas do teste, não do sistema sob teste. Decidir se cabe uma causa nova (`LOCATOR`/`AUTOMACAO`) ou heurística no classificador. | 🟡 achado novo | — |
| 5 | **`ocr_lido` perdido quando o step falha** — ver §3.6. O padrão `if step.success and _ocr[0]` descarta o valor lido exatamente no caso em que ele é diagnóstico. Vale revisar em todos os flows, não só no CadastroMin. | 🟡 achado novo | — |
| 6 | **`CadastroPacienteMinFlow` não tem teste unitário** — o flow-piloto da Fase 0 é o único coberto só por integração (~2 min por execução). Todo gate dele custa tela real. Candidato a `test_cadastro_paciente_min_flow.py` com `ctx` falso que devolva tuplas de verdade (regra 42). | 🟡 dívida visível | — |
| 7 | CM06 (Sexo) roda sem verificação pyjab real por race condition de startup do Java Access Bridge (herdado de v0.5.35). | 🟡 conhecido, não bloqueia | — |
| 8 | Mapear names pyjab restantes (AB06, AB09, AB10, AB11, AB12). | 🟡 paralelo | — |
| 9 | `tests/integration/msi3/jornadas/anestesia_pre_operatorio/test_frequencia_aplicacao.py` importa caminho `src.flows.msi3...` que nunca existiu (pré-existente, fora de `tests/unit`). | 🟡 conhecido, não bloqueia | — |
| 10 | `test_cadastro_paciente_flow.py` desatualizado — 27 steps esperados vs 4 reais, responsável pela maior parte das 89 falhas do baseline. Decidir: atualizar ou marcar `xfail` com justificativa. | 🟡 dívida visível | — |
| 11 | Observação não investigada: falha isolada em CM07/BRASILEIRO por popup HC-INCOR (09:34 de 31/07) — não se repetiu em 10 execuções desde então. Revisitar só se voltar. | 🟢 monitorar | — |
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

**É o padrão de referência para qualquer futura migração de locator para o ObjectRepository.** Quatro propriedades a preservar ao replicar:

1. `getattr` cobre "o atributo pode não existir"; `isinstance` cobre "o atributo existe mas mente sobre o que é" (regra 42).
2. Bootstrap zerado equivale a ausente — nas duas fontes.
3. Sem `try/except`: ausência esperada devolve `None`, erro de programador explode.
4. **Criar o resolvedor é metade do trabalho** — a outra metade é o grep pela fonte antiga até dar zero (regra 44).

### 5.y [NOVO v0.5.39] Consumo do resolvedor no ponto de chamada

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

`objects/cadastro_min.yaml` é a **fonte primária provada** de coordenada e região OCR do `CadastroPacienteMinFlow`, e a única fonte de `jab_name` e `tela.titulo_jab`.

`configs/si3/si3_cadastro_paciente_min/config.yaml` contém: sistema/tipo/runner/ocr_engine, credenciais (referência a `.env`), `dados_faker`, `dados:` (listas de cenário) e `regioes_ocr` — este último agora **sem nenhum consumidor**, alvo da pendência #1. Nenhuma coordenada.

---

## 9. Próximo passo concreto (início do próximo chat)

1. **Pendência #1 — Fase 0.2c-2.** Remover a seção `regioes_ocr:` inteira (7 chaves) do `config.yaml` do CadastroMin e corrigir a string da linha ~684 do flow. Gate: `pytest tests/unit` contra o baseline 799/89 + 3x na tela real + commit (regra 41).
2. Depois **0.2b** (`.template()`), uma migração de cada vez, gate próprio.
3. `conftest.py` de integração (0.3) permanece por último — extrair fixture antes do contrato do ObjectRepository estabilizar significaria reescrevê-la.
4. As pendências #4, #5 e #6 (observabilidade e cobertura) não bloqueiam a Fase 0 e podem entrar quando Helio quiser trocar de assunto.

---

**Marco desta sessão (31/07, 3ª — v0.5.39):** a precedência do ObjectRepository deixou de ser suposição e virou fato medido — perturbação deliberada de 40px fez CM04 ler a linha errada da tela, e a reversão restaurou o comportamento; a Fase 0.2c foi redesenhada pela medição antes de qualquer código, ao descobrir que 3 dos 7 locators liam o config direto e que remover as chaves teria produzido dois falsos-sucessos silenciosos (CM05 verde sem verificar, `paciente_id` contaminado saindo para os flows de admissão); os três pontos foram migrados, gate fechado com unit idêntico ao baseline e 3 execuções reais, commit `ec07a57`; duas regras novas incorporadas (centralizar a decisão não migra quem já decidia sozinho; tolerante embaixo, estrito em cima) e dois gaps de observabilidade registrados como pendências abertas em vez de corrigidos de passagem.
