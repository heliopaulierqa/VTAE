# src/core/result.py
"""
Tipos de resultado do VTAE.
v0.5.10: StepResult.description — propaga descricao do _step() para o JSON.
         Habilita nomes legiveis nos screenshots e no execution.json.
         Exemplo: "L01 - clicar no campo usuario e digitar"
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CausaFalha(Enum):
    """Classificacao da causa raiz de um step com falha."""
    OCR_REGIAO               = "ocr_regiao"
    OCR_LEITURA              = "ocr_leitura"
    TEMPLATE_NAO_ENCONTRADO  = "template_nao_encontrado"
    TIMEOUT                  = "timeout"
    COORDENADA               = "coordenada"
    AMBIENTE                 = "ambiente"
    SISTEMA                  = "sistema"
    CONFIGURACAO             = "configuracao"
    ESTADO_AUSENTE           = "estado_ausente"
    DESCONHECIDA             = "desconhecida"


@dataclass
class StepResult:
    """Resultado de um step individual dentro de um flow."""

    step_id: str
    success: bool
    duration_ms: float
    screenshot_path: str | None = None
    error: str | None = None
    causa_falha: CausaFalha | None = None
    validated: bool | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # NOVO v0.5.10 — descricao legivel propagada pelo BaseFlow._step()
    # Exemplos: "clicar no campo usuario e digitar"
    #           "abrir modulo Ambulatorio via Localizar no Menu"
    # Gravada no execution.json e usada para nomear screenshots
    description: str = ""

    def __str__(self) -> str:
        status = "OK" if self.success else "FALHOU"
        # Inclui description no __str__ quando disponivel
        desc = f" — {self.description}" if self.description else ""
        base = f"[{self.step_id}]{desc} | {status} | {self.duration_ms:.0f}ms"
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
        status = "PASSOU" if self.success else "FALHOU"
        return (
            f"\n{'='*50}\n"
            f"Flow: {self.flow_name} — {status}\n"
            f"Steps: {total - failed}/{total} OK | "
            f"Tempo total: {self.total_duration_ms:.0f}ms\n"
            f"{'='*50}"
        )