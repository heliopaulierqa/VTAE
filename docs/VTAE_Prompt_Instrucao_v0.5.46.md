# VTAE — Prompt de Instrução Geral do Projeto

**Data:** 05/08/2026 | **Versão:** v0.5.46
Use este documento como primeira mensagem no próximo chat.
Referência acima deste documento: **`docs/VTAE_Projeto_v1.1.md`** (APROVADO 03/08/2026) — a "constituição" do projeto.
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
32. pyjab não substitui OCR/OpenCV/Playwright — complementa. Como ESCRITOR fica fora desta fase.
33. ~~AdmissaoAmbulatorioFlow como flow-modelo~~ — **SUPERADA (v1.1 Decisão #6):** pilotos são CadastroPacienteMinFlow (desktop) e TipoAnestesiaFlow (web).
34. `DatabaseRunner`: CONGELADO por segurança do InCor até liberação.
35. **Padrão de aprendizado:** nenhum código sem que Helio explique o que faz e por quê. Diff em 3 partes (o quê / por quê / conceito). Desenho em português antes de código. Helio digita diffs pequenos. Fim de sessão: Helio resume em 2 frases.
36. Anti-especulação: diante de falha, medir e reverter empiricamente ANTES de gerar hipóteses.
37. Sandbox Linux pode estar indisponível — trabalho via pasta conectada; `git`/`pytest` com Helio.
38. O registro escrito não é a fonte de verdade — o disco é.
39. Argumento posicional casa por posição; campo duplicado em `@dataclass` sobrescreve default sem criar campo.
40. Separação por natureza: **locator** em `objects/*.yaml` (muda com a TELA); **dado de teste** em `config.yaml` (muda com o CENÁRIO); **segredo** em `.env` (muda com a MÁQUINA).
41. **Gate fechado termina em commit.** diff → grep → pytest unit vs baseline → 3x tela real (quando aplicável) → commit. `git add` seletivo quando a working tree tem pendências de outra fase.
42. Mock mente sobre o que tem: teste valida a FORMA da chamada. Preferir **fake** a `MagicMock`.
43. Fontes idênticas não provam precedência; fonte única removida dispensa perturbação.
44. Ao centralizar acesso a um dado, o grep obrigatório é pela FONTE, não pelo helper.
45. **Tolerante embaixo, estrito em cima.** Tela é ambiente: degrada e oscila, então resolvedor/verificador devolvem estado e quem chama decide se é fatal. Configuração NÃO é ambiente: YAML malformado é defeito de escrita e explode antes do primeiro clique.
46. Guard nunca executado não é robustez — caminho declarado tem que ser exercitado ao menos em unitário.
47. Fonte única exige inventário: chaves órfãs no `objects/` só aparecem por inventário manual (Fase 6, tooling).
48. Baseline de falhas é dívida registrada, não contrato: nenhum teste que passava pode falhar. **Baseline atual: 866 passed / 86 failed em `tests/unit`.**
49. **YAML declara, Python decide.** O YAML de flow nunca ganha `if`, loop ou variável. Lógica de negócio real vira step nomeado em Python.
50. **O motor cresce por demanda de teste real, não por antecipação.** Generalizar para caso hipotético é dívida, não robustez.
51. **Espera por condição, nunca por tempo.** Título de janela, template visível ou estado pyjab — jamais `time.sleep` como mecanismo primário.
52. **Prompt operacional não cria escopo** (v1.1 §6). Hierarquia: Projeto v1.1 → Plano de Fase → prompt.
53. **Direção competitiva:** superar o TestComplete onde ele é fraco por design — verificação em camadas, legado desktop/Citrix, evidência auditável por step.
54. **Obrigatoriedade é do CENÁRIO, não do elemento.** O `objects/*.yaml` não carrega `criticidade`. Campo que o teste declara é preenchido e verificado ESTRITO; campo não declarado não é tocado.
55. **Baseline se mede com `pytest tests/unit -q`.** `testpaths = tests` no `pyproject.toml` faz `pytest` sem argumento coletar integração, que abre o SI3 real.
56. **Camada exata é propriedade da TELA, declarada e nunca inferida.** `tela.camada_exata: pyjab | playwright | nenhuma`; ausente = `nenhuma`. Obrigatória apenas em `lov` e `lov_lista`. **Corolário:** entregar tela nova em `objects/` inclui declarar `camada_exata`.
57. **Quando o OCR decide um LOV, o containment do `_similar` é desligado.**
58. **`vtae/core/` não importa `vtae/flows/`.** `_normalizar`/`_similar` vivem em `vtae/core/texto.py`. Tolerância do `_similar`: **0.230**.
59. **Confiança degradada é perda real, não ausência de recurso.** `degradado=True` só quando a tela DECLARA ter camada exata e ela não pôde ser usada.
60. **Aviso ao testador nunca rouba foco durante a execução.** Marcação no `StepResult`, faixa no `report.html`, resumo no console ao fim.
61. **Valor esperado de um check se conta, não se prevê.** Publicar esperado chutado destrói o próprio check. Atenção: `@pytest.mark.parametrize` com N valores conta como N testes, não 1 (erro cometido em 04/08 e de novo em 05/08).
62. **[NOVA v0.5.46] Ler o `VTAE_Projeto_v1.1.md` ANTES de desenhar qualquer peça — não só os arquivos de código que o prompt listar.** O §9 do prompt lista arquivos de código; isso não substitui a constituição. Desenhar uma peça sem abrir o v1.1 produziu, em 05/08, um formato de YAML inventado, aprovado de boa fé, digitado por Helio, e incompatível com o §4 do documento aprovado. Custo real: ~130 linhas de código e 12 testes jogados fora. A ordem é: v1.1 → prompt → arquivos de código → desenho.
63. **[NOVA v0.5.46] Um YAML de flow por MÓDULO, nunca por caso de teste.** A sequência varia muito menos que os casos: o cadastro min tem 1 sequência e 6 cenários (positivo/negativo × brasileiro/estrangeiro/naturalizado), todos rodando os mesmos steps. Os casos saem dos dados do `config.yaml` (regra 40). Mil testes cabem em dezenas de sequências, não em mil arquivos.
64. **[NOVA v0.5.46] Verbo do motor exige DOIS sistemas medidos.** Enquanto só um sistema mostra como uma ação funciona, ela é step nomeado. `abrir_modulo` saiu de `VERBOS_MOTOR` por isso: no SI3 é menu+pesquisa+popup+duplo clique, no MSI3 seria uma URL, e não há parte comum medida. Promove-se a verbo quando o teste web existir. É a regra 50 aplicada ao vocabulário do YAML.

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor. OpenCV, Playwright, EasyOCR, pyjab/JAB e oracledb (congelado) para sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — APEX).

