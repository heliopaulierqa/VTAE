# VTAE — Prompt de Instrução Geral do Projeto
**Data:** 06/08/2026 | **Versão:** v0.5.49 — SESSÃO ENCERRADA (gate fechado, commit feito)
Use este documento como primeira mensagem no próximo chat.
Referência acima deste documento: **`docs/VTAE_Projeto_v0.1.md`** (documento VIVO — consolida e substitui v1/v1.1)
e **`docs/VTAE_Manual_Tecnico_v0.1.md`** (documento VIVO — substitui Manual v1).
Este prompt é registro operacional: onde paramos e o que fazer a seguir.

---
## 0. REGRAS DE TRABALHO — LEIA PRIMEIRO
**ESTAS REGRAS SÃO INEGOCIÁVEIS.** As regras 1–75 do v0.5.48 continuam
valendo integralmente. Abaixo, o que nasceu nesta sessão.

### Regras novas (76–78)
76. **Este documento é atualizado EM TEMPO REAL, a cada decisão fechada —
    não no fim da sessão.** Claude escreve o delta no arquivo em disco no
    momento em que a decisão acontece. Sessão cair no meio, nada se perde.
    Isso já tinha sido acordado antes e não estava sendo cumprido — a
    partir de agora é regra numerada e cobrável.
77. **Papel de Claude na construção de testes: NÃO escreve testes novos.**
    Helio escreve; Claude revisa, explica conceitos, aponta onde e por quê.
    O cadastro_min é a BANCADA onde os padrões são fechados (gates). Depois
    dos gates, todos os testes novos são construídos por Helio do zero,
    usando o padrão de 5 peças: YAML de flow + objects YAML + templates +
    config + boot pytest.
78. **Durante execução em tela real, o SI3 é dono da tela.** Nenhuma janela
    pode cobrir o formulário — OCR lê a tela inteira, quem está na frente
    vence. Rodar preferencialmente de PowerShell avulso (fora do VS Code),
    minimizar após o Enter. Fato medido 2x em 05/08 (tarde-2): S07 falhou
    nas duas rodadas com o VS Code restaurado por cima do Form_Pac0010 no
    momento da leitura OCR do sexo — região (543,192,633,212) lia pixels
    do terminal. CAUSA DA RESTAURAÇÃO DO VS CODE AINDA NÃO MEDIDA (Helio
    afirma que fica minimizado; auto_diag mostra restaurado — não se sabe
    o que o traz à frente; rodada 3 em PowerShell avulso isola a questão).
79. **Documentos vivos únicos (decisão de Helio, 05/08):**
    `docs/VTAE_Projeto_v0.1.md` e `docs/VTAE_Manual_Tecnico_v0.1.md` são a
    fonte da verdade e DEVEM ser consultados no início de cada sessão e
    atualizados EM TEMPO REAL. Neles vive o histórico: o que FOI FEITO, o que
    ESTÁ SENDO FEITO e o que VAI SER FEITO (Projeto §2). As versões antigas
    (Projeto v1/v1.1/PROPOSTA, Manual v1, documentacao_tecnica_v.0) serão
    apagadas por Helio.

---
## 1. O que é o VTAE
Framework híbrido de automação de testes hospitalares do InCor. OpenCV,
Playwright, EasyOCR, pyjab/JAB e oracledb (congelado) para sistemas
legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — APEX).
- **Versão:** v0.5.49 · **Python:** 3.13+
- **Documento de referência:** `docs/VTAE_Projeto_v1.1.md`
- **Fase atual:** **Fase 2 — O MOTOR.** Motor validado 17/17 em tela real
  (manhã 05/08). Gate 3x EM ANDAMENTO — 2 rodadas falharam por
  interferência de janela (regra 78), não por defeito do motor.

---
## 2. Decisões fechadas NESTA sessão (05/08 tarde-2)
1. **Commit do v0.5.48 realizado** (9 arquivos) — pendência #1 anterior fechada.
2. **Ordem de trabalho revisada e aprovada por Helio:**
   gate 3x → limpeza da geração 2 → triagem dos 86 unitários vermelhos →
   unitário do LeitorJab.
3. **Papel do cadastro_min esclarecido por Helio:** é bancada para fechar
   os padrões. Nada dele será aproveitado como teste de produção. Após os
   gates, HELIO constrói todos os testes do zero (regra 77).
4. **Avaliação do projeto feita a pedido de Helio.** Conclusão: o repositório
   carrega 3 gerações simultâneas (flows antigos; geração intermediária
   morta — dsl_interpreter 673 linhas, components/, object_repository,
   objects antigo; motor novo). A sensação de complicação vem daí. Maior
   problema: 86 unitários sempre vermelhos ensinam a ignorar vermelho.
5. **Atualização deste documento em tempo real** (regra 76).

---
## 3. O que mudou no código nesta sessão
### 3.1 `vtae/cli/run.py` — 3 correções
- `"python"` → `sys.executable` nas DUAS chamadas de subprocess
  (linhas ~105 e ~266) — regra 30, que estava violada ali.
- `-s` adicionado ao pytest — o console era capturado e a execução parecia
  travada (foi o gatilho da 1ª rodada perdida: Helio foi olhar o terminal
  "travado" e a janela cobriu o SI3).
- `--count={repeat}` agora só entra quando `repeat > 1` — o plugin
  pytest-repeat não existe no .venv.
- **DESCOBERTA IMPORTANTE:** com `"python"` no PATH, o CLI rodava os testes
  no **Python GLOBAL** (C:\Users\...\Python313), não no .venv. Todos os
  resultados anteriores do `vtae run` rodaram fora do venv sem ninguém
  saber. Com `sys.executable` o ambiente ficou honesto. O .venv NÃO tem:
  pytest-repeat, allure-pytest, base-url, playwright plugin (o global
  tinha). Instalar no venv conforme necessidade for aparecendo.

### 3.2 `configs/si3/si3_cadastro_paciente_min/config.yaml`
`nacionalidade_opcoes` reduzida para gate — rodada atual: só ESTRANGEIRO
ativo (BRASILEIRO e NATURALIZADO comentados, com comentário explicando).
**RESTAURAR as 3 opções após o gate.**

---
## 4. Gate 3x — estado ao vivo
| Rodada | Nacionalidade | Resultado | Causa |
|---|---|---|---|
| 1 (13:40) | ESTRANGEIRO (sorteio nem chegou lá) | ❌ S07 sexo — OCR leu '' 5x | VS Code cobrindo o form (S07_auto_diag_001.png) + console capturado sem -s |
| 2 (13:52) | ESTRANGEIRO (idem) | ❌ S07 sexo — OCR leu '' 5x | VS Code cobrindo o form DE NOVO (auto_diag 13:53). Campo estava PREENCHIDO (FEMININO no print de Helio) — falhou a leitura, não o preenchimento |
| 3 | — | PENDENTE | Protocolo: PowerShell avulso fora do VS Code, minimizar após Enter, mãos fora até o fim |

**ATUALIZAÇÃO 15:14 — caminho ESTRANGEIRO FECHADO: 3 execuções consecutivas
17/17 verde em PowerShell avulso (15:10, 15:12, 15:14).** Nas 2 primeiras o
pyjab não conectou e o OCR validou (degradação funcionou); na 3ª conectou
(decisor exata nos 3 LOVs). Conexão pyjab medida como INSTÁVEL com tela limpa
— correlação com janela na frente descartada; causa pendente de medição.
**ATUALIZAÇÃO FINAL 06/08 08:25 — GATE FECHADO: ESTRANGEIRO 3x +
NATURALIZADO + BRASILEIRO, 5 execuções consecutivas 17/17. BRASILEIRO com
decisor exata nos 3 LOVs. Config restaurado (3 opções). Placar pyjab: 2
conexões em 6 rodadas limpas — instabilidade registrada, investigação na
fila.** Próximo: commit → limpeza da geração 2.

### Fato registrado SEM causa confirmada (não especular — regra 36)
- pyjab não conectou nas 2 rodadas: `HWND:xxxx is not Java Window`
  (HWND diferente a cada rodada). Na rodada verde da manhã conectou.
  Correlação observada: nas 2 falhas o VS Code estava na frente no momento
  da conexão. CAUSA NÃO MEDIDA. A rodada 3 limpa decide: se conectar,
  era a janela; se falhar de novo, investigar pyjab (init/pump da
  WindowsAccessBridge — hipótese, só olhar depois da medição).
- Debug do verify_lov vai para `/tmp/verify_lov_debug_*.png` — caminho
  POSIX escrito literalmente; no Windows cai na raiz do drive corrente.
  Candidato a correção: salvar na pasta de evidence. (menor, não urgente)

