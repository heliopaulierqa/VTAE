# VTAE — Prompt de Instrução Geral do Projeto

**Data:** 04/08/2026 (2ª sessão do dia) | **Versão:** v0.5.45
Use este documento como primeira mensagem no próximo chat.
Referência acima deste documento: **VTAE_Projeto_v1.1.md** (APROVADO 03/08/2026) — a "constituição" do projeto.
Este prompt é registro operacional: onde paramos e o que fazer a seguir.

---

## 0. REGRAS DE TRABALHO — LEIA PRIMEIRO

**ESTAS REGRAS SÃO INEGOCIÁVEIS E NUNCA PODEM SER QUEBRADAS:**

1. NUNCA criar ou alterar arquivo sem que Helio veja o conteúdo atual primeiro.
2. NUNCA gerar arquivo completo sem receber o upload / ler o arquivo atual.
3. AGUARDAR O UPLOAD (ou ler o arquivo real) antes de gerar qualquer código — jamais antecipar ou assumir conteúdo.
4. Para alterações pontuais: informar exatamente ONDE e O QUE mudar — não gerar arquivo completo.
5. NUNCA romper ou alterar nenhum contrato/padrão estabelecido sem que Helio saiba e aprove.
6. NUNCA reescrever lógica de negócio de um flow — apenas as linhas explicitamente solicitadas.
7. Quando um flow está validado e funcionando, qualquer mudança é CIRÚRGICA: confirmar com diff antes de entregar.
8. Antes de responder sobre qualquer falha: pesquisar o histórico — o padrão pode já ter sido resolvido antes.
9. Não propor soluções cosméticas — cada mudança responde uma das 5 perguntas de observabilidade.
10. Não circular — se uma abordagem falhou 2x, propor alternativa diferente, não insistir.
11. Medir antes de confiar — `diagnose()` contra arquivo real antes de rodar a jornada inteira.
12. Medir sensibilidade E especificidade dos templates.
13. Gerar arquivo completo SOMENTE quando Helio pedir expressamente.
14. Nenhum `.env` com comentário na mesma linha de um `VAR=valor`.
15. Mudanças de observabilidade são GATE: uma jornada de cada vez, 3x consecutivas antes de propagar.
16. Subprocessos do CLI sempre usam `sys.executable`, nunca `"python"`.
17. `pyperclip.copy()` + Ctrl+V: delay ≥0.15s entre as chamadas; 0.5s entre clique em campo e ação seguinte.
18. Templates SEMPRE via `pyautogui.screenshot()` + `PIL.crop()` — nunca Win+Shift+S.
19. `diagnose()`: template primeiro, screenshot depois; para arquivo, sobrescrever `matcher._capture_screen`.
20. `regioes_ocr` no YAML exige espaço após dois pontos: `{ x1: 27, y1: 145 }`.
21. Coordenadas com janela maximizada. Preferir clique via template quando o elemento pode se deslocar.
22. Dois `FlowContext` separados quando dois flows têm configs diferentes.
23. `_verify_campo_obrigatorio` / `_verify_campo_opcional` exigem `ocr_holder: list` como último argumento.
24. Campos com reformatação automática (data, CPF) NÃO usam valor exato via OCR — verificação por estrutura.
25. `ocr_lido` propagado ao StepResult.
26. Popups são âncoras frágeis para guards genéricos; templates apertados de elemento específico e conhecido são confiáveis quando medidos.
27. Campo Profissional em lista de procedimentos SI3: `_selecionar_via_lov`.
28. `max(numeros, key=len)` no OCR de campos com múltiplos números.
29. Cenário negativo em Oracle Forms tem duas falhas silenciosas: popup conhecido (template apertado) e match parcial em LOV (pyjab).
30. Verificação pyjab é camada PARALELA ao OCR — exata, sem Levenshtein. `JABDriver` sob demanda, cacheado em `ctx.jab`.
31. `JAVA_HOME` do pyjab setado programaticamente via config, NUNCA via `setx`.
32. pyjab não substitui OCR/OpenCV/Playwright — complementa. Como ESCRITOR fica fora desta fase; como SENSOR de espera, entra quando um teste real exigir.
33. ~~AdmissaoAmbulatorioFlow como flow-modelo~~ — **SUPERADA pelo v1.1 (Decisão #6):** pilotos do motor são CadastroPacienteMinFlow (desktop) e TipoAnestesiaFlow (web).
34. `DatabaseRunner`: CONGELADO por segurança do InCor até liberação.
35. **Padrão de aprendizado:** nenhum código sem que Helio explique o que faz e por quê. Diff em 3 partes (o quê / por quê / conceito). Desenho em português antes de código. Helio digita diffs pequenos; colar reservado a blocos mecânicos. Fim de sessão: Helio resume em 2 frases.
36. Anti-especulação: diante de falha, medir e reverter empiricamente ANTES de gerar hipóteses.
37. Sandbox Linux pode estar indisponível — trabalho via pasta conectada; `git`/`pytest` com Helio.
38. O registro escrito não é a fonte de verdade — o disco é. Pendência de prompt que não rastreia a uma fase do Projeto v1.1 é sugestão, não trabalho.
39. Argumento posicional casa por posição; campo duplicado em `@dataclass` sobrescreve default sem criar campo.
40. Separação por natureza: **locator** em `objects/*.yaml` (muda com a TELA); **dado de teste** em `config.yaml` (muda com o CENÁRIO); **segredo** em `.env` (muda com a MÁQUINA).
41. **Gate fechado termina em commit.** diff → grep → pytest unit vs baseline → 3x tela real (quando aplicável) → commit. Mensagem multi-linha: `git commit -F arquivo.txt`. `git add` seletivo quando a working tree tem pendências de outra fase.
42. Mock mente sobre o que tem: teste valida a FORMA da chamada, não só que houve chamada. Preferir **fake** a `MagicMock`.
43. Fontes idênticas não provam precedência; fonte única removida dispensa perturbação.
44. Ao centralizar acesso a um dado, o grep obrigatório é pela FONTE, não pelo helper.
45. Tolerante embaixo, estrito em cima: resolvedor/verificador devolve estado; quem chama decide se é fatal.
46. Guard nunca executado não é robustez — caminho declarado tem que ser exercitado ao menos em unitário.
47. Fonte única exige inventário: chaves órfãs no `objects/` só aparecem por inventário manual (Fase 6, tooling).
48. Baseline de falhas é dívida registrada, não contrato: nenhum teste que passava pode falhar; melhora exige causa nominal. **Baseline atual: 840 passed / 86 failed em `tests/unit`.**
49. **YAML declara, Python decide.** O YAML de flow nunca ganha `if`, loop ou variável. Lógica de negócio real vira step nomeado em Python.
50. **O motor cresce por demanda de teste real, não por antecipação.** Generalizar para caso hipotético é dívida, não robustez.
51. **Espera por condição, nunca por tempo.** Título de janela, template visível ou estado pyjab — jamais `time.sleep` como mecanismo primário. Sleep físico documentado (clipboard, pós-clique) é exceção.
52. **Prompt operacional não cria escopo** (v1.1 §6). Hierarquia: Projeto v1.1 → Plano de Fase → prompt.
53. **Direção competitiva:** superar o TestComplete onde ele é fraco por design — verificação em camadas, legado desktop/Citrix, evidência auditável por step.
54. **Obrigatoriedade é do CENÁRIO, não do elemento.** O `objects/*.yaml` não carrega `criticidade`. Todo campo que o teste declara é preenchido e verificado ESTRITO; campo não declarado não é tocado. "Estrito" significa *nunca pular em silêncio* — não *exigir a camada exata em todo campo* (regra 56).
55. **Baseline se mede com `pytest tests/unit -q`.** `testpaths = tests` no `pyproject.toml` faz `pytest` sem argumento coletar os testes de integração, que abrem o SI3 real. Não existe marcador separando integração de unitário (gap conhecido, Fase 3).
56. **Camada exata é propriedade da TELA, declarada e nunca inferida.** `tela.camada_exata: pyjab | playwright | nenhuma` no `objects/*.yaml`; ausente = `nenhuma`. Obrigatória apenas em `lov` e `lov_lista`, onde há falha silenciosa medida (caso ALLIANZ, 3x). Texto livre, máscara e resultado gerado seguem servidos por OCR.
    **[COROLÁRIO v0.5.45]** Entregar uma tela nova em `objects/` **inclui declarar `camada_exata`**. Foi exatamente o que faltou no arquivo do piloto (§3.2): sem a linha, o default `"nenhuma"` faz `_ler_exato` retornar no primeiro `if` e os `jab_name` já mapeados são ignorados em silêncio — a proteção da peça 3 desligada sem nenhum aviso.
57. **Quando o OCR decide um LOV, o containment do `_similar` é desligado.** `'ALLIANZ'` está contido em `'ALLIANZ SAUDE'` — é por aí que o match parcial do Forms passaria verde num sistema sem camada exata. Fora de LOV o containment permanece.
58. **`vtae/core/` não importa `vtae/flows/`.** `_normalizar`/`_similar` vivem em `vtae/core/texto.py`, reexportados por `base_flow.py`. Tolerância do `_similar`: **0.230**.
59. **Confiança degradada é perda real, não ausência de recurso.** `degradado=True` só quando a tela DECLARA ter camada exata e ela não pôde ser usada. Sistema que simplesmente não tem uma (Citrix) informa pelo `camada_decisora`, sem marcar degradação.
60. **Aviso ao testador nunca rouba foco durante a execução.** Popup no meio da corrida quebra o Oracle Forms. Quebrar o silêncio se faz por: marcação no `StepResult` durante, faixa no topo do `report.html` e resumo no console ao fim.
61. **[NOVA v0.5.45] Valor esperado de um check se conta, não se prevê.** Publicar um esperado chutado ("esperado: 38 objetos") destrói o próprio check: se o número vier diferente, não há como saber se errou o arquivo ou a previsão. Ou o esperado sai de uma contagem independente, ou o check se anuncia pelo que realmente é — "não levantou exceção". Erro cometido em §3.4 desta sessão.

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor. OpenCV, Playwright, EasyOCR, pyjab/JAB e oracledb (congelado) para sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — APEX).

