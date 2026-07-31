# VTAE — Prompt de Instrução Geral do Projeto

Data: 29/07/2026 | Versão: v0.5.33 | Use este documento como primeira mensagem no próximo chat.
Hierarquia: **VTAE_Projeto_v1.md** (constituição) → **VTAE_Projeto_v1.1_PROPOSTA.md** (revisão de estado, aprovada em conversa 29/07, formalização pendente) → **VTAE_Manual_Tecnico_v1.md** (referência técnica completa, gerado 29/07) → este prompt (registro operacional: onde paramos, o que fazer).

---

## 0. REGRAS DE TRABALHO — LEIA PRIMEIRO

Todas as regras do prompt v0.5.32 permanecem válidas (não repetidas aqui por espaço — consultar o v0.5.32 se necessário). As essenciais + as NOVAS acordadas em 29/07:

1. NUNCA criar/alterar arquivo sem Helio ver o conteúdo atual primeiro; aguardar upload/leitura antes de gerar código.
2. Mudança em flow validado é CIRÚRGICA — diff aprovado antes, zero alteração fora do pedido.
3. Gerar arquivo completo SOMENTE quando pedido expressamente.
4. Gate: 3x consecutivas antes de considerar validado.
5. Regra 19: `dados.get(x, default)` PROIBIDO em flow — todo dado passa por `_dado()`.
6. Templates sempre medidos (diagnose) antes de confiar; sensibilidade E especificidade.
7. pyjab: JAVA_HOME de mentira em código (nunca setx); leitura exata sem Levenshtein; pyjab LÊ, não escreve.
8. Banco CONGELADO (segurança InCor) — nada de banco até liberação.
9. Regra 43 (aprendizado): desenho em português antes de código; diff explicado (o que/por quê/conceito Python); "não entendi" bloqueia merge.
10. **[NOVA 29/07] UMA FRENTE POR VEZ**: uma frente de trabalho fechada por completo, com registro escrito, antes de qualquer outra existir. Claude NÃO propõe, NÃO descobre, NÃO sugere nada fora da frente atual. Se fizer, Helio corta na hora citando esta regra.
11. **[NOVA 29/07] VALIDAÇÃO DOCUMENTAL ANTES DE EXECUÇÃO**: nenhuma mudança começa sem Helio validar o documento/desenho que a descreve.
12. **[NOVA 29/07] SEM ESCOPO NOVO POR RESPOSTA**: o trabalho restante de cada fase é lista FECHADA. Item fora da lista = decisão nova de Helio, nunca iniciativa de Claude.
13. **[NOVA 29/07] VERIFICAÇÃO COM CAMINHO ABSOLUTO**: toda verificação de arquivo (Glob/Grep) usa caminho absoluto da raiz do projeto. Falso negativo por caminho relativo já causou erro real (4 duplicados "confirmados deletados" que não tinham sido).
14. **[NOVA 29/07] A RÉGUA DO PROJETO**: a prova de sucesso não é palavra — é (a) teste novo cabe em poucas linhas; (b) manual cabe em 1 página; (c) segundo flow no padrão sai MENOR que o primeiro. Qualquer um falhando = motor não pronto = parar e corrigir motor.

## 1. CONTEXTO DE RELACIONAMENTO — IMPORTANTE

Sessão de 29/07 teve crise de confiança séria. Helio expressou: sensação de bagunça arquitetural, de escopo mudando a cada resposta, de não conseguir criar um teste sozinho ("precisa fazer um curso"), de informação escondida, e perguntou diretamente "CONSEGUE ME AJUDAR???". Compromissos assumidos por Claude em resposta (além das regras novas acima): transparência total incluindo erros próprios (o erro do Glob relativo foi admitido espontaneamente); tom objetivo sem retórica; a promessa central do framework ("criar teste com o mínimo de código") está EM ABERTO e só se cumpre com entrega verificável, não com argumento. NÃO recair em: propostas não pedidas, explicações longas, escopo novo, otimismo não fundamentado.

## 2. O que é o VTAE

Framework híbrido de automação de testes (InCor): OpenCV + EasyOCR + pyjab + Playwright para Oracle Forms (SI3, SisLab) e APEX (MSI3). Visão (Projeto v1 §4): framework desacoplado, pip-instalável, Modelo de Elemento universal (múltiplos locators por objeto), Recorder-rascunho, repositório de objetos com tooling. Python 3.13. Detalhes técnicos completos: **docs/VTAE_Manual_Tecnico_v1.md**.

## 3. O que foi feito na sessão de 29/07 (v0.5.32 → v0.5.33)

