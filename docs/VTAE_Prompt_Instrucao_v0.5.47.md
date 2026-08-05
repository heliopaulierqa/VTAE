# VTAE — Prompt de Instrução Geral do Projeto

**Data:** 05/08/2026 | **Versão:** v0.5.47
Use este documento como primeira mensagem no próximo chat.
Referência acima deste documento: **`docs/VTAE_Projeto_v1.1.md`** (APROVADO 03/08/2026) — a "constituição" do projeto.
Este prompt é registro operacional: onde paramos e o que fazer a seguir.

---

## 0. REGRAS DE TRABALHO — LEIA PRIMEIRO

**ESTAS REGRAS SÃO INEGOCIÁVEIS E NUNCA PODEM SER QUEBRADAS:**

1. NUNCA criar ou alterar arquivo sem que Helio veja o conteúdo atual primeiro.
2. NUNCA gerar arquivo completo sem receber o upload / ler o arquivo atual.
3. AGUARDAR O UPLOAD (ou ler o arquivo real) antes de gerar qualquer código.
4. Para alterações pontuais: informar exatamente ONDE e O QUE mudar.
5. NUNCA romper contrato/padrão estabelecido sem que Helio saiba e aprove.
6. NUNCA reescrever lógica de negócio de um flow — apenas as linhas solicitadas.
7. Flow validado e funcionando: qualquer mudança é CIRÚRGICA, com diff antes.
8. Antes de responder sobre falha: pesquisar o histórico.
9. Não propor soluções cosméticas — cada mudança responde uma das 5 perguntas de observabilidade.
10. Não circular — se uma abordagem falhou 2x, propor alternativa diferente.
11. Medir antes de confiar — `diagnose()` contra arquivo real antes da jornada.
12. Medir sensibilidade E especificidade dos templates.
13. Gerar arquivo completo SOMENTE quando Helio pedir expressamente.
14. Nenhum `.env` com comentário na mesma linha de um `VAR=valor`.
15. Mudanças de observabilidade são GATE: uma jornada por vez, 3x consecutivas.
16. Subprocessos do CLI sempre usam `sys.executable`.
17. `pyperclip.copy()` + Ctrl+V: delay ≥0.15s; 0.5s entre clique em campo e ação seguinte.
18. Templates SEMPRE via `pyautogui.screenshot()` + `PIL.crop()`.
19. `diagnose()`: para arquivo, sobrescrever `matcher._capture_screen`.
20. `regioes_ocr` no YAML exige espaço após dois pontos.
21. Coordenadas com janela maximizada; preferir template quando o elemento se desloca.
22. Dois `FlowContext` separados quando dois flows têm configs diferentes.
23. `_verify_campo_obrigatorio` / `_verify_campo_opcional` exigem `ocr_holder: list`.
24. Campos com reformatação automática NÃO usam valor exato via OCR.
25. `ocr_lido` propagado ao StepResult.
26. Popups são âncoras frágeis para guards genéricos; templates apertados de elemento conhecido são confiáveis quando medidos.
27. Campo Profissional em lista de procedimentos SI3: `_selecionar_via_lov`.
28. `max(numeros, key=len)` no OCR de campos com múltiplos números.
29. Cenário negativo em Forms tem duas falhas silenciosas: popup conhecido e match parcial em LOV.
30. Verificação pyjab é camada PARALELA ao OCR — exata, sem Levenshtein.
31. `JAVA_HOME` do pyjab setado via config, NUNCA via `setx`.
32. pyjab não substitui OCR/OpenCV/Playwright. Como ESCRITOR fica fora desta fase.
33. ~~Ambulatório como flow-modelo~~ — SUPERADA (v1.1 Decisão #6).
34. `DatabaseRunner`: CONGELADO por segurança do InCor.
35. **Padrão de aprendizado:** nenhum código sem que Helio explique o que faz e por quê. Diff em 3 partes (o quê / por quê / conceito Python). Desenho em português antes de código. Helio digita diffs pequenos. Fim de sessão: Helio resume em 2 frases.
36. Anti-especulação: medir e reverter empiricamente ANTES de gerar hipóteses.
37. Sandbox Linux pode estar indisponível — `git`/`pytest` com Helio.
38. O registro escrito não é a fonte de verdade — o disco é.
39. Argumento posicional casa por posição; campo novo em `@dataclass` entra no FIM.
40. **Separação por natureza:** locator em `objects/*.yaml`; dado de teste em `config.yaml`; segredo em `.env`.
41. **Gate fechado termina em commit.** diff → grep → pytest unit vs baseline → 3x tela real → commit.
42. Mock mente sobre o que tem: preferir **fake** a `MagicMock`.
43. Fontes idênticas não provam precedência.
44. Ao centralizar acesso a um dado, o grep obrigatório é pela FONTE.
45. **Tolerante embaixo, estrito em cima.** Tela é ambiente e degrada; configuração é defeito de escrita e explode antes do primeiro clique.
46. Guard nunca executado não é robustez.
47. Fonte única exige inventário.
48. Baseline de falhas é dívida registrada. **Baseline atual: 969 passed / 86 failed em `tests/unit`.**
49. **YAML declara, Python decide.**
50. **O motor cresce por demanda de teste real, não por antecipação.**
51. **Espera por condição, nunca por tempo.**
52. **Prompt operacional não cria escopo** (v1.1 §6).
53. **Direção competitiva:** superar o TestComplete onde ele é fraco por design.
54. **Obrigatoriedade é do CENÁRIO, não do elemento.**
55. **Baseline se mede com `pytest tests/unit -q`.**
56. **Camada exata é propriedade da TELA, declarada e nunca inferida.**
57. **Quando o OCR decide um LOV, o containment do `_similar` é desligado.**
58. **`vtae/core/` não importa `vtae/flows/`.** Tolerância do `_similar`: 0.230.
59. **Confiança degradada é perda real, não ausência de recurso.**
60. **Aviso ao testador nunca rouba foco durante a execução.**
61. **Valor esperado de um check se conta, não se prevê.** Errado 3x (04/08, 05/08 manhã, 05/08 tarde). **Correção mecânica obrigatória: `grep -c "^def test_"` no arquivo antes de publicar qualquer número.** Somar de cabeça é proibido.
62. **Ler o `VTAE_Projeto_v1.1.md` ANTES de desenhar qualquer peça.** Ordem: v1.1 → prompt → arquivos de código → desenho.
63. **Um YAML de flow por MÓDULO, nunca por caso de teste.**
64. **Verbo do motor exige DOIS sistemas medidos** — senão é step nomeado.
65. **[NOVA v0.5.47] `vtae/core/` não fala com `pyautogui` nem `pygetwindow`.** O core decide O QUE fazer; o runner faz COMO. Ação primitiva nova entra como método do `OpenCVRunner` (`click_xy`, `press`, `focar_janela`, `maximizar_janela`, `double_click_xy`), nunca como import dentro do motor. É o que mantém o motor testável com runner falso e o que vai permitir Citrix e web sem reescrever a decisão. **Dívida registrada:** o `esperas.py` ainda importa `pygetwindow` direto — inconsistência conhecida, a acertar quando aquele arquivo for tocado por outro motivo (regra 7).
66. **[NOVA v0.5.47] Campo pré-preenchido se VERIFICA, não se preenche.** O Nome do cadastro chega preenchido da tela de pesquisa; digitar por cima mudaria comportamento validado 3x. Daí o verbo `verificar: { campo, valor }`. **Corolário:** na verificação explícita, `NAO_VERIFICAVEL` é FALHA (na auto-verificação continua sendo aviso) — pedir prova e não conseguir lê-la significa que nada foi provado.
67. **[NOVA v0.5.47] Fatia não entrega stub.** Ao quebrar uma peça em fatias, a ordem tem que evitar que qualquer fatia deixe código morto ou caminho não exercitado (regra 46). Foi por isso que a mecânica (`acoes.py`) veio antes do executor, e não depois.
68. **[NOVA v0.5.47] O registro de steps nomeados é DECLARADO no YAML** (`steps_python: <modulo>`), nunca inferido do nome do flow nem injetado por convenção. Mesma razão da regra 56: "esqueci de declarar" e "esta tela não tem" precisam ser situações distinguíveis.
69. **[NOVA v0.5.47] Parâmetro que muda POLÍTICA, não cálculo, é parâmetro — não função nova.** `_aplicar(..., explicito=False)`: a leitura, a comparação e o veredito são idênticos; só a consequência de um status muda. Duplicar a função duplicaria a tabela do §6 em dois lugares.

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor. OpenCV, Playwright, EasyOCR, pyjab/JAB e oracledb (congelado) para sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — APEX).

