# VTAE — Manual de Criação de Testes (o padrão de 5 peças)

**Versão do documento:** v0.1 · **Criado em:** 06/08/2026, sessão 3, a partir da Fase 3 aberta (Projeto v0.1 §2.3 item 7)
**Público:** Helio, escrevendo um teste de produção do zero no motor.
**Base:** este manual descreve o padrão como ele existe HOJE em `cadastro_paciente_min` — o único teste que já passou pelo gate 3x completo no motor. Nada aqui é aspiracional; onde a visão do Projeto v1 diverge do código real (ex.: `criticidade` nunca foi implementada como chave do YAML — quem decide falha × aviso é o verbo usado no flow, `preencher` vs `verificar`), este manual segue o código.

> Ler antes: `VTAE_Projeto_v0.1.md` (visão, histórico, fases) e `VTAE_Manual_Tecnico_v0.1.md` (mapa do código). Este manual é o terceiro documento vivo — o "como fazer" que faltava entre os dois.

---

## 1. As 5 peças, em uma frase cada

Um teste de produção no motor não é um arquivo — são cinco, cada um com um lugar único (regra de organização do Manual Técnico §2):

| # | Peça | Onde mora | Responde |
|---|---|---|---|
| 1 | **Objects YAML** | `objects/si3/<tela>.yaml` | Que elementos existem nesta tela, e como alcançar/verificar cada um? |
| 2 | **Templates** | `templates/si3/<tela>/*.png` | Recortes de tela para os elementos que precisam de template (âncoras, popups, campos que se deslocam) |
| 3 | **Config** | `configs/si3/si3_<tela>/config.yaml` + `.env` | Quais dados o teste usa, e quais credenciais? |
| 4 | **Steps nomeados** (opcional) | `vtae/flows/si3/<tela>/steps.py` | A lógica de negócio que os 4 verbos genéricos do motor não cobrem |
| 5 | **Flow YAML + teste** | `flows/si3/<tela>.yaml` + `tests/integration/si3/test_<tela>.py` | O roteiro (ordem dos passos) e o contrato de 3 linhas que dispara tudo |

A ordem de leitura acima **não é a ordem de construção**. Construir de trás para frente (flow primeiro) te deixa escrevendo um roteiro para elementos que ainda não existem. A ordem que funciona na prática é a da seção 2.

---

## 2. Ordem de construção recomendada

### 2.1 Objects YAML — comece aqui

Cada elemento é declarado **uma vez só**, com tipo + todos os locators que ele tiver. Estrutura mínima de um arquivo (`objects/si3/cadastro_min.yaml`, real):

```yaml
tela:
  titulo_jab: "Form_Pac0010"     # janela Java (Access Bridge) — só se pyjab existir nesta tela
  camada_exata: pyjab            # pyjab | playwright | nenhuma — DECLARADO, nunca inferido
  ancora: campo_nome_social      # elemento que prova que a tela abriu
  titulo_janela: "Form_Pac0010"  # título (parcial) da janela do Windows — usado por F10 e esperas

objetos:
  nome:
    tipo: texto
    coordenada: { x: 63, y: 159 }
    regiao_ocr: { x1: 27, y1: 145, x2: 447, y2: 168 }

  sexo:
    tipo: lov
    coordenada: { x: 648, y: 200 }
    regiao_ocr: { x1: 543, y1: 192, x2: 633, y2: 212 }
    jab_name: 'Descrição do Sexo.'
    btn_ok: btn_ok_lov

  btn_ok_lov:
    tipo: botao
    coordenada: { x: 222, y: 360 }
```

O bloco `tela:` é propriedade da TELA inteira, não de um objeto — declarado uma vez, vale para todo o arquivo. Se a tela não tem camada exata (nem pyjab nem web), declare `camada_exata: nenhuma` mesmo assim: o default é "nenhuma", mas declarado explicitamente evita que "esqueci de mapear" pareça "este sistema não tem camada exata" (são duas situações diferentes, e é o motivo de essa linha existir).

**Cada objeto pode ter:** `tipo`, `coordenada` (x/y), `regiao_ocr` (x1/y1/x2/y2), `template` (caminho do PNG), `jab_name` (locator exato), e — só quando o tipo exigir — `btn_ok`, `campo_localizar`, `titulo_janela` (ver seção 3, tabela de tipos).

