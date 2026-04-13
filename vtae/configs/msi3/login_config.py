class LoginConfigMsi3:
    USER = "helio.paulier"
    PASSWORD = "helio.paulier"
    SYSTEM = "msi3"
    URL = "https://lebombo.incor.usp.br:8443/apex_protot/r/paciente/usu0010/login_desktop"

    # Seletores CSS dos campos de login
    CAMPO_USUARIO = "#P9999_USERNAME"
    CAMPO_SENHA = "#P9999_PASSWORD"

    # Elemento que confirma login bem-sucedido
    # Ajuste para um seletor que aparece após o login no MSI3
    TELA_PRINCIPAL = "h3.t-Card-title"
