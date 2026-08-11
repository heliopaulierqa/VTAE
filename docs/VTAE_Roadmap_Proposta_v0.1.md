# VTAE — Roadmap de Direção (proposta para estudo e decisão de Helio)

**Status:** PROPOSTA — não é decisão, não é documento vivo ainda. Helio estuda e decide quais fases entram, em que ordem.
**Criado em:** 06/08/2026, a partir do pedido de revisar todo o histórico e propor solução, no estilo do `VTAE_Projeto_v0.5.13.docx` (item 6 como sequência-base).

> **Aviso técnico, uma vez só:** o ambiente que abre e gera arquivos Word ficou indisponível nesta sessão (4 tentativas, mesmo bloqueio já registrado antes em `VTAE_Prompt_Instrucao_v0.5.35.md`, regra 43). Não consegui abrir o anexo nem ler o item 6. Este documento incorpora tudo que você apontou hoje, mas a SEQUÊNCIA abaixo é minha proposta, não confirmada contra o item 6. Cole o texto dele aqui (ou aguarde o ambiente voltar) e eu reconcilio.

---

## 1. De onde este roadmap parte — o diagnóstico de hoje, sem retoque

**Funciona, comprovado com log, não promessa:** o motor (as peças que decidem sozinhas como preencher e como conferir cada campo por tipo) — 927 unitários verdes. `cadastro_paciente_min` — gate 3x fechado, rodou de ponta a ponta na tela real várias vezes. As duas camadas de verificação (imagem + leitura exata do componente) funcionando juntas, uma cobrindo a falha da outra. `src/` (a pasta antiga) de fato apagada. Os flows antigos que já tinham gate fechado antes continuam intactos.

**Confuso, não quebrado:** documentação em múltiplas gerações sem uma fonte única de verdade (`README.md` cita `src/` e um manual `.docx` que não existem mais; dois "Prompt de Instrução" soltos, de versões diferentes, em lugares diferentes; um processo antigo de 1 arquivo nunca reconciliado com o processo novo de 5). Cinco arquivos por tela nova, sem ferramenta que monte o esqueleto.

**Quebrado de verdade, não diagnosticado:** duas quedas silenciosas hoje (execução termina em "0/0 steps", sem erro registrado). `S04 verificar nome` falhou 2x por OCR não ler nada. Instabilidade do pyjab contornada duas vezes (hoje e 29-30/07), nunca com causa raiz medida.

Este roadmap propõe onde cada um desses três entra na sequência — nenhum é ignorado, nenhum vira "pendência solta".

---

## 2. Premissas inegociáveis — extraídas diretamente do que você disse hoje

Toda fase abaixo é medida contra estas quatro coisas. Uma fase que não atende pelo menos uma delas não deveria entrar no roadmap:

1. **Reuso de técnica entre testes.** Rodar um teste 3x, 10x ou 100x não é o valor — é só repetição do mesmo teste. O valor está em uma técnica resolvida numa tela (uma verificação, um popup, uma navegação) ficar disponível pra QUALQUER outra tela sem reconstruir do zero. Hoje isso não existe.
2. **Testes encadeáveis.** No sistema real as telas não são ilhas — um paciente cadastrado numa tela é admitido em outra, agendado em outra. O framework precisa tratar isso como jornada, não como testes isolados que por acaso compartilham um dado.
3. **Portabilidade desktop/web.** O mesmo padrão de teste precisa servir SI3/SisLab (desktop, Oracle Forms) e MSI3 (web, APEX) sem reescrever a lógica — só trocar a camada que toca a tela.
4. **Premissa permanente, acima de qualquer ferramenta:** em qualquer ponto do roadmap, Helio tem que conseguir entender e criar o próximo teste. Isso vale independente de existir scaffold, recorder, CI/CD ou qualquer outra automação por baixo — a automação serve essa premissa, nunca o contrário.

---

## 3. Por que a ordem importa — a metáfora do barco

