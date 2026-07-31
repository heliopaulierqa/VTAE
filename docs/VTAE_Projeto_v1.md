
VTAE — Projeto v1
Data de aprovação: 23/07/2026 · Autor: Helio Paulier (com apoio de Claude) · Status: APROVADO Origem: Anteprojeto v0 (22/07/2026), aprovado por Helio sem alterações de conteúdo.
Este é o documento de referência do VTAE — a "constituição" do projeto. Fica ACIMA dos prompts de instrução de sessão (registro operacional) e dos Planos de Fase (detalhamento sob demanda). Ele muda raramente; os planos de fase mudam a cada fase.
Hierarquia de documentos:
Projeto v1 (este) — visão, fases, gates, método. Estável.
Plano da Fase N — criado quando a fase N abre, com o detalhamento técnico dela. Vira registro histórico quando a fase fecha.
Prompt de instrução de sessão (vX.Y.Z) — registro operacional: o que foi feito, onde paramos. Referencia este documento em vez de carregar a visão.

1. Identificação
Campo
Valor
Nome
VTAE — Visual Test Automation Engine
Mantenedor
Helio Paulier (desenvolvedor único)
Origem
InCor/USP — automação de testes de sistemas hospitalares
Versão do código na aprovação
v0.5.31
Princípio central
Confiança: teste que executa sem validar resultado é script, não teste

2. Problema que o VTAE resolve
Sistemas hospitalares legados (Oracle Forms) e modernos (APEX) não têm automação de testes confiável. Ferramentas comerciais de record & replay produzem scripts que executam sem verificar; ferramentas web não enxergam desktop legado nem Citrix. O VTAE combina camadas (visual, acessibilidade, web, banco) para que cada teste responda 5 perguntas de observabilidade: o que executou, o que digitou/clicou, o sistema respondeu certo, por que falhou, e o sistema é estável ao longo do tempo.
3. O que JÁ EXISTE e está provado (fatos, não intenção)
9 flows implementados, 7 com gate 3x fechado ou validado (Login, CadastroMin, Cadastro completo, AdmissaoAmbulatorio, AdmissaoInternacao, Agendamento, SisLab, MSI3).
Camada visual (OpenCV + template matching + EasyOCR) validada em produção de testes — funciona inclusive onde nenhuma outra camada funcionaria (é o denominador comum universal, incluindo Citrix).
Camada de acessibilidade (pyjab/JAB) validada 3x — detecta o defeito que nenhuma camada visual pega: match parcial silencioso em LOV (caso ALLIANZ).
DatabaseRunner implementado e testado com conexão real (fonte de domínio + fallback YAML com WARNING). CONGELADO por segurança — ver §7.
Disciplina de processo: gates de 3x consecutivas, diffs cirúrgicos, medição antes de confiança, 42 regras consolidadas, 8 skills documentadas.
Flow-modelo: AdmissaoAmbulatorioFlow (AB01–AB16) — onde padrões novos nascem.
4. Visão (onde o VTAE quer chegar)
Um framework de automação de testes desacoplado do InCor, instalável (pip install vtae), capaz de testar qualquer aplicação — Oracle Forms, web moderna, Citrix, desktop genérico — com:
Modelo de Elemento universal: cada objeto de tela num registro único com múltiplos locators (jab → template → coordenada → web) e camada de verificação como atributo.
Recorder que gera rascunho (nunca teste final): captura cliques, gera templates, esqueleto de flow e YAML — o humano adiciona as verificações.
Repositório de objetos com tooling de gestão e inventário.
InCor como primeiro cliente, não como dono — o caos de sistemas da USP é o campo de prova.
Teste de honestidade do desacoplamento: grep -ri "si3|incor" vtae/ retorna vazio.
5. Fases do projeto (ordem obrigatória, gate entre cada)
Cada fase ganha um Plano de Fase próprio no momento em que abre — com desenho em português, formato de dados, passos e critério de gate destrinchado. Este documento registra só o contrato de cada fase: entregável, gate e aprendizado.

Fase 0 — Piloto do Modelo de Elemento (ABERTA — fase atual)




Entregável
ObjectRepository (adapter ~60-80 linhas) + objects/cadastro_min.yaml convertido do config atual
Piloto
CadastroPacienteMinFlow (CM01–CM10) — exceção consciente à regra 33, por ser mudança estrutural, não de verificação
Gate de saída
3x consecutivas sem regressão no CadastroMin
Helio aprende
Leitura de YAML em Python, classes simples, dicionários, o padrão adapter
Risco
Baixíssimo — camada nova de leitura, zero alteração de lógica nos steps

Fase 1 — Extração do Core (desacoplamento gradual)

| Jornada-modelo | `CadastroPacienteMinFlow` — mesmo piloto da Fase 0, mais rápido de rodar a cada módulo extraído |




