# vtae/components/si3/login_component.py
from vtae.core.context import FlowContext
from vtae.core.result import FlowResult
from vtae.flows.si3.login.login_flow import LoginFlow


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