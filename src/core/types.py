"""
Tipos e exceções comuns do framework VTAE.
Importar daqui — nunca usar Exception genérica nos flows.
"""


class VtaeError(Exception):
    """Exceção base do framework."""


class StepError(VtaeError):
    """Falha em um step de execução."""


class TemplateNotFoundError(VtaeError):
    """
    Template OpenCV nao encontrado na tela apos todas as tentativas.

    Campos estruturados — chegam ao StepResult e ao execution.json:
        template:   caminho do template que falhou
        score:      melhor score encontrado (0.0 a 1.0)
        threshold:  threshold exigido
        tentativas: numero de tentativas realizadas
    """
    def __init__(self, message: str, template: str = "",
                 score: float = 0.0, threshold: float = 0.0,
                 tentativas: int = 0):
        super().__init__(message)
        self.template   = template
        self.score      = score
        self.threshold  = threshold
        self.tentativas = tentativas


class ConfigError(VtaeError):
    """Erro de configuração — YAML inválido ou campo ausente."""


class RunnerError(VtaeError):
    """Erro no runner (Playwright ou OpenCV)."""