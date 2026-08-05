# VTAE — Prompt de Instrução Geral do Projeto
**Data:** 03/08/2026 | **Versão:** v0.5.41
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
35. **Padrão de aprendizado:** nenhum código entra sem que Helio explique o que faz e por quê. Todo diff vem com (a) o que muda, (b) por que muda, (c) qual conceito Python está em jogo. Helio digita diffs pequenos; colar é reservado para blocos mecânicos. Fim de sessão: Helio resume em 2 frases o que foi feito — se não sair natural, a próxima sessão revisita em vez de avançar.
36. Regra de disciplina anti-especulação: diante de uma falha, medir e reverter empiricamente ANTES de gerar hipóteses.
37. Ambiente: o sandbox Linux pode ficar indisponível em algumas sessões — trabalho continua via leitura/edição direta na pasta conectada do Windows. Quando indisponível, `git` e `pytest` ficam com Helio. **O terminal é PowerShell: `grep` não existe — usar `Select-String` (que NÃO tem `-Recurse`; usar `Get-ChildItem -Recurse -Include *.py | Select-String "padrao"`), e envolver em `(...).Count` para que "zero ocorrências" imprima `0` em vez de nada.**
38. Prompts operacionais podem ficar atrasados em relação ao código. Antes de aceitar como verdade uma pendência marcada "a fazer" num prompt antigo, ler o arquivo real no repositório — **o registro escrito não é a fonte de verdade, o disco é.**
39. Argumento posicional casa por posição, não por nome — remover um parâmetro do meio de uma assinatura reordena silenciosamente os que vêm depois em toda chamada posicional. Verificar com grep após qualquer edição desse tipo, não só reler o diff. Vale também para campos duplicados em `@dataclass`: a segunda declaração do mesmo nome sobrescreve o default da primeira sem criar novo campo — a ordem dos argumentos posicionais é a da PRIMEIRA aparição.
40. Separação de dado por natureza, não por conveniência: **locator** (coordenada/regiao_ocr/template/jab_name) vive em `objects/*.yaml` porque muda quando a TELA muda; **dado de teste** (dados_faker, listas, cenário) vive em `config.yaml` porque muda quando o CENÁRIO muda; **segredo** vive em `.env` porque muda quando a MÁQUINA muda. Teste mental: *"se o SI3 mudar de layout amanhã, o que preciso reabrir?"*
41. **Gate fechado termina em commit.** A sequência é: diff → grep de verificação → `pytest unit` contra baseline → 3x na tela real → **commit**. Sem o commit, a próxima sessão herda working tree suja e não distingue o que foi validado do que era rascunho. A mensagem registra o número do gate (unit passed/failed e quantas execuções reais), não só o que mudou. **Confirmado em 03/08: a Fase 0.2b (v0.5.40 §3.2) tinha gate fechado desde 31/07 mas o commit nunca foi feito — a sessão seguinte herdou 2 arquivos modificados sem rastro no git. Working tree só ficou honesta quando o commit foi feito retroativamente, com a mensagem registrando a data real do gate.**
42. **Mock mente sobre o que tem.** `MagicMock` responde truthy a qualquer atributo e a qualquer chamada. Todo código novo em `BaseFlow` que leia um atributo opcional de `ctx` precisa validar a **FORMA do valor recebido** (`isinstance`, `len`, conteúdo), não apenas a existência do atributo (`getattr`/`is not None`).
43. **Fontes idênticas não provam precedência.** Quando uma migração troca a origem de um dado e as duas origens têm valores iguais, execuções verdes provam ausência de regressão, não que a nova origem está no comando. A prova positiva exige perturbar deliberadamente a nova fonte, ver o efeito, e desfazer. Corolário: quando a fonte antiga é **removida**, a perturbação deixa de ser necessária — passar já prova que só existe uma fonte.
44. **Centralizar a decisão não migra quem já decidia sozinho.** Criar um resolvedor no `BaseFlow` só muda o comportamento de quem o chama. Ao centralizar acesso a um dado, o grep obrigatório é pela **FONTE**, não pelo helper — e ele só está fechado quando o resultado é zero. Corolário aprendido em 03/08: grep pelo nome do dict/constante alterado não basta quando o consumo é indireto (ex: `test_send.py` não cita `MODULOS` mas depende dele via `enviar_relatorio` → import interno). Quando o grep direto não explica uma mudança de resultado de teste, a prova é `git stash` + rodar de novo, não uma segunda hipótese de grep.
45. **Tolerante embaixo, estrito em cima.** Um resolvedor de locator devolve `None` para ausência e não decide se aquilo é fatal — quem chama decide, campo a campo, porque a criticidade é do campo e não do mecanismo. Corolário: ao migrar um acesso que hoje levanta exceção (`dict[chave]`) para um resolvedor tolerante, é obrigatório reintroduzir a explosão explícita no ponto de chamada.
46. **Guard nunca executado não é robustez — é decoração.** Um `if self._tpl_existe(tpl):` cujo arquivo nunca esteve no disco torna o ramo do template código morto permanente. Ao mapear qualquer locator baseado em arquivo, conferir que o arquivo EXISTE na pasta.
47. **Fonte única dispensa a perturbação, mas exige o inventário.** Depois que a fonte redundante sai, um verde já prova precedência. O que *não* fica provado por execução verde é o inverso: chaves presentes no `objects/` que nenhum código consome — não há grep que pegue isso automaticamente, só inventário manual (Fase 5, tooling).
48. **[NOVA v0.5.41] Baseline de falhas é dívida registrada, não contrato a preservar.** O critério de gate não é "N passed / M failed idêntico ao baseline anterior" — isso trata testes historicamente quebrados como se fossem a meta. O critério correto é: nenhum teste que passava passou a falhar, e toda melhora no número (queda em M) tem causa nominal identificada, nunca é revertida por reflexo. Achado em 03/08: uma limpeza de caminhos no CLI destravou 3 testes de `test_send.py` que estavam corretos e falhavam porque o `MODULOS["sislab"]` apontava para um `stem` de arquivo que não existia — o teste sempre esteve certo, o código é que estava errado. Baseline `799 passed / 89 failed` foi promovido para `802 passed / 86 failed` nesta sessão, com a queda de 3 falhas explicada nominalmente (ver §3.2 abaixo), não revertida.

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor (São Paulo). Combina OpenCV, Playwright, EasyOCR, pyjab/Java Access Bridge e oracledb (DatabaseRunner) para automatizar sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — Oracle APEX).

