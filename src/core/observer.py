"""
VTAE Observer — Obs-Fase1b: evidências reais

v0.5.9 — correções de observabilidade real:
  1. inject_logger() chamado no __init__ quando ctx disponível — não só no report()
     → antes: logger só era injetado no report(), que é chamado DEPOIS dos flows
     → agora: chamar observer.inject_logger(ctx) logo após criar o FlowContext
               garante 100% dos logs desde o início
  2. log_step_result() salva screenshot automático quando step falha e não tem screenshot
     → captura o estado real da tela no momento do log (mais próximo da falha real)
  3. Seção "steps sem validação" no log_flow_result é listada nominalmente
     → facilita saber quais steps específicos ainda precisam de verify/confirm
  4. _atualizar_flakiness mantém série temporal simples (last_10_results)
     → permite ver se step começou a falhar recentemente ou sempre foi instável
"""

import json
import logging
import os
import platform
import socket
import time
import uuid
from datetime import datetime

from src.core.result import FlowResult, StepResult


def _coletar_ambiente() -> dict:
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
            out = subprocess.check_output(["xrandr", "--current"], text=True, timeout=3)
            for line in out.splitlines():
                if "*" in line:
                    ambiente["resolucao"] = line.strip().split()[0]
                    break
        except Exception:
            ambiente["resolucao"] = "desconhecida"
    return ambiente