- **Versão:** v0.5.46 · **Python:** 3.13+
- **Documento de referência:** **`docs/VTAE_Projeto_v1.1.md`**
- **Fase atual:** **Fase 2 — O MOTOR.** Peças 1, 2 e 3 CONCLUÍDAS. **Peça 4 EM ANDAMENTO:** o leitor do YAML de flow está pronto e testado; falta o executor.
- Fases 0 e 1: concluídas. Fase 3: Helio refaz os testes de admissão e o cadastro completo com o motor.

## 2. Estado dos flows

Inalterado. Os flows atuais continuam funcionando mas serão REFEITOS na Fase 3 — nenhum conserto neles, salvo pedido expresso de Helio.

## 3. O que foi feito em 05/08/2026 (v0.5.45 → v0.5.46)

Sessão com pasta conectada; `pytest` e `git` com Helio. **Baseline: 840/86 → 866/86** (+26 testes, nenhuma falha nova).

### 3.1 [FEITO] `esperar_janela_aparecer` — peça 2

Acrescentado a `vtae/core/motor/esperas.py`, simétrico ao `esperar_janela_sumir`, com 3 unitários em `tests/unit/test_esperas.py` (8 → 11 casos).

**Motivo medido:** dentro dos popups de nacionalidade, `esperar_visivel` cai na âncora da tela (`campo_nome_social`), que fica visível **atrás** do popup — a espera passaria verde sem o popup existir (regra 46). Os elementos `lov_lista` já declaram `titulo_janela` (`"Lista de UF"`, `"Lista de Ci"`, `"Lista de Pa"`); faltava o verbo.

A duplicação de 6 linhas com `esperar_janela_sumir` foi paga conscientemente — extrair helper mexeria em método já fechado (regra 7). Extrair quando houver o terceiro caso.

### 3.2 [ERRO GRAVE — vira regra 62] Peça 4 desenhada sem ler o v1.1

