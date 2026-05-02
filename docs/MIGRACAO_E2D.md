# E2-D — Guia de migração: *_config.py → ConfigLoader

## Antes (vtae/configs/sislab/cadastro_funcionario_config.py)

```python
from faker import Faker
_fake = Faker("pt_BR")

class CadastroFuncionarioConfigSislab:
    USER     = "admin"
    PASSWORD = "admin"
    DADOS = {
        "nome":         _fake.name().upper(),
        "cpf":          _fake.cpf().replace(".", "").replace("-", ""),
        "cargo":        "ANALISTA DE RH",
        "departamento": "ADMINISTRAÇÃO",
        "salario":      str(_fake.random_int(min=2000, max=9999)),
        "admissao":     _fake.date_of_birth(minimum_age=18).strftime("%m/%d/%Y"),
    }
```

## Depois (vtae/tests/integration/sislab/test_cadastro_funcionario_sislab.py)

```python
from src.config.loader import ConfigLoader

def test_cadastro_funcionario_sislab():
    # carrega config do YAML — ambiente dev por padrão
    config = ConfigLoader.carregar("sislab")

    observer = ExecutionObserver(test_name="test_cadastro_funcionario_sislab")
    runner   = OpenCVRunner(confidence=config.confidence)
    ctx      = FlowContext(
        runner=runner,
        config=config,
        evidence_dir=observer.evidence_dir,
    )
    ...
```

## Compatibilidade garantida

O SystemConfig expõe as mesmas propriedades que os *_config.py antigos:
- config.USER       → credenciais.usuario resolvido
- config.PASSWORD   → credenciais.senha resolvida
- config.DADOS      → dict gerado pelo Faker conforme config.yaml
- config.url        → URL do ambiente ativo
- config.confidence → threshold do ambiente ativo

O FlowContext acessa ctx.config.USER e ctx.config.PASSWORD via as propriedades
do SystemConfig — zero mudança nos flows.

## Período de transição

Durante a transição, os *_config.py podem coexistir com o ConfigLoader.
Migrar um teste por vez, verificando que continua passando após cada migração.

Os *_config.py serão removidos na E4 junto com os aliases vtae/.
