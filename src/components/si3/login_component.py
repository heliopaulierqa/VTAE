# src/components/si3/login_component.py
from src.core.context import FlowContext
from src.core.result import FlowResult
from src.flows.si3.login_flow import LoginFlow


class LoginComponent:
    """
    Componente de login reutilizável.
    Valida pré-condições antes de delegar ao LoginFlow.
    """
    def execute(self, ctx: FlowContext) -> FlowResult:
        if not ctx.user or not ctx.password:
            raise ValueError(
                "LoginComponent requer credenciais no contexto. "
                "Verifique ctx.config ou ctx.credentials."
            )
        return LoginFlow().execute(ctx)