- **Versão:** v0.5.45 · **Python:** 3.13+
- **Documento de referência:** **VTAE_Projeto_v1.1.md**
- **Fase atual:** **Fase 2 — O MOTOR.** Peças 1, 2 e 3 CONCLUÍDAS. Bloqueio da peça 4 removido. Próxima: **peça 4 (executor do YAML de flow)** — começa pelo desenho em português.
- Fases 0 e 1: concluídas. Fase 3 (após o motor): Helio refaz os testes de admissão e o cadastro completo com o motor.

## 2. Estado dos flows

Inalterado. Os flows atuais continuam funcionando mas serão REFEITOS na Fase 3 — nenhum conserto neles, salvo pedido expresso de Helio.

## 3. O que foi feito na 2ª sessão de 04/08/2026 (v0.5.44 → v0.5.45)

Sessão sem sandbox Linux (**7ª vez** — VHDX ausente). Trabalho por leitura/edição direta na pasta conectada; `pytest` e `git` com Helio.
**Nenhum arquivo Python foi tocado. Baseline permanece 840/86, não remedida (nada a remedir).**

### 3.1 [FEITO] Pendência #1 fechada — `objects/si3/cadastro_min.yaml` corrigido

Erro de parse **confirmado**: `tipo: X    coordenada: {...}` na mesma linha física faz o YAML tentar ler `X    coordenada: {...}` como escalar simples, e escalar simples não pode conter `: ` → `mapping values are not allowed in this context` na linha 63.

