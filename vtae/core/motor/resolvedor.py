# vtae/core/motor/resolvedor.py
"""
Resolvedor de alvo — peca 2 do motor (Projeto v1.1, Fase 2).

Responde UMA pergunta: onde eu clico/digito para chegar neste elemento?
Nao clica, nao digita, nao espera, nao verifica.

Ordem desktop: template -> coordenada. Web: seletor.
pyjab nao entra: nao escreve nesta fase (regra 32).

Tolerante (regra 45): devolve None e loga o motivo; quem chama decide
se e fatal.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Alvo:
    estrategia: str                     # "template" | "coordenada" | "seletor"
    ponto: tuple[int, int] | None = None
    seletor: str | None = None
    degradado: bool = False             # template declarado falhou -> caiu na coordenada


class Resolvedor:
    def __init__(self, objects, runner, logger=None):
        self._objects = objects
        self._runner = runner
        self._logger = logger

    def _log(self, msg: str) -> None:
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)

    def resolver(self, nome: str) -> Alvo | None:
        elemento = self._objects.elemento(nome)
        if elemento is None:
            self._log(f"[resolvedor] '{nome}' nao declarado em objects/")
            return None

        seletor = elemento.get("seletor")
        if seletor:
            self._log(f"[resolvedor] '{nome}' por seletor: {seletor}")
            return Alvo("seletor", seletor=seletor)

        template = elemento.get("template")
        coordenada = elemento.get("coordenada")

        if template:
            achado = self._runner.find_template(template)
            if achado:
                self._log(f"[resolvedor] '{nome}' por template em ({achado.x}, {achado.y})")
                return Alvo("template", ponto=(achado.x, achado.y))
            if coordenada is None:
                self._log(f"[resolvedor] '{nome}': template nao encontrado e sem "
                          f"coordenada — inalcancavel")
                return None
            self._log(f"[resolvedor] DEGRADACAO em '{nome}': template nao encontrado, "
                      f"usando coordenada fixa")
            return Alvo("coordenada", ponto=(coordenada["x"], coordenada["y"]),
                        degradado=True)

        if coordenada:
            return Alvo("coordenada", ponto=(coordenada["x"], coordenada["y"]))

        self._log(f"[resolvedor] '{nome}' sem template, coordenada ou seletor — "
                  f"inalcancavel")
        return None