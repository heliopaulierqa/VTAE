import pytest
from unittest.mock import MagicMock

from vtae.core.base_runner import BaseRunner
from vtae.core.context import FlowContext
from vtae.configs.sislab.login_config import LoginConfigSisLab


@pytest.fixture
def mock_runner():
    """Runner mockado para testes unitários — não precisa de tela real."""
    runner = MagicMock(spec=BaseRunner)
    runner.click_template.return_value = True
    runner.safe_click.return_value = True
    runner.wait_template.return_value = True
    runner.screenshot.return_value = "evidence/mock/step.png"
    return runner


@pytest.fixture
def ctx(mock_runner):
    """FlowContext padrão para testes, com SisLab config e runner mockado."""
    return FlowContext(
        runner=mock_runner,
        config=LoginConfigSisLab,
        evidence_dir="evidence/test/",
    )