Nada de coordenada duplicada em outro lugar. Se um dado de teste também precisa saber algo sobre o campo, ele referencia o NOME do objeto, nunca copia a coordenada.

### 2.2 Templates — só onde a coordenada fixa não basta

O `resolvedor` (peça 2 do motor) tenta `template` primeiro e cai para `coordenada` se não achar (com aviso de degradação). Use template para:
- **Âncoras** — elementos só para confirmar que a tela abriu, nunca clicados (`campo_nome_social` no cadastro_min)
- **Popups que aparecem ou não** — o motor precisa achar (ou não achar) sem travar
- **Qualquer coisa que se desloca** — diálogos nativos do Windows que redimensionam com a mensagem

Regra de captura (inegociável, Manual Técnico §6.1): `pyautogui.screenshot()` + `PIL.crop()`, **nunca** Win+Shift+S nem recorte colado no chat. Recorte apertado — só o elemento estável, nunca a parte que varia (mensagem, valor). Convenção de pasta: `templates/si3/<nome_da_tela>/<nome_do_objeto>.png`, mesmo nome do objeto no YAML.

Depois de capturar, meça antes de confiar: `scripts/diagnose_contra_arquivo.py` compara o template contra um screenshot salvo (nunca contra a tela ao vivo por engano — é um bug conhecido do `diagnose()` nativo). Meça sensibilidade E especificidade: o template tem que achar o elemento quando ele está lá, e **não achar nada** quando não está.

### 2.3 Config — dados e credenciais

Dois arquivos por tela, em `configs/si3/si3_<tela>/`:

**`.env`** — só credenciais e segredos, nunca no YAML (nunca comitar):
```
SI3_USER=usuario
SI3_PASS=senha
```

**`config.yaml`** — tudo o resto:
```yaml
sistema: si3_<tela>
tipo: desktop
runner: opencv
ocr_engine: easyocr

ambientes:
  dev:
    url: ''
    confidence: 0.75

credenciais:
  usuario: ${SI3_USER}
  senha:   ${SI3_PASS}

dados_faker:
  - campo: nome
    tipo: faker
    metodo: name
    transformacao: sem_prefixo_upper

dados:
  jab_home_fake: ${SI3_JAB_HOME_FAKE:-C:\jab_home}
  sexo_opcoes: [MASCULINO, FEMININO]
```

`dados_faker:` gera valor NOVO a cada execução (Faker); `dados:` é fixo ou lista para sorteio no flow via `{sorteio:...}`. As transformações disponíveis (`vtae/config/schema.py`): `sem_pontuacao`, `upper`, `lower`, `truncar_50`, `sem_prefixo`, `sem_prefixo_upper`, `data_ddmmaaaa` (converte a data do Faker pro formato que o Forms espera). Se faltar uma, é caso de medir o formato real da tela antes de inventar uma nova.

`config.DADOS` mescla `dados:` + o gerado por `dados_faker:` num dicionário só — é o que o flow YAML interpola com `{faker:chave}` / `{sorteio:chave}` (seção 2.5) e o que os steps nomeados leem via `ctx.config.DADOS["chave"]`.

Locators **não** vivem aqui — fonte única é o objects YAML (regra 40, repetida no cabeçalho de todo `config.yaml` real).

### 2.4 Steps nomeados — só quando a lógica de negócio exigir

A maior parte de uma tela cabe nos 4 verbos genéricos do motor (seção 4). Steps nomeados existem para o que **só aquele sistema mostra** — navegação (`abrir_modulo` não existe no MSI3 do mesmo jeito que no SI3), popups em cascata (`preencher_nacionalidade` do cadastro_min: 3 sub-popups atrás de uma LOV), ou qualquer decisão condicional.

Assinatura fixa de todo step nomeado, em `vtae/flows/si3/<tela>/steps.py`:

```python
def nome_do_step(ctx, motor, argumento):
    ...
```

- `ctx` — `FlowContext` (runner, config, objects)
- `motor` — o `Executor`: `motor.acoes`, `motor.esperas`, `motor.verificador`, `motor.interpolador`, `motor.objetos`, e o método `motor.verificar(nome, esperado)`
- `argumento` — o valor do YAML, **já interpolado** quando é texto