Entregável
Pacote vtae/ separado do projeto incor-tests/; um módulo extraído por vez (BaseFlow, TemplateMatcher, runners, observer, report)
Gate de saída
Jornada-modelo roda 3x sem regressão após CADA módulo extraído; grep de desacoplamento limpo nos módulos migrados
Helio aprende
Pacotes e imports, estrutura de projeto Python, pyproject.toml
Risco
Médio — mudança de endereço com renomeação de fronteira (SI3_JAB_HOME_FAKE → VTAE_JAB_HOME, _focar_si3 → focus_window(titulo))

| Jornada-modelo | 













Fase 2 — Resolvedor multi-locator no flow-modelo




Entregável
self.obj(ctx, "campo_x") decidindo jab → template → coordenada, logando a estratégia usada
Piloto
AdmissaoAmbulatorioFlow (volta a valer a regra 33 — isto É mudança de comportamento) - `AdmissaoAmbulatorioFlow` (volta a valer a regra 33 — isto É mudança de comportamento). Não nasce no Cadastro Mínimo porque é o único flow com pyjab validado 3x — o resolvedor precisa exercitar os 3 ramos (jab → template → coordenada), não só 2. 
Gate de saída
3x sem regressão + log mostrando qual locator resolveu cada elemento
Helio aprende
Métodos, encadeamento, tratamento de exceções, design de API

Fase 3 — Cliente 2 (prova do desacoplamento)




Entregável
Uma aplicação Citrix do InCor (pequena) automatizada usando SÓ o pacote vtae + objetos/flow próprios
Gate de saída
Flow do cliente 2 com gate 3x, sem NENHUMA alteração no core para acomodá-lo
Helio aprende
Perfil citrix do engine visual (thresholds, latência), reuso real
Pendência
Escolher a aplicação candidata (decisão de Helio — §8)

Fase 4 — Recorder-rascunho




Entregável
Recorder que captura clique+template+OCR de label, gera YAML de objetos + esqueleto de flow com # TODO: verificação
Contrato
Output é RASCUNHO. Verificações são sempre adicionadas por humano (preserva regra 9)
Gate de saída
Template auto-gerado passa em diagnose_contra_arquivo automaticamente (regra 11 embutida)

Fase 5 — Tooling do repositório de objetos




Entregável
vtae objects --tela X: inventário, templates renderizados, dívida técnica visível (elementos só-coordenada)
Evolução
Interface web local (Flask) — só se o CLI provar valor

6. Método de trabalho e aprendizado (governa TODAS as fases)
Regra de ouro: nenhum código entra sem que Helio explique o que faz e por quê. "Não entendi" bloqueia merge como teste falhando.
Diff explicado: toda mudança vem com (a) o que muda, (b) por que, (c) qual conceito Python está em jogo — 2-3 frases.
Desenho antes de código: toda peça nova é apresentada primeiro em português (o que cada parte faz); código só depois do "faz sentido" de Helio.
Helio digita diffs pequenos (não cola). Colar é reservado para blocos mecânicos (YAML convertido).
Inversão periódica: Helio propõe a solução primeiro (pseudocódigo/português), Claude refina.
Fechamento com explicação: fim de sessão, Helio resume em 2 frases o que foi feito. Se não sair natural, a próxima sessão revisita em vez de avançar.
Velocidade se ajusta à absorção, não o contrário. O roadmap não tem prazo — tem ordem e gates.
7. Fora de escopo / congelado
DatabaseRunner e tudo de banco — congelado por decisão de segurança do InCor. O código existente permanece, o fallback YAML segue funcional. As pendências de banco (tabelas de domínio, db_assert, gate 3x com banco real) ficam suspensas até liberação. Nada nas Fases 0–5 depende de banco.
pyjab como escritor — spike futuro isolado (regra 35), depois da Fase 5.
Reconhecimento "com IA" estilo marketing — descartado por princípio: heurísticas não medíveis violam a regra 11.
Mobile — fora do horizonte atual.
8. Decisões
#
Decisão
Status
Bloqueia
1
Aprovar o anteprojeto (vira Projeto v1)
✅ APROVADO 23/07/2026
—
2
Regra de aprendizado entra no prompt de instrução
✅ APROVADO — entra no v0.5.32
—
3
Aplicação Citrix candidata a cliente 2
⏳ Pendente (Helio)
Fase 3
4
Nome público do framework se for publicado (VTAE mantém?)
⏳ Pendente (Helio)
Fase 1+ (publicação)

9. Riscos assumidos
Risco
Mitigação
Desenvolvedor único + escopo amplo
Fases estritamente sequenciais; gate impede frente aberta demais
Código gerado mais rápido que compreensão absorvida
§6 — o método É a mitigação; velocidade cede
Auto-template do recorder recortar área instável
diagnose_contra_arquivo automático no gate da Fase 4
Extração do core quebrar flow validado
Um módulo por vez, 3x de regressão após cada um

10. Estado atual e próximo passo
Fase atual: Fase 0 — ABERTA em 23/07/2026.
Próximo passo concreto: Helio envia cadastro_paciente_min_flow.py + config.yaml do cadastro → Claude devolve o desenho em português do ObjectRepository (nasce aí o Plano da Fase 0) → Helio valida o desenho → só então o código, explicado, construído junto (§6).