- **Versão:** v0.5.47 · **Python:** 3.13+
- **Documento de referência:** **`docs/VTAE_Projeto_v1.1.md`**
- **Fase atual:** **Fase 2 — O MOTOR.** Peças 1, 2, 3 e **4 CONCLUÍDAS**. O piloto (YAML + `steps.py`) está escrito e validado contra os arquivos reais **sem tela**. Falta o gate 3x em tela real.
- Fases 0 e 1: concluídas. Fase 3: Helio refaz os testes de admissão e o cadastro completo com o motor.

## 2. Estado dos flows

Inalterado. Os flows atuais continuam funcionando mas serão REFEITOS na Fase 3 — nenhum conserto neles, salvo pedido expresso de Helio.

## 3. O que foi feito em 05/08/2026 (v0.5.46 → v0.5.47)

Sessão com pasta conectada; `pytest` e `git` com Helio; sandbox Linux indisponível (regra 37).
**Baseline: 866 → 969 (+103 casos, nenhuma falha nova).**

### 3.1 [FEITO] Peça 4 completa — seis fatias, cada uma medida antes da seguinte

| fatia | entrega | linhas | casos |
|---|---|---|---|
| 1 | `interpolacao.py` — `{faker:X}` / `{sorteio:X}` | 115 | 13 |
| 2 | `passo.py` — o `_step` do motor + `Coleta` | 126 | 18 |
| 3 | `validacao.py` — validação antecipada | 138 | 17 |
| 4 | `acoes.py` — mecânica por `tipo` | 161 | 16 |
| 5 | `executor.py` — o laço que junta tudo | 212 | 16 |
| 7 | verbo `verificar` (plano + validação + executor) | — | 13 |
| 8 | o piloto: YAML + `steps.py` + config | 38 + 219 | 2 |