Regra de ouro (Manual `jab_reader.py`/`acoes.py`): nenhum step nomeado chama `pyautogui` direto. Toda mecânica de tela passa por `motor.acoes` (clicar, clicar_duas_vezes, preencher, salvar) e `motor.esperas` (esperar_visivel, esperar_janela_aparecer, esperar_janela_sumir) — nunca `time.sleep` cego.

Exemplo real, `abrir_modulo` do cadastro_min:

```python
def abrir_modulo(ctx, motor, nome_modulo):
    ctx.runner.maximizar_janela(JANELA_MENU)
    motor.acoes.preencher("localizar_menu", nome_modulo)
    motor.acoes.clicar("btn_pesquisar_menu")
    motor.acoes.clicar("btn_nao_popup")
    motor.acoes.clicar_duas_vezes("menu_cadastro_paciente")
    if not motor.esperas.esperar_visivel("nome_pesquisa"):
        raise StepError(f"o modulo '{nome_modulo}' nao abriu — ...")
```

**Step nomeado não ganha auto-verificação** — se ele precisa provar um valor, chama `motor.verificar(nome, esperado)` explicitamente (é o que `preencher_nacionalidade` faz no final, depois dos 3 popups).

Registro obrigatório no fim do arquivo, num dicionário `STEPS` — é o que a validação antecipada (peça 4) cobra antes do primeiro clique:

```python
STEPS = {
    "abrir_modulo": abrir_modulo,
    "pesquisar": pesquisar,
    "novo": novo,
}
```

Se a tela não precisar de nenhuma lógica especial, **não crie o arquivo** — nem todo flow tem `steps_python:` no cabeçalho.

### 2.5 Flow YAML — o roteiro

`flows/si3/<tela>.yaml`. Um arquivo por MÓDULO, nunca por caso de teste (regra 63) — cenários diferentes (positivo/negativo, brasileiro/estrangeiro) mudam os DADOS no config, não o roteiro.

```yaml
flow: cadastro_paciente_min
objetos: objects/si3/cadastro_min.yaml
steps_python: vtae.flows.si3.cadastro_min.steps   # omitir se não houver steps nomeados

steps:
  - abrir_modulo: CADASTRO DE PACIENTE
  - pesquisar:    "{faker:nome}"
  - novo:

  - verificar:  { campo: nome,            valor: "{faker:nome}" }
  - preencher:  { campo: data_nascimento, valor: "{faker:data_nascimento}" }
  - preencher:  { campo: sexo,            valor: "{sorteio:sexo_opcoes}" }
  - preencher_nacionalidade: "{sorteio:nacionalidade_opcoes}"

  - salvar: f10
  - gerar_matricula:
  - ler_resultado: matricula
  - sair:
```

Cada step é um dicionário de **uma chave só** — a chave é o verbo. `{faker:chave}` e `{sorteio:chave}` são os únicos formatos de interpolação (não existe concatenação tipo `"Sr. {faker:nome}"` — nasce quando um teste real precisar, medido). Sem `id:` — o id (`S01`, `S02`...) é derivado da ORDEM no YAML, automaticamente.

### 2.6 O teste — 3 linhas, sempre

```python
def test_<nome_do_flow>(si3):
    resultado = si3.executar("flows/si3/<tela>.yaml")
    assert resultado.success
```

A fixture `si3` (escopo `module`, em `tests/integration/si3/conftest.py`) abre e loga no SI3 **uma vez por arquivo** — se o arquivo tiver mais de um `si3.executar()` (jornada encadeada), reusa a mesma sessão logada.

---

## 3. Tipos de campo — o que `tipo:` decide

`tipo` no objects YAML decide COMO preencher (peça `acoes.py`) e COMO verificar (peça `verificacao.py`). É a única fonte — não existe uma segunda declaração de "obrigatório"/"crítico" em lugar nenhum do YAML (ver nota no topo deste manual).

