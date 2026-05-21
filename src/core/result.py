from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class CausaFalha(Enum):
    """Classificação da causa raiz de um step com falha."""
    OCR_REGIAO          = "ocr_regiao"           # região OCR não calibrada ou vazia
    OCR_LEITURA         = "ocr_leitura"          # OCR rodou mas não leu o esperado
    TEMPLATE_NAO_ENCONTRADO = "template_nao_encontrado"  # safe_click/double_click falhou
    TIMEOUT             = "timeout"              # wait_template excedeu o tempo
    COORDENADA          = "coordenada"           # pyautogui.click em posição errada
    AMBIENTE            = "ambiente"             # sistema não estava aberto/na tela correta
    SISTEMA             = "sistema"              # erro inesperado do Oracle Forms
    CONFIGURACAO        = "configuracao"         # campo ausente no config.yaml ou .env
    ESTADO_AUSENTE      = "estado_ausente"       # paciente_id ou dado de jornada nao encontrado
    DESCONHECIDA        = "desconhecida"         # exception não classificada


@dataclass
class StepResult:
    """Resultado de um step individual dentro de um flow."""

    step_id: str
    success: bool
    duration_ms: float
    screenshot_path: str | None = None
    error: str | None = None
    causa_falha: CausaFalha | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __str__(self) -> str:
        status = "✅" if self.success else "❌"
        base = f"{status} [{self.step_id}] {self.duration_ms:.0f}ms"
        if self.error:
            base += f" | erro: {self.error}"
        if self.causa_falha:    
            base += f" | causa: {self.causa_falha.value}"
        return base


@dataclass
class FlowResult:
    """Resultado agregado de um flow completo."""

    flow_name: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps)

    @property
    def total_duration_ms(self) -> float:
        return sum(s.duration_ms for s in self.steps)

    @property
    def failed_steps(self) -> list[StepResult]:
        return [s for s in self.steps if not s.success]

    def summary(self) -> str:
        total = len(self.steps)
        failed = len(self.failed_steps)
        status = "✅ PASSOU" if self.success else "❌ FALHOU"
        return (
            f"\n{'='*50}\n"
            f"Flow: {self.flow_name} — {status}\n"
            f"Steps: {total - failed}/{total} OK | "
            f"Tempo total: {self.total_duration_ms:.0f}ms\n"
            f"{'='*50}"
        )
