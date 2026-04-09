"""
DSL Interpreter — Fase 5
Executa testes definidos em YAML sem necessidade de código Python.

Exemplo de YAML:
    flow: admissao
    steps:
      - action: login
      - action: click
        template: templates/admissao/btn_modulo.png
      - action: wait
        template: templates/admissao/tela_admissao.png
"""

from typing import Any


class DSLInterpreter:
    """
    Interpreta e executa um teste definido em YAML.
    Conecta ações do YAML com flows e o runner.
    """

    SUPPORTED_ACTIONS = {"login", "click", "type", "wait", "screenshot"}

    def __init__(self, ctx):
        self.ctx = ctx

    def run(self, test_definition: dict[str, Any]) -> None:
        """Executa um teste a partir de um dicionário (carregado de YAML)."""
        flow_name = test_definition.get("flow", "unknown")
        steps = test_definition.get("steps", [])

        print(f"[DSL] Executando flow: {flow_name} ({len(steps)} steps)")

        for i, step in enumerate(steps, 1):
            action = step.get("action")
            if action not in self.SUPPORTED_ACTIONS:
                raise ValueError(f"Ação desconhecida: '{action}'. Suportadas: {self.SUPPORTED_ACTIONS}")
            self._execute_action(i, step)

    def _execute_action(self, index: int, step: dict) -> None:
        action = step["action"]
        print(f"[DSL] Step {index:02d}: {action}")

        if action == "login":
            from vtae.flows.login_flow import LoginFlow
            LoginFlow().execute(self.ctx)

        elif action == "click":
            template = step.get("template")
            if not template:
                raise ValueError(f"Step 'click' requer campo 'template'.")
            self.ctx.runner.safe_click(template)

        elif action == "type":
            text = step.get("text", "")
            self.ctx.runner.type_text(text)

        elif action == "wait":
            template = step.get("template")
            timeout = step.get("timeout", 10.0)
            if not template:
                raise ValueError(f"Step 'wait' requer campo 'template'.")
            self.ctx.runner.wait_template(template, timeout=timeout)

        elif action == "screenshot":
            name = step.get("name", f"step_{index:02d}.png")
            self.ctx.runner.screenshot(f"{self.ctx.evidence_dir}{name}")
