# VTAE — Prompt de Instrução Geral do Projeto

**Data:** 04/08/2026 | **Versão:** v0.5.44
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
42. Mock mente sobre o que tem: teste valida a FORMA da chamada, não só que houve chamada. Preferir **fake** a `MagicMock` — o Mock devolve truthy para qualquer coisa e o teste passa sem provar nada.
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
54. **Obrigatoriedade é do CENÁRIO, não do elemento.** O `objects/*.yaml` não carrega `criticidade`. Todo campo que o teste declara é preenchido e verificado ESTRITO; campo não declarado não é tocado. Cenário negativo se declara no YAML de flow. **Corolário refinado na v0.5.44:** "estrito" significa *nunca pular em silêncio* — não significa *exigir a camada exata em todo campo* (ver regra 56).
55. **Baseline se mede com `pytest tests/unit -q`.** `testpaths = tests` no `pyproject.toml` faz `pytest` sem argumento coletar os testes de integração, que abrem o SI3 real e tentam logar. Não existe marcador separando integração de unitário (gap conhecido, Fase 3).
56. **[NOVA v0.5.44] Camada exata é propriedade da TELA, declarada e nunca inferida.** `tela.camada_exata: pyjab | playwright | nenhuma` no `objects/*.yaml`; ausente = `nenhuma`. Inferir pela presença de `titulo_jab` faria "esqueci de calibrar este campo" virar "este sistema não tem camada exata" — as duas situações que a verificação existe para separar. **Ela é obrigatória apenas em `lov` e `lov_lista`**, onde há falha silenciosa medida (caso ALLIANZ, 3x). Texto livre, máscara e resultado gerado seguem servidos por OCR — exigir mais reprovaria campos que nunca precisaram de `jab_name` (`nome`, `matricula`, `data_nascimento`).
57. **[NOVA v0.5.44] Quando o OCR decide um LOV, o containment do `_similar` é desligado.** `'ALLIANZ'` está contido em `'ALLIANZ SAUDE'` — é por aí que o match parcial do Forms passaria verde num sistema sem camada exata. Fora de LOV o containment permanece: ele existe porque o OCR corta a borda do campo.
58. **[NOVA v0.5.44] `vtae/core/` não importa `vtae/flows/`.** O núcleo não pode depender da camada que ele vai substituir. `_normalizar`/`_similar` vivem em `vtae/core/texto.py` e são reexportados por `base_flow.py` (o import antigo segue válido). Tolerância do `_similar`: **0.230** — é o valor que passou os gates em tela real; docstring corrigida, prompt corrigido.
59. **[NOVA v0.5.44] Confiança degradada é perda real, não ausência de recurso.** `degradado=True` só quando a tela DECLARA ter camada exata e ela não pôde ser usada. Sistema que simplesmente não tem uma (Citrix) informa pelo `camada_decisora`, sem marcar degradação — aviso que aparece sempre é aviso que ninguém lê.
60. **[NOVA v0.5.44] Aviso ao testador nunca rouba foco durante a execução.** Popup no meio da corrida quebra o Oracle Forms (o clique seguinte vai para a janela errada). Quebrar o silêncio se faz por: marcação no `StepResult` durante, faixa no topo do `report.html` e resumo no console ao fim. Janela, se houver, só depois da execução.

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor. OpenCV, Playwright, EasyOCR, pyjab/JAB e oracledb (congelado) para sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — APEX).

- **Versão:** v0.5.44 · **Python:** 3.13+
- **Documento de referência:** **VTAE_Projeto_v1.1.md**
- **Fase atual:** **Fase 2 — O MOTOR.** Peças 1, 2 e 3 CONCLUÍDAS. Próxima: **peça 4 (executor do YAML de flow)**.
- Fases 0 e 1: concluídas. Fase 3 (após o motor): Helio refaz os testes de admissão e o cadastro completo com o motor.

## 2. Estado dos flows

Inalterado. Os flows atuais continuam funcionando mas serão REFEITOS na Fase 3 — nenhum conserto neles, salvo pedido expresso de Helio.

