from dataclasses import dataclass, field
from typing import Any

from src.runners.base_runner import BaseRunner
from src.core.result import FlowResult


@dataclass
class FlowContext:
    """
    Contexto compartilhado entre todos os flows e steps.
    Elimina o padrão (runner, config, user, password, ...) espalhado por todo lugar.
    """

    runner: BaseRunner
    config: Any = None
    credentials: dict = field(default_factory=dict)
    evidence_dir: str = "evidence/"
    _results: list[FlowResult] = field(default_factory=list, repr=False)

    @property
    def user(self) -> str | None:
        return self.credentials.get("user") or getattr(self.config, "USER", None)

    @property
    def password(self) -> str | None:
        return self.credentials.get("password") or getattr(self.config, "PASSWORD", None)

    def add_result(self, result: FlowResult) -> None:
        self._results.append(result)

    def all_passed(self) -> bool:
        return all(r.success for r in self._results)

    def print_summary(self) -> None:
        for result in self._results:
            print(result.summary())
            for step in result.steps:
                print(f"  {step}")
