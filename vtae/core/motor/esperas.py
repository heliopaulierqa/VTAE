# vtae/core/motor/esperas.py
"""
Espera por condicao — peca 2 do motor (regra 51).

Nunca espera tempo: espera template ficar visivel ou janela sumir.
Nenhum verbo levanta excecao — devolve bool e loga. Quem chama decide
se e fatal (regra 45).
"""
import time

TIMEOUT_PADRAO = 10.0
INTERVALO_POLL = 0.3


class Esperas:
    def __init__(self, objects, runner, logger=None):
        self._objects = objects
        self._runner = runner
        self._logger = logger

    def _log(self, msg: str) -> None:
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)

    def esperar_visivel(self, nome: str, timeout: float = TIMEOUT_PADRAO) -> bool:
        elemento = self._objects.elemento(nome)
        if elemento is None:
            self._log(f"[espera] '{nome}' nao declarado em objects/")
            return False

        template = elemento.get("template")
        origem = f"'{nome}'"

        if template is None:
            ancora = self._objects.ancora()
            alvo = self._objects.elemento(ancora) if ancora else None
            template = alvo.get("template") if alvo else None
            origem = f"ancora '{ancora}'"

        if template is None:
            self._log(f"[espera] AVISO: sem condicao para {origem} — seguindo sem esperar")
            return True

        if self._runner.wait_template(template, timeout=timeout):
            return True

        self._log(f"[espera] timeout de {timeout}s esperando {origem} ({template})")
        return False

    def esperar_janela_sumir(self, titulo_parcial: str,
                             timeout: float = TIMEOUT_PADRAO) -> bool:
        try:
            import pygetwindow as gw
        except ImportError:
            self._log("[espera] AVISO: pygetwindow ausente — sem como esperar janela")
            return False

        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            if not any(titulo_parcial in t for t in gw.getAllTitles()):
                return True
            time.sleep(INTERVALO_POLL)

        self._log(f"[espera] timeout de {timeout}s — janela '{titulo_parcial}' aberta")
        return False