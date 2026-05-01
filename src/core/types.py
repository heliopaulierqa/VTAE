"""
Tipos e exceções comuns do framework VTAE.
Importar daqui — nunca usar Exception genérica nos flows.
"""


class VtaeError(Exception):
    """Exceção base do framework."""


class StepError(VtaeError):
    """Falha em um step de execução."""


class TemplateNotFoundError(VtaeError):
    """Template OpenCV não encontrado na tela após todas as tentativas."""


class ConfigError(VtaeError):
    """Erro de configuração — YAML inválido ou campo ausente."""


class RunnerError(VtaeError):
    """Erro no runner (Playwright ou OpenCV)."""
