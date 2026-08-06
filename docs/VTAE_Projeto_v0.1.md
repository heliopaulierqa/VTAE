# VTAE — Projeto (documento vivo)

**Versão do documento:** v0.1 · **Atualizado em:** 05/08/2026 15:20 (em tempo real durante as sessões)
**Substitui e consolida:** VTAE_Projeto_v1.md (23/07) e VTAE_Projeto_v1.1.md (03/08) — já apagados por Helio.

> **REGRA DE USO (inegociável):** este documento e o `VTAE_Manual_Tecnico_v0.1.md`
> DEVEM ser consultados no início de qualquer sessão de trabalho e atualizados
> EM TEMPO REAL a cada decisão fechada. Eles carregam o histórico do que FOI
> FEITO, o que ESTÁ SENDO FEITO e o que VAI SER FEITO (§2). Sessão que não
> atualizar estes documentos está quebrando o método.

---

## 1. O que é o VTAE e para onde vai

Framework de automação de testes hospitalares do InCor para sistemas que
ferramentas comuns não alcançam: Oracle Forms legado (SI3, SisLab), Oracle APEX
(MSI3) e, no futuro, Citrix. Camadas: OpenCV/template, EasyOCR, pyjab/Java
Access Bridge, Playwright, oracledb (congelado).

**Princípio central:** teste que executa sem validar resultado é script, não teste.

**O centro do projeto é o MOTOR** — qualquer teste montado com a menor
quantidade possível de código, mesmo padrão em todos. O contrato de visão:

```python
def test_cadastro_paciente_min(si3):
    resultado = si3.executar("flows/si3/cadastro_min.yaml")
    assert resultado.success
```

3 linhas de Python; o resto declarado em dois YAMLs — o **YAML de flow**
(roteiro: steps em ordem) e o **YAML de objetos** (cada campo declarado UMA vez
com `tipo`, `criticidade` e todos os locators: coordenada, regiao_ocr, template,
jab_name, seletor web). `tipo` decide COMO preencher e COMO verificar;
`criticidade` decide falha × aviso. Lógica de negócio real vira step nomeado.

**Papel das pessoas (decisão de 05/08):** o cadastro_min é a BANCADA onde os
padrões são fechados via gates. Depois disso, **HELIO escreve todos os testes
do zero** com o padrão de 5 peças (YAML de flow + objects + templates + config
+ boot/fixture). Claude NÃO escreve testes — explica, revisa e aponta onde/por
quê. Nada do legado será aproveitado como teste de produção.

## 2. HISTÓRICO — feito · fazendo · a fazer

### 2.1 O que FOI FEITO (marcos com data)