Claude leu os quatro arquivos de código que o §9 do v0.5.45 listava e **não abriu o `VTAE_Projeto_v1.1.md`**. Desenhou um formato de YAML de flow próprio (step com `id`/`nome`, verbos `clicar`/`esperar`/`verificar`/`python`, `elemento:`, `<<dados.X>>`/`sortear_de:`), apresentou como se fosse "o programado", Helio aprovou de boa fé e digitou ~130 linhas.

O v1.1 §4 (linhas 63-76) já definia outro formato desde 03/08. Os dois são incompatíveis: o `plano.py` daquele desenho rejeitaria o exemplo do próprio documento aprovado com `ConfigError: 'id' ausente`.

**O erro não era só de forma, era conceitual.** O desenho tinha `clicar: btn_ok_lov`, e o §4 linha 93 diz literalmente *"Nenhuma coordenada, nenhum sleep, nenhuma verificação manual dentro de teste"*. Traduzir o flow atual clique por clique é o oposto de declarar intenção — foi por isso que aquele YAML precisava de 4 dos 10 steps em Python, contra 1 no formato do v1.1.

**Custo:** `plano.py` e `test_plano.py` reescritos do zero. Helio pediu que Claude reescrevesse (erro de Claude não se paga com digitação de Helio).

### 3.3 [FEITO] `plano.py` — leitor do YAML de flow, formato v1.1

`vtae/core/motor/plano.py` + `tests/unit/test_plano.py` (23 casos). Lê, valida a forma e devolve estruturas; **não** executa, **não** interpola.

Formato aceito (idêntico ao v1.1 §4):

```yaml
flow: cadastro_paciente_min
objetos: objects/si3/cadastro_min.yaml

steps:
  - abrir_modulo: CADASTRO DE PACIENTE
  - preencher: { campo: nome,            valor: "{faker:nome}" }
  - preencher: { campo: data_nascimento, valor: "{faker:data_nascimento}" }
  - preencher: { campo: sexo,            valor: "{sorteio:sexo_opcoes}" }
  - preencher_nacionalidade: "{sorteio:nacionalidade_opcoes}"
  - preencher: { campo: cor_etnia,       valor: "{sorteio:cor_etnia_opcoes}" }
  - salvar: f10
  - ler_resultado: matricula
```

Cada step é um dicionário de UMA chave. `VERBOS_MOTOR = ("preencher", "salvar", "ler_resultado")`; qualquer outra chave é **step nomeado**, e a cobrança da função registrada acontece no executor. Por isso não existe "verbo desconhecido" no leitor.

### 3.4 [DECIDIDO] Cinco divergências do §4, aprovadas por Helio

| # | Divergência | Razão |
|---|---|---|
| D1 | Nacionalidade é **step nomeado**, não `preencher` | O §4 se contradiz: a linha 72 escreve `preencher: {campo: nacionalidade}`, o texto das linhas 95-96 manda step nomeado. Vale o texto — três popups não cabem num `preencher` |
| D2 | **Sem `id` no YAML.** `Step.id` é derivado da ordem (`S01`, `S02`…) | O v1.1 não declara id. Os `CM01`-`CM10` morrem com os flows antigos na Fase 3 |
| D3 | `criticidade` **não é lida** | Removida pela regra 54 na peça 1, com aprovação de Helio. O §4 linha 84 ainda a mostra — divergência preexistente |
| D4 | Verbo do motor = lista fechada; **qualquer outra chave é step nomeado** | v1.1 §4 linhas 95-96 |
| D5 | `abrir_modulo` **não** é verbo do motor | Vira regra 64 — ver 3.5 |

### 3.5 [FEITO] Três verbos, não quatro

Ao desenhar o executor, `abrir_modulo` se mostrou sem parte comum entre SI3 e MSI3. Saiu de `VERBOS_MOTOR` e virou step nomeado — **o YAML não muda uma vírgula**, só a classificação interna. Vira regra 64.

Verbos genéricos que sobraram, com o motivo de cada um ser genérico:

| verbo | por que é genérico |
|---|---|
| `preencher` | peça 2 resolve o locator; `tipo` do `objects/` decide a mecânica |
| `ler_resultado` | peça 3, `tipo: resultado`, polling |
| `salvar: f10` | o argumento **é** a mecânica (`f10` no Forms, um elemento no web) |

