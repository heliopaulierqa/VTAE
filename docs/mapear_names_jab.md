# Como mapear um `jab_name` — passo a passo

Procedimento para descobrir o *name* de um campo via Java Access Bridge e
escrevê-lo no YAML de objetos. Vale para qualquer tela Oracle Forms (SI3, SisLab).

Validado em 30/07/2026 mapeando Sexo, Cor/Raça e Naturalidade no `Form_Pac0010`.

---

## 0. Pré-condições (as três, sem exceção)

1. **Terminal NÃO elevado.** `Win+R` → `cmd` → Enter. O título da janela não pode
   conter "Administrador". Terminal do VS Code aberto como admin **não serve**.
2. **Tela alvo aberta no sistema**, no estado em que o teste a encontra. Se der,
   com um registro carregado — ver o valor real na tela é o que confirma o campo.
3. **Python do venv**: `.venv\Scripts\python`. O pyjab está instalado só lá.

No `cmd`, para entrar na pasta do projeto use `cd /d` — sem o `/d` o `cmd` não
troca de unidade e você fica no `C:`.

---

## 1. Descobrir o título exato da janela

```
.venv\Scripts\python -c "from pyjab.common.win32utils import Win32Utils; [print(repr(t)) for t in Win32Utils.enum_windows().values() if t.strip()]"
```

Usa a mesma função que o pyjab usa internamente, então mostra exatamente o que
ele vê.

O casamento de título no pyjab é `fnmatch` (glob), **não** substring: o título
precisa casar **por inteiro**. Se o título real tiver qualquer coisa a mais, use
curinga — `"*Pac0010*"`.

---

## 2. Gerar o dump completo dos elementos

```
.venv\Scripts\python scripts\mapear_names_jab.py "Form_Pac0010"
```

Sem 2º argumento **nada é impresso no console** — o dump completo vai para
`scripts\jab_dump.txt`. Abra o arquivo e use Ctrl+F.

O 2º argumento é um filtro de console opcional, por termo contido no *name*.

---

## 3. Achar o campo no dump — busque pelo VALOR, não pelo nome do campo

Este é o passo que mais engana. Os *names* do Forms não seguem o rótulo em
português da tela.

Exemplo real: o campo "Nacionalidade" não tem nenhum name contendo "nacional".
Buscar `nacional` devolvia zero. O que achou foi buscar o **valor visível na
tela** — `BRASILEIRO` — que levou ao name `Tipo de naturalidade`.

Ordem de busca recomendada:

1. o valor que está na tela (`BRASILEIRO`, `MASCULINO`, `BRANCA`)
2. o rótulo em português, como fallback
3. sinônimos (`etnia` → `cor`, `raca`; `nacionalidade` → `naturalidade`, `pais`)

---

## 4. Escolher a linha certa

Pegue a linha com **role `text`** e com o valor da tela aparecendo em `text`.

O que **não** serve:

| Role | Por quê |
|---|---|
| `push button` | é o botão da LOV, não o campo — `text` é `None` |
| `combo box` | `text` é `None`, a comparação quebra |
| `label` | rótulo estático, `text` é `None` |

Cuidado com pares `Identificação` / `Descrição` do mesmo campo:

```
name: 'Identificação da Cor/Raça.'   | text: '2'         <- código interno
name: 'Descrição da Cor/Raça.'       | text: 'BRANCA'    <- é este
```

Use sempre o `Descrição ...`, que é o que o usuário vê e o que o teste preenche.

---

## 5. Checar ambiguidade antes de confiar

Conte quantas linhas do dump têm o **mesmo** name. Se for mais de uma, o
`_verify_campo_via_jab` faz `elementos[0].text` e você precisa saber o que vem no
índice 0 — se vier um `combo box`, `.text` é `None` e o step falha por motivo
errado (falso-negativo).

```
.venv\Scripts\python -c "import os,logging; os.environ.setdefault('JAVA_HOME',r'C:\jab_home'); logging.getLogger('pyjab').setLevel(logging.ERROR); from pyjab.jabdriver import JABDriver; d=JABDriver(title='Form_Pac0010'); [print(i, e.role, repr(e.text)) for i,e in enumerate(d.find_elements_by_name('Tipo de naturalidade'))]"
```

Troque o título e o name. Esperado: índice 0 = role `text` com o valor da tela.

Medido em 30/07 para `Tipo de naturalidade`: `0 text 'BRASILEIRO'` /
`1 combo box None` — o índice 0 é o certo.

---

## 6. Escrever no YAML de objetos

Em `objects/<tela>.yaml`, no objeto correspondente. **Nada vai no config** — o
`jab_name` é propriedade do objeto, e o título da janela é propriedade da tela.

```yaml
tela:
  titulo_jab: "Form_Pac0010"

objetos:
  campo_sexo:
    regiao_ocr: { x1: 543, y1: 192, x2: 633, y2: 212 }
    jab_name: 'Descrição do Sexo.'
```

O name vai **exato**: acentos, pontuação e o ponto final. Aspas simples.

---

## 7. Sintomas e o que significam

| Sintoma | Causa real |
|---|---|
| `no java window found by title 'X' in '30'seconds` | mensagem enganosa. Pode ser título que não casa **ou** o bridge dizendo que não é janela Java. Se o `enum_windows` do passo 1 lista o título, o problema **não** é o título — é elevação do terminal ou a JVM sem Access Bridge. |
| Script roda e não imprime nada | normal sem filtro. O resultado está em `scripts\jab_dump.txt`. |
| `O sistema não pode encontrar o caminho especificado` | `cd` sem `/d` no `cmd` — você não saiu do `C:`. |
| Comparação falha com valor lido vazio | `elementos[0]` provavelmente é `combo box` ou `push button`. Rode o passo 5. |

---

## Referência de código

- `scripts/mapear_names_jab.py` — gera o dump
- `pyjab/common/win32utils.py:238` — `get_hwnds_by_title`, casamento `fnmatch`
- `pyjab/jabdriver.py:246` — `get_java_window_hwnd`, o `_is_java_window` que falha silencioso
- `vtae/flows/base_flow.py` — `_verify_campo_via_jab`, quem consome o `jab_name`