| Data | Marco |
|---|---|
| 23/07/2026 | Projeto v1 aprovado; regra de aprendizado instituída; banco congelado (segurança InCor); Fase 0 aberta |
| até 03/08 | Fase 0 concluída (ObjectRepository + objects piloto, gate 3x); Fase 1 concluída (todo código em `vtae/`, `src/` extinto); Projeto v1.1 aprovado — motor vira o centro |
| 03–05/08 | Fase 2: peças 1–4 do motor construídas (objects com tipo/criticidade; ações por tipo + resolvedor multi-locator; verificação por tipo; interpretador do YAML de flow) |
| 05/08 manhã | **O MOTOR RODOU: cadastro de ponta a ponta em tela real, 17/17 verde, camada exata (pyjab) ativa nos 3 LOVs.** 38 linhas de YAML + 219 de Python substituem 823 linhas de flow. Commit feito |
| 05/08 tarde | Ambiente ficou honesto: CLI rodava pytest no Python GLOBAL (corrigido: `sys.executable` + `-s` + `--count` condicional no `run.py`). Regras 76–79. Docs vivos únicos criados (este + Manual v0.1) |
| 05/08 15:14 | **Gate — caminho ESTRANGEIRO fechado: 3 execuções consecutivas 17/17 verde (15:10, 15:12, 15:14)** |
| 06/08 07:40 | **Gate — caminho NATURALIZADO verde: 17/17** (pyjab não conectou, OCR validou — 5ª medição da instabilidade: 1 sucesso em 5) |
| 06/08 08:25 | **GATE 3x FECHADO — BRASILEIRO 17/17 com decisor exata nos 3 LOVs. Três caminhos de nacionalidade verdes, 5 execuções consecutivas sem falha. Config restaurado (3 opções).** Placar pyjab: 2 conexões em 6 rodadas limpas |
| 06/08 | **Commit do gate + CLI honesto + docs vivos realizado.** Sessão encerrada com working tree limpa |
| 06/08 (sessão 2) | **Limpeza da geração 2 aprovada por Helio** após levantamento de referências (grep no repo inteiro). Saem: dsl_interpreter.py, test_dsl_interpreter.py, vtae/components/, test_login_component.py, objects/cadastro_min.yaml antigo, test_cadastro_paciente_min.py (teste do flow antigo) + entrada `cadastro_paciente_min_flow` do CLI. **Correções ao plano original:** test_piloto_cadastro_min.py MANTIDO (não é órfão — valida o motor sem tela e guarda a pendência 7); object_repository.py MANTIDO (é núcleo do motor: executor.py o importa). Flow antigo de 823 linhas fica inalcançável até a Fase 3 (sem escopo novo) |
| 06/08 (sessão 2) | **Triagem dos 86 vermelhos FECHADA.** Causas: (a) `test_cadastro_paciente_flow.py` — 82 falhas, teste do flow legado mockado desatualizado (flow real funciona em tela, o unitário mockado só simulava até CP04) — DELETADO; (b) `test_login_flow_msi3.py` — 2 falhas por `assert_called_with` capturando só a última chamada de `wait_template` (a do `confirm_template` do BaseFlow, timeout=8/threshold=0.7) em vez da chamada explícita do flow (timeout=15.0) — corrigido para `assert_any_call`; 1 falha (`test_mw05_chama_inspecionar_pagina_em_falha`) testava uma chamada a `ApexHelper.inspecionar_pagina` que o código nunca implementou — Helio decidiu deletar o teste, não implementar a feature; (c) `test_config_loader.py` — mensagem de erro do teste tinha acento, código não — projeto inteiro escreve sem acento por padrão, teste corrigido. **Baseline final: 920 passed, 0 failed.** Vermelho volta a significar quebra real |

### 2.2 O que ESTÁ SENDO FEITO (agora)

**LIMPEZA DA GERAÇÃO 2 EXECUTADA (06/08, sessão 2)** — `git rm` dos 6 arquivos
feito por Helio; run.py e docs vivos atualizados. Staged, aguardando commit.

**Triagem concluída e aplicada por Helio (06/08 sessão 2). Baseline atual:
920 passed, 0 failed (920 coletados — 101 a menos que os 1021 de antes,
soma da limpeza da geração 2 + deleção dos dois testes obsoletos).**
Ver marco em §2.1 para a causa de cada grupo de falha e a correção aplicada.
**Peça 5 do motor: fixture `si3` construída (06/08 sessão 2)** —
`tests/integration/si3/conftest.py`, escopo `module` (decisão de Helio: abre
e loga 1x por arquivo, jornadas encadeadas reusam a sessão). Desenhada por
Claude, digitada por Helio em 4 blocos (regra 43); 1 erro estrutural
encontrado na revisão (fixture aninhada dentro da classe `SessaoSi3` por
indentação — pytest não descobriria) e corrigido. Limitação registrada, não
bloqueante: `report.html` é sobrescrito a cada `executar()` na mesma sessão
— jornada com 2+ flows só guarda o relatório do último. Revisitar na Fase 3.
Teste de produção escrito por Helio (regra 77) — `tests/integration/si3/
test_cadastro_paciente_min.py`, as 3 linhas do contrato. **GATE 3x FECHADO
(06/08 sessão 2): 3 execuções consecutivas 14/14, 10:09–10:19.** Placar
pyjab nas 3 rodadas: conectou em 2 (r1, r2 — decisor exata nos 3 LOVs),
falhou em 1 (r3 — `HWND is not Java Window`, degradou para OCR que
validou). Running total do placar de instabilidade: 4 conexões em 9
rodadas limpas desde 05/08. `vtae/cli/run.py` atualizado (2 entradas
apontavam para o teste provisório — `MODULOS["si3"]` e
`TESTES["cadastro_paciente_min"]` — ambas redirecionadas para o teste de
produção antes da deleção, senão `vtae run` quebraria).
`test_cadastro_min_motor.py` provisório removido por Helio (`git rm`).
**Item 6 do §2.3 fechado — peça 5 do motor concluída.**