### 3.6 [MEDIDO] Diagnóstico de "framework sujo" levantado por Helio

Contagem real, não impressão:

| item | número | consumidores em produção |
|---|---|---|
| arquivos `.py` em `vtae/` | 73 (21 são `__init__.py`) | — |
| `core/dsl_interpreter.py` | 673 linhas | **zero** (só o próprio teste, com 30 casos) |
| `components/` | 6 arquivos | **zero** (só `test_login_component.py`) |
| `objects/cadastro_min.yaml` (antigo) vs `objects/si3/cadastro_min.yaml` (novo) | 2 arquivos, mesmo papel | antigo: 2 · novo: **zero** |

Conclusão: 52 módulos de código não é inchaço; o que produz a sensação é o **entulho registrado e nunca removido**. A limpeza está na peça 5, como o v1.1 previu. O `dsl_interpreter.py` é a **primeira** tentativa de mover a sequência para YAML e nunca ganhou consumidor — a peça 4 é a segunda, e as duas convivem no disco até a peça 5.

## 4. Pendências (todas rastreiam ao v1.1)

| # | Pendência | Fase v1.1 | Prioridade |
|---|---|---|---|
| 1 | **Peça 4 — desenho em português do executor**, antes de qualquer código | Fase 2, peça 4 | 🔴 próxima |
| 2 | Peça 4 — `flows/si3/cadastro_min.yaml` (o YAML do piloto) | Fase 2, peça 4 | 🔴 |
| 3 | Peça 4 — `steps.py` da tela: `abrir_modulo`, `preencher_nacionalidade`, `sair` | Fase 2, peça 4 | 🔴 |
| 4 | Peça 4 — gate 3x em tela real | Fase 2, peça 4 | 🔴 gate |
| 5 | Working tree acumulada: `summary_generator.py`, 2 `git rm` do MSI3 morto, `objects/si3/cadastro_min.yaml`, `esperas.py`+teste, `plano.py`+teste — commit com `git add` seletivo (regra 41) | Fase 2 | 🟡 |
| 6 | Comentário morto na linha 4 do `objects/si3/cadastro_min.yaml` (diz `tipo + criticidade`; criticidade saiu na v0.5.43) | Fase 2 | 🟢 1 palavra |
| 7 | Trocar o consumidor: flow e `tests/integration/si3/components/test_cadastro_paciente_min.py:63` ainda carregam `objects/cadastro_min.yaml` (antigo). **19 nomes mudaram** entre os dois arquivos (`campo_nome`→`nome`, `campo_sexo_lov`+`campo_sexo`→`sexo`…) — apontar o flow velho para o arquivo novo o quebraria | Fase 2, peça 4 | 🟡 |
| 8 | Faixa de avisos no `report.html` + resumo no console (regra 60) | Fase 2, peça 5 | 🟡 |
| 9 | `input_value` no `PlaywrightRunner` (camada exata web) | Fase 2, peça 5 | 🟡 |
| 10 | `ocr_engine: tesseract` no config do TipoAnestesia | Fase 2, peça 5 | 🟡 |
| 11 | Limpeza: `dsl_interpreter.py` + teste, `components/` + teste, `objects/cadastro_min.yaml` antigo | Fase 2, peça 5 | 🟡 |
| 12 | N de backspaces: decisão foi N fixo generoso (20) no motor | Fase 2, peça 4 | 🟡 |
| 13 | pyjab através de janela de popup — o leitor exato precisa trocar de janela? | Fase 3 | 🟢 |
| 14 | `lov_lista` dos popups de nacionalidade sem `jab_name` nem `regiao_ocr` | Fase 3 | 🟢 |
| 15 | `test_login_sislab.py` não registrado no CLI | Fase 3 | 🟢 |
| 16 | Names pyjab das admissões (AB06, AB09-AB12) | Fase 3 | 🟢 |
| 17 | Marcador `integration` para separar unit de tela real | Fase 3 | 🟢 |
| 18 | Aplicação Citrix candidata | Fase 4 | ⏳ Helio |
| 19 | Banco congelado até liberação InCor | — | ⏸ |

## 5. Campos do piloto que hoje NÃO podem ser verificados

Medido no `objects/si3/cadastro_min.yaml` — sem `regiao_ocr` e sem `jab_name`:

