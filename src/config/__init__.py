"""
src.config — Camada de configuração do VTAE.

Exports principais:
    ConfigLoader  — carrega config.yaml e retorna SystemConfig
    SystemConfig  — configuração completa de um sistema
    ConfigError   — exceção lançada em erros de configuração (em src.core.types)

Uso rápido:
    from src.config import ConfigLoader

    config = ConfigLoader.carregar("sislab")
    config = ConfigLoader.carregar("msi3", ambiente="homologacao")
"""

from src.config.loader import ConfigLoader
from src.config.schema import (
    SystemConfig,
    AmbienteConfig,
    CredenciaisConfig,
    DadoFakerConfig,
)

__all__ = [
    "ConfigLoader",
    "SystemConfig",
    "AmbienteConfig",
    "CredenciaisConfig",
    "DadoFakerConfig",
]