---
## 5. Pendências (ordem acordada nesta sessão)
| # | Pendência | Prioridade |
|---|---|---|
| 1 | **Gate 3x** — rodada 3 em PowerShell avulso; depois NATURALIZADO e BRASILEIRO | 🔴 em andamento |
| 2 | Restaurar `nacionalidade_opcoes` (3 valores) no config após gate | 🔴 amarrada ao gate |
| 3 | **Limpeza da geração 2**: dsl_interpreter.py (673 linhas), vtae/components/, objects/cadastro_min.yaml antigo, object_repository (avaliar — o teste provisório ainda usa titulo_jab()), testes órfãos (test_dsl_interpreter, test_login_component, test_piloto_cadastro_min) | 🔴 após gate |
| 4 | **Triagem dos 86 unitários vermelhos** — agrupar por arquivo: (a) morrem com a limpeza, (b) obsoletos, (c) quebras reais | 🔴 após limpeza |
| 5 | Unitário do LeitorJab — desenho já aprovado (FakeDriver injetado para ler(); fake em sys.modules para conexão) | 🟡 |
| 6 | Commit das mudanças desta sessão (run.py + config + este doc) | 🟡 quando gate fechar ou sessão encerrar |
| 7 | pesquisar() espera por título ambíguo ("Cadastro De Pacientes" = tela de Parâmetros também) — guard que não pode falhar | 🟡 herdada do v0.5.48 |
| 8 | Fixture si3 (peça 5) — aposenta o teste provisório | 🟡 herdada |
| 9 | Instalar no .venv os plugins pytest que faltam, conforme necessidade | 🟢 |
| 10 | verify_lov debug png: salvar em evidence, não /tmp | 🟢 |
| 11 | hora segue NAO_VERIFICAVEL (sem regiao_ocr, sem jab_name) | 🟢 herdada |
| 12 | args: do DadoFakerConfig não existe — nr_portaria ignora em silêncio | 🟢 herdada |
| 13 | Banco congelado até liberação do InCor | ⏸ |
| 14 | Atualizar custom instructions do projeto Claude (estão em v0.5.32) para apontar para docs/ como fonte da verdade | 🟢 Helio |

---
## 6. Como Helio quer trabalhar (reafirmado nesta sessão)
- Parceria: o que Claude descobre, Helio precisa saber junto. Ao abrir um
  arquivo, dizer QUAL e O QUE tem nele. Causa mostrada onde aparece (print,
  linha, número), não veredito.
- **Ação antes de teoria.** Menos explicação, mais efetividade. Não repetir
  o que já foi dito na sessão.
- Não pedir a Helio coisas que ele já fez — checar histórico e este doc antes.
- Claude NÃO escreve os testes novos (regra 77) — explica e revisa.
- Este documento atualizado em tempo real (regra 76).

---
## 7. Próximo passo concreto (início do próximo chat)
**Consultar PRIMEIRO os docs vivos: `docs/VTAE_Projeto_v0.1.md` (§2 —
feito/fazendo/a fazer) e `docs/VTAE_Manual_Tecnico_v0.1.md` (regra 79).**

1. **LIMPEZA DA GERAÇÃO 2** — Claude lista cada arquivo a deletar
   (dsl_interpreter.py, vtae/components/, objects/cadastro_min.yaml antigo,
   test_dsl_interpreter, test_login_component, test_piloto_cadastro_min) e
   verifica o que ainda os referencia (atenção: object_repository é usado
   pelo teste provisório via titulo_jab — avaliar). Helio aprova antes de
   qualquer remoção. Commit próprio.
2. Triagem dos 86 unitários vermelhos (agrupar por arquivo).
3. Unitário do LeitorJab (desenho já aprovado).
4. Investigar instabilidade pyjab (2 conexões em 6) — medição, não chute.
5. Peça 5 (fixture si3) e peça 6 (testes-padrão 3 linhas) fecham a Fase 2.
6. Depois: Fase 3 — HELIO escreve os testes do zero, Claude revisa (regra 77).

**Marco desta sessão (até agora):** o ambiente ficou honesto — descoberto
que o CLI rodava testes no Python global desde sempre (corrigido com
sys.executable); console ao vivo com -s; papel do cadastro_min e de Claude
esclarecidos; registro em tempo real instituído como regra 76. Gate 3x
em andamento, 0/3, duas falhas ambientais diagnosticadas por evidência.
