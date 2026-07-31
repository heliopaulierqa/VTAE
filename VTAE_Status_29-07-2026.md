# VTAE — Levantamento de Status

**Data:** 29/07/2026
**Escopo:** o que foi concluído e o que falta, verificado contra o código real
**Origem:** inspeção direta dos arquivos (Glob/Grep com caminho absoluto) + resultado da suíte de testes

> Este documento é um levantamento de estado, para subsidiar a decisão do caminho a
> seguir. Não altera nenhuma decisão do Projeto v1 — apenas registra a realidade
> atual do código.

---

## 1. Nota de método — correção de verificação

As confirmações de deleção feitas durante a sessão de migração usaram busca com
caminho **relativo**, que resolvia para uma pasta diferente da raiz do projeto.
Isso produziu falsos negativos: alguns arquivos foram reportados como "deletados"
sem que a checagem tivesse de fato olhado o diretório certo.

Todo este documento foi refeito com **caminho absoluto**. Os números e listas
abaixo são o estado real em 29/07/2026.

---

## 2. O que foi CONCLUÍDO

### 2.1 Migração estrutural `src/` → `vtae/`

Todos os flows do projeto têm hoje sua versão oficial em `vtae/flows/`,
organizada por domínio:

| Módulo | Destino em `vtae/flows/` | Flows |
|---|---|---|
| SI3 — login | `si3/login/` | `LoginFlow`, `LoginSi3Flow` |
| SI3 — cadastro | `si3/cadastro/`, `si3/cadastro_min/` | `CadastroPacienteFlow`, `CadastroPacienteMinFlow` |
| SI3 — admissão | `si3/admissao/` | `BaseAdmissaoFlow`, `Ambulatorio`, `Internacao`, `ComAgendamento` |
| SI3 — agendamento | `si3/agendamento/` | `AgendamentoFlow` |
| SisLab | `sislab/login/`, `sislab/cadastro_funcionario/` | `LoginFlowSisLab`, `CadastroFuncionarioFlowSislab` |
| MSI3 | `msi3/login/`, `msi3/tipo_anestesia/`, `msi3/cadastro_orientacao/`, `msi3/apex_helper.py` | `LoginFlowMsi3`, `TipoAnestesiaFlow`, `CadastrarOrientacaoFlow`, `ApexHelper` |

### 2.2 Cobertura de testes unitários

- **799 testes passando**, com baseline de 89 falhas pré-existentes **inalterado**
  (zero regressões introduzidas pela migração).
- Testes unitários novos escritos do zero nesta etapa, no padrão comportamental
  já estabelecido (sucesso + falha por step, não smoke test):
  - `test_login_si3_flow.py` — 26 testes
  - `test_agendamento_flow.py` — 50 testes
  - `test_login_flow_sislab.py` — 21 testes
  - `test_cadastro_funcionario_flow_sislab.py` — 51 testes
  - `test_tipo_anestesia_flow.py` — 44 testes
  - `test_cadastrar_orientacao_flow.py` — 8 testes

### 2.3 Gate GUI

- Módulo **admissão**: 3 jornada tests, 3× consecutivas cada, sem falha — gate fechado.

### 2.4 Limpeza e correções pontuais

- Código morto removido: `src/components/sislab/cadastro_funcionario_component.py`
  (importava classe inexistente `CadastroFuncionarioFlow`; nada no projeto o referenciava).
- Arquivo renomeado na migração: `cadastrar_orientação_flow.py` →
  `cadastrar_orientacao_flow.py` (era o único arquivo do projeto com acento no nome).
- Imports corrigidos em testes de integração (SisLab ×2, MSI3 ×1, SI3 jornadas ×3).
- `vtae/core/dsl_interpreter.py`: branch `msi3` corrigido para o novo caminho.

---

## 3. O que FALTA — dívida estrutural

Esta seção é o núcleo do problema levantado: o framework hoje **não permite
escrever um teste novo com pouco código**. Cada item abaixo é uma causa concreta
disso, verificada no código.

### 3.1 Modelo de Elemento aplicado pela metade — dentro do próprio piloto

O `CadastroPacienteMinFlow` (piloto da Fase 0) usa **duas formas diferentes** de
localizar um elemento, no mesmo arquivo:

- `CM01`, `CM02`, `CM03`, `CM05`, `CM07`, `CM09`, `CM10` → `ctx.objects.coord("...")`
  (Modelo de Elemento — forma nova)
- `CM06`, `CM08` → `self._coord(coords, "...")`
  (coordenada direta do `config.yaml` — forma antiga)

Enquanto o piloto tiver duas formas convivendo, não existe padrão para propagar.

### 3.2 A terceira camada (pyjab) nunca chegou ao piloto

A Fase 0 previa 3 camadas: OpenCV (clique/navegação) + OCR (texto) + pyjab
(leitura exata em Oracle Forms).

Estado real: `_verify_campo_via_jab` aparece em **1 flow apenas**
(`AdmissaoAmbulatorioFlow`), além do helper em `base_flow.py`.
**Nenhum step do `CadastroPacienteMinFlow` usa pyjab.**

### 3.3 Campos do mesmo TIPO com código diferente cada um

`CM06` (Sexo), `CM07` (Nacionalidade) e `CM08` (Cor/Etnia) são todos campos do
**mesmo tipo** — lista / LOV. Mas cada um tem seu próprio bloco de código:

- `CM06` — clicar → digitar → TAB → OK (inline no step)
- `CM07` — ~100 linhas, `if BRASILEIRO / elif ESTRANGEIRO / else NATURALIZADO`,
  3 popups distintos, 3 helpers privados
  (`_preencher_popup_brasileiro` / `_estrangeiro` / `_naturalizado`)
- `CM08` — usa `_selecionar_em_lov` (o helper genérico que já existe)