1. **Migração src/→vtae/ CONCLUÍDA para flows**: sislab/ (login + cadastro_funcionario) e msi3/ (login, tipo_anestesia, cadastrar_orientacao renomeado sem acento, apex_helper) migrados com testes novos. `src/flows/` vazio (só `__init__.py`). Suite: **799 passando / 89 baseline** (inalterado, zero regressões).
2. **Higiene**: 4 flows duplicados deletados de src/ (verificado com caminho absoluto); componente morto sislab deletado; 2 imports quebrados do `dsl_interpreter._action_login` corrigidos (sislab → caminho real; fallback → raise StepError explícito).
3. **Auditoria e documentos criados**: `VTAE_Status_29-07-2026.md` (status verificado contra código), `docs/VTAE_Projeto_v1.1_PROPOSTA.md` (revisão do Projeto v1 — constatação central: Fase 1 foi executada fora de ordem com Fase 0 aberta; ordem de retomada aprovada por Helio em conversa), `docs/VTAE_Manual_Tecnico_v1.md` (manual técnico completo).
4. **Fase 0 — código CONCLUÍDO** (aguarda gate):
   - CM06 migrado de `self._coord` para `ctx.objects.coord` — flow inteiro numa forma só.
   - `ObjectRepository` (ainda em `src/core/`) ganhou `jab_name(nome)` (tolerante, None se não mapeado) e `titulo_jab()` (seção `tela:` do YAML).
   - `objects/cadastro_min.yaml` ganhou seção `tela: titulo_jab: "Form_Pac0010"` + placeholders `# jab_name:` nos 3 campos LOV.
   - Flow ganhou `_verificar_via_jab_se_mapeado()` chamado em CM06/CM07/CM08 (padrão AB07: conexão lazy cacheada em ctx.jab, tolerante; título vem de `ctx.objects.titulo_jab()`).
   - Decisão de arquitetura: título da janela é propriedade da TELA → mora no objects YAML, NÃO no config (Helio questionou, Claude corrigiu a orientação inicial errada).
   - `scripts/mapear_names_jab.py` criado (dump completo → `scripts/jab_dump.txt`; filtro por termo; silencia WARNINGs pyjab).
   - **1 rodada do teste passou** com o código novo (zero regressão, camada pyjab em bootstrap).
   - **Mapeado**: janela = `Form_Pac0010`; campo Sexo = `jab_name: 'Descrição do Sexo.'` (role text, confirmado com valor na tela).
5. **Mistério dos dados resolvido** (pergunta de Helio sobre cadastro completo preencher com YAML apagado): (a) `dados_faker` guarda REGRAS, não valores — Faker gera a cada execução (LGPD, by design; schema.py DADOS = fixos + faker, faker sobrescreve); (b) `CadastroPacienteFlow` tem defaults hardcoded (hora "00:00", sexo "M") VIOLANDO a regra 19 — mesmo flow do bug CP04 (~82 falhas do baseline).
6. **Decisões de Helio em 29/07**: piloto de consolidação = CadastroPacienteMinFlow (delegou, critério: reaproveitar testes); desktop primeiro, web depois (piloto web MSI3 futuro, mesmo Modelo de Elemento); "concluir o programado, depois testes do zero com os padrões" (radar); refazer testes do zero SÓ após concluir atividades previstas.

## 4. FRENTE ATUAL (única — regra 10): fechar a Fase 0

Lista FECHADA do que falta:

| # | Item | Quem |
|---|---|---|
| 1 | Mapear names JAB de Nacionalidade e Cor/Etnia: `python scripts/mapear_names_jab.py "Form_Pac0010" nacional` e `... etnia` (fallback: `cor`, `raca`). Escolher linha de role **text** (não push button), de preferência com `text` mostrando o valor da tela | Helio roda, Claude confirma o name |
| 2 | Preencher os 3 `jab_name` em `objects/cadastro_min.yaml` (Sexo já conhecido: `'Descrição do Sexo.'` — exato, com acento e ponto). NÃO adicionar nada no config (orientação anterior revogada) | Helio |
| 3 | Rodar `vtae run --test cadastro_paciente_min` 3x consecutivas. Na 1ª: conferir que avisos "jab_name não mapeado" sumiram e apareceu `OK (pyjab)` em CM06/07/08 | Helio |
| 4 | Reescrever `docs/criar_teste_novo.md` como manual de **1 página** (entregável de fechamento da Fase 0 — critério: se não couber em 1 página, motor não está pronto) | Claude, com validação de Helio |

Gate fecha → Fase 0 encerra com padrão completo (OpenCV + OCR + pyjab + ObjectRepository) num flow só.

## 5. Depois da Fase 0 (ordem aprovada na proposta v1.1 §10 — NÃO iniciar sem Helio abrir)

1. Regularizar Fase 1: Plano retroativo; restos de `src/` (config/, cli/ — bug conhecido: subprocess usa Python do sistema, summary falha —, components/, renomeações de fronteira, grep de desacoplamento). Inclui decisão pendente: migrar `src/core/object_repository.py` → `vtae/core/` (Helio ainda NÃO autorizou).
2. Fase 2 (resolvedor multi-locator) — decisão #7 pendente: piloto Ambulatório vs CadastroMin (registrada para abertura da fase).
3. Radar: bootstrap jornada tests; testes do zero com padrão consolidado; bug CP04 + violações regra 19 do CadastroPacienteFlow (decisão #8 pendente); Recorder (Fase 4).

## 6. Fatos técnicos de referência rápida

- Suite unit: 799 passando / 89 baseline (82 CadastroPacienteFlow quebrado, 3 test_login_flow_msi3 assinatura, 3 test_send, 1 test_config_loader acento).
- Janela JAB do cadastro: `Form_Pac0010`. Sexo: `'Descrição do Sexo.'`.
- `_step()` do BaseFlow: `confirm_template` presente ⇒ `validated=True` automático.
- ObjectRepository: `coord()`, `regiao_ocr()`, `template()`, `jab_name()` (tolerante), `titulo_jab()`.
- Bootstrap universal: recurso não calibrado (região OCR, template, jab_name, titulo_jab) = AVISO + pula, nunca quebra.
- Sandbox Linux do Claude estava indisponível na sessão 29/07 (não leu .docx) — Projeto v1 está em `docs/VTAE_Projeto_v1.md` (texto).

## 7. Início do próximo chat

1. Helio cola este prompt.
2. Claude confirma a frente atual (§4) e NADA além dela.
3. Helio traz o resultado do item 1 (as duas buscas de names) OU diz o rumo que decidiu após ler o manual técnico.

Marco da sessão 29/07 (v0.5.33): migração de flows 100% concluída; higiene feita; Fase 0 codificada e 1x verde; 1 de 3 names mapeado; manual técnico entregue; crise de confiança enfrentada com regras novas de trabalho (10-14) — a promessa do framework segue em aberto e a régua de cobrança está definida.
