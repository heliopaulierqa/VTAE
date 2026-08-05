# VTAE — Prompt de Instrução Geral do Projeto
**Data:** 04/08/2026 | **Versão:** v0.5.42
Use este documento como primeira mensagem no próximo chat.
Referência acima deste documento: **VTAE_Projeto_v1.1.md** (APROVADO 03/08/2026) — a "constituição" do projeto. Substitui o v1 como referência.
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
32. pyjab não substitui OCR/OpenCV/Playwright — complementa.
33. ~~AdmissaoAmbulatorioFlow como flow-modelo~~ — **SUPERADA pelo v1.1 (Decisão #6):** pilotos do motor são CadastroPacienteMinFlow (desktop) e TipoAnestesiaFlow (web). O Ambulatório permanece referência técnica do pyjab 3x; será reescrito na Fase 3.
34. `DatabaseRunner`: CONGELADO por segurança do InCor até liberação.
35. **Padrão de aprendizado:** nenhum código sem que Helio explique o que faz e por quê. Diff em 3 partes (o quê / por quê / conceito). Desenho em português antes de código. Helio digita diffs pequenos; colar reservado a blocos mecânicos. Fim de sessão: Helio resume em 2 frases.
36. Anti-especulação: diante de falha, medir e reverter empiricamente ANTES de gerar hipóteses.
37. Sandbox Linux pode estar indisponível — trabalho via pasta conectada; `git`/`pytest` com Helio. PowerShell: sem `grep`; usar `Get-ChildItem -Recurse -Include *.py | Select-String "padrao"`, envolver em `(...).Count`.
38. O registro escrito não é a fonte de verdade — o disco é. Ler o arquivo real antes de aceitar pendência de prompt antigo. **Corolário (04/08): vale também para o Projeto — pendência de prompt que não rastreia até uma fase do Projeto v1.1 é sugestão, não trabalho.**
39. Argumento posicional casa por posição; campo duplicado em `@dataclass` sobrescreve default sem criar campo. Verificar com grep após edição de assinatura.
40. Separação por natureza: **locator** em `objects/*.yaml` (muda com a TELA); **dado de teste** em `config.yaml` (muda com o CENÁRIO); **segredo** em `.env` (muda com a MÁQUINA).
41. **Gate fechado termina em commit.** diff → grep → pytest unit vs baseline → 3x tela real → commit (mensagem registra o gate). Mensagem multi-linha: `git commit -F arquivo.txt`.
42. Mock mente sobre o que tem: código em `BaseFlow` que lê atributo opcional de `ctx` valida a FORMA do valor, não só a existência.
43. Fontes idênticas não provam precedência; fonte única removida dispensa perturbação.
44. Ao centralizar acesso a um dado, o grep obrigatório é pela FONTE, não pelo helper; quando grep não explica resultado, a prova é `git stash` + rodar de novo.
45. Tolerante embaixo, estrito em cima: resolvedor devolve `None`; quem chama decide se é fatal, campo a campo.
46. Guard nunca executado não é robustez — conferir que o arquivo do template EXISTE.
47. Fonte única exige inventário: chaves órfãs no `objects/` só aparecem por inventário manual (Fase 6, tooling).
48. Baseline de falhas é dívida registrada, não contrato: nenhum teste que passava pode falhar; melhora no número exige causa nominal. Baseline atual: **802 passed / 86 failed**. *(Nota v1.1: falhas ligadas a testes legados que serão refeitos na Fase 3 perdem prioridade — morrem com a reescrita.)*
49. **[NOVA v0.5.42] YAML declara, Python decide.** O YAML de flow NUNCA ganha `if`, loop ou variável — no dia em que ganhar, viramos uma linguagem de programação ruim (a morte do `dsl_interpreter` antigo e a doença crônica dos frameworks keyword-driven). Lógica de negócio real (ex.: Nacionalidade com 3 sub-popups) vira step nomeado em Python, nunca parâmetro do motor.
50. **[NOVA v0.5.42] O motor cresce por demanda de teste real, não por antecipação.** Dois pilotos definem o escopo; tipo de campo, ação ou verificação nova só entra quando um teste real exigir. Generalizar para caso hipotético é dívida, não robustez.
51. **[NOVA v0.5.42] Espera por condição, nunca por tempo.** Princípio de nascimento do motor: esperar título de janela, template visível ou estado pyjab (is_enabled/is_showing) — jamais `time.sleep` como mecanismo primário. Sleep fixo só como último recurso, documentado com o motivo. Os 48 sleeps do flow atual são a maior fonte de flakiness e não podem ser reproduzidos no motor.
52. **[NOVA v0.5.42] Prompt operacional não cria escopo** (v1.1 §6). A hierarquia é Projeto v1.1 → Plano de Fase → prompt. Sub-fases inventadas em prompts (ex.: 0.3/0.4, canceladas em 03/08) não se repetem. Sem escopo novo por resposta: item fora da lista fechada da fase = decisão de Helio, não iniciativa.
53. **[NOVA v0.5.42] Direção competitiva:** superar o TestComplete onde ele é fraco por design — verificação em camadas, legado desktop/Citrix, evidência auditável por step — e não persegui-lo recurso a recurso. Record & replay (Fase 5) vem por último: gravar = gerar YAML de objetos tipados + YAML de flow, nunca script cego.

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor (São Paulo). OpenCV, Playwright, EasyOCR, pyjab/JAB e oracledb (congelado) para sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — APEX).