## 3. O que foi feito na sessão de 04/08/2026 (v0.5.43 → v0.5.44)

Sessão sem sandbox Linux (6ª vez) — trabalho via pasta conectada; `pytest` e `git` com Helio.

### 3.1 [FEITO] Peça 3 desenhada, corrigida em rota e entregue — gate fechado

O desenho em português foi aprovado ("faz sentido") antes de qualquer código. Quatro decisões de Helio governaram a implementação:

- **divergência entre camadas = aviso registrado**, não falha;
- **6 dígitos fixo** para máscara — Helio observou que o formato pode mudar (`AAAA/DD/MM`), o que é o melhor argumento a favor de contar dígitos: `_normalizar` remove separadores, então a contagem é imune à ordem;
- **tolerância 0.230 mantida** (o que passou os gates), textos corrigidos;
- **`camada_exata` declarada na tela** + containment desligado quando o OCR decide um LOV.

Entregue:

- `vtae/core/texto.py` (novo) — `_normalizar`/`_similar` extraídos do `base_flow`, com `permitir_containment` novo.
- `vtae/core/motor/verificacao.py` (novo) — `Veredito` (frozen) + `Verificador`. Status: `OK` / `DIVERGENTE` / `VAZIO` / `NAO_VERIFICAVEL`. Nunca levanta exceção.
- `ObjectRepository.camada_exata()` — default `"nenhuma"`, declarado nunca inferido.
- `base_flow.py` — 3 edições cirúrgicas (remove `import unicodedata`, reexporta do core, apaga as duas funções).
- `tests/unit/test_verificacao.py` (novo) — 21 unitários com **fakes**, não `MagicMock`.

**Baseline: 819/86 → 840/86, os 86 intactos.**

### 3.2 [MEDIDO] Erro de desenho pego ao escrever os testes

A primeira versão exigia locator exato de **qualquer** tipo quando a tela declarava `camada_exata`. Isso reprovaria `nome`, `matricula`, `identificador` e `data_nascimento` — campos que nunca tiveram `jab_name` e nunca precisaram. Confundiu-se "verificação estrita" com "camada exata obrigatória". Corrigido com `EXIGEM_CAMADA_EXATA = ("lov", "lov_lista")` — vira a regra 56. **O erro só apareceu porque os testes foram escritos; nenhuma releitura o teria pego.**

### 3.3 [MEDIDO] `objects/si3/cadastro_min.yaml` provavelmente não parseia — PENDENTE

14 linhas do arquivo da peça 1 têm `tipo: X    coordenada: {...}` na **mesma linha física** (medido: não há CR isolado no arquivo). Em YAML de bloco isso é erro de parse. Atinge `nome`, `data_nascimento`, `hora`, `sexo`, `nacionalidade`, `cor_etnia`, os 4 popups de nacionalidade, `matricula` e `identificador`.

Passou despercebido porque **ninguém carrega esse arquivo**: o flow e `tests/integration/si3/components/test_cadastro_paciente_min.py:63` usam `objects/cadastro_min.yaml` (o antigo). Regra 46 do lado do dado.

Medição pendente (um comando):
```
python -c "import yaml;yaml.safe_load(open('objects/si3/cadastro_min.yaml',encoding='utf-8'));print('OK')"
```
Se falhar: a correção são 14 quebras de linha, **sem tocar em nenhum número**. Bloqueia a peça 4.

### 3.4 [MEDIDO] `PlaywrightRunner` não tem leitura exata de campo

`get_text` usa `inner_text` (`playwright_runner.py:203`), que devolve `""` para `<input>`. Ou seja, `camada_exata: playwright` ainda não tem adaptador — falta um `input_value`. Não implementado (regra 50): nasce na peça 5, junto da fixture `msi3`.

### 3.5 [CONTEXTO] Aviso em popup — proposto por Helio, adiado com fundamento

