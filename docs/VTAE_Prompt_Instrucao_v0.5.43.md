# VTAE — Prompt de Instrução Geral do Projeto

**Data:** 04/08/2026 | **Versão:** v0.5.43
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
41. **Gate fechado termina em commit.** diff → grep → pytest unit vs baseline → 3x tela real (quando aplicável) → commit. Mensagem multi-linha: `git commit -F arquivo.txt`.
42. Mock mente sobre o que tem: teste valida a FORMA da chamada, não só que houve chamada.
43. Fontes idênticas não provam precedência; fonte única removida dispensa perturbação.
44. Ao centralizar acesso a um dado, o grep obrigatório é pela FONTE, não pelo helper.
45. Tolerante embaixo, estrito em cima: resolvedor devolve `None`; quem chama decide se é fatal.
46. Guard nunca executado não é robustez — caminho declarado tem que ser exercitado ao menos em unitário.
47. Fonte única exige inventário: chaves órfãs no `objects/` só aparecem por inventário manual (Fase 6, tooling).
48. Baseline de falhas é dívida registrada, não contrato: nenhum teste que passava pode falhar; melhora exige causa nominal. **Baseline atual: 819 passed / 86 failed em `tests/unit`.**
49. **YAML declara, Python decide.** O YAML de flow nunca ganha `if`, loop ou variável. Lógica de negócio real vira step nomeado em Python.
50. **O motor cresce por demanda de teste real, não por antecipação.** Generalizar para caso hipotético é dívida, não robustez.
51. **Espera por condição, nunca por tempo.** Título de janela, template visível ou estado pyjab — jamais `time.sleep` como mecanismo primário. Sleep físico documentado (clipboard, pós-clique) é exceção; `sleep` entre duas medições de uma condição não conta.
52. **Prompt operacional não cria escopo** (v1.1 §6). Hierarquia: Projeto v1.1 → Plano de Fase → prompt.
53. **Direção competitiva:** superar o TestComplete onde ele é fraco por design — verificação em camadas, legado desktop/Citrix, evidência auditável por step.
54. **[NOVA v0.5.43] Obrigatoriedade é do CENÁRIO, não do elemento.** O `objects/*.yaml` não carrega `criticidade`. Todo campo que o teste declara é preenchido e verificado ESTRITO; campo não declarado não é tocado. Cenário negativo (campo vazio → esperar erro do Forms) se declara no YAML de flow. Corolário: no motor, campo sem região OCR ou `jab_name` calibrado é erro de configuração — nunca verificação pulada em silêncio.
55. **[NOVA v0.5.43] Baseline se mede com `pytest tests/unit -q`.** `testpaths = tests` no `pyproject.toml` faz `pytest` sem argumento coletar os testes de integração, que abrem o SI3 real e tentam logar. Não existe marcador separando integração de unitário (gap conhecido, candidato à Fase 3).

---

## 1. O que é o VTAE

Framework híbrido de automação de testes hospitalares do InCor. OpenCV, Playwright, EasyOCR, pyjab/JAB e oracledb (congelado) para sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — APEX).

- **Versão:** v0.5.43 · **Python:** 3.13+
- **Documento de referência:** **VTAE_Projeto_v1.1.md**
- **Fase atual:** **Fase 2 — O MOTOR.** Peças 1 e 2 CONCLUÍDAS. Próxima: **peça 3 (verificação)**.
- Fases 0 e 1: concluídas. Fase 3 (após motor): Helio refaz os testes de admissão e o cadastro completo com o motor.

## 2. Estado dos flows

Inalterado. Os flows atuais continuam funcionando mas serão REFEITOS na Fase 3 — nenhum conserto neles, salvo pedido expresso de Helio.

## 3. O que foi feito na sessão de 04/08/2026 (v0.5.42 → v0.5.43)

Sessão sem sandbox Linux (5ª vez) — trabalho via pasta conectada; `pytest` e `git` com Helio.

### 3.1 [FEITO] Peça 1 validada com correção de rumo
Helio recusou a distinção obrigatorio/opcional: **todos os campos são testáveis, e todo campo declarado no teste vale como qualquer outro**. As 15 linhas `criticidade` saíram do `objects/si3/cadastro_min.yaml` — vira a regra 54. O `_verify_campo_opcional` de hoje foi diagnosticado como dívida de calibração (pula em silêncio quando a região está em bootstrap `{0,0,0,0}`), não como conceito a preservar.

Confirmado também que `nacionalidade`, `matricula` e `identificador` nunca tiveram coordenada no arquivo validado — nada foi removido; inventar coordenada não medida violaria as regras 3 e 11.