Nenhum motivo técnico obriga essa divergência — é ausência de um contrato
"campo tipo lista + valor" que o motor genérico resolva sozinho.

### 3.4 Helpers *bespoke* reinventando a mesma ideia em cada flow

A mesma operação — clicar em algo e confirmar que a tela reagiu — está
reescrita com nomes e lógicas diferentes por flow:

| Flow | Helper próprio | O que faz |
|---|---|---|
| `AgendamentoFlow` | `_fechar_popup_ok` | fecha popup se aparecer |
| `CadastroFuncionarioFlowSislab` | `_clicar_com_fallback` | template → coordenada fixa |
| `CadastroPacienteMinFlow` | `_verificar_popup_erro_incor`, `_aguardar_popup_fechar`, `_aguardar_titulo_janela` | detecção/espera de popup |
| MSI3 | `ApexHelper` (classe inteira) | espera/erro/grade no APEX |

O `base_flow.py` já tem `_clicar_aguardar()` genérico — mas os flows não o usam
de forma consistente.

### 3.5 Coordenadas *hardcoded* preservadas

`CadastroFuncionarioFlowSislab` mantém constantes de classe
(`_COORD_BTN_FUNCIONARIOS`, `_COORD_BTN_NOVO`, `_COORD_BTN_SALVAR`,
`_REGIAO_GRADE`, `_CARGO_POSICAO`, `_DEPTO_POSICAO`). Migradas verbatim,
por decisão consciente de não alterar lógica durante a migração — mas seguem
como dívida.

---

## 4. O que FALTA — pendências operacionais

### 4.1 Arquivos duplicados ainda em `src/flows/`

Estes 4 arquivos têm versão oficial em `vtae/` mas **continuam existindo** em
`src/` (a deleção nunca chegou a ser solicitada):

- `src/flows/si3/agendamento_flow.py`
- `src/flows/si3/login/login_si3_flow.py`
- `src/flows/sislab/login_flow_sislab.py`
- `src/flows/sislab/cadastro_funcionario_flow_sislab.py`

### 4.2 Imports quebrados dentro de `vtae/`

`vtae/core/dsl_interpreter.py`, método `_action_login`:

- linha 206 — `from src.flows.sislab.login_flow import LoginFlow`
  → módulo **nunca existiu** (o arquivo real é `login_flow_sislab.py`,
  classe `LoginFlowSisLab`). Quebrado desde antes da migração.
- linha 210 — `from src.flows.login_flow import LoginFlow` (fallback genérico)
  → módulo **não existe**.

### 4.3 Testes de integração quebrados (fora do escopo da migração)

- `tests/integration/msi3/jornadas/anestesia_pre_operatorio/test_frequencia_aplicacao.py`
  → importa `FrequenciaAplicacaoFlow`, que **não existe em lugar nenhum** do projeto;
  além disso `configs/msi3/config.yaml` não existe (erro de coleta no pytest).
- `tests/integration/si3/test_login_real.py`
  → importa `vtae.core.observer` (o correto é `vtae.report.observer`).

### 4.4 Bootstrap dos testes de jornada (tarefa aberta)

Não existe `conftest.py` em `tests/integration/`. Cada teste de jornada só traz um
comentário de pré-condição ("SisLab aberto e maximizado", "MSI3 acessível via
browser") e exige que o sistema seja aberto **manualmente** antes de rodar.

### 4.5 Baseline de 89 falhas — conteúdo real

Estáveis desde o início da migração, concentradas em 4 arquivos:

| Arquivo | Qtd | Causa |
|---|---|---|
| `test_cadastro_paciente_flow.py` | ~82 | **bug real** — CP04 aborta com `not enough values to unpack (expected 2, got 0)`; o flow para no 4º de 27 steps |
| `test_login_flow_msi3.py` | 3 | assinatura: teste espera `wait_template(tpl, timeout=15.0)`, código chama `timeout=8, threshold=0.7` |
| `test_send.py` | 3 | "Nenhum relatório encontrado" na busca do relatório sislab |
| `test_config_loader.py` | 1 | comparação de string acentuada ("não encontrado" vs "nao encontrado") |

Nenhuma delas foi introduzida pela migração — mas a de `test_cadastro_paciente_flow.py`
indica um **bug real de produção** no CP04, não apenas um teste desatualizado.

---

## 5. Congelado / não iniciado

- **Banco (DatabaseRunner)** — congelado por decisão de segurança do InCor.
  `src/runners/database_runner.py` intocado; `_conectar_db` / `_obter_via_banco_ou_yaml`
  preservados em `base_flow.py`; fallback YAML funcional.
- **`src/core/object_repository.py`** — não migrado (por regra: exige confirmação explícita).
- **`src/config/`, `src/cli/`, `src/components/`** — não migrados
  (`loader.py`, `schema.py`, `run.py`, `send.py`, `summary.py`,
  `login_component.py`, `cadastro_paciente_component.py`, `apex_form_component.py`).
- **Record & Replay** — não iniciado, não escopado.

---

## 6. Pontos para decisão

1. **Consolidar o Modelo de Elemento** — unificar acesso a elemento (§3.1), levar
   pyjab ao piloto (§3.2) e transformar campo-do-mesmo-tipo em declaração
   em vez de bloco de código (§3.3). É o que destrava "escrever teste novo
   com pouco código".
2. **Eliminar helpers bespoke** (§3.4) em favor do que já existe genérico em
   `base_flow.py`.
3. **Higiene**: deletar os 4 duplicados (§4.1) e corrigir os imports quebrados (§4.2).
4. **Bug CP04** (§4.5) — decidir se entra agora ou depois.
5. **Bootstrap dos jornada tests** (§4.4) — tarefa aberta, não bloqueia nada.