- **Versão atual:** v0.5.41
- **Python:** 3.13+
- **Fase atual (Projeto v1):** Fase 0 — Modelo de Elemento. **Fases 0.1, 0.2, 0.2c-1, 0.2c-2 e 0.2b concluídas, commitadas e no `main`.** Resta a **0.3** (conftest de integração) para fechar a Fase 0.
- **Banco:** congelado por segurança.
- **Documento de referência:** VTAE_Projeto_v1.md

O `objects/cadastro_min.yaml` é hoje a **fonte única** de coordenada, região OCR, caminho de template, `jab_name` e `tela.titulo_jab` do `CadastroPacienteMinFlow`. Não sobrou locator no `config.yaml` nem hardcoded no Python.

**Estado do git ao fechar esta sessão:**
```
2da7cf4 (HEAD -> main) limpeza pre-0.3: remove 2 arquivos mortos, corrige 6 caminhos do CLI
425f210 Fase 0.2b: templates migram para o ObjectRepository
d707aea (origin/main, origin/HEAD) Fase 0.2c-2: remove regioes_ocr do config.yaml do CadastroMin
```
`main` está 2 commits à frente de `origin/main` — **push pendente**, fica com Helio.

---

## 2. Estado atual dos flows — inalterado desde v0.5.32

Ver tabela completa no Projeto v1. Nenhum flow mudou de status nesta sessão. A sessão de 03/08 mexeu em infraestrutura de teste e CLI, não em lógica de flow (exceto o commit retroativo da 0.2b, que já estava validado em tela real desde 31/07).

---

## 3. O que foi feito na sessão de 03/08/2026 (v0.5.40 → v0.5.41)

Sessão sem sandbox Linux disponível (VHDX ausente, terceira vez seguida) — todo o trabalho via leitura/edição direta na pasta conectada e `git`/`pytest` rodados por Helio no PowerShell (regra 37).

### 3.1 [FEITO] Medição da pendência #1 (Fase 0.3) — três achados que corrigem o registro anterior

Antes de desenhar a fixture, leitura de todos os 13 arquivos de integração + `run.py` + `object_repository.py` + `context.py` (regra 38: o disco, não o prompt, é a fonte).

