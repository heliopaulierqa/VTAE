VTAE — Prompt de Instrução Geral do Projeto
Data: 30/07/2026 | Versão: v0.5.35 | Use este documento como primeira mensagem no próximo chat.
Referência acima deste documento: VTAE_Projeto_v1.md — a "constituição" do projeto. Este prompt é registro operacional: onde paramos e o que fazer a seguir. Para visão, fases e método, consultar o Projeto v1.

0. REGRAS DE TRABALHO — LEIA PRIMEIRO
ESTAS REGRAS SÃO INEGOCIÁVEIS E NUNCA PODEM SER QUEBRADAS:
NUNCA criar ou alterar arquivo sem que Helio veja o conteúdo atual primeiro
NUNCA gerar arquivo completo sem receber o upload do arquivo atual
AGUARDAR O UPLOAD antes de gerar qualquer código — jamais antecipar ou assumir conteúdo
Para alterações pontuais: informar exatamente ONDE e O QUE mudar — não gerar arquivo completo
NUNCA romper ou alterar nenhum contrato/padrão estabelecido sem que Helio saiba e aprove
NUNCA reescrever lógica de negócio de um flow — apenas as linhas explicitamente solicitadas
Quando um flow está validado e funcionando, qualquer mudança é CIRÚRGICA: confirmar com diff antes de entregar; zero alteração em qualquer step, helper ou lógica não solicitada.
Antes de responder sobre qualquer falha: pesquisar o histórico de chats — o padrão pode já ter sido resolvido antes.
Não propor soluções cosméticas — cada mudança responde uma das 5 perguntas de observabilidade. Testes veem o que acontece de verdade; nunca ancorar continuidade num elemento visual específico sem medir.
Não circular — se uma abordagem falhou 2x, propor alternativa diferente, não insistir.
Medir antes de confiar — diagnose() contra arquivo real (nunca tela ao vivo por engano) antes de rodar a jornada inteira.
Medir sensibilidade E especificidade — não só "o template acha o popup", mas "o template NÃO acha nada numa tela sem popup".
Gerar arquivo completo SOMENTE quando Helio pedir expressamente.
Nenhum .env pode ter comentário na mesma linha de um VAR=valor — comentário em linha separada, acima.
Mudanças de observabilidade são GATE: uma jornada de cada vez, 3x consecutivas antes de propagar.
Subprocessos do CLI sempre usam sys.executable, nunca a string "python" — EXCETO onde já documentado como dívida pré-existente (ver §6).
pyperclip.copy() + Ctrl+V precisa de delay mínimo (≥0.15s) entre as duas chamadas, e 0.5s entre clique em campo e ação seguinte.
Templates SEMPRE via pyautogui.screenshot() + PIL.crop() — nunca Win+Shift+S nem recorte colado no chat.
diagnose(): template primeiro, screenshot depois. O nativo sempre captura a tela ao vivo — para arquivo, sobrescrever matcher._capture_screen (scripts/diagnose_contra_arquivo.py).
regioes_ocr no YAML exige espaço após dois pontos: { x1: 27, y1: 145 }.
Coordenadas com janela maximizada. Preferir clique via template quando o elemento pode se deslocar (diálogos nativos do Windows que redimensionam com a mensagem).
Dois FlowContext separados quando dois flows têm configs diferentes.
_verify_campo_obrigatorio / _verify_campo_opcional exigem ocr_holder: list como último argumento.
Campos com reformatação automática (data, CPF, telefone) NÃO usam valor exato via OCR — verificação por estrutura (mínimo de dígitos), padrão CM05. Candidato a migrar para _verify_campo_via_jab.
ocr_lido propagado ao StepResult: step.ocr_lido = _ocr[0] if _ocr[0] is not None else ''.
Popups são âncoras frágeis para GUARDS GENÉRICOS — mas templates apertados de um ELEMENTO ESPECÍFICO E JÁ CONHECIDO continuam confiáveis quando medidos. Guard genérico entre todos os steps = frágil. Template específico de um popup conhecido, chamado no ponto certo (ex: _fechar_popups_convenio após digitar carteirinha) = padrão que funciona, desde que o recorte seja apertado.
Campo Profissional em lista de procedimentos SI3: não aceita digitação direta — _selecionar_via_lov.
max(numeros, key=len) no OCR de campos com múltiplos números.
Cenário negativo em Oracle Forms tem DUAS formas de falha silenciosa: (a) com popup específico e conhecido → template apertado do botão; (b) sem popup, match parcial em LOV → verificação estrutural via pyjab. NÃO existe mais guard genérico de popup entre steps.
Verificação estrutural via pyjab é uma segunda camada, PARALELA ao OCR — VALIDADA 3x CONSECUTIVAS. Lê o valor real do componente (.text), comparação exata, sem tolerância Levenshtein. JABDriver conecta sob demanda, cacheado em ctx.jab.
JAVA_HOME do pyjab é setado programaticamente no código, lido do config (.env), NUNCA via setx.
A escolha da camada de verificação por tipo de campo segue a matriz da seção 6. pyjab não substitui OCR/OpenCV/Playwright — complementa.
AdmissaoAmbulatorioFlow é o flow-modelo do projeto para padrões de verificação e observabilidade. Padrões estruturais novos (Modelo de Elemento, ObjectRepository) estreiam no CadastroPacienteMinFlow na Fase 0.
DatabaseRunner: CONGELADO por decisão de segurança do InCor até liberação. Nada nas Fases 0–5 depende de banco.
Padrão de aprendizado (regra 43): nenhum código entra sem que Helio explique o que faz e por quê. Todo diff vem com (a) o que muda, (b) por que muda, (c) qual conceito Python está em jogo. Helio digita diffs pequenos, não cola. Fim de sessão: Helio resume em 2 frases o que foi feito.
[NOVA v0.5.35] Regra de disciplina anti-especulação (aprendida em 29-30/07): diante de uma falha, medir e reverter empiricamente ANTES de gerar hipóteses. Se Helio disser "para de especular", a resposta correta é reverter a última mudança documentada e testar — não propor nova teoria.
[NOVA v0.5.35] Ambiente: o sandbox Linux de Claude (bash/shell) pode ficar indisponível em algumas sessões. Quando isso ocorrer, todo trabalho em arquivos do projeto continua via leitura/edição direta na pasta conectada do Windows — sem acesso a delete de arquivo. Exclusões ficam pendentes até Helio rodar o comando manualmente (PowerShell) ou o sandbox voltar.

