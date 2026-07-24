# src/core/object_repository.py
import yaml


class ObjectRepository:
    def __init__(self, objetos: dict):
        self._objetos = objetos

    @classmethod
    def from_yaml(cls, caminho: str) -> "ObjectRepository":
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = yaml.safe_load(f)
        objetos = conteudo.get("objetos", {})
        return cls(objetos)

    def _obter_objeto(self, nome: str) -> dict:
        objeto = self._objetos.get(nome)
        if objeto is None:
            raise KeyError(
                f"Objeto '{nome}' nao encontrado em objects/cadastro_min.yaml"
            )
        return objeto

    def coord(self, nome: str) -> tuple[int, int]:
        objeto = self._obter_objeto(nome)
        c = objeto.get("coordenada")
        if c is None:
            raise KeyError(f"Objeto '{nome}' nao tem 'coordenada' definida.")
        return c["x"], c["y"]

    def regiao_ocr(self, nome: str) -> tuple[int, int, int, int]:
        objeto = self._obter_objeto(nome)
        r = objeto.get("regiao_ocr")
        if r is None:
            raise KeyError(f"Objeto '{nome}' nao tem 'regiao_ocr' definida.")
        return r["x1"], r["y1"], r["x2"], r["y2"]

    def template(self, nome: str) -> str:
        objeto = self._obter_objeto(nome)
        t = objeto.get("template")
        if t is None:
            raise KeyError(f"Objeto '{nome}' nao tem 'template' definido.")
        return t