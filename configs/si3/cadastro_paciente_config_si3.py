# vtae/configs/si3/paciente_config.py
from faker import Faker

_fake = Faker("pt_BR")


class CadastroPacienteConfigSi3:
    """
    Credenciais e dados dinamicos para o teste de cadastro de paciente
    no SI3 (Oracle Forms desktop).
    DADOS gerado a cada importacao — cada execucao usa um paciente unico.
    """

    USER     = "seu_usuario"
    PASSWORD = "sua_senha"
    SYSTEM   = "si3"

    DADOS = {
        "nome":            _fake.name().upper(),
        "nome_social":     "",   # opcional — preencher se necessario
        "data_nascimento": _fake.date_of_birth(
                               minimum_age=18, maximum_age=80
                           ).strftime("%d/%m/%Y"),
        "hora":            "00:00",
        "sexo":            _fake.random_element(["M", "F"]),
        "nacionalidade":   "BRASILEIRO",
        "mae":             _fake.name_female().upper(),
        "pai":             _fake.name_male().upper(),
        "cor_etnia":       "BRANCA",
        "cpf":             _fake.cpf().replace(".", "").replace("-", ""),
    }
