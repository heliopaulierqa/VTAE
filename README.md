VTAE — Visual Test Automation Engine

Automação de testes via visão computacional para sistemas legados.

Show Image
Show Image
Show Image

O que é o VTAE
O VTAE é um framework de automação de testes construído sobre visão computacional. Em vez de depender de seletores HTML ou APIs do sistema, ele interage com a tela como um usuário humano: localiza elementos por imagem, clica, digita e captura evidências em cada etapa.
Ideal para sistemas legados onde não há acesso ao código-fonte ou a APIs de automação.

Instalação
Dependências Python
bashpip install opencv-python pyautogui pillow numpy

# Verificar instalação
python -c "import cv2, pyautogui, numpy; print('ok')"
Dependências do projeto (modo desenvolvimento)
bashpip install pytest pytest-cov

# Rodar testes unitários
PYTHONPATH=. python -m pytest vtae/tests/unit/ -v

Windows (PowerShell): substitua PYTHONPATH=. por $env:PYTHONPATH=".";


Estrutura do projeto
vtae/
├── core/
│   ├── base_runner.py      # contrato abstrato do runner
│   ├── context.py          # FlowContext — contexto compartilhado
│   └── result.py           # StepResult e FlowResult
├── flows/
│   ├── login_flow.py       # fluxo de login
│   ├── admissao_flow.py    # fluxo de admissão
│   └── suprimentos_flow.py
├── runners/
│   └── opencv_runner.py    # runner real (visão computacional)
├── components/
│   └── login_component.py  # bloco reutilizável com validação
├── configs/
│   └── sislab/
│       └── login_config.py
├── legacy/
│   └── login.py            # código antigo isolado
├── dsl/
│   └── interpreter.py      # executa testes escritos em YAML
├── cli/
│   └── run.py              # interface de linha de comando
└── tests/
    ├── conftest.py         # fixtures compartilhadas
    ├── unit/               # testes sem tela real (32 testes)
    └── integration/        # testes com sistema real

Como usar
1. Testes unitários (sem tela real)
bash# Rodar todos os testes unitários
PYTHONPATH=. python -m pytest vtae/tests/unit/ -v

# Com relatório de cobertura
PYTHONPATH=. python -m pytest vtae/tests/unit/ --cov=vtae
2. Teste de integração (com sistema real)
bash# 1. Abra o sistema alvo na tela
# 2. Garanta que os templates estão em templates/sislab/
# 3. Execute:
PYTHONPATH=. python -m pytest vtae/tests/integration/ -v -s

O flag -s mostra os prints em tempo real — útil para acompanhar a execução.

3. Via CLI
bashpython -m vtae.cli.run run --all
python -m vtae.cli.run run --module admissao
python -m vtae.cli.run run --test login
4. Via DSL (YAML)
Crie um arquivo em tests_yaml/ com a seguinte estrutura:
yaml# tests_yaml/login_admissao.yaml
flow: admissao
steps:
  - action: login
  - action: click
    template: templates/sislab/admissao/btn_modulo.png
  - action: wait
    template: templates/sislab/admissao/tela_admissao.png
  - action: screenshot
    name: admissao/evidencia_01.png

FlowContext — conceito central
O FlowContext é o objeto que circula por todos os flows. Em vez de passar runner, config, user, password separadamente em cada método, tudo fica encapsulado em um único contexto:
pythonfrom vtae.runners.opencv_runner import OpenCVRunner
from vtae.core.context import FlowContext
from vtae.configs.sislab.login_config import LoginConfigSisLab

runner = OpenCVRunner(confidence=0.8)
ctx = FlowContext(
    runner=runner,
    config=LoginConfigSisLab,
    evidence_dir="evidence/",
)

# ctx.user      → "admin"  (vem do config)
# ctx.password  → "123"
# ctx.runner    → instância do OpenCVRunner

Capturar templates
O OpenCVRunner localiza elementos na tela comparando com imagens de referência (templates). Para criar os templates:

Abra o sistema alvo (ex: SisLab)
Use a ferramenta de recorte — Win + Shift + S no Windows
Recorte apenas o elemento: botão, campo, ícone — sem fundo desnecessário
Salve como .png na pasta correta:

templates/
└── sislab/
    └── login/
        ├── btn_usuario.png
        ├── btn_senha.png
        └── btn_entrar.png

Dica: quanto menor e mais específico o recorte, menos falsos positivos.


Convenção de IDs de steps
PrefixoFlowL01, L02...LoginFlowA01, A02...AdmissaoFlowS01, S02...SuprimentosFlow
Os IDs aparecem nos logs, nos nomes dos screenshots de evidência e nos relatórios de falha.

Status das fases
#FaseStatus1Consolidação (estrutura de pastas)✅ Concluída2Flows (Login, Admissão, Suprimentos)✅ Concluída3Robustez (retry, timeout, safe_click)🟡 Em andamento4Observabilidade (logs, evidências, métricas)🔜 Planejada5DSL — testes em YAML🟣 Estrutura criada6CLI — execução por terminal🟣 Estrutura criada7CI/CD — pipeline automático🔜 Planejada8Interface gráfica (opcional)🔜 Planejada

Changelog
v0.2.0

BaseRunner, FlowContext, StepResult, FlowResult
LoginFlow, AdmissaoFlow, SuprimentosFlow com steps tipados
OpenCVRunner — runner real com visão computacional
DSL interpreter para testes em YAML
CLI: vtae run --all / --module / --test
32 testes unitários com runner mockado
pyproject.toml, Makefile, CHANGELOG.md

v0.1.0

Estrutura inicial de pastas
LoginFlow, AdmissaoFlow, SuprimentosFlow (esqueletos)
LoginConfigSisLab


Próximos passos

 Fase 3 — Robustez: implementar retry real no OpenCVRunner
 Fase 4 — Observabilidade: logs estruturados por step, métricas de execução
 Capturar templates reais do SisLab
 Criar primeiro teste de integração com sistema real