Helio propôs avisos em popup na tela para quebrar o silêncio do erro. Recusado **durante a execução** (rouba foco do Forms e quebra o teste que está avisando — regra 60), aceito o problema de fundo: a peça 3 produz o dado marcado, e o relatório é quem o mostra. Encaixa com a edição pendente do `summary_generator.py`.

## 4. Pendências (todas rastreiam ao v1.1)

| # | Pendência | Fase v1.1 | Prioridade |
|---|---|---|---|
| 1 | Medir `objects/si3/cadastro_min.yaml` com `yaml.safe_load`; se falhar, 14 quebras de linha | Fase 2, antes da peça 4 | 🔴 bloqueia |
| 2 | Peça 4 — executor do YAML de flow: junta resolvedor + esperas + verificação e vai à tela real (gate 3x acontece aqui) | Fase 2, peça 4 | 🔴 próxima |
| 3 | Working tree: edição do `summary_generator.py` + 2 `git rm` do MSI3 morto — commit na peça 5 | Fase 2, peça 5 | 🟡 registrada |
| 4 | Faixa de avisos no `report.html` + resumo no console (regra 60) | Fase 2, peça 5 ou relatório | 🟡 registrada |
| 5 | `input_value` no `PlaywrightRunner` (adaptador da camada exata web) | Fase 2, peça 5 | 🟡 registrada |
| 6 | `ocr_engine: tesseract` no config do TipoAnestesia — corrigir junto com a fixture `msi3` | Fase 2, peça 5 | 🟡 registrada |
| 7 | Associação `titulo_janela` ↔ campo é inferência da tupla do flow — confirmar em tela real | Fase 2, peça 4 | 🟡 |
| 8 | N de backspaces: decisão foi N fixo generoso (20) no motor, override por elemento só se um campo desmentir | Fase 2, peça 4 | 🟡 |
| 9 | `jab_name` de `data_nascimento` — mapear se um dia a ordem dos dígitos precisar ser provada | Fase 3 | 🟢 |
| 10 | `lov_lista` dos popups de nacionalidade sem `jab_name` — exigidos só se o teste os declarar (regra 54) | Fase 3 | 🟢 |
| 11 | `test_login_sislab.py` não registrado no CLI | Fase 3 | 🟢 |
| 12 | Names pyjab das admissões (AB06, AB09-AB12) | Fase 3 | 🟢 |
| 13 | Marcador `integration` para separar unit de tela real | Fase 3 | 🟢 |
| 14 | Aplicação Citrix candidata | Fase 4 | ⏳ Helio |
| 15 | Banco congelado até liberação InCor | — | ⏸ |

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
Novo em `core/`: **`texto.py`** e **`motor/`** (`resolvedor.py`, `esperas.py`, `verificacao.py`).
`dsl_interpreter.py` e `components/` mortos serão substituídos/removidos pelo motor (peça 4).

## 9. Próximo passo concreto (início do próximo chat)

1. Rodar a medição do `objects/si3/cadastro_min.yaml` (§3.3). Se falhar, corrigir as 14 quebras de linha — mecânico, zero número alterado.
2. Desenho em português da **peça 4 — executor**: como o YAML de flow é lido, como um step vira `resolver → esperar → agir → verificar → evidência`, onde o `Veredito` vira falha de step e onde vira aviso. Zero código antes do "faz sentido".
3. Uma peça por vez. A peça 5 (fixtures `si3`/`msi3` + limpeza do MSI3 morto + faixa de avisos no relatório) vem depois.

---

**Marco desta sessão (04/08 — v0.5.44):** a peça 3 fechou o motor de decisão — ele já sabe *onde* agir (peça 2), *quando* agir (peça 2) e agora *se deu certo*, com a matriz do Projeto v1 §6 virando tabela executável. O ganho de comportamento é que verificação não some mais em silêncio: campo declarado e não calibrado vira erro nomeado, discordância entre camadas fica registrada, e confiança degradada é sinalizada só quando há perda real. Nada do que roda hoje foi tocado.

**Resumo de Helio (regra 35):**
_"Ajuste de camadas, construção de um motor de decisão."_