- **`login_si3_fixture.py` não era fixture.** Era uma cópia obsoleta do `test_cadastro_paciente_min`, sem ObjectRepository, registrada no CLI como `login_si3_novo` e dentro de `MODULOS["si3"]`.
- **`cadastro_paciente_fixture.py` não era órfão** (ao contrário do que o v0.5.39 registrava) — tem 3 consumidores vivos (internação, ambulatório com/sem agendamento).
- **`test_login_real.py` quebrava a coleta** — importava `vtae.core.observer` e `vtae.flows.login_flow`, nenhum dos dois existe.
- Achado extra: `FlowContext` declarava `jab`/`db` duas vezes (regra 39); 6 caminhos no CLI apontavam para arquivos inexistentes, silenciados pelo filtro de "ausentes" do `_rodar_pytest`.

Decisão de Helio: família A (`test_cadastro_paciente_min`, auto-boot com `abrir_si3_navegador` + `LoginSi3Flow` + dois configs) é o **modelo** para a fixture canônica da 0.3. A simplificação do próprio flow (823 linhas para ~6-13 campos reais) fica para uma **Fase 0.4**, logo após a 0.3 fechar — não entra agora, mas está planejada.

### 3.2 [FEITO] Limpeza pré-0.3 — dois commits, não um

**Commit `425f210`** — registro retroativo da Fase 0.2b (v0.5.40 §3.2), que tinha gate fechado em 31/07 mas nunca foi commitada. `git diff` confirmou que as mudanças pendentes na working tree eram exatamente as 3 chaves `template:` no YAML e as mudanças de `_TPL`/`ctx.objects.template()`/remoção do ramo morto do CM06 descritas no v0.5.40 — nada a mais, nada a menos.

**Commit `2da7cf4`** — limpeza propriamente dita:
- `login_si3_fixture.py` e `test_login_real.py` removidos.
- `MODULOS` / `TESTES` / `_MAPA_TESTE_SISTEMA` (`vtae/cli/run.py`): 6 caminhos inexistentes corrigidos ou removidos.
- `FlowContext`: duplicata de `jab`/`db` removida.
- `README.md` e `summary_generator.py`: referências às remoções.

**Achado não previsto:** corrigir o caminho do sislab em `MODULOS["sislab"]` destravou 3 testes de `test_send.py` (`TestEnviarRelatorio::test_envia_quando_execution_json_existe` e os dois de `somente_em_falha`). Causa: `enviar_relatorio` monta `evidence/<data>/<stem>/execution.json` a partir do `Path(arq).stem` de `MODULOS`; o stem antigo (`test_01_cadastro_funcionario`) nunca casava com o real (`test_cadastro_funcionario_sislab`), então a função sempre retornava "nenhum relatório encontrado" antes de chegar à lógica testada. Os testes estavam certos; o caminho é que estava errado. Ver regra 48.

**Gate:** `pytest tests/unit` foi de `799 passed / 89 failed` (baseline anterior, confirmado via `git stash` contra o HEAD limpo) para **`802 passed / 86 failed`** com os dois commits aplicados — 0 regressões, 3 melhoras com causa nominal. **Novo baseline: 802/86.** Nenhuma execução em tela real nesta sessão (nenhum dos dois commits toca lógica de flow).

### 3.3 [ACHADO] Pendência #10 tem causa diferente da registrada

O prompt v0.5.40 registrava a causa como "import `src.flows.msi3...` que nunca existiu". A coleta real (`pytest tests/integration --collect-only -q`) mostrou outra coisa:

```
tests/.../test_frequencia_aplicacao.py:6: from configs.msi3.login_config import LoginConfigMsi3
configs/msi3/login_config.py:8: _cfg = _CL.carregar("msi3")
ConfigError: Arquivo de configuracao nao encontrado: 'configs\msi3\config.yaml'
```

`configs/msi3/login_config.py` chama `ConfigLoader.carregar()` **no corpo do módulo, em tempo de import** — não dentro de uma função. Como `configs/msi3/config.yaml` não existe, a simples coleta do arquivo de teste (sem executá-lo) já lança `ConfigError` e aborta a coleta de **toda a pasta** `tests/integration` (`Interrupted: 1 error during collection`). Isso é bloqueante para a Fase 0.3: uma fixture em `tests/integration/conftest.py` não roda em nenhum teste se a coleta abortar antes.

### 3.4 [ACHADO] Pendência nova — `test_login_sislab.py` não registrado

`tests/integration/sislab/test_login_sislab.py` existe, coleta e passa na inspeção — mas não está em `MODULOS`, `TESTES` nem `_MAPA_TESTE_SISTEMA`. Não foi tocado nesta sessão (mudaria comportamento do CLI, não é limpeza). Registrado como pendência.