Motor completo: **1.279 linhas em 9 arquivos**. Para comparação medida: os flows do SI3 somam **4.297 linhas em 9 arquivos**, e só o `cadastro_paciente_min_flow.py` tem 823.

### 3.2 [FEITO] O piloto existe e é coerente — provado sem abrir o SI3

`flows/si3/cadastro_min.yaml` (38 linhas) + `vtae/flows/si3/cadastro_min/steps.py` (219 linhas, ~70 de docstring) substituem as 823 linhas do flow atual. Sumiram: 48 `time.sleep`, 42 chamadas `pyautogui`, 33 resoluções de coordenada e a verificação escrita à mão campo a campo.

`tests/unit/test_piloto_cadastro_min.py` lê os **arquivos reais** (YAML do flow, `objects/si3/`, `steps.py`, `config.yaml`) e passa tudo pela validação antecipada. Um nome errado aparece em 30 segundos de `pytest`, não no meio de uma jornada com o SI3 aberto.

### 3.3 [DECIDIDO] D6–D18 aprovadas por Helio

| # | Decisão | Onde encostou |
|---|---|---|
| D6 | `steps_python:` no cabeçalho do YAML | vira regra 68 |
| D7 | `gerar_matricula` é step nomeado | `steps.py` |
| D8 | `sair` é step nomeado | `steps.py` |
| D9 | ~~Executor herda BaseFlow~~ **RETIRADA** — violaria a regra 58; virou `passo.py` (cópia) | `passo.py` |
| D10 | `StepResult.avisos: list[str]` | `result.py` |
| D11 | Transformação `data_ddmmaaaa` no schema; motor não mexe em dado | `schema.py` + config |
| D12 | ~~Sem verbo `verificar`~~ **SUPERADA por D18** | — |
| D13 | Motor não grava `estado_jornada.json` nesta peça | — |
| D14 | Chaves de mecânica no `objects/` (`btn_ok`, `campo_localizar`, `titulo_janela`) | preexistente |
| D15 | Sorteio cacheado por chave | `interpolacao.py` |
| D16 | `tela.titulo_janela` declarado; motor foca antes do F10 | `objects/` + `acoes.py` |
| D17 | Ações primitivas viram métodos do runner | vira regra 65 |
| D18 | **Verbo `verificar` nasce de caso real** (Nome pré-preenchido) | vira regra 66 |

### 3.4 [MEDIDO] A reclamação de Helio sobre "Frankenstein" — e o que ela mudou

Helio travou a sessão apontando arquitetura suja e falta de resultado visível. A medição deu razão a ele em parte:

- `vtae/core/dsl_interpreter.py` — **673 linhas, zero consumidores** (a primeira tentativa de YAML→teste, de antes do ObjectRepository);
- `vtae/components/` — 6 arquivos, zero consumidores;
- `objects/cadastro_min.yaml` (velho) e `objects/si3/cadastro_min.yaml` (novo) — mesmo papel, coexistindo, 19 nomes diferentes entre eles.

