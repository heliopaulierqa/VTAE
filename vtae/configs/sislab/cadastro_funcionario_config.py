# vtae/configs/sislab/cadastro_funcionario_config.py
from faker import Faker

_fake = Faker("pt_BR")


class CadastroFuncionarioConfigSislab:
    """
    Credenciais e dados dinâmicos para o teste de cadastro de funcionário
    no SisLab (Oracle Forms desktop).

    DADOS é gerado a cada importação — cada execução usa um funcionário único,
    evitando conflitos de CPF duplicado no sistema.
    """

    USER     = "seu_usuario"   # substitua pelo usuário real
    PASSWORD = "sua_senha"     # substitua pela senha real
    SYSTEM   = "sislab"

    DADOS = {
        "nome":     _fake.name().upper(),
        "cpf":      _fake.cpf(),                          # formato: 000.000.000-00
        "cargo":    _fake.job()[:50].upper(),             # Oracle Forms limita o campo
        "salario":  str(_fake.random_int(min=1500, max=15000)),
        "admissao": _fake.date_of_birth(minimum_age=18, maximum_age=40)
                        .strftime("%m/%d/%Y"),            # formato mm/dd/yyyy conforme tela
    }
