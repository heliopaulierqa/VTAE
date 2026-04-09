"""
VTAE Observer — Fase 4: Observabilidade
Responsável por logs estruturados, evidências organizadas e relatório de execução.
"""

import json
import logging
import os
from datetime import datetime

from vtae.core.result import FlowResult, StepResult


class ExecutionObserver:
    """
    Observador de execução do VTAE.
    Registra logs estruturados (.log + .json) e organiza evidências por data/teste.

    Uso:
        observer = ExecutionObserver(test_name="test_login_real")
        ctx = FlowContext(runner=runner, config=config, evidence_dir=observer.evidence_dir)
        # ... executa os flows ...
        observer.report(ctx)
    """

    def __init__(self, test_name: str, base_dir: str = "evidence"):
        self.test_name = test_name
        self.started_at = datetime.now()

        date_str = self.started_at.strftime("%Y-%m-%d")
        time_str = self.started_at.strftime("%H-%M-%S")

        self.evidence_dir = os.path.join(base_dir, date_str, test_name) + os.sep
        os.makedirs(self.evidence_dir, exist_ok=True)

        self._log_path = os.path.join(self.evidence_dir, "execution.log")
        self._json_path = os.path.join(self.evidence_dir, "execution.json")

        self._logger = self._setup_logger(time_str)
        self._logger.info(f"Iniciando execução: {test_name}")
        self._logger.info(f"Evidências em: {self.evidence_dir}")

    # ──────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────

    def log_step_start(self, step_id: str, description: str = "") -> None:
        """Registra o início de um step."""
        msg = f"[{step_id}] INICIANDO"
        if description:
            msg += f" — {description}"
        self._logger.info(msg)

    def log_step_result(self, step: StepResult) -> None:
        """Registra o resultado de um step."""
        status = "OK" if step.success else "FALHOU"
        msg = f"[{step.step_id}] {status} | {step.duration_ms:.0f}ms"
        if step.screenshot_path:
            msg += f" | screenshot: {step.screenshot_path}"
        if step.error:
            msg += f" | erro: {step.error}"

        if step.success:
            self._logger.info(msg)
        else:
            self._logger.error(msg)

    def log_flow_result(self, result: FlowResult) -> None:
        """Registra o resultado completo de um flow."""
        status = "PASSOU" if result.success else "FALHOU"
        self._logger.info(
            f"Flow {result.flow_name} — {status} | "
            f"{len(result.steps) - len(result.failed_steps)}/{len(result.steps)} steps OK | "
            f"{result.total_duration_ms:.0f}ms total"
        )
        for step in result.failed_steps:
            self._logger.error(f"  Step falhou: [{step.step_id}] {step.error}")

    def report(self, ctx) -> str:
        """
        Gera o relatório final (.log já escrito, salva .json).
        Retorna o caminho do JSON gerado.
        """
        finished_at = datetime.now()
        duration_s = (finished_at - self.started_at).total_seconds()

        all_flows = ctx._results
        total_steps = sum(len(f.steps) for f in all_flows)
        failed_steps = sum(len(f.failed_steps) for f in all_flows)
        all_passed = all(f.success for f in all_flows)

        status = "PASSOU" if all_passed else "FALHOU"
        self._logger.info(
            f"Execução finalizada — {status} | "
            f"{total_steps - failed_steps}/{total_steps} steps OK | "
            f"{duration_s:.1f}s total"
        )

        report = {
            "test_name": self.test_name,
            "status": status,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round(duration_s, 2),
            "summary": {
                "total_flows": len(all_flows),
                "total_steps": total_steps,
                "passed_steps": total_steps - failed_steps,
                "failed_steps": failed_steps,
            },
            "flows": [
                {
                    "flow_name": f.flow_name,
                    "success": f.success,
                    "total_duration_ms": round(f.total_duration_ms, 1),
                    "steps": [
                        {
                            "step_id": s.step_id,
                            "success": s.success,
                            "duration_ms": round(s.duration_ms, 1),
                            "screenshot": s.screenshot_path,
                            "error": s.error,
                            "timestamp": s.timestamp,
                        }
                        for s in f.steps
                    ],
                }
                for f in all_flows
            ],
        }

        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self._logger.info(f"Relatório JSON salvo em: {self._json_path}")
        return self._json_path

    # ──────────────────────────────────────────────
    # Setup interno
    # ──────────────────────────────────────────────

    def _setup_logger(self, time_str: str) -> logging.Logger:
        """Configura logger que escreve no arquivo .log e no terminal."""
        logger_name = f"vtae.{self.test_name}.{time_str}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)-5s] %(message)s",
            datefmt="%H:%M:%S",
        )

        # handler arquivo
        file_handler = logging.FileHandler(self._log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # handler terminal
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger
