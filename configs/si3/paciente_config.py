# configs/si3/paciente_config.py
# MIGRADO — credenciais agora em configs/si3/.env
# Mantido para retrocompatibilidade. Remover na v0.5.0.

from src.config import ConfigLoader as _CL
from pathlib import Path as _P

_cfg = _CL.carregar("si3", configs_dir=_P("configs"))

class PacienteConfigSi3:
    USER     = _cfg.USER
    PASSWORD = _cfg.PASSWORD
    SYSTEM   = "si3"