Ajustar a direção ANTES de içar as velas: as Fases C, D e E abaixo mexem na FORMA como um teste é construído (reuso, encadeamento, portabilidade). Fazer isso DEPOIS de já ter escrito 10-15 telas novas no padrão atual significa retrabalhar 10-15 telas. Fazer ANTES significa que cada tela nova, a partir da Fase G, já nasce mais barata. É por isso que cobertura (Fase G, "escrever mais testes") vem depois da arquitetura de reuso, não antes — mesmo sabendo que adiar cobertura tem custo.

---

## 4. Fases propostas

### Fase A — Saneamento documental
**Ataca:** o cenário CONFUSO.
**Entrega:** uma única fonte de verdade confirmada (`docs/VTAE_Projeto_v0.1.md` + `docs/VTAE_Manual_Tecnico_v0.1.md` + este roadmap depois de decidido). `README.md` reescrito pra bater com o estado real (sem `src/`, sem `.docx` morto). Os dois "Prompt de Instrução" soltos (`VTAE_Prompt_Instrucao_v0.5.35.md` na raiz, `v0.5.49` em `docs/`) arquivados ou apagados — eles já foram substituídos, mas continuam lá.
**Critério de pronto:** abrir a pasta do projeto e não achar nenhum documento que descreva um estado que não existe mais.
**Risco:** baixo. Não toca código.

### Fase B — Estabilização
**Ataca:** o cenário QUEBRADO.
**Entrega:** causa medida (não chutada) das duas quedas silenciosas de hoje — precisa de captura completa do terminal na próxima ocorrência, o `.log` estruturado não guarda isso. Causa medida da falha de OCR em `S04 verificar nome`. Decisão fechada sobre o pyjab: ou a causa raiz de fundo (por que o Access Bridge demora a registrar) é medida de vez, ou o comportamento atual (retry por campo, tolerante) é formalmente aceito como definitivo — mas com decisão registrada, não como pendência eterna.
**Critério de pronto:** rodar `cadastro_paciente_min` 10x seguidas sem nenhuma queda silenciosa.
**Risco:** médio — pode exigir instrumentação nova (captura de terminal, logging adicional).

### Fase C — Biblioteca de elementos compartilhados
**Ataca:** premissa 1 (reuso de técnica) — o ponto mais importante que você levantou hoje.

Preciso ser preciso aqui sobre o que é tecnicamente possível reusar e o que não é, pra não prometer o que não se cumpre: a COORDENADA de um campo é sempre específica da tela onde ele está desenhado — isso não reduz a zero entre cadastro e admissão, por exemplo, porque são posições diferentes na tela. O que É genuinamente compartilhável, e hoje não é reusado, são dois grupos concretos:

- **Elementos que são literalmente o MESMO componente do Forms reaproveitado pelo sistema real** — o popup de erro HC-INCOR, as janelas de LOV genéricas do sistema (Lista de País, Lista de UF, Lista de Cidade), elementos de navegação do Menu Principal. Esses têm coordenada/template IDÊNTICOS não importa qual tela os chamou, porque é a mesma janela interna do Forms. Hoje cada `objects/<tela>.yaml` redeclara isso do zero.
- **A mecânica por tipo** (como preencher um `lov`, como verificar um `texto`) — essa parte JÁ é 100% reusada hoje, é o que `acoes.py`/`verificacao.py` fazem. Isso não é uma lacuna, é algo que já funciona bem e vale deixar registrado como acerto.

**Entrega:** um arquivo de objetos comuns (ex.: `objects/si3/_comum.yaml`) com os elementos do primeiro grupo, e um mecanismo pequeno no `ObjectRepository` pra uma tela declarar que herda desse arquivo — resolve o nome na tela primeiro, cai no comum se não achar. Mudança cirúrgica, não reescrita.
**Critério de pronto:** o popup HC-INCOR (ou outro elemento comprovadamente repetido) declarado uma vez, usado por duas telas diferentes sem duplicar YAML.
**Risco:** médio — mexe em `object_repository.py`, peça central do motor.

### Fase D — Jornadas declarativas
**Ataca:** premissa 2 (testes encadeáveis).

