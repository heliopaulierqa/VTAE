# VTAE — Projeto v1.1

**Data:** 03/08/2026 · **Base:** Projeto v1 aprovado em 23/07/2026
**Status:** APROVADO por Helio em 03/08/2026.
**Substitui:** a proposta v1.1 de 29/07 (`VTAE_Projeto_v1.1_PROPOSTA.md`), que fica como registro histórico.

Este documento consolida a readequação decidida por Helio em 03/08/2026:
**o centro do projeto é o MOTOR — um framework onde qualquer teste é montado
com a menor quantidade possível de código e com o mesmo padrão em todos os testes.**
Tudo o mais se organiza ao redor disso.

---

## 1. Identificação — sem mudança em relação ao v1

Princípio central mantido: teste que executa sem validar resultado é script, não teste.
Versão do código nesta proposta: v0.5.41.

## 2. Problema que o VTAE resolve — sem mudança

## 3. O que JÁ EXISTE e está provado

Tudo do v1 continua valendo, mais o consolidado desde 23/07:

- Todos os flows migrados de `src/` para o pacote `vtae/`, organizados por domínio.
- `ObjectRepository` + `objects/cadastro_min.yaml` funcionando como fonte única de
  locators do CadastroPacienteMinFlow (coordenada, regiao_ocr, template, jab_name,
  titulo_jab). Nenhum locator no config.yaml nem hardcoded.
- Camadas provadas individualmente: OpenCV/template, EasyOCR, pyjab (3x, caso
  ALLIANZ), Playwright (MSI3). A matriz de decisão do v1 §6 segue válida.
- Suíte unitária com baseline conhecido (802 passed / 86 failed em 03/08).

**Constatação que motiva esta revisão:** apesar de tudo isso, montar um teste novo
hoje exige centenas de linhas. O CadastroPacienteMinFlow tem 823 linhas para
preencher 6 campos — 48 `time.sleep`, 42 chamadas `pyautogui`, 33 resoluções de
coordenada, verificação escrita à mão em cada campo, e ~20 linhas de boot+login
copiadas em cada arquivo de teste. O framework tem as camadas certas, mas **não
tem o motor que as monta**. O valor prometido no v1 §4 (campos declarados por
tipo, verificação automática) nunca foi entregue. Esta revisão coloca esse
entregável no centro.

## 4. Visão — reafirmada e tornada executável

A visão do v1 §4 não muda; ela vira contrato concreto. **Todo teste do VTAE terá
esta cara — e apenas esta cara:**

```python
def test_cadastro_paciente_min(si3):
    resultado = si3.executar("flows/si3/cadastro_min.yaml")
    assert resultado.success
```

```python
def test_tipo_anestesia(msi3):
    resultado = msi3.executar("flows/msi3/tipo_anestesia.yaml")
    assert resultado.success
```

O teste é **pré-montado**: 3 linhas em Python, o resto declarado em dois YAMLs.

**YAML de flow** — a montagem do teste (o que fazer, em ordem):

```yaml
flow: cadastro_paciente_min
objetos: objects/si3/cadastro_min.yaml

steps:
  - abrir_modulo: CADASTRO DE PACIENTE
  - preencher: { campo: nome,            valor: "{faker:nome}" }
  - preencher: { campo: data_nascimento, valor: "{faker:data_nascimento}" }
  - preencher: { campo: sexo,            valor: "{sorteio:sexo_opcoes}" }
  - preencher: { campo: nacionalidade,   valor: "{sorteio:nacionalidade_opcoes}" }
  - preencher: { campo: cor_etnia,       valor: "{sorteio:cor_etnia_opcoes}" }
  - salvar: f10
  - ler_resultado: matricula
```

**YAML de objetos** — cada campo declarado UMA vez, com tipo, criticidade e
todos os locators no mesmo registro (Modelo de Elemento do v1 §4, completo):

```yaml
sexo:
  tipo: lov                    # texto | data | lov | lov_lista | botao | resultado
  criticidade: obrigatorio     # obrigatorio -> falha | opcional -> avisa
  coordenada: { x: 648, y: 200 }
  regiao_ocr: { x1: 543, y1: 192, x2: 633, y2: 212 }
  jab_name: 'Descrição do Sexo.'
```

Um campo web é o mesmo registro com `seletor: "#P50_CODIGO"` — o motor decide
Playwright em vez de OpenCV. Um motor, dois mundos, um padrão.