**Eram 17 linhas, não 14** — o registro da v0.5.44 subestimou. Elementos atingidos: `nome`, `data_nascimento`, `hora`, `sexo`, `nacionalidade`, `cor_etnia`, `estado_brasileiro`, `cidade_brasileiro`, `pais_estrangeiro`, `data_entrada_brasil`, `estado_estrangeiro`, `municipio_estrangeiro`, `pais_naturalizado`, `data_naturalizacao`, `nr_portaria`, `matricula`, `identificador`.

Corrigido com 17 quebras de linha, indentação de 4 espaços preservada, **zero número alterado**.

**Medição de Helio no terminal real:**
```
OK 47 objetos, camada: pyjab
```
Contagem independente das chaves de primeiro nível (`^  \w+:$`): **47**. Bate. O arquivo parseia e nenhum elemento grudou ou se partiu.

### 3.2 [ACHADO NOVO] `tela.camada_exata` ausente — a proteção estava desligada

O `tela:` do arquivo tinha `titulo_jab` e `ancora`, **mas não `camada_exata`**. Pelo que a peça 3 implementou (`object_repository.py:45`, default `"nenhuma"`), isso faria `verificacao.py:117` retornar imediatamente e **nunca usar os `jab_name`** de `sexo`, `nacionalidade` e `cor_etnia` — piloto rodando com a proteção ALLIANZ desligada, sem `degradado`, sem aviso, porque a tela declarou não ter camada exata.

