# vtae/configs/msi3/login_config.py
# MIGRADO — credenciais agora em vtae/configs/msi3/.env
# Mantido para retrocompatibilidade. Remover na v0.5.0.

from src.config import ConfigLoader as _CL
from pathlib import Path as _P

_cfg = _CL.carregar("msi3")

class LoginConfigMsi3:
    USER          = _cfg.USER
    PASSWORD      = _cfg.PASSWORD
    SYSTEM        = "msi3"
    URL           = _cfg.url
    url            = _cfg.ambiente.url   # alias minúsculo para o flow
    CAMPO_USUARIO = "#P9999_USERNAME"
    CAMPO_SENHA   = "#P9999_PASSWORD"
    TELA_PRINCIPAL = "h3.t-Card-title"