Ou seja: hoje o repo tem **duas** implementações de "YAML vira teste" e **dois** arquivos de objetos do mesmo cadastro. **Consequência da reclamação: a limpeza (peça 5) sobe na fila — entra logo depois do gate 3x, não no fim.**

O que não procede: o motor em si não é o entulho. O que confunde é a convivência de motor novo, flows velhos e código morto ao mesmo tempo.

### 3.5 [REGISTRADO] Mudanças de comportamento a olhar no gate

- Campo Localizar da LOV: era `Ctrl+A` + digitar, virou **backspace ×20**. Mecânica validada 3x sendo trocada — olhar no gate.
- `abrir_modulo` clica `btn_nao_popup` incondicionalmente (comportamento herdado do CM01).
- `nr_portaria` no config declara `args: "####/####"`, chave que o `DadoFakerConfig` **não tem** — ignorada em silêncio, o Faker gera `numerify()` sem argumento. Gap preexistente, valor válido, não bloqueia o gate.

## 4. Pendências (todas rastreiam ao v1.1)

| # | Pendência | Fase v1.1 | Prioridade |
|---|---|---|---|
| 1 | **Medir `tela.titulo_janela`** e trocar o `"MEDIR"` no `objects/si3/cadastro_min.yaml` | Fase 2, peça 4 | 🔴 bloqueia o gate |
| 2 | Teste de integração **provisório** (~20 linhas: login + `Executor`) — a fixture é a peça 5 | Fase 2, peça 4 | 🔴 |
| 3 | **Gate 3x em tela real** nos 3 caminhos de nacionalidade | Fase 2, peça 4 | 🔴 gate |
| 4 | Commit da árvore acumulada com `git add` seletivo (regra 41) | Fase 2 | 🟡 |
| 5 | **Limpeza:** `dsl_interpreter.py` + teste, `components/` + teste, `objects/cadastro_min.yaml` antigo | Fase 2, peça 5 | 🟡 subiu na fila (§3.4) |
| 6 | Fixtures `si3` / `msi3` — o teste de 3 linhas do v1.1 §4 | Fase 2, peça 5 | 🟡 |
| 7 | Faixa de avisos no `report.html` + resumo no console (regra 60) | Fase 2, peça 5 | 🟡 |
| 8 | `input_value` no `PlaywrightRunner` (camada exata web) | Fase 2, peça 5 | 🟡 |
| 9 | `ocr_engine: tesseract` no config do TipoAnestesia | Fase 2, peça 5 | 🟡 |
| 10 | `esperas.py` importa `pygetwindow` direto — inconsistência da regra 65 | Fase 2, peça 5 | 🟢 |
| 11 | `args:` do `DadoFakerConfig` não existe (§3.5) | Fase 2, peça 5 | 🟢 |
| 12 | Trocar o consumidor: flow antigo e teste de integração ainda usam `objects/cadastro_min.yaml` | Fase 3 | 🟡 |
| 13 | pyjab através de janela de popup | Fase 3 | 🟢 |
| 14 | `lov_lista` dos popups de nacionalidade sem `jab_name` nem `regiao_ocr` | Fase 3 | 🟢 |
| 15 | `test_login_sislab.py` não registrado no CLI | Fase 3 | 🟢 |
| 16 | Names pyjab das admissões (AB06, AB09-AB12) | Fase 3 | 🟢 |
| 17 | Marcador `integration` para separar unit de tela real | Fase 3 | 🟢 |
| 18 | Aplicação Citrix candidata | Fase 4 | ⏳ Helio |
| 19 | Banco congelado até liberação InCor | — | ⏸ |

## 5. Campos do piloto que hoje NÃO podem ser verificados

Inalterado (medido no `objects/si3/cadastro_min.yaml`): `hora` sempre; +2 no caminho BRASILEIRO; +4 no ESTRANGEIRO; +3 no NATURALIZADO. Verificáveis: 7.

**Consequência prática agora que o motor roda:** esses campos passam com **aviso** no `StepResult.avisos` (auto-verificação). Se algum dia forem declarados com `verificar:` no YAML, viram falha (regra 66).

## 6. Tabela do motor — quem decide o quê (peças 3 e 4, implementadas)