Hoje encadear flows é código Python chamando `si3.executar()` várias vezes manualmente dentro do teste, reaproveitando login via a fixture de escopo `module` e compartilhando `paciente_id` via `estado_jornada.json`. Funciona, mas não é declarado — é um padrão que cada teste de jornada tem que reimplementar em Python.

**Entrega:** um YAML de jornada — lista de flows na ordem, mais o dado que se propaga entre eles (o `paciente_id` de um cadastro virando entrada da admissão seguinte, por exemplo) — e o teste continua sendo as mesmas 3 linhas, só que apontando pra jornada em vez de um flow só.
**Critério de pronto:** uma jornada de 2 flows (ex.: cadastro → admissão) descrita inteiramente em YAML, sem nenhuma linha de Python nova além do padrão de 3 linhas.
**Risco:** médio.

### Fase E — Prova de portabilidade desktop/web
**Ataca:** premissa 3 (desktop/web).

A arquitetura já tem os encaixes pra isso — `resolvedor.py` já trata `seletor` (web) do mesmo jeito que trata `template`/`coordenada` (desktop); o `config.yaml` já aceita `runner: opencv | playwright`. Mas isso NUNCA foi exercitado de ponta a ponta pelo motor novo — os testes MSI3 que existem hoje (FrequenciaAplicacao, TipoAnestesia) são da geração antiga, flow Python, não passam pelo motor.
**Entrega:** uma tela pequena do MSI3 rodando pelo MESMO motor, provando (ou corrigindo, com medição) que os mesmos verbos e tipos funcionam via Playwright.
**Critério de pronto:** um teste web de 3 linhas, gate 3x fechado, mesmo padrão do cadastro_min.
**Risco:** médio-alto — é a primeira vez que o motor toca Playwright de verdade.

### Fase F — Ferramenta de esqueleto (scaffold)
**Ataca:** o "5 arquivos não é administrável" que você levantou ontem.
**Entrega:** um comando (`vtae novo-teste <nome>`) que gera os arquivos que sobram depois das Fases C/D prontas — já com o bloco `tela:` pronto, já herdando `_comum.yaml` quando fizer sentido, teste de 3 linhas já escrito e rodando (com 0 campos, mas rodando).
**Por que depois de C e D, não antes:** gerar esqueleto do padrão ANTIGO agora, e depois mudar o padrão nas Fases C/D, geraria retrabalho — o próprio problema que este roadmap tenta evitar.
**Critério de pronto:** rodar o comando pra uma tela nova e ter, em segundos, um teste que roda (vazio) sem erro de configuração.
**Risco:** baixo — é ferramenta nova, não mexe no motor.

### Fase G — Cobertura (a Fase 3 original, agora mais barata)
**Ataca:** ter mais que 1 teste de produção.
**Entrega:** Pronto Socorro e as próximas telas, construídas por Helio com o scaffold (Fase F) + biblioteca comum (Fase C) + jornadas (Fase D) já prontas — cada tela nova custa uma fração do que custou o cadastro_min, porque boa parte já existe.
**Critério de pronto:** cada tela com seu gate 3x próprio, como já é a regra.

### Fase H — CI/CD
**Ataca:** execução automática, sem alguém digitando `pytest` na mão.
**Entrega:** depende de infraestrutura, não só código — uma máquina dedicada sempre ligada e logada (não um runner que nasce e morre), um gatilho que dispara sozinho, um jeito de avisar quando quebra. Só faz sentido com massa crítica de testes (Fase G em andamento) e depois da estabilização (Fase B) — rodar sozinho, sem humano olhando, torna os problemas da Fase B mais perigosos, não menos.
**Critério de pronto:** a definir junto com Helio quando esta fase chegar — decisão de infraestrutura, não só de código.

---

## 5. O que este roadmap NÃO decide

Não decide qual fase vem primeiro de verdade — isso é seu, por pedido explícito de hoje. Não decide se alguma fase deveria ser cortada. Não assume que o item 6 do documento anexado bate com esta sequência — precisa ser conferido assim que eu conseguir ler o anexo (ou você colar o texto dele).