| `tipo` | Mecânica de preencher | Chaves extras exigidas | Como verifica |
|---|---|---|---|
| `texto` | clica, backspace×20, digita | — | OCR, tolerância Levenshtein ~30% |
| `data` | clica, backspace×20, digita | — | OCR por ESTRUTURA (mínimo de dígitos, `MIN_DIGITOS_MASCARA=6`) — nunca valor exato, o Forms reformata |
| `lov` | clica, digita, TAB, clica `btn_ok` | `btn_ok` | camada exata (se a tela declarar) OU OCR sem containment (`ALLIANZ` não casa com `ALLIANZ SAUDE`) |
| `lov_lista` | clica, F9, clica `campo_localizar`, digita, ENTER, clica `btn_ok` | `campo_localizar`, `btn_ok`, `titulo_janela` | mesma coisa que `lov` |
| `botao` | (não se preenche — `clicar()` direto) | — | não verificável (`verificar` num botão é erro de YAML, pego na validação antecipada) |
| `resultado` | (não se preenche — só lido) | — | OCR por polling (`ler_resultado`, espera até 15s pela condição, nunca tempo fixo) |

`lov` vs `lov_lista`: `lov` é o campo com combo direto (digita e sai, tipo Sexo). `lov_lista` é quando falta a lista completa atrás de F9 (Grupo Étnico, Estado, País) — precisa de uma janela de busca interna do Forms, que **não tem handle do Windows** (`pygetwindow` não a vê — por isso `lov_lista` usa `PAUSA_LOV` fixa em vez de esperar por condição, um dos poucos lugares do motor que foge da regra 51, e está documentado assim no código).

`camada_exata: pyjab` na tela só entra em jogo pra `lov`/`lov_lista` — são os únicos tipos que sofrem "match parcial silencioso" (o Forms aceita um texto que bate parcialmente com um item da lista, sem erro visível; só a leitura exata via Access Bridge pega isso).

---

## 4. Verbo do motor vs step nomeado — como decidir

Só 4 verbos são genéricos (`plano.py`, `VERBOS_MOTOR`): `preencher`, `verificar`, `salvar`, `ler_resultado`. Qualquer outra palavra no YAML é tratada como step nomeado — não existe "verbo desconhecido" no plano, a cobrança de que a função exista acontece na validação antecipada.

- **`preencher`** — digita/seleciona e AUTO-verifica o valor (releitura estável, até 3 tentativas se DIVERGENTE). Se o campo não for verificável (sem `regiao_ocr` calibrada e sem `jab_name`), o resultado é AVISO, não falha — campo cego é limitação conhecida do mapeamento, não defeito do sistema.
- **`verificar`** — prova um valor SEM tocar no campo (o Nome do cadastro chega pré-preenchido da tela de pesquisa). Diferente de `preencher`: aqui NÃO_VERIFICÁVEL é FALHA, não aviso — pedir prova e não conseguir lê-la significa que nada foi provado.
- **`salvar`** — hoje só aceita `f10` (Forms não salva com Ctrl+S).
- **`ler_resultado`** — só funciona em elemento `tipo: resultado`; faz polling até 15s.

Se o que você precisa fazer é: **navegação, popups em cascata, decisão condicional, qualquer coisa com "se X então Y"** — é step nomeado, em Python, registrado em `STEPS`.

---

## 5. Scripts de apoio — calibração sem rodar a jornada inteira

| Script | Uso | O que resolve |
|---|---|---|
| `scripts/posicao_mouse.py` | `python scripts/posicao_mouse.py` | Captura até 4 coordenadas por contagem regressiva de 5s |
| `scripts/testar_regiao_ocr.py` | `python scripts/testar_regiao_ocr.py <img.png> x1 y1 x2 y2` | Testa uma `regiao_ocr` isolada contra um screenshot já salvo — sem rodar ~90s de jornada por tentativa |
| `scripts/diagnose_contra_arquivo.py` | função `diagnose_contra_arquivo(template, screenshot)` | Score de template contra arquivo salvo (nunca tela ao vivo por engano) |
| `scripts/mapear_names_jab.py` | `python scripts/mapear_names_jab.py "Titulo Da Janela" [filtro]` | Lista `role \| name \| text` de todos os elementos Java da janela — copiar o `name` exato para `jab_name:` |

Fluxo típico de calibração de um campo novo: captura o template ou coordenada (`posicao_mouse.py`), roda o flow uma vez pra gerar um screenshot em `evidence/`, mede a `regiao_ocr` contra esse arquivo (`testar_regiao_ocr.py`) até o OCR ler limpo, e só então roda a jornada completa.

---