| caminho | campos cegos |
|---|---|
| sempre | `hora` |
| + BRASILEIRO | `estado_brasileiro`, `cidade_brasileiro` → **3** |
| + ESTRANGEIRO | `pais_estrangeiro`, `data_entrada_brasil`, `estado_estrangeiro`, `municipio_estrangeiro` → **5** |
| + NATURALIZADO | `pais_naturalizado`, `data_naturalizacao`, `nr_portaria` → **4** |

Verificáveis: 7 (`nome`, `data_nascimento`, `sexo`, `nacionalidade`, `cor_etnia`, `matricula`, `identificador`).

**Decisão tomada (05/08):** o motor verifica automaticamente todo campo que preenche, com dois pesos — na auto-verificação, `NAO_VERIFICAVEL` é **aviso**; `DIVERGENTE`/`VAZIO` é **falha**. Quando o teste pede verificação explicitamente, `NAO_VERIFICAVEL` passa a ser falha.

## 6. Tabela do motor — quem decide o quê (peça 3, implementada)

| `tipo:` no `objects/` | camada que decide | comparação | apoio |
|---|---|---|---|
| `lov`, `lov_lista` | exata (**obrigatória**) | igualdade após `_normalizar` | OCR, sem containment |
| `data` (máscara) | exata se houver locator; senão OCR | ≥ 6 dígitos, imune à ordem | — |
| `texto` | OCR | `_similar` 0.230, com containment | exata se houver |
| `resultado` | OCR | não-vazio | — |
| `botao` | nenhuma | — | `NAO_VERIFICAVEL` se chamado |

Veredito → consequência (contrato da peça 4):

| veredito | auto-verificação | `verificar` explícito |
|---|---|---|
| `OK` | passa | passa |
| `DIVERGENTE` / `VAZIO` | **falha** | **falha** |
| `NAO_VERIFICAVEL` | aviso | **falha** |
| `OK` + `degradado` | aviso | aviso |
| `OK` + `divergencia` | aviso | aviso |

## 7. Padrões Oracle Forms consolidados

Inalterados — ver v0.5.32 §7 e v0.5.45 §7.

## 8. Arquitetura

`vtae/` (cli, config, core, flows, runners, report, vision) + `objects/` + `configs/` + `templates/` + `tests/`.
Em `core/`: **`texto.py`**, **`object_repository.py`** e **`motor/`** (`resolvedor.py`, `esperas.py`, `verificacao.py`, **`plano.py`**).
A pasta **`flows/`** na raiz (para os YAML de flow, conforme v1.1 §4 linha 49) **ainda não existe** — nasce na peça 4.
`dsl_interpreter.py` e `components/` estão mortos e serão removidos na peça 5.

## 9. Próximo passo concreto (início do próximo chat)

1. **Claude lê PRIMEIRO o `docs/VTAE_Projeto_v1.1.md` inteiro** (regra 62), depois `vtae/core/motor/plano.py`, `resolvedor.py`, `esperas.py`, `verificacao.py` e `object_repository.py`. Zero proposta antes disso.
2. **Desenho em português do executor**, marcando explicitamente cada ponto em que ele diverge do §4 do v1.1 — para Helio aprovar item a item, e não descobrir a divergência três passos depois.
   Pontos que o desenho precisa fechar: como `preencher` usa o `tipo` do `objects/` para decidir a mecânica (`texto`/`data` → digita; `lov` → digita+TAB+`btn_ok`; `lov_lista` → F9+`campo_localizar`+ENTER+`btn_ok`+espera `titulo_janela` sumir); onde a interpolação `{faker:X}`/`{sorteio:X}` acontece (o executor, com `config.DADOS`); como o step nomeado é registrado e cobrado; como o `Veredito` vira `StepResult` conforme a tabela do §6.
3. Só depois: código, explicado, construído junto (regra 35).
4. Peça 5 (fixtures + limpeza + faixa de avisos) vem depois do gate 3x da peça 4.

---

**Marco desta sessão (05/08, v0.5.46):** a peça 4 começou, quebrou e foi refeita certo. O leitor do YAML de flow existe, no formato do documento aprovado, com 23 unitários. No caminho, um erro caro ficou registrado como regra 62 — Claude desenhou uma peça inteira sem ler a constituição do projeto, e Helio digitou código que foi jogado fora. A regra existe para que o próximo chat comece pela leitura certa.

**Resumo de Helio (regra 35):**
_"________________________________________"_