- **Versão:** v0.5.42 · **Python:** 3.13+
- **Documento de referência:** **VTAE_Projeto_v1.1.md** (aprovado 03/08/2026)
- **Fase atual:** **Fase 2 — O MOTOR.** Contrato: todo teste com a cara de 3 linhas (`def test_x(si3): resultado = si3.executar("flows/..."); assert resultado.success`), montado em dois YAMLs (flow + objetos tipados). 6 peças, uma por vez. Pilotos: CadastroMin (desktop) + TipoAnestesia (web). Login como fixture (`si3`/`msi3`).
- Fases 0 e 1: CONCLUÍDAS (v1.1 §5). Sub-fases 0.3/0.4 dos prompts antigos: CANCELADAS.
- Fase 3 (após motor ok): Helio refaz os testes de admissão e o cadastro completo com o motor. Testes legados NÃO recebem manutenção até lá.

## 2. Estado dos flows

Tabela do v0.5.32 segue como registro histórico. Com o v1.1: os flows atuais continuam funcionando mas serão REFEITOS na Fase 3 — nenhum conserto neles, salvo pedido expresso de Helio.

## 3. O que foi feito na sessão de 04/08/2026 (v0.5.41 → v0.5.42)

Sessão sem sandbox Linux (4ª vez) — trabalho via pasta conectada.

### 3.1 [DECISÃO] Correção de rumo — origem desta versão
Helio constatou que as sub-fases 0.3/0.4 e as pendências dos prompts não rastreavam até o Projeto v1 — escopo criado por prompts operacionais, invertendo a hierarquia. Decisões: manter só o que rastreia ao Projeto; CadastroMin + TipoAnestesia como testes-padrão; login como fixture; testes legados serão refeitos, não aproveitados; o centro do projeto é o MOTOR (menor quantidade de código possível, mesmo padrão em todos os testes, desktop e web).

### 3.2 [FEITO] Projeto v1.1 redigido e APROVADO (03/08)
`docs/VTAE_Projeto_v1.1.md` — substitui o v1 como constituição. Consolida: Fases 0/1 concluídas; Fase 2 = Motor (6 peças); Fase 3 = reescrita dos testes; Fases 4-6 = Citrix, Recorder, Tooling (renumeradas); Decisões #6-#9 tomadas. A proposta v1.1 de 29/07 vira registro histórico.

### 3.3 [FEITO] Peça 1 do motor entregue — aguardando "faz sentido" de Helio
`objects/si3/cadastro_min.yaml` criado (pasta `objects/si3/` é NOVA; o antigo `objects/cadastro_min.yaml` está INTACTO e segue sendo o usado pelo flow validado). Conteúdo: mesmos locators validados, reorganizados com `tipo` + `criticidade`; pares partidos unificados (`campo_sexo_lov`+`campo_sexo` → `sexo`; idem `cor_etnia`); LOVs referenciam botões auxiliares (`btn_ok:`); 3 `btn_localizar_lov_*` removidos (código morto — regra 46/47, o padrão usa ENTER). Pontos a validar por Helio: classificações `opcional` em `hora`, `data_entrada_brasil` e campos dos sub-popups (o flow atual não os verifica — trocar a palavra se forem obrigatórios de negócio).