## 6. Construção incremental — não escreva tudo de uma vez

O jeito que funcionou no cadastro_min: um campo por vez, na ordem da tela.

1. Declare o elemento no objects YAML com só `tipo` + `coordenada` (sem `regiao_ocr` ainda — bootstrap, verificação pulada com aviso, não quebra).
2. Adicione o step no flow YAML.
3. Rode o flow (`vtae run --test <nome>` ou pytest direto) e confira o screenshot em `evidence/` — o clique/digitação foi no lugar certo?
4. Calibre a `regiao_ocr` contra o screenshot real (`testar_regiao_ocr.py`) até o OCR ler limpo.
5. Se o campo for `lov`/`lov_lista` numa tela com `camada_exata: pyjab`, mapeie o `jab_name` (`mapear_names_jab.py`) — segunda camada, paralela ao OCR, não substitui.
6. Só depois de um campo fechar, parte para o próximo.

Isso é mais lento por campo, mas é a diferença entre depurar UM problema por vez e depurar catorze de uma vez quando o flow inteiro falha na primeira tentativa.

**Gate 3x** (regra que fecha qualquer teste novo, sem exceção): 3 execuções CONSECUTIVAS sem falha, sem interrupção manual no meio. Se pyjab estiver na tela, registre também quantas dessas 3 conectaram de primeira — instabilidade de conexão é esperada e tolerada (degrada pra OCR), não é motivo de reprovar o gate, mas vale registrar no Projeto v0.1 §2.1 quando fechar.

---

## 7. Armadilhas conhecidas do Oracle Forms (SI3/SisLab)

Direto do Manual Técnico §6, as que mais custam tempo se esquecidas:

- **F10 salva, Ctrl+S não.**
- **TAB não fecha LOV** — clicar OK explicitamente.
- **LOV é janela interna** — sem handle do Windows, `pygetwindow`/`esperar_janela_aparecer` nunca vê. É por isso que `lov_lista` usa pausa fixa em vez de esperar condição (único lugar assim, documentado no código de `acoes.py`).
- **Janela pode abrir reduzida** — maximizar antes do primeiro clique.
- **Região OCR não pode alcançar o campo vizinho** — um ícone da LOV ao lado pode entrar na leitura e sujar o texto (caso real: `cor_etnia` lia `'PRETA 2 ='` até a região ser apertada).
- **Âncora de template tem que ser específica da TELA** — um template genérico demais casa em telas diferentes com formas parecidas (caso real: `novo` usava um template que também casava na LISTA de pacientes, não só no formulário; a correção foi trocar para confirmação por TÍTULO DA JANELA).
- **Popup sem handle de janela** (ex.: HC-INCOR) só é detectável por template — nunca por `esperar_janela_aparecer`.
- **Conexão pyjab pode falhar no primeiro campo verificado** — corrida de startup do Access Bridge registrando a janela, transitória. Desde 06/08 o `LeitorJab` tenta de novo a cada campo que ainda não conectou (não fica preso pra sempre); ainda assim, é normal ver o primeiro campo sem `jab_lido` no log e os seguintes com.

---

## 8. Quando for a vez da Admissão de Pronto Socorro

Não existe flow legado de pronto socorro pra herdar (a tabela de flows do projeto nunca teve um — só ambulatório e internação existiam na geração 1). Isso é bom: não tem nada pra "não aproveitar" — é construção do zero de verdade, seguindo exatamente a ordem da seção 2.

Ponto de partida prático:
1. Abrir a tela real no SI3, listar os campos na ordem em que aparecem.
2. Para cada campo: é `texto`, `data`, `lov`, `lov_lista`, `botao` ou `resultado`? (seção 3)
3. Escrever o objects YAML só com `tipo` + `coordenada` de todos eles (bootstrap).
4. Escrever o flow YAML na mesma ordem da tela.
5. Rodar, olhar o screenshot, ir campo a campo (seção 6) — calibrar OCR, mapear jab_name onde a tela tiver `camada_exata`.
6. Steps nomeados só entram se algum campo tiver lógica condicional real (popup em cascata, decisão) — não force um step nomeado onde `preencher`/`verificar` bastam.
7. Gate 3x fecha o teste.

Este manual fica igual para o próximo flow depois deste — o padrão não muda, só os campos.