class ExecutionObserver:
    """
    Observador de execução do VTAE.

    Uso correto para 100% dos logs desde o início:

        observer = ExecutionObserver(test_name="test_admissao_ambulatorio")
        ctx = FlowContext(runner=runner, config=config, evidence_dir=observer.evidence_dir)
        observer.inject_logger(ctx)   ← AQUI — antes de qualquer flow
        LoginFlow().execute(ctx, observer=observer)
        AdmissaoAmbulatorioFlow().execute(ctx, observer=observer)
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

        # Contador para screenshots automáticos de diagnóstico
        self._auto_screenshot_count = 0

    # ----------------------------------------------------------------
    # inject_logger — deve ser chamado ANTES dos flows
    # ----------------------------------------------------------------

    def inject_logger(self, ctx) -> None:
        """
        Injeta o logger no runner via FlowContext.

        DEVE ser chamado logo após criar o FlowContext, antes de qualquer flow.
        Se chamado só no report() (como era antes), os logs do Login e dos
        primeiros flows NÃO chegam ao execution.log.

        Funciona para OpenCVRunner e PlaywrightRunner (ambos têm set_logger agora).
        """
        ctx.set_logger(self._logger)
        self._logger.info(
            f"[Observer] logger injetado no runner "
            f"({type(ctx.runner).__name__})"
        )

    # ----------------------------------------------------------------
    # API pública
    # ----------------------------------------------------------------

    def log_step_start(self, step_id: str, description: str = "") -> None:
        msg = f"[{step_id}] INICIANDO"
        if description:
            msg += f" — {description}"
        self._logger.info(msg)

    def log_step_result(self, step: StepResult) -> None:
        status = "OK" if step.success else "FALHOU"
        msg = f"[{step.step_id}] {status} | {step.duration_ms:.0f}ms"

        if step.validated is True:
            msg += " [VALIDADO]"
        elif step.validated is False and step.success:
            msg += " [NAO VALIDADO]"
        elif step.validated is None and step.success:
            # Step bem-sucedido sem nenhuma validação — sinalizar explicitamente
            msg += " [SEM VALIDACAO — resultado nao confirmado]"

        if step.screenshot_path:
            msg += f" | screenshot: {step.screenshot_path}"
        elif not step.success:
            # CORREÇÃO: step falhou e não tem screenshot — capturar agora
            # Este screenshot reflete o estado real da tela no momento do log
            auto_path = self._capturar_screenshot_diagnostico(step.step_id)
            if auto_path:
                step.screenshot_path = auto_path  # atualiza o StepResult
                msg += f" | screenshot-auto: {auto_path}"

        if step.confidence_score is not None:
            msg += f" | score: {step.confidence_score:.3f}"
        if step.template_path:
            msg += f" | template: {step.template_path}"
        if step.error:
            msg += f" | erro: {step.error}"
        if step.causa_falha:
            msg += f" | causa: {step.causa_falha.value}"

        if step.success:
            self._logger.info(msg)
        else:
            self._logger.error(msg)

    def log_flow_result(self, result: FlowResult) -> None:
        status = "PASSOU" if result.success else "FALHOU"
        validated_count = sum(1 for s in result.steps if s.validated is True)
        sem_validacao   = [s for s in result.steps if s.success and s.validated is None]
        total_ok = len(result.steps) - len(result.failed_steps)

        self._logger.info(
            f"Flow {result.flow_name} — {status} | "
            f"{total_ok}/{len(result.steps)} steps OK | "
            f"{validated_count} validados"
            + (f" | {len(sem_validacao)} sem validacao" if sem_validacao else "")
            + f" | {result.total_duration_ms:.0f}ms total"
        )

        # Listar nominalmente steps sem validação — facilita saber o que falta
        if sem_validacao:
            ids = ", ".join(s.step_id for s in sem_validacao)
            self._logger.warning(
                f"  Steps sem validacao pós-ação: [{ids}] — "
                f"estes steps reportam sucesso sem confirmar o estado da tela."
            )

        for step in result.failed_steps:
            causa = f" [{step.causa_falha.value}]" if step.causa_falha else ""
            self._logger.error(f"  Step falhou: [{step.step_id}]{causa} {step.error}")

    def report(self, ctx) -> str:
        """
        Gera o relatório final: execution.log, execution.json, report.html.

        NOTA: inject_logger() deve ter sido chamado ANTES dos flows para que
        todos os logs cheguem ao execution.log. O report() ainda chama
        inject_logger() mas só cobre logs do ponto de report() em diante.
        """
        # Garante que o logger está injetado (caso não tenha sido chamado antes)
        self.inject_logger(ctx)

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

        # — JSON —
        report_data = {
            "execution_id": self.execution_id,
            "test_name": self.test_name,
            "status": status,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round(duration_s, 2),
            "ambiente": self._ambiente,
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
                            "validated": s.validated,
                            "duration_ms": round(s.duration_ms, 1),
                            "screenshot": s.screenshot_path,
                            "error": s.error,
                            "causa_falha": s.causa_falha.value if s.causa_falha else None,
                            "confidence_score": round(s.confidence_score, 3) if s.confidence_score is not None else None,
                            "template_path": s.template_path,
                            "timestamp": s.timestamp,
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

        # — HTML —
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

    def _capturar_screenshot_diagnostico(self, step_id: str) -> str | None:
        """
        Captura screenshot automático quando step falha sem screenshot.
        Salva em evidence_dir para aparecer no report.html.

        Este screenshot é tirado no momento do log_step_result() —
        o mais próximo possível do momento real da falha.
        """
        try:
            import pyautogui
            self._auto_screenshot_count += 1
            path = os.path.join(
                self.evidence_dir,
                f"{step_id}_auto_diag_{self._auto_screenshot_count:03d}.png"
            )
            pyautogui.screenshot(path)
            self._logger.debug(f"[Observer] screenshot de diagnóstico: {path}")
            return path
        except Exception as e:
            self._logger.debug(f"[Observer] falha ao capturar screenshot automático: {e}")
            return None

    def _atualizar_flakiness(self, report_data: dict) -> None:
        """
        Acumula histórico de pass/fail por step_id em evidence/flakiness.json.

        v0.5.9: adiciona last_10_results — série temporal simples.
        Permite ver se step começou a falhar recentemente ou sempre foi instável.
        Exemplo: [1,1,1,0,0,0,0,0,0,0] → passou nas 3 primeiras, falhou nas últimas 7.
        """
        flakiness_path = os.path.join("evidence", "flakiness.json")

        try:
            with open(flakiness_path, encoding="utf-8") as f:
                historico = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            historico = {}

        for flow in report_data.get("flows", []):
            for step in flow.get("steps", []):
                sid = step["step_id"]
                dur = step.get("duration_ms", 0) or 0

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
                h.setdefault("validated_count", 0)
                h.setdefault("last_confidence_score", None)
                h.setdefault("min_confidence_score", None)
                # Obs-Fase2: série temporal — últimos 10 resultados (1=passou, 0=falhou)
                h.setdefault("last_10_results", [])

                passou = step["success"]

                if passou:
                    h["pass_count"] += 1
                    if step.get("validated") is True:
                        h["validated_count"] = h.get("validated_count", 0) + 1
                else:
                    h["fail_count"] += 1
                    h["last_failure"] = report_data["finished_at"]
                    h["last_causa_falha"] = step.get("causa_falha")
                    score = step.get("confidence_score")
                    if score is not None:
                        h["last_confidence_score"] = score
                        if h["min_confidence_score"] is None or score < h["min_confidence_score"]:
                            h["min_confidence_score"] = score

                # Série temporal — mantém só os últimos 10
                h["last_10_results"].append(1 if passou else 0)
                if len(h["last_10_results"]) > 10:
                    h["last_10_results"] = h["last_10_results"][-10:]

                # Duração média e máxima
                h["total_execucoes"] += 1
                h["total_duration_ms"] += dur
                h["avg_duration_ms"] = round(h["total_duration_ms"] / h["total_execucoes"], 1)
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