O default é correto por desenho (regra 56). O que faltava era a declaração. Adicionada uma linha em `tela:`, com comentário explicando por que a ausência é perigosa e não neutra:
```yaml
  camada_exata: pyjab
```
Vira o **corolário da regra 56**.

**Por que isso importa para a peça 4:** sem essa linha, o gate 3x da peça 4 rodaria com o caminho da leitura exata **nunca executado** — passaria verde provando menos do que parece (regra 46). E declarar depois seria mudança em gate fechado (regra 7).

### 3.3 [CORRIGIDO EM ROTA] O trade-off apresentado era falso

Foi apresentada a Helio uma escolha entre (a) só as quebras de linha e (b) quebras + `camada_exata`, com o custo de (b) descrito como "antecipa a pendência 10 — os 4 `lov_lista` de nacionalidade viram `NAO_VERIFICAVEL`".

**Medição desfez o dilema:** `estado_brasileiro`, `cidade_brasileiro`, `pais_estrangeiro` e `pais_naturalizado` não têm **nem `regiao_ocr` nem `jab_name`** — só coordenada. Por `verificacao.py:150-153`, sem leitura exata e sem região calibrada eles já caem em `NAO_VERIFICAVEL` hoje, com ou sem `camada_exata`. Declarar não custou nada a mais para eles. A pendência 10 dispara ou não conforme **a peça 4 decidir se verifica todo campo que preenche** — decisão de desenho, não desta linha.

### 3.4 [ERRO REGISTRADO] Esperado chutado num check

O comando de verificação foi entregue a Helio com "Esperado: `OK 38 objetos`". O 38 foi inventado — ninguém contou. O real é 47. Se tivesse vindo 46, não haveria como distinguir erro do arquivo de erro da previsão. Vira a **regra 61**. O que de fato provou o arquivo foi o `safe_load` não levantar exceção; a contagem só virou prova depois, com o `grep` independente.

### 3.5 [ABERTO] `camada_exata` é da tela — e os popups são outras janelas

Registrado para a peça 4 não ser surpreendida: os popups de LOV são **janelas Java separadas** (`titulo_janela: "Lista de UF"`, `"Lista de Ci"`, `"Lista de Pa"`), enquanto o `JABDriver` conecta pelo `titulo_jab` do formulário principal (`Form_Pac0010`). Se algum dia esses campos ganharem `jab_name`, o leitor exato vai precisar **trocar de janela**. Não é problema agora — ninguém lê esses campos. Vira problema no dia em que a pendência 10 for endereçada.

### 3.6 [PENDENTE — 1 palavra] Comentário morto na linha 4

O cabeçalho do arquivo diz `tipo + criticidade + todos os locators`. `criticidade` saiu na v0.5.43 (regra 54). Texto morto, não tocado por falta de ok explícito.

## 4. Pendências (todas rastreiam ao v1.1)

| # | Pendência | Fase v1.1 | Prioridade |
|---|---|---|---|
| 1 | **Peça 4 — desenho em português do executor**, antes de qualquer código | Fase 2, peça 4 | 🔴 próxima |
| 2 | Peça 4 — implementação: `resolver → esperar → agir → verificar → evidência`; gate 3x em tela real acontece aqui | Fase 2, peça 4 | 🔴 depois de #1 |
| 3 | Working tree: `summary_generator.py` + 2 `git rm` do MSI3 morto + `objects/si3/cadastro_min.yaml` desta sessão — commit na peça 4/5 (`git add` seletivo, regra 41) | Fase 2 | 🟡 registrada |
| 4 | Comentário morto na linha 4 do `objects/si3/cadastro_min.yaml` (§3.6) | Fase 2 | 🟢 1 palavra |
| 5 | Faixa de avisos no `report.html` + resumo no console (regra 60) | Fase 2, peça 5 | 🟡 registrada |
| 6 | `input_value` no `PlaywrightRunner` (adaptador da camada exata web) | Fase 2, peça 5 | 🟡 registrada |
| 7 | `ocr_engine: tesseract` no config do TipoAnestesia — corrigir junto com a fixture `msi3` | Fase 2, peça 5 | 🟡 registrada |
| 8 | Associação `titulo_janela` ↔ campo é inferência da tupla do flow — confirmar em tela real | Fase 2, peça 4 | 🟡 |
| 9 | N de backspaces: decisão foi N fixo generoso (20) no motor, override por elemento só se um campo desmentir | Fase 2, peça 4 | 🟡 |
| 10 | pyjab através de janela de popup — o leitor exato precisa trocar de janela? (§3.5) | Fase 3 | 🟢 |
| 11 | `jab_name` de `data_nascimento` — mapear se um dia a ordem dos dígitos precisar ser provada | Fase 3 | 🟢 |
| 12 | `lov_lista` dos popups de nacionalidade sem `jab_name` nem `regiao_ocr` — exigidos só se a peça 4 verificar campo preenchido (regra 54) | Fase 3 | 🟢 |
| 13 | `test_login_sislab.py` não registrado no CLI | Fase 3 | 🟢 |
| 14 | Names pyjab das admissões (AB06, AB09-AB12) | Fase 3 | 🟢 |
| 15 | Marcador `integration` para separar unit de tela real | Fase 3 | 🟢 |
| 16 | Aplicação Citrix candidata | Fase 4 | ⏳ Helio |
| 17 | Banco congelado até liberação InCor | — | ⏸ |

## 5. Tabela do motor — quem decide o quê (peça 3, implementada)

| `tipo:` no `objects/` | camada que decide | comparação | apoio |
|---|---|---|---|
| `lov`, `lov_lista` | exata (**obrigatória**) | igualdade após `_normalizar` | OCR, sem containment |
| `data` (máscara) | exata se houver locator; senão OCR | ≥ 6 dígitos, imune à ordem | — |
| `texto` | OCR | `_similar` 0.230, com containment | exata se houver |
| `resultado` | OCR | não-vazio | — |
| `botao` | nenhuma | — | `NAO_VERIFICAVEL` se chamado |

Três situações que antes colapsavam num `print`:

| situação | veredito |
|---|---|
| sistema sem camada exata (Citrix) | decide o OCR, sem marcar degradação |
| campo declarado e não calibrado | `NAO_VERIFICAVEL` (erro de configuração) |
| driver declarado que não conectou | `degradado=True`, segue pelo OCR |

## 6-7. Padrões consolidados e padrões Oracle Forms

Inalterados — ver v0.5.40 §5, Projeto v1.1 §5 e v0.5.32 §7.

## 8. Arquitetura

`vtae/` (cli, config, core, flows, runners, report, vision) + `objects/` + `configs/` + `templates/` + `tests/`.
Em `core/`: **`texto.py`** e **`motor/`** (`resolvedor.py`, `esperas.py`, `verificacao.py`).
`dsl_interpreter.py` e `components/` mortos serão substituídos/removidos pelo motor (peça 4).

**Atenção para a peça 4:** o flow e `tests/integration/si3/components/test_cadastro_paciente_min.py:63` ainda carregam **`objects/cadastro_min.yaml`** (o antigo, na raiz de `objects/`). O arquivo novo, corrigido e com `camada_exata`, é **`objects/si3/cadastro_min.yaml`** e continua sem nenhum consumidor. A troca do consumidor é parte da peça 4.

## 9. Próximo passo concreto (início do próximo chat)

1. **Claude lê primeiro** `vtae/core/motor/resolvedor.py`, `vtae/core/motor/esperas.py`, `vtae/core/motor/verificacao.py` e o `cadastro_paciente_min_flow.py` — e verifica se já existe algum YAML de flow escrito ou se o formato é papel em branco. Zero proposta antes da leitura (regra 3).
2. **Desenho em português da peça 4 — executor:** como o YAML de flow é lido; como um step vira `resolver → esperar → agir → verificar → evidência`; onde o `Veredito` vira falha de step e onde vira aviso; **se o motor verifica todo campo que preenche ou só os que o YAML manda verificar** (§3.3 deixou essa decisão explicitamente para cá). Zero código antes do "faz sentido" de Helio.
3. Só depois: código, explicado, construído junto (regra 35). Uma peça por vez.
4. A peça 5 (fixtures `si3`/`msi3` + limpeza do MSI3 morto + faixa de avisos no relatório) vem depois.

---

**Marco desta sessão (04/08, 2ª — v0.5.45):** o bloqueio da peça 4 foi removido e um segundo defeito, que ninguém tinha visto, foi encontrado no caminho: a tela do piloto não declarava `camada_exata`, o que faria o gate da peça 4 passar verde com a leitura exata nunca executada. Os dois defeitos têm a mesma assinatura — arquivo que ninguém carrega não reclama de nada. Nenhum código Python foi tocado.

**Resumo de Helio (regra 35):**
_"________________________________________"_