### 3.2 [FEITO] Peça 2 entregue e commitada — gate fechado
- `vtae/core/motor/resolvedor.py`: resolve o alvo na ordem template → coordenada (desktop) ou seletor (web), logando a estratégia vencedora. `degradado=True` quando o template declarado falha e a coordenada assume — sinal de tela deslocada que hoje passa despercebido.
- `vtae/core/motor/esperas.py`: `esperar_visivel` e `esperar_janela_sumir`. Elemento sem template cai na âncora da tela; sem âncora, AVISA e segue (nunca em silêncio).
- `ObjectRepository` ganhou `elemento()` e `ancora()`, ambos tolerantes. Os quatro métodos existentes intocados.
- `objects/si3/cadastro_min.yaml`: `ancora: campo_nome_social` em `tela:`; `titulo_janela` nos quatro `lov_lista`, tirando do código a tupla de títulos varrida em loop.
- 17 unitários novos (9 do resolvedor, 8 das esperas). **Baseline: 811/86 → 819/86, os 86 intactos.**
- `esperar_habilitado` (pyjab) NÃO entrou: nenhum teste real precisa hoje (regras 50 e 46).

### 3.3 [MEDIDO] `pytest -q` sem argumento dirige o SI3 real
Descoberto ao tentar medir o baseline: a execução abriu o SI3, tentou logar 8 vezes e foi interrompida por Helio. Vira a regra 55. Nenhum dano — mas a corrida gerou pastas em `evidence/` e atualizou `flakiness.json`.

### 3.4 [MEDIDO] Dois achados no caminho
- `test_frequencia_aplicacao.py` (arquivo morto do MSI3) tem **duas** causas independentes de import quebrado: o `FrequenciaAplicacaoFlow` inexistente (medido na sessão anterior) e `from configs.msi3.login_config import ...`, com `configs` não sendo pacote importável. Enquanto existir, `pytest -q` puro nunca coleta. Morre na peça 5.
- `test_tipo_anestesia.py` — **um dos dois pilotos da Fase 2** — está com `ocr_engine: tesseract` no config, engine removida na v0.5.11. Nem chega a abrir o browser. Trabalho real quando a fixture `msi3` chegar (peça 5).

## 4. Pendências (todas rastreiam ao v1.1)

| # | Pendência | Fase v1.1 | Prioridade |
|---|---|---|---|
| 1 | Peça 3 — verificação: absorve a matriz do Projeto v1 §6 (pyjab exato para LOV e máscara, OCR/Levenshtein para texto livre, screenshot sempre) | Fase 2, peça 3 | 🔴 próxima |
| 2 | Working tree: edição do `summary_generator.py` pendente + 2 `git rm` do MSI3 morto — commit na peça 5 | Fase 2, peça 5 | 🟡 registrada |
| 3 | `ocr_engine: tesseract` no config do TipoAnestesia — corrigir junto com a fixture `msi3` | Fase 2, peça 5 | 🟡 registrada |
| 4 | Associação `titulo_janela` ↔ campo é inferência da tupla do flow — confirmar em tela real | Fase 2, peça 4 | 🟡 |
| 5 | Limpar N de backspaces: decisão foi N fixo generoso (20) no motor, override por elemento só se um campo desmentir — conferir no gate de tela real | Fase 2, peça 4 | 🟡 |
| 6 | `test_login_sislab.py` não registrado no CLI | Fase 3 | 🟢 |
| 7 | Names pyjab das admissões (AB06, AB09-AB12) | Fase 3 | 🟢 |
| 8 | Marcador `integration` para separar unit de tela real | Fase 3 | 🟢 |
| 9 | Aplicação Citrix candidata | Fase 4 | ⏳ Helio |
| 10 | Banco congelado até liberação InCor | — | ⏸ |

## 5-7. Padrões consolidados, matriz de verificação, padrões Oracle Forms

Inalterados — ver v0.5.40 §5, Projeto v1.1 §5 e v0.5.32 §7. A matriz do v1 §6 vira TABELA DO MOTOR na peça 3.

## 8. Arquitetura

`vtae/` (cli, config, core, flows, runners, report, vision) + `objects/` + `configs/` + `templates/` + `tests/`.
Novo: `objects/si3/` (Modelo de Elemento) e **`vtae/core/motor/`** (resolvedor + esperas).
`dsl_interpreter.py` e `components/` mortos serão substituídos/removidos pelo motor (peça 4).

## 9. Próximo passo concreto (início do próximo chat)

1. Desenho em português da **peça 3 — verificação**: `verificar(elemento, valor_esperado)` escolhendo a camada por tipo (pyjab exato / OCR com tolerância / estrutural para máscara), com screenshot sempre como evidência. Zero código antes do "faz sentido".
2. Uma peça por vez. Nenhuma peça avança sem a anterior fechada.
3. As peças 4 (executor do YAML de flow) e 5 (fixtures `si3`/`msi3` + limpeza do MSI3 morto) vêm depois, nessa ordem.

---

**Marco desta sessão (04/08 — v0.5.43):** a peça 1 do motor foi validada com uma correção que virou regra — obrigatoriedade é do cenário, não do elemento, e todo campo declarado no teste é verificado estrito. A peça 2 foi entregue inteira e commitada com gate fechado: o motor já sabe *onde* agir (resolvedor com degradação logada) e *quando* agir (espera por condição, com âncora de tela para elementos sem template). Nada do que roda hoje foi tocado.

**Resumo de Helio (regra 35, 2 frases):**
_[a preencher]_