### 3.4 [PARCIAL] Limpeza MSI3 — absorvida pela peça 5
Medição da sessão: `test_frequencia_aplicacao.py` importa `FrequenciaAplicacaoFlow`, que NÃO EXISTE no repositório (grep confirmado) — a causa da coleta abortar não é só o config faltante; o arquivo é morto na íntegra. `configs/msi3/login_config.py` tem esse teste como único consumidor (também morto; carrega config em tempo de import — conceito: import é execução). **Estado da working tree:** linha `test_frequencia_aplicacao` do `summary_generator.py` JÁ REMOVIDA (edição aplicada); os dois `git rm` NÃO executados. Tudo entra no primeiro commit da peça 5 (pré-requisito da fixture: sem coleta limpa, conftest não roda).

### 3.5 [CONTEXTO] Avaliação de direção
Claude confirmou a direção (elemento tipado + repositório + steps declarativos + motor = padrão da indústria) e as sugestões viraram as regras 49-53 por decisão de Helio.

## 4. Pendências (todas rastreiam ao v1.1)

| # | Pendência | Fase v1.1 | Prioridade |
|---|---|---|---|
| 1 | Helio valida a peça 1 (`objects/si3/cadastro_min.yaml` — tipos e criticidades) | Fase 2, peça 1 | 🔴 imediato |
| 2 | Desenho em português da peça 2: `preencher()` por tipo + resolvedor multi-locator (jab → template → coordenada → seletor web, logando estratégia). Código só após "faz sentido" | Fase 2, peça 2 | 🔴 próxima |
| 3 | Working tree: edição do `summary_generator.py` pendente + 2 `git rm` do MSI3 morto — commit na peça 5 | Fase 2, peça 5 | 🟡 registrada |
| 4 | `test_login_sislab.py` não registrado no CLI — reavaliar na Fase 3 (reescrita) | Fase 3 | 🟢 |
| 5 | Names pyjab das admissões (AB06, AB09-AB12) — só quando a reescrita das admissões chegar | Fase 3 | 🟢 |
| 6 | Aplicação Citrix candidata | Fase 4 | ⏳ Helio |
| 7 | Banco congelado até liberação InCor | — | ⏸ |

Canceladas em 03-04/08 (sem rastro no v1.1): fixture da antiga 0.3 como entregável próprio; simplificação 0.4; conserto de `ocr_lido` CM04/CM05; testes unitários do CadastroMin legado; `test_cadastro_paciente_flow` desatualizado; `test_config_loader` til — tudo morre com a reescrita da Fase 3.

## 5-7. Padrões consolidados, matriz de verificação, padrões Oracle Forms

Inalterados — ver v0.5.40 §5, Projeto v1.1 §5 (peça 3 absorve a matriz) e v0.5.32 §7. A matriz de decisão do v1 §6 vira TABELA DO MOTOR na peça 3.

## 8. Arquitetura

`vtae/` (cli, config, core, flows, runners, report, vision) + `objects/` + `configs/` + `templates/` + `tests/`. Novo: `objects/si3/` (Modelo de Elemento, peça 1). `dsl_interpreter.py` e `components/` mortos serão substituídos/removidos pelo motor (peça 4).

## 9. Próximo passo concreto (início do próximo chat)

1. Helio dá o "faz sentido" (ou correções) na peça 1 — em especial os `tipo`/`criticidade` atribuídos.
2. Claude devolve o desenho em português da peça 2 (`preencher()` + resolvedor multi-locator), já nascendo sob as regras 49-51 (YAML declara / cresce por demanda / espera por condição). Zero código antes do "faz sentido".
3. Uma peça por vez. Nenhuma peça avança sem a anterior fechada.

---

**Marco desta sessão (04/08 — v0.5.42):** o projeto foi readequado ao que sempre foi a visão: um MOTOR onde testes se montam com o mínimo de código e um único padrão, desktop e web. O Projeto v1.1 foi aprovado como nova constituição; Fases 0/1 declaradas concluídas; as sub-fases sem lastro foram canceladas e virou regra que prompt não cria escopo (52). A peça 1 do motor (YAML de objetos tipados) foi entregue sem tocar em nada validado. Cinco regras novas (49-53) nasceram das decisões de direção: YAML declara e Python decide, o motor cresce por demanda, espera é por condição e não por tempo, e a competição com o TestComplete se dá onde ele é fraco — verificação, legado e evidência.
