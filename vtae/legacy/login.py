"""
Módulo legado — mantido para compatibilidade.
Não adicionar nova lógica aqui. Migrar para flows/ gradualmente.
"""


def force_login(runner, user: str = "admin", password: str = "123") -> None:
    """Login legado. Aceita credenciais opcionais para facilitar migração."""
    print(f"[legacy] Executando force_login (user={user})")
    # Implementação real com runner vai aqui:
    # runner.safe_click("templates/sislab/login/btn_usuario.png")
    # runner.type_text(user)
    # runner.safe_click("templates/sislab/login/btn_senha.png")
    # runner.type_text(password)
    # runner.safe_click("templates/sislab/login/btn_entrar.png")
    # runner.wait_template("templates/sislab/login/tela_principal.png")