1. O que é o VTAE
Framework híbrido de automação de testes hospitalares do InCor (São Paulo). Combina OpenCV, Playwright, EasyOCR, pyjab/Java Access Bridge e oracledb (DatabaseRunner) para automatizar sistemas legados (SI3, SisLab — Oracle Forms) e modernos (MSI3 — Oracle APEX).
Versão atual: v0.5.35
Python: 3.13+
Fase atual (Projeto v1): Fase 0 — Piloto do Modelo de Elemento. Piloto no CadastroPacienteMinFlow (CM01–CM10). Banco congelado por segurança.
Documento de referência: VTAE_Projeto_v1.md

2. Estado atual dos flows — inalterado desde v0.5.32
(ver tabela completa no Projeto v1; nenhum flow mudou de status nesta sessão — trabalho foi 100% estrutural: migração de pastas e correção de um bug de observabilidade em CadastroPacienteMinFlow, sem tocar lógica de negócio de nenhum flow)

3. O que foi feito na sessão de 29-30/07/2026 (v0.5.34 → v0.5.35)
3.1 [FEITO] Diagnosticado e corrigido: flakiness de conexão pyjab em CadastroPacienteMinFlow
Sintoma: `vtae run --test cadastro_paciente_min` começou a falhar de forma intermitente no campo CM06 (Sexo) — primeiro campo verificado via pyjab no flow — com "HWND is not Java Window".
Hipóteses especulativas levantadas e descartadas com evidência do próprio Helio: Hyper-V/reboot (sem reboot confirmado), terminal elevado como causa diferencial (elevado há 6 meses sem problema — não é a variável que mudou), mismatch de elevação terminal↔SI3 (especulação sem medição, rejeitada por Helio: "para de especular").
Ação tomada por instrução direta de Helio: reverter `_verificar_via_jab_se_mapeado` em `vtae/flows/si3/cadastro_min/cadastro_paciente_min_flow.py` do comportamento hard-fail (`raise AssertionError` quando JABDriver não conecta) de volta ao comportamento tolerante (log de aviso + `return`, verificação pyjab pulada naquele campo), igual ao padrão já usado para objetos não mapeados.
Resultado: 4 execuções consecutivas verdes. Log de evidência (`execution.log`) confirma o padrão real: CM06 falha a primeira tentativa de conexão JAB (janela SI3 recém-aberta, ainda registrando no Access Bridge) e segue OCR-only; CM07/CM08, tentados ~20-40s depois na mesma run, conectam e verificam com sucesso (`jab_lido: 'BRASILEIRO'`, `jab_lido: 'AMARELA'`).
Causa raiz real: race condition de startup no registro do Java Access Bridge da janela SI3 — não é bug de código, é timing. **Não corrigido** — é workaround aceito por decisão explícita de Helio ("fecha por aqui"). CM06 roda hoje sem verificação pyjab real (só OCR); CM07/CM08 verificam normalmente.
3.2 [FEITO] Migração completa `src/` → `vtae/` — item 1 do §5 do Projeto v1
Executada em 3 etapas aprovadas por Helio, com checagem de zero-regressão (baseline `pytest tests/unit`: 799 passed / 89 failed) após cada etapa:
Etapa 1 — módulos-folha sem import interno de `src`: `core/object_repository.py`, `runners/database_runner.py`, `components/si3/login_component.py`, `components/si3/cadastro_paciente_component.py`, `components/msi3/apex_form_component.py`. Regressão encontrada e corrigida: `tests/unit/test_base_flow.py` mockava `src.runners.database_runner.DatabaseRunner` (import local dentro de função — o patch precisa mirar o módulo-fonte, não o importador). Corrigido para `vtae.runners.database_runner.DatabaseRunner`.
Etapa 2 — `config/`: `schema.py`, `loader.py`, `__init__.py`, mais 15 arquivos consumidores repontados de `from src.config` para `from vtae.config`.
Etapa 3 — `cli/`: `run.py`, `send.py`, `summary.py`, `__init__.py`. Fix crítico: `pyproject.toml` `[project.scripts]` apontava `vtae = "src.cli.run:main"` — sem essa correção o comando `vtae` do terminal continuaria rodando o `src/` órfão para sempre, mesmo com todo o código migrado. Corrigido para `vtae.cli.run:main`; `pip install -e .` rodado por Helio para regenerar o entry point.
Verificação end-to-end real (não só pytest): `vtae systems` executado por Helio, retornou "sislab" — confirmado como comportamento correto e pré-existente (ConfigLoader só detecta configs a um nível de profundidade; SI3/MSI3 estão mais aninhados), não regressão.
3.3 [FEITO] Apagado `src/` residual
Helio rodou `Remove-Item -Recurse -Force src` (PowerShell). Confirmado zero regressão: `pytest tests/unit -q` → 799 passed / 89 failed, idêntico ao baseline.
Ajuste cosmético em `pyproject.toml`: `[tool.setuptools.packages.find] include` tinha `["src*", "vtae*"]` — removido `"src*"` (pasta não existe mais). Reinstalação (`pip install -e .`) + `pytest tests/unit -q` a confirmar no início da próxima sessão (ver pendência #1).
3.4 [CONTEXTO] Skill `vtae-jab-mapping` salva nesta sessão
Procedimento documentado e salvo como skill reutilizável: descoberta de `jab_name` via Java Access Bridge (precondições, dump, busca por valor, desambiguação por role, escrita no YAML).

4. Pendências imediatas (ordem de execução)
#
Pendência
Prioridade
Depende de
1
Confirmar `pip install -e .` + `pytest tests/unit -q` = 799/89 após remoção de "src*" do pyproject.toml
🔴 imediato — fecha a sessão anterior
—
2
CadastroMin (Fase 0): Helio envia `cadastro_paciente_min_flow.py` + `config.yaml` do cadastro — abre o Plano da Fase 0 (ObjectRepository)
🔴 imediato
#1
3
Claude devolve desenho em português do ObjectRepository (formato YAML + adapter) — zero código neste passo
🔴 imediato
#2
4
Helio valida o desenho — "faz sentido" antes de qualquer código
🔴 imediato
#3
5
Implementar ObjectRepository (~60-80 linhas) + `objects/cadastro_min.yaml`
🔴 imediato
#4
6
Rodar 3x consecutivas sem regressão no CadastroMin — fecha gate da Fase 0
🔴 gate
#5
7
CM06 (Sexo) roda sem verificação pyjab real por race condition de startup — considerar retry/delay se voltar a incomodar (declarado fora de escopo por ora)
🟡 conhecido, não bloqueia
—
8
Mapear names pyjab restantes (AB06, AB09, AB10, AB11, AB12)
🟡 paralelo
—
9
`tests/integration/msi3/jornadas/anestesia_pre_operatorio/test_frequencia_aplicacao.py` importa `src.flows.msi3...` — caminho que nunca existiu de fato (pré-existente, fora do escopo da migração, não está em `tests/unit`)
🟡 conhecido, não bloqueia
—
10
Escolher aplicação Citrix candidata a cliente 2 (Fase 3)
🟡 a definir
Helio
11
Todos os itens de banco suspensos até liberação do InCor
⏸ congelado
Liberação segurança

5. Padrões consolidados de código — inalterados desde v0.5.32
Ver seção 5 do prompt v0.5.32/v0.5.34 (não reproduzido aqui por brevidade — nenhuma mudança de padrão nesta sessão, só localização de arquivo). Principais: `_verify_campo_obrigatorio`/`_verify_campo_opcional`, `_verify_campo_via_jab`, fallback banco→YAML (congelado), `diagnose_contra_arquivo`, guard genérico revogado, `_db_assert_admissao` (esqueleto preservado, congelado).

6. Matriz de decisão — qual camada verifica o quê
Inalterada — ver Projeto v1 §6 ou prompt v0.5.32.

7. Padrões Oracle Forms consolidados
Inalterados — ver Projeto v1 ou prompt v0.5.32. Um item novo, empírico, desta sessão: a janela do SI3 pode levar dezenas de segundos após abrir para terminar de se registrar no Java Access Bridge — o primeiro campo verificado via pyjab no fluxo é o mais sujeito a essa falha de conexão inicial.

8. Arquitetura atual — pasta única `vtae/`
```
vtae/
├── cli/            (run.py, send.py, summary.py)
├── components/     (si3/, msi3/)
├── config/         (loader.py, schema.py)
├── core/           (object_repository.py, + demais já existentes)
├── flows/          (si3/, msi3/ — todo o código de negócio, intocado)
├── runners/        (database_runner.py, + demais já existentes)
└── ...
```
`src/` não existe mais. Todo import no projeto usa `from vtae....`. Entry point do CLI (`pyproject.toml [project.scripts]`) aponta para `vtae.cli.run:main`.

9. Próximo passo concreto (início do próximo chat)
Confirmar o resultado do `pip install -e .` + `pytest tests/unit -q` pendente (item 1) — deve bater 799/89.
Depois disso, a migração estrutural está oficialmente fechada. Abrir a Fase 0 de fato: Helio envia os arquivos atuais do CadastroMin (`cadastro_paciente_min_flow.py` + `config.yaml`) para Claude desenhar o ObjectRepository em português, sem código, seguindo a regra de aprendizado (regra 43).
Marco desta sessão (29-30/07, v0.5.35): flakiness de pyjab em CM06 diagnosticada e revertida para comportamento tolerante por decisão empírica de Helio (não especulativa); migração completa `src/` → `vtae/` executada em 3 etapas com zero regressão, incluindo fix do entry point do CLI; `src/` apagado por Helio e confirmado sem regressão; pyproject.toml limpo do resíduo `"src*"`; skill `vtae-jab-mapping` salva.
