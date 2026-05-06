import pytest
from unittest.mock import MagicMock
from vtae.core.base_runner import BaseRunner
from vtae.core.context import FlowContext


class _MockConfig:
    """Config mínimo para testes unitários — sem dependência de .env."""
    USER     = "test_user"
    PASSWORD = "test_pass"
    SYSTEM   = "sislab"
    URL      = "http://sislab.local"


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
    """FlowContext padrão para testes, com config mockado e runner mockado."""
    return FlowContext(
        runner=mock_runner,
        config=_MockConfig,
        evidence_dir="evidence/test/",
    )
