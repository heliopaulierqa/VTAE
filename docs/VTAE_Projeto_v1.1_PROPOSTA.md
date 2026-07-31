# VTAE — Projeto v1.1 (PROPOSTA — aguardando validação de Helio)

**Data da proposta:** 29/07/2026 · **Base:** Projeto v1 aprovado em 23/07/2026 (v0.5.31)
**Status:** PROPOSTA — nada neste documento foi aplicado. Nenhum código muda antes da validação.

Convenções desta proposta:
- Texto sem marcação = igual ao Projeto v1, continua valendo.
- **[FEITO]** = concluído desde 23/07, verificado contra o código real.
- **[PARCIAL]** = começou, não fechou gate ou tem lacuna identificada.
- **[PENDENTE]** = não iniciado.
- **[CONSTATAÇÃO]** = fato novo descoberto na auditoria de 29/07 que o v1 não previa.
- **[A CONFIRMAR]** = depende de informação que só Helio tem.

---

## 0. A constatação central desta revisão

**[CONSTATAÇÃO]** Entre 23/07 e 29/07, o trabalho executado foi majoritariamente a
**Fase 1 (Extração do Core)** — migração de todos os flows de `src/` para o pacote
`vtae/`, organizados por domínio, com testes unitários novos e baseline preservado
(799 passando / 89 falhas pré-existentes).

Porém: **a Fase 1 foi executada sem Plano de Fase aberto, e com a Fase 0 ainda
incompleta.** O Projeto v1 diz "ordem obrigatória, gate entre cada" — isso não foi
respeitado na prática. Esta proposta regulariza a situação: reconhece o que foi
feito, nomeia o que ficou para trás, e devolve o projeto ao trilho de fases.

---

## 1. Identificação — sem mudança

Única atualização: versão do código na aprovação do v1 era v0.5.31; a versão
operacional atual é **[A CONFIRMAR — Helio informa o número que quer registrar]**.

## 2. Problema que o VTAE resolve — sem mudança

## 3. O que JÁ EXISTE e está provado — atualizado

Tudo do v1 continua valendo. Acréscimos verificados em 29/07:

- **[FEITO]** Todos os flows migrados para `vtae/flows/`, por domínio:
  `si3/login/`, `si3/cadastro/`, `si3/cadastro_min/`, `si3/admissao/`,
  `si3/agendamento/`, `sislab/login/`, `sislab/cadastro_funcionario/`,
  `msi3/login/`, `msi3/tipo_anestesia/`, `msi3/cadastro_orientacao/` + `msi3/apex_helper.py`.
- **[FEITO]** Suíte unitária: 799 testes passando; baseline de 89 falhas
  pré-existentes inalterado (zero regressões da migração). ~200 testes novos
  escritos no padrão comportamental (sucesso + falha por step).
- **[FEITO]** Gate GUI do módulo admissão: 3 jornada tests × 3x, sem falha.
- **[FEITO]** Limpezas: componente morto do SisLab deletado; arquivo com acento
  no nome renomeado (`cadastrar_orientação_flow.py` → `cadastrar_orientacao_flow.py`);
  imports de 6 testes de integração corrigidos.
- **[CONSTATAÇÃO]** O "flow-modelo AdmissaoAmbulatorioFlow" continua sendo a única
  referência com pyjab validado — mas por decisão de Helio (sessão 29/07), o ponto
  de **consolidação do padrão** passa a ser o CadastroPacienteMinFlow (ver §5, Fase 0).
  O Ambulatório permanece como referência técnica do pyjab, não como molde.

## 4. Visão — sem mudança

Reafirmada por Helio em 29/07 com ênfase: o objetivo é **criar um teste novo com o
mínimo de código possível** — campos declarados por TIPO (texto, lista, data), com a
camada de verificação decidida automaticamente pelo tipo, não escrita à mão em cada
step. O modelo de referência é o TestComplete. O SI3 é oportunidade de evolução,
não o dono do framework.

## 5. Fases — estado real em 29/07

### Fase 0 — Piloto do Modelo de Elemento — **[PARCIAL]** (segue ABERTA)

| Item | Estado |
|---|---|
| ObjectRepository + `objects/cadastro_min.yaml` | **[FEITO]** — existe e funciona |
| CM01–CM10 usando `ctx.objects` | **[PARCIAL]** — 8 de 10 steps migrados; **CM06 e CM08 ainda usam `self._coord()`** (forma antiga) no mesmo arquivo |
| Camada pyjab no piloto | **[PENDENTE]** — nenhum step do CadastroMin usa `_verify_campo_via_jab` (o helper existe pronto no BaseFlow, validado 3x no Ambulatório) |
| Gate de saída (3x sem regressão) | **[A CONFIRMAR]** — Helio confirma se houve rodada 3x APÓS a introdução do ObjectRepository |

**Trabalho restante da Fase 0 (lista fechada, sem escopo novo):**
1. CM06 e CM08: trocar `self._coord()` por `ctx.objects.coord()` — mudança mecânica.
2. Adicionar `_verify_campo_via_jab` nos 3 campos LOV (CM06 Sexo, CM07 Nacionalidade,
   CM08 Cor/Etnia) — chamar o helper existente, não criar nada.
3. Rodar 3x consecutivas → gate fecha → **Fase 0 encerra com o padrão completo
   (OpenCV + OCR + pyjab + ObjectRepository) num único flow pequeno e legível.**

### Fase 1 — Extração do Core — **[PARCIAL]** (executada fora de ordem)