| `tipo:` no `objects/` | camada que decide | comparação | mecânica do `preencher` |
|---|---|---|---|
| `lov` | exata (**obrigatória**) | igualdade após `_normalizar` | digita · TAB · `btn_ok` |
| `lov_lista` | exata (**obrigatória**) | igualdade após `_normalizar` | F9 · espera janela · `campo_localizar` · ENTER · `btn_ok` · espera janela sumir |
| `data` | exata se houver locator; senão OCR | ≥ 6 dígitos | digita |
| `texto` | OCR | `_similar` 0.230, com containment | digita |
| `resultado` | OCR | não-vazio (polling) | não se preenche |
| `botao` | nenhuma | — | não se preenche |

Veredito → consequência:

| veredito | auto-verificação (`preencher`) | `verificar` explícito |
|---|---|---|
| `OK` | passa | passa |
| `DIVERGENTE` / `VAZIO` | **falha** | **falha** |
| `NAO_VERIFICAVEL` | aviso | **falha** (regra 66) |
| `OK` + `degradado` | aviso | aviso |
| `OK` + `divergencia` | aviso | aviso |

## 7. Padrões Oracle Forms consolidados

Inalterados — ver v0.5.32 §7. Acréscimo: ver §3.5 (Ctrl+A → backspace no campo Localizar).

## 8. Arquitetura

```
flows/si3/cadastro_min.yaml        ← NOVO: roteiro declarado (v1.1 §4)
objects/si3/cadastro_min.yaml      ← locators (regra 40)
configs/si3/.../config.yaml        ← dados de teste (regra 40)
templates/                         ← imagens
vtae/
  core/motor/   plano · interpolacao · validacao · acoes · esperas ·
                resolvedor · verificacao · passo · executor   (1.279 linhas)
  core/         texto · object_repository · result · context
  runners/      opencv (ganhou click_xy, press, focar_janela,
                maximizar_janela, double_click_xy) · playwright · database
  flows/si3/cadastro_min/steps.py  ← NOVO: o único Python específico da tela
```

**Nota sobre os dois "flows":** `flows/` na raiz é declaração (YAML de roteiro); `vtae/flows/` é código Python. A colisão de nome é temporária — na Fase 3 os flows Python são substituídos pelo motor e a pasta tende a virar `vtae/steps/`. Helio aprovou manter o nome do v1.1 §4 por ora.

`dsl_interpreter.py` e `components/` estão mortos e saem na peça 5.

## 9. Próximo passo concreto (início do próximo chat)

**Se o resumo de fechamento não saiu natural (ver abaixo), a sessão abre com um passeio pelo piloto** — os 14 steps do `flows/si3/cadastro_min.yaml`, um a um, Helio dizendo o que cada linha faz e Claude só confirmando ou corrigindo. Zero código novo. Só depois disso:

1. Helio mede o `titulo_janela` com o SI3 aberto:
   `python -c "import pygetwindow as gw; print([t for t in gw.getAllTitles() if t.strip()])"`
2. Teste de integração provisório (login + `Executor`), marcado como temporário.
3. Gate 3x em tela real, nos três caminhos de nacionalidade.
4. Commit (regra 41) e então a limpeza da peça 5.

---

**Marco desta sessão (05/08, v0.5.47):** a peça 4 fechou inteira — seis fatias, cada uma com desenho em português, aprovação, código e medição antes da seguinte. O piloto existe: 823 linhas viraram 38 de YAML mais 219 de Python, provadas coerentes contra os arquivos reais sem abrir o SI3. Nenhuma linha do motor tocou a tela ainda — até o gate 3x, é promessa. No caminho, Helio travou a sessão cobrando arquitetura limpa e resultado visível; a medição deu razão a ele quanto ao entulho (673 linhas mortas no `dsl_interpreter.py`, dois `objects/` do mesmo cadastro), e a limpeza subiu na fila.

**Resumo de Helio (regra 35):**
_"ajustes nos motores e criação dos artefatos que servirão a este motor"_

**Leitura do termômetro:** o resumo está certo no formato e genérico no conteúdo — "motores" e "artefatos" caberiam em qualquer sessão. Pela regra 35, a próxima sessão **revisita antes de avançar** (passeio pelo piloto, §9), a menos que Helio diga que a versão com substância abaixo é o que ele quis dizer:

> _"Fechamos o interpretador do YAML de flow: o motor lê um roteiro declarado, valida tudo antes do primeiro clique e verifica sozinho cada campo que preenche. E escrevemos o primeiro roteiro real — o cadastro mínimo em 38 linhas de YAML mais 219 de Python, provado coerente contra os arquivos do projeto sem abrir o SI3."_
