from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StepResult:
    """Resultado de um step individual dentro de um flow."""

    step_id: str
    success: bool
    duration_ms: float
    screenshot_path: str | None = None
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __str__(self) -> str:
        status = "✅" if self.success else "❌"
        base = f"{status} [{self.step_id}] {self.duration_ms:.0f}ms"
        if self.error:
            base += f" | erro: {self.error}"
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