### 3.5 [PROCESSO] Dois incidentes de execução no PowerShell, sem impacto no código

- `Select-String` não tem `-Recurse` — o padrão correto é `Get-ChildItem -Recurse -Include *.py | Select-String "padrao"`. Corrigido e incorporado à regra 37.
- Um `git commit -m "..."` multi-linha foi digitado sem o `git` na frente (virou `commit -m ...`, comando não encontrado) e um segundo ficou preso em continuação de heredoc (`>>`). Nenhum commit foi feito nesse meio-tempo — confirmado via `git log` e `git show --stat` antes de qualquer correção (regra 36: medir antes de agir). Resolvido escrevendo as mensagens em arquivo (`_msg_commit_a.txt` / `_msg_commit_b.txt`) e usando `git commit -F arquivo.txt`, removidos após uso. Padrão a repetir sempre que a mensagem de commit tiver múltiplas linhas.

---

## 4. Pendências imediatas (ordem de execução)

| # | Pendência | Prioridade | Depende de |
|---|---|---|---|
| 1 | **Push de `main` para `origin/main`** — 2 commits pendentes (`425f210`, `2da7cf4`). | 🔴 imediato | — |
| 2 | **Fase 0.3 — fecha a Fase 0.** Desenhar e criar `tests/integration/conftest.py` com fixture canônica de boot do SI3 (família A: `abrir_si3_navegador` + `LoginSi3Flow` + dois configs + `ObjectRepository`). Precisa resolver a pendência #3 (coleta abortando) antes ou junto, via `collect_ignore` documentado. Devolver desenho em português primeiro (regra 3), esperar "faz sentido" de Helio, só então código (regra 35). | 🔴 próxima | #3 |
| 3 | **Coleta de `tests/integration` aborta** por causa de `configs/msi3/login_config.py` chamar `ConfigLoader.carregar("msi3")` em tempo de import, e `configs/msi3/config.yaml` não existir. Resolver via `collect_ignore` no conftest da 0.3, ou criar o config.yaml faltante — decidir com Helio. | 🔴 bloqueia #2 | — |
| 4 | **Fase 0.4 — simplificar `cadastro_paciente_min_flow.py`** (823 linhas para ~6-13 campos reais). Entra logo após a 0.3 fechar, decisão de Helio. Não usar o `dsl_interpreter.py` existente como base — ele não conhece ObjectRepository, pyjab, nem as camadas de verificação; nasceu antes delas e por isso nunca foi adotado por nenhum flow. | 🟡 planejada, após #2 | #2 |
| 5 | `test_login_sislab.py` existe e não está registrado em `MODULOS`/`TESTES`/`_MAPA_TESTE_SISTEMA`. Decidir se entra e em qual chave. | 🟡 | — |
| 6 | `causa_falha` classifica erro de automação (locator errado, template desatualizado) como `SISTEMA` — falso no relatório gerencial. | 🟡 | — |
| 7 | `ocr_lido` perdido quando o step falha — **causa identificada nesta sessão**: `_step` do `BaseFlow` já grava via `ocr_holder`, mas CM04 e CM05 do `CadastroPacienteMinFlow` não passam `ocr_holder` — só fazem atribuição tardia que nunca chega ao observer. CM06/07/08 passam `ocr_holder` **e** repetem a atribuição tardia (redundante, 3 linhas cada). Conserto: passar `ocr_holder` em CM04/CM05, remover as atribuições tardias redundantes de CM06/07/08. Gate próprio. | 🟡 causa conhecida, conserto pequeno | — |
| 8 | `CadastroPacienteMinFlow` não tem teste unitário — único flow-piloto coberto só por integração (~2 min/execução). | 🟡 dívida visível | — |
| 9 | CM06 sem clique por template (decorrência consciente da regra 46 — CM06 §3.3 do v0.5.40). Gate próprio se algum dia precisar. | 🟢 monitorar | — |
| 10 | CM06 (Sexo) roda sem verificação pyjab real por race condition de startup do Java Access Bridge (herdado de v0.5.35). | 🟡 conhecido, não bloqueia | — |
| 11 | Mapear names pyjab restantes (AB06, AB09, AB10, AB11, AB12). | 🟡 paralelo | — |
| 12 | `test_cadastro_paciente_flow.py` desatualizado — 27 steps esperados vs 4 reais, responsável pela maior parte das falhas do baseline. Decidir: atualizar ou marcar `xfail` com justificativa. | 🟡 dívida visível | — |
| 13 | `test_config_loader.py::test_arquivo_nao_encontrado` — espera `"não encontrado"` com til, loader emite `"nao encontrado"` sem. | 🟢 trivial | — |
| 14 | Observação não investigada: falha isolada em CM07/BRASILEIRO por popup HC-INCOR (09:34 de 31/07) — não se repetiu em 16 execuções desde então. Revisitar só se voltar. | 🟢 monitorar | — |
| 15 | Escolher aplicação Citrix candidata a cliente 2 (Fase 3). | 🟡 a definir | Helio |
| 16 | Todos os itens de banco suspensos até liberação do InCor. | ⏸ congelado | Liberação segurança |