**Fato medido (6 rodadas limpas): conexão pyjab é INSTÁVEL — conectou em 2
(15:14 de 05/08 e 08:24 de 06/08, decisor exata nos 3 LOVs), falhou em 4
(`HWND is not Java Window`, degradou para OCR que validou).** Correlação com
janela na frente DESCARTADA. Causa não medida. A degradação projetada
(regra 71) segurou o verde em todas — o desenho funcionou. Candidato a
investigar: TIMEOUT_CONEXAO=10s vs tempo real de registro do Access Bridge
(hipótese — medir antes de mudar).

### 2.3 O que VAI SER FEITO (ordem acordada em 05/08)

1. ~~Fechar o gate~~ ✅ 06/08.
2. ~~Limpeza da geração 2~~ ✅ 06/08 sessão 2.
3. ~~Triagem dos 86 unitários vermelhos~~ ✅ 06/08 sessão 2 — 920 passed, 0 failed.
4. Investigar instabilidade da conexão pyjab (medição, não chute).
5. Unitário do `LeitorJab` (desenho aprovado: FakeDriver injetado + fake em
   `sys.modules`).
6. ~~Peça 5 do motor: fixture `si3`~~ ✅ 06/08 sessão 2 — gate 3x fechado,
   teste provisório removido. `msi3` fica para quando um teste web novo pedir.
7. Fase 3: **Helio constrói os testes do zero** (admissões, cadastro completo),
   cada um com gate 3x próprio; Claude revisa e explica.
8. Fases futuras: Cliente 2/Citrix · Recorder (gravar = gerar YAMLs) · Tooling.
9. ⏸ Banco congelado até liberação do InCor.

## 3. Fases — estado

| Fase | Conteúdo | Estado |
|---|---|---|
| 0 | Piloto do Modelo de Elemento | ✅ concluída |
| 1 | Extração do core para `vtae/` | ✅ concluída |
| 2 | **O MOTOR** (6 peças) | 🟡 atual — peças 1–5 prontas (fixture si3, gate 3x fechado 06/08); geração 2 removida e 86 vermelhos zerados (06/08 sessão 2); falta só peça 6 (testes-padrão 3 linhas — já demonstrada no cadastro_min, falta propagar) |
| 3 | Reescrita dos testes (por Helio, do zero) | aguarda gate da Fase 2 |
| 4–6 | Citrix · Recorder · Tooling | futuras |

## 4. Método de trabalho

Do v1 §6, íntegro: nenhum código sem explicação em português aprovada antes;
diff em 3 partes (o que muda, por que, conceito Python em jogo); desenho antes
de código; Helio digita diffs pequenos; velocidade cede à absorção; prompt
operacional não cria escopo (rastreabilidade até uma fase deste documento);
sem escopo novo por resposta.

Acréscimos de 05/08 (regras 76–79 do prompt de instrução):
**documentos vivos atualizados em tempo real; Claude não escreve testes novos;
durante execução em tela real o SI3 é dono da tela — nada pode cobrir o
formulário; estes dois documentos são a fonte da verdade.**

## 5. Decisões (registro acumulado)

| # | Decisão | Status |
|---|---|---|
| 1 | Anteprojeto → Projeto v1 | ✅ 23/07 |
| 2 | Regra de aprendizado | ✅ v0.5.32 |
| 3 | Banco congelado (segurança InCor) | ⏸ até liberação |
| 4 | Motor no centro (Projeto v1.1) | ✅ 03/08 |
| 5 | Pilotos: CadastroMin (desktop) + TipoAnestesia (web) | ✅ 03/08 |
| 6 | Testes existentes serão REFEITOS, não aproveitados | ✅ 03/08 |
| 7 | Login vira fixture (`si3`/`msi3`) | ✅ 03/08 |
| 8 | cadastro_min = bancada de padrões; testes futuros escritos POR HELIO | ✅ 05/08 |
| 9 | Docs vivos únicos (este + Manual v0.1); versões antigas apagadas | ✅ 05/08 |
| 10 | Aplicação Citrix candidata / nome público do framework | ⏳ Helio |

## 6. Fora de escopo / congelado

Banco (InCor); pyjab-escritor (spike futuro isolado); mobile; "IA de marketing".
Testes legados não recebem manutenção — funcionam até serem substituídos.
