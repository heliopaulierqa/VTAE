# src/core/observer.py
"""
VTAE Observer — Fase 5b: Observabilidade
v0.5.10:
  - description gravada no execution.json por step
    (ex: "L01 - clicar no campo usuario e digitar")
  - _step_descriptions removido — description vem direto do StepResult
"""

import json
import logging
import os
import platform
import socket
import uuid
from datetime import datetime

from src.core.result import FlowResult, StepResult


def _coletar_ambiente() -> dict:
    """Coleta informacoes do ambiente de execucao."""
    ambiente = {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "resolucao": None,
    }
    try:
        import ctypes
        user32 = ctypes.windll.user32
        ambiente["resolucao"] = f"{user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}"
    except Exception:
        try:
            import subprocess
            out = subprocess.check_output(
                ["xrandr", "--current"], text=True, timeout=3
            )
            for line in out.splitlines():
                if "*" in line:
                    res = line.strip().split()[0]
                    ambiente["resolucao"] = res
                    break
        except Exception:
            ambiente["resolucao"] = "desconhecida"
    return ambiente


class ExecutionObserver:
    """
    Observador de execucao do VTAE.
    Registra logs estruturados (.log + .json) e gera relatorio HTML automatico.

    Uso:
        observer = ExecutionObserver(test_name="test_admissao_internacao_jornada")
        ctx = FlowContext(runner=runner, config=config, evidence_dir=observer.evidence_dir)
        observer.inject_logger(ctx)   # ANTES dos flows
        LoginFlow().execute(ctx, observer=observer)
        observer.report(ctx)
    """

    def __init__(self, test_name: str, base_dir: str = "evidence"):
        self.test_name = test_name
        self.started_at = datetime.now()
        self.execution_id = str(uuid.uuid4())

        date_str = self.started_at.strftime("%Y-%m-%d")
        time_str = self.started_at.strftime("%H-%M-%S")

        self.evidence_dir = os.path.join(base_dir, date_str, test_name) + os.sep
        os.makedirs(self.evidence_dir, exist_ok=True)

        self._log_path  = os.path.join(self.evidence_dir, "execution.log")
        self._json_path = os.path.join(self.evidence_dir, "execution.json")
        self._html_path = os.path.join(self.evidence_dir, "report.html")

        self._ambiente = _coletar_ambiente()
        self._logger   = self._setup_logger(time_str)

        self._logger.info(f"Iniciando execucao: {test_name}")
        self._logger.info(f"execution_id: {self.execution_id}")
        self._logger.info(f"Evidencias em: {self.evidence_dir}")
        self._logger.info(
            f"Ambiente: {self._ambiente['os']} | "
            f"{self._ambiente['hostname']} | "
            f"resolucao: {self._ambiente['resolucao']}"
        )

    # ----------------------------------------------------------------
    # inject_logger — DEVE ser chamado ANTES dos flows
    # ----------------------------------------------------------------

    def inject_logger(self, ctx) -> None:
        """
        Injeta o logger do observer no contexto.
        Chamar ANTES de qualquer flow para garantir 100% dos logs.
        """
        ctx._logger = self._logger

    # ----------------------------------------------------------------
    # API publica
    # ----------------------------------------------------------------

    def log_step_start(self, step_id: str, description: str = "") -> None:
        """Loga inicio de step. description e o texto legivel do step."""
        msg = f"[{step_id}] INICIANDO"
        if description:
            msg += f" — {description}"
        self._logger.info(msg)

    def log_step_result(self, step: StepResult) -> None:
        """Loga resultado de step. Inclui description quando disponivel."""
        status = "OK" if step.success else "FALHOU"
        # Inclui description no log quando disponivel
        desc = f" — {step.description}" if step.description else ""
        msg = f"[{step.step_id}]{desc} | {status} | {step.duration_ms:.0f}ms"
        if step.screenshot_path:
            msg += f" | screenshot: {step.screenshot_path}"
        if step.error:
            msg += f" | erro: {step.error}"
        if step.causa_falha:
            msg += f" | causa: {step.causa_falha.value}"
        if step.validated is True:
            msg += " | validado=True"
        elif step.validated is False:
            msg += " | validado=False"

        if step.success:
            self._logger.info(msg)
        else:
            self._logger.error(msg)

    def log_flow_result(self, result: FlowResult) -> None:
        status = "PASSOU" if result.success else "FALHOU"
        # Identifica steps sem validacao para sinalizacao nominal
        sem_validacao = [
            s.step_id for s in result.steps
            if s.success and s.validated is None
        ]
        self._logger.info(
            f"Flow {result.flow_name} — {status} | "
            f"{len(result.steps) - len(result.failed_steps)}/{len(result.steps)} steps OK | "
            f"{result.total_duration_ms:.0f}ms total"
        )
        if sem_validacao:
            self._logger.warning(
                f"  Steps sem validacao: {sem_validacao} — "
                f"considere adicionar confirm_template ou verify_fill"
            )
        for step in result.failed_steps:
            self._logger.error(f"  Step falhou: [{step.step_id}] {step.error}")

    def report(self, ctx) -> str:
        """
        Gera o relatorio final:
          - execution.log  (ja escrito durante a execucao)
          - execution.json (com description por step — novo v0.5.10)
          - report.html    (relatorio visual para gestao)

        Retorna o caminho do HTML gerado.
        """
        finished_at = datetime.now()
        duration_s  = (finished_at - self.started_at).total_seconds()

        all_flows    = ctx._results
        total_steps  = sum(len(f.steps) for f in all_flows)
        failed_steps = sum(len(f.failed_steps) for f in all_flows)
        all_passed   = all(f.success for f in all_flows)

        status = "PASSOU" if all_passed else "FALHOU"
        self._logger.info(
            f"Execucao finalizada — {status} | "
            f"{total_steps - failed_steps}/{total_steps} steps OK | "
            f"{duration_s:.1f}s total"
        )

        # ── JSON ──────────────────────────────────────────────────────
        report_data = {
            "execution_id":   self.execution_id,
            "test_name":      self.test_name,
            "status":         status,
            "started_at":     self.started_at.isoformat(),
            "finished_at":    finished_at.isoformat(),
            "duration_seconds": round(duration_s, 2),
            "ambiente":       self._ambiente,
            "summary": {
                "total_flows":   len(all_flows),
                "total_steps":   total_steps,
                "passed_steps":  total_steps - failed_steps,
                "failed_steps":  failed_steps,
            },
            "flows": [
                {
                    "flow_name":        f.flow_name,
                    "success":          f.success,
                    "total_duration_ms": round(f.total_duration_ms, 1),
                    "steps": [
                        {
                            "step_id":        s.step_id,
                            # NOVO v0.5.10 — nome legivel do step
                            # Ex: "clicar no campo usuario e digitar"
                            "description":    s.description,
                            "success":        s.success,
                            "duration_ms":    round(s.duration_ms, 1),
                            "screenshot":     s.screenshot_path,
                            "error":          s.error,
                            "causa_falha":    s.causa_falha.value if s.causa_falha else None,
                            "validated":      s.validated,
                            "timestamp":      s.timestamp,
                        }
                        for s in f.steps
                    ],
                }
                for f in all_flows
            ],
        }

        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        self._logger.info(f"Relatorio JSON salvo em: {self._json_path}")
        self._atualizar_flakiness(report_data)

        # ── HTML ──────────────────────────────────────────────────────
        try:
            from src.core.report_generator import generate
            html_path = generate(self._json_path, self._html_path)
            self._logger.info(f"Relatorio HTML salvo em: {html_path}")
            print(f"\nRelatorio HTML: {html_path}\n")
        except Exception as e:
            self._logger.warning(f"Nao foi possivel gerar relatorio HTML: {e}")

        return self._html_path

    # ----------------------------------------------------------------
    # Internos
    # ----------------------------------------------------------------

    def _atualizar_flakiness(self, report_data: dict) -> None:
        """
        Acumula historico de pass/fail por step_id em evidence/flakiness.json.
        Acumula tambem duracao media e maxima por step.
        v0.5.10: grava description no flakiness para referencia.
        """
        flakiness_path = os.path.join("evidence", "flakiness.json")

        try:
            with open(flakiness_path, encoding="utf-8") as f:
                historico = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            historico = {}

        for flow in report_data.get("flows", []):
            for step in flow.get("steps", []):
                sid  = step["step_id"]
                dur  = step.get("duration_ms", 0) or 0
                desc = step.get("description", "")

                if sid not in historico:
                    historico[sid] = {}
                h = historico[sid]
                h.setdefault("pass_count", 0)
                h.setdefault("fail_count", 0)
                h.setdefault("last_failure", None)
                h.setdefault("last_causa_falha", None)
                h.setdefault("avg_duration_ms", 0.0)
                h.setdefault("max_duration_ms", 0.0)
                h.setdefault("total_duration_ms", 0.0)
                h.setdefault("total_execucoes", 0)
                # NOVO v0.5.10 — description para referencia no flakiness
                if desc:
                    h["description"] = desc

                if step["success"]:
                    h["pass_count"] += 1
                else:
                    h["fail_count"] += 1
                    h["last_failure"]     = report_data["finished_at"]
                    h["last_causa_falha"] = step.get("causa_falha")

                h["total_execucoes"]  += 1
                h["total_duration_ms"] += dur
                h["avg_duration_ms"]   = round(
                    h["total_duration_ms"] / h["total_execucoes"], 1
                )
                if dur > h["max_duration_ms"]:
                    h["max_duration_ms"] = round(dur, 1)

        with open(flakiness_path, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)

        self._logger.info(f"flakiness.json atualizado: {flakiness_path}")

    def _setup_logger(self, time_str: str) -> logging.Logger:
        logger_name = f"vtae.{self.test_name}.{time_str}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)-5s] %(message)s",
            datefmt="%H:%M:%S",
        )

        file_handler = logging.FileHandler(self._log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger