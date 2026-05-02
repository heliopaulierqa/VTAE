# vtae/configs/sislab/cadastro_funcionario_config.py
from faker import Faker

_fake = Faker("pt_BR")


class CadastroFuncionarioConfigSislab:
    USER     = "admin"
    PASSWORD = "admin123"

    DADOS = {
        "nome":       _fake.name().upper(),
        "cpf":        _fake.cpf().replace(".", "").replace("-", ""),
        "cargo":      "ANALISTA DE RH",        # dropdown fixo — opções: ANALISYTA DE QA, ANALISTA DE RH
        "departamento": "ADMINISTRAÇÃO",        # dropdown fixo — opções: TECNOLOGIA DA INFOMAÇÃO, ADMINISTRAÇÃO, RECUSROS HUMANOS
        "salario":    str(_fake.random_int(min=2000, max=9999)),
        "admissao":   _fake.date_of_birth(minimum_age=18).strftime("%m/%d/%Y"),
    }