| Item | Estado |
|---|---|
| Flows extraídos para `vtae/` | **[FEITO]** (ver §3) |
| `core/`, `vision/`, `runners/`, `report/` em `vtae/` | **[FEITO]** (sessões anteriores) |
| Restos em `src/` | **[PARCIAL]** — permanecem: `src/config/` (loader, schema), `src/cli/` (run, send, summary), `src/components/` (3 componentes), `src/core/object_repository.py` (não migrado por regra — exige confirmação explícita), `src/runners/database_runner.py` (congelado) |
| **[CONSTATAÇÃO]** 4 flows duplicados ainda em `src/flows/` | agendamento, login_si3, login_sislab, cadastro_funcionario_sislab — versão oficial já está em `vtae/`, deleção nunca foi solicitada (falha de verificação com caminho relativo, corrigida em 29/07) |
| **[CONSTATAÇÃO]** 2 imports quebrados em `vtae/core/dsl_interpreter.py` | branch sislab aponta para módulo que nunca existiu; fallback genérico aponta para módulo inexistente |
| Grep de desacoplamento (`grep -ri "si3\|incor" vtae/`) | **[PENDENTE]** — não executado; sabidamente não passaria hoje (nomes como `_focar_si3` seguem no BaseFlow) |
| Renomeações de fronteira (SI3_JAB_HOME_FAKE → VTAE_JAB_HOME, `_focar_si3` → `focus_window`) | **[PENDENTE]** |

### Fase 2 — Resolvedor multi-locator — **[PENDENTE]**

**[A DECIDIR — Helio]** O v1 fixava o piloto no AdmissaoAmbulatorioFlow (único com
pyjab 3x). Se a Fase 0 terminar com pyjab no CadastroMin (item 2 da lista acima),
o CadastroMin passa a exercitar os 3 ramos (jab → template → coordenada) e vira
candidato natural a piloto da Fase 2 também — flow menor, mais rápido de rodar.
Decisão registrada aqui para o Plano da Fase 2, não precisa ser tomada agora.

### Fase 3 — Cliente 2 (Citrix) — **[PENDENTE]** — aplicação candidata segue sem escolha (§8)

### Fase 4 — Recorder-rascunho — **[PENDENTE]**

### Fase 5 — Tooling do repositório — **[PENDENTE]**

## 6. Método de trabalho — reforçado

Tudo do v1 continua. Dois reforços acordados em 29/07:

- **Validação documental antes de execução:** nenhuma mudança de código começa sem
  que Helio tenha validado antes o documento/desenho que a descreve. (Já era o
  espírito do "desenho antes de código"; agora é regra explícita, incluindo
  atualizações deste próprio projeto.)
- **Sem escopo novo por resposta:** o trabalho restante de cada fase é uma lista
  fechada registrada no Plano da Fase. Item fora da lista = nova decisão de Helio,
  não iniciativa unilateral.

## 7. Fora de escopo / congelado — sem mudança

(Banco congelado; pyjab-escritor spike futuro; sem "IA de marketing"; sem mobile.)

## 8. Decisões — atualizada

| # | Decisão | Status | Bloqueia |
|---|---|---|---|
| 1 | Aprovar anteprojeto → Projeto v1 | ✅ 23/07/2026 | — |
| 2 | Regra de aprendizado no prompt | ✅ v0.5.32 | — |
| 3 | Aplicação Citrix candidata | ⏳ Helio | Fase 3 |
| 4 | Nome público do framework | ⏳ Helio | publicação |
| 5 | **Aprovar esta revisão v1.1** | ⏳ Helio | tudo abaixo |
| 6 | Ordem de retomada (ver §10) | ⏳ Helio | próxima sessão |
| 7 | Piloto da Fase 2 (Ambulatório × CadastroMin) | ⏳ Helio — decidir na abertura da Fase 2 | Fase 2 |
| 8 | Bug real CP04 (`test_cadastro_paciente_flow`, ~82 falhas do baseline): corrigir quando? | ⏳ Helio | — |

## 9. Riscos — um acréscimo

| Risco | Mitigação |
|---|---|
| (todos os do v1 — mantidos) | |
| **[NOVO]** Fases executadas fora de ordem geram sensação de bagunça e perda de entendimento (ocorreu entre 23–29/07) | §6 reforçado: validação documental antes de execução + lista fechada por fase; nenhuma fase avança sem a anterior gated |

## 10. Estado atual e próximo passo — proposta para decisão de Helio

**Fase atual:** Fase 0 — ABERTA (com Fase 1 parcialmente adiantada fora de ordem).

**Ordem de retomada proposta** (Helio aprova, altera ou reordena):

1. **Higiene imediata** (sem lógica, só limpeza): deletar os 4 flows duplicados de
   `src/flows/`; corrigir os 2 imports quebrados do `dsl_interpreter.py`.
   Risco zero, fecha a porta da confusão src/vtae.
2. **Fechar a Fase 0** com a lista de 3 itens do §5 — termina com o padrão completo
   demonstrado num flow só.
3. **Regularizar a Fase 1**: abrir o Plano da Fase 1 retroativo, listar o que resta
   (`src/config`, `src/cli`, componentes, renomeações de fronteira, grep de
   desacoplamento) e fechar item a item com gate.
4. Só então: Fase 2 em diante, na ordem do v1.
5. **Registro de radar** (compromissos já assumidos, sem data): bootstrap dos
   jornada tests; refazer testes do zero com o padrão consolidado (pedido de Helio,
   29/07 — "concluir o que estamos fazendo e depois fazer os testes do zero com os
   padrões"); Record & Replay (Fase 4).

**Nada desta lista começa antes do "sim" de Helio a este documento.**