Nenhuma coordenada, nenhum sleep, nenhuma verificação manual dentro de teste.
`tipo` decide COMO preencher e COMO verificar; `criticidade` decide se falha ou
avisa. Lógica de negócio real (ex.: Nacionalidade com 3 sub-popups) vira step
nomeado (`preencher_nacionalidade:`) — o único código específico que sobra.

## 5. Fases — renumeradas a partir desta revisão

### Fase 0 — Piloto do Modelo de Elemento — **CONCLUÍDA**

O contrato do v1 foi cumprido: ObjectRepository + objects/cadastro_min.yaml +
gate 3x sem regressão. As sub-fases criadas nos prompts operacionais (0.3
conftest, 0.4 simplificação) **ficam canceladas** — o que elas pretendiam
resolver é absorvido pela Fase 2 (fixtures e reescrita fazem parte do motor).

### Fase 1 — Extração do Core — **CONCLUÍDA (com restos registrados)**

Todo o código vive em `vtae/`. Restos que NÃO bloqueiam o motor e ficam para a
futura fase de desacoplamento: renomeações de fronteira (`SI3_JAB_HOME_FAKE` →
`VTAE_JAB_HOME`, `_focar_si3` → `focus_window`), grep de desacoplamento
(`grep -ri "si3|incor" vtae/` vazio).

### Fase 2 — O MOTOR — **fase atual (esta revisão a define)**

Absorve e amplia a antiga Fase 2 (resolvedor multi-locator): o resolvedor é o
coração do motor, não uma fase isolada.

**Peças do motor (ordem de construção — uma por vez, cada uma testável sozinha):**

| # | Peça | O que entrega |
|---|---|---|
| 1 | YAML de objetos com `tipo`/`criticidade` | Locators de um mesmo campo unificados num registro só (fim do par `campo_sexo_lov`/`campo_sexo`); mecânico, Helio cola |
| 2 | Ações por tipo + resolvedor multi-locator | `preencher(campo, valor)` única; mecânica (click/backspace/digitar/F9/TAB/OK/esperas) decidida pelo `tipo`; locator decidido na ordem jab → template → coordenada → seletor web, **logando qual estratégia resolveu** (gate herdado do v1 Fase 2) |
| 3 | Verificação por tipo | A matriz do v1 §6 vira tabela do motor: lov/lov_lista → pyjab exato + OCR evidência; data/máscara → pyjab ou estrutura (mín. dígitos); texto → OCR Levenshtein 30%; resultado → polling. `criticidade` decide falha × aviso. Screenshot sempre (pyjab prova o que o sistema TEM; screenshot prova o que o usuário VÊ) |
| 4 | Interpretador do YAML de flow | Lê os `steps:` e executa via peças 2-3. O `dsl_interpreter.py` existente NÃO é a base — nasceu antes do ObjectRepository e do pyjab; será substituído e removido |
| 5 | Fixtures `si3` e `msi3` | Login como pré-condição declarada: boot + login + contexto pronto num lugar só (elimina as ~20 linhas copiadas em cada teste). Todo teste SI3/MSI3 recebe a fixture |
| 6 | Os dois testes-padrão | `test_cadastro_paciente_min` (desktop) e `test_tipo_anestesia` (web), escritos DO ZERO no padrão de 3 linhas — o molde de todos os testes futuros |