---

## 5. Padrões consolidados de código

Inalterados desde v0.5.40. Ver v0.5.40 §5 para `_verify_campo_obrigatorio`/`_verify_campo_opcional`, `_verify_campo_via_jab`, `_resolver_regiao_ocr`, consumo de template via ObjectRepository (§5.z), fallback banco→YAML (congelado).

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
├── components/   (si3/, msi3/ — cadastro_paciente_component.py e apex_form_component.py
│                  são codigo morto, nao usados por nenhum flow; nao tocados nesta sessao)
├── config/       (loader.py, schema.py)
├── core/         (object_repository.py, context.py, dsl_interpreter.py — este ultimo tambem
│                  codigo morto do ponto de vista de flows, mas com testes unitarios no
│                  baseline; decisao sobre ele fica para a Fase 0.4)
├── flows/        (si3/, msi3/ — todo o código de negócio)
├── runners/      (database_runner.py, ...)
└── ...
```

`objects/cadastro_min.yaml` — **fonte única** de coordenada, `regiao_ocr`, `template`, `jab_name` e `tela.titulo_jab` do `CadastroPacienteMinFlow`.
`configs/si3/si3_cadastro_paciente_min/config.yaml` — sistema/tipo/runner/ocr_engine, credenciais (referência a `.env`), `dados_faker` e `dados:`. **Nenhum locator.**

---

## 9. Próximo passo concreto (início do próximo chat)

1. Confirmar com Helio que o `push` (pendência #1) foi feito, ou fazer o `push` primeiro se ainda não.
2. **Pendência #3** — decidir com Helio: `collect_ignore` no conftest da 0.3 (rápido, documentado, resolve a Fase 0) ou criar `configs/msi3/config.yaml` de verdade (resolve a causa raiz, mas é escopo maior e toca MSI3, fora do que a 0.3 pretende tocar).
3. **Pendência #2 — Fase 0.3.** Desenho da fixture canônica em português, modelo família A (`test_cadastro_paciente_min` como referência), dois conftest por diretório (`tests/integration/conftest.py` genérico + `tests/integration/si3/conftest.py` com o boot do SI3). Lembrar: `cmd_jornada` roda cada step em subprocess separado — a fixture não pode prometer login único por sessão de jornada, só eliminar duplicação de boot e padronizar `inject_logger`/`observer.report`, que hoje 3 arquivos esquecem.
4. Esperar "faz sentido" de Helio antes de qualquer código (regra 35).
5. As pendências #5 a #16 não bloqueiam nada e podem entrar quando Helio quiser trocar de assunto.

---

**Marco desta sessão (03/08 — v0.5.41):** a Fase 0.2b, que tinha gate fechado desde 31/07 mas nunca foi commitada, virou registro em `425f210` — achado direto da regra 41 em ação: a working tree não distinguia mais o que era validado do que era rascunho até o `git diff` provar que as duas mudanças pendentes eram exatamente a 0.2b descrita no v0.5.40. Uma limpeza de dois arquivos mortos e seis caminhos falsos no CLI (`2da7cf4`) revelou, como efeito colateral, um defeito real no `vtae send` que fazia 3 testes corretos falharem por um `stem` de caminho errado — o baseline do unit subiu de 799/89 para 802/86, e a regra 48 nasceu para formalizar que essa subida é correção, não regressão a temer. A pendência #10 (antiga) foi diagnosticada de novo com causa correta: config carregado em tempo de import aborta a coleta inteira da pasta de integração, o que bloqueia a Fase 0.3 até ser tratado. A Fase 0 fica a uma etapa do fim — falta só a 0.3, cujo desenho começa já sabendo o que a fixture precisa resolver antes de existir.