**Pilotos (Decisão #7 do v1.1 de 29/07 — TOMADA):** CadastroPacienteMinFlow
(desktop) e TipoAnestesiaFlow (web). O AdmissaoAmbulatorioFlow **não** será o
piloto — decisão de Helio, 03/08. O motivo original do v1 (único flow com os 3
ramos de locator) envelheceu: o cadastro_min.yaml hoje tem coordenada, template
e jab_name. O Ambulatório permanece como referência técnica do pyjab validado
3x; será reescrito com o motor na Fase 3.

**Gate de saída da Fase 2:** os dois testes-padrão rodando 3x consecutivas sem
regressão, com log mostrando qual locator resolveu cada elemento, e o teste
inteiro (Python) com no máximo ~5 linhas. Comparação registrada: 823 linhas → N.

**Pré-requisito técnico (pequeno, dentro da Fase 2):** a coleta de
`tests/integration` aborta hoje por código morto do MSI3
(`test_frequencia_aplicacao.py` importa flow inexistente; `login_config.py`
carrega config em tempo de import). Sem coleta, a fixture da peça 5 não roda.
Remoção dos mortos entra como primeiro passo da peça 5.

**Limitação registrada (sem promessa falsa):** `vtae run --jornada` executa cada
teste em subprocess separado — a fixture elimina duplicação de código, mas não
faz login único por jornada. Tratável depois, se incomodar.

### Fase 3 — Reescrita dos testes com o motor

Decisão de Helio (03/08): **os testes existentes serão refeitos, não aproveitados.**
Quando o motor estiver ok (gate da Fase 2 fechado), Helio refaz, nesta ordem de
intenção declarada: testes de admissão e o teste completo de cadastro. Cada
teste reescrito segue o padrão dos dois pilotos e fecha gate 3x próprio.

Consequência imediata: **manutenção dos testes legados perde prioridade.**
Falhas do baseline unitário ligadas a testes que serão refeitos
(ex.: `test_cadastro_paciente_flow.py` com 27 steps esperados vs 4 reais) não
serão consertadas — morrem com a reescrita.

### Fase 4 — Cliente 2 (Citrix) · Fase 5 — Recorder-rascunho · Fase 6 — Tooling

Contratos idênticos às antigas Fases 3, 4 e 5 do v1, apenas renumeradas.
O Recorder ganha sentido novo: com o motor pronto, gravar = gerar YAML de
objetos + YAML de flow — não esqueleto de Python.

## 6. Método de trabalho — mantido, com dois reforços

Tudo do v1 §6 continua (nenhum código sem que Helio explique; diff em 3 partes;
desenho antes de código; Helio digita diffs pequenos; velocidade cede à absorção).

Reforços incorporados desta revisão:

1. **Prompt operacional não cria escopo.** A hierarquia é Projeto → Plano de
   Fase → prompt. Pendência listada num prompt que não rastreia até uma fase
   deste documento é sugestão, não trabalho — precisa de decisão explícita de
   Helio para virar tarefa.
2. **Sem escopo novo por resposta.** O trabalho de cada fase é lista fechada.
   Item fora da lista = nova decisão de Helio, não iniciativa do assistente.

## 7. Fora de escopo / congelado — sem mudança

Banco congelado (segurança InCor); pyjab-escritor spike futuro; sem "IA de
marketing"; sem mobile. Acréscimo: **testes legados não serão mantidos** (§5,
Fase 3) — ficam funcionando até serem substituídos, mas não recebem conserto.

## 8. Decisões

| # | Decisão | Status |
|---|---|---|
| 1 | Anteprojeto → Projeto v1 | ✅ 23/07/2026 |
| 2 | Regra de aprendizado no prompt | ✅ v0.5.32 |
| 3 | Aplicação Citrix candidata (Fase 4) | ⏳ Helio |
| 4 | Nome público do framework | ⏳ Helio |
| 5 | Proposta v1.1 de 29/07 | Superada por este documento |
| 6 | Pilotos do motor: CadastroMin (desktop) + TipoAnestesia (web); Ambulatório fora | ✅ Helio, 03/08/2026 |
| 7 | Testes existentes serão refeitos com o motor, não aproveitados | ✅ Helio, 03/08/2026 |
| 8 | Login vira fixture (`si3` / `msi3`) para todos os testes | ✅ Helio, 03/08/2026 |
| 9 | **Aprovar este documento (vira Projeto v1.1)** | ✅ Helio, 03/08/2026 |

## 9. Riscos

Todos os do v1 mantidos, mais:

| Risco | Mitigação |
|---|---|
| Prompts operacionais voltarem a criar escopo próprio (ocorreu entre 23/07 e 03/08 — sub-fases 0.1–0.4 sem lastro no v1) | §6 reforço 1: rastreabilidade obrigatória até uma fase deste documento |
| Motor genérico demais tentando cobrir casos que são lógica de negócio | Contrato do §4: negócio real vira step nomeado, não parâmetro do motor |
| Reescrever os pilotos e o motor ao mesmo tempo esconder qual dos dois falhou | Peças 1-5 testáveis isoladamente; pilotos só entram na peça 6 |

## 10. Estado atual e próximo passo

**Fase atual:** Fase 2 (Motor) — abre quando Helio aprovar este documento.

**Pendência de working tree:** uma edição já aplicada em 03/08
(`summary_generator.py` — remoção da linha do teste morto `test_frequencia_aplicacao`).
Entra no primeiro commit da peça 5 junto com a remoção dos arquivos mortos do MSI3.

**Próximo passo concreto após o "aprovado":**
1. Peça 1 — Claude entrega o `objects/si3/cadastro_min.yaml` reescrito com
   `tipo`/`criticidade` e campos unificados (bloco mecânico — Helio cola).
2. Peça 2 — desenho em português do `preencher()` + resolvedor, "faz sentido"
   de Helio, então código construído junto (regra de aprendizado).
3. Uma peça por vez. Nenhuma peça avança sem a anterior fechada.
