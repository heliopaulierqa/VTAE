# vtae/core/object_repository.py
import yaml


class ObjectRepository:
    def __init__(self, objetos: dict, tela: dict = None):
        self._objetos = objetos
        self._tela = tela or {}

    @classmethod
    def from_yaml(cls, caminho: str) -> "ObjectRepository":
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = yaml.safe_load(f)
        objetos = conteudo.get("objetos", {})
        tela = conteudo.get("tela", {})
        return cls(objetos, tela)

    def titulo_jab(self) -> str | None:
        """
        Titulo da janela Java (JABDriver) — propriedade da TELA, nao de
        um objeto. Tolerante: None se nao mapeado (bootstrap).
        """
        return self._tela.get("titulo_jab")
    
    def titulo_janela(self) -> str | None:
        """
        Titulo (parcial) da janela do sistema operacional desta tela.
        Propriedade da TELA, como titulo_jab. Tolerante: None quando nao
        declarada — o motor avisa e segue sem garantir foco.
        """
        return self._tela.get("titulo_janela")
    
    def ancora(self) -> str | None:
        """
        Nome do elemento que prova que a tela esta pronta. Propriedade da
        TELA, como titulo_jab. Tolerante: None quando nao declarada.
        """
        return self._tela.get("ancora")
    
    def camada_exata(self) -> str:
        """
        Como esta tela permite ler o valor REAL de um campo, e nao o
        bitmap: "pyjab" (Oracle Forms), "playwright" (web) ou "nenhuma"
        (Citrix, legado sem acessibilidade).

        Propriedade da TELA, como titulo_jab e ancora.

        Default "nenhuma" e DECLARADO, nunca inferido: se o motor
        adivinhasse pela presenca de titulo_jab, "esqueci de mapear este
        campo" viraria "este sistema nao tem camada exata" — as duas
        situacoes que a peca 3 existe para separar.
        """
        return self._tela.get("camada_exata", "nenhuma")

    def _obter_objeto(self, nome: str) -> dict:
        objeto = self._objetos.get(nome)
        if objeto is None:
            raise KeyError(
                f"Objeto '{nome}' nao encontrado em objects/cadastro_min.yaml"
            )
        return objeto
    

    def elemento(self, nome: str) -> dict | None:
        """
        Devolve o elemento inteiro (tipo + locators) ou None se o nome
        nao existe. TOLERANTE por design: quem pergunta e o resolvedor
        do motor, que precisa testar "tem template?" sem tomar KeyError.

        Distinguir None de "existe mas sem locator" e o que permite o
        motor dar dois erros diferentes: nome nao declarado vs elemento
        inalcancavel. Os demais metodos ficam como estao.
        """
        objeto = self._objetos.get(nome)
        if objeto is None:
            return None
        return dict(objeto)    

    def coord(self, nome: str) -> tuple[int, int]:
        objeto = self._obter_objeto(nome)
        c = objeto.get("coordenada")
        if c is None:
            raise KeyError(f"Objeto '{nome}' nao tem 'coordenada' definida.")
        return c["x"], c["y"]

    def regiao_ocr(self, nome: str) -> tuple[int, int, int, int] | None:
        """
        Regiao de leitura OCR do objeto.

        TOLERANTE por design (None em vez de KeyError), mesmo motivo de
        jab_name(): a calibracao e feita campo a campo na tela real, e
        regiao ausente e bootstrap, nao erro. Objeto inexistente tambem
        devolve None — um nome errado reaparece como AVISO no log do step
        ("regiao 'X' nao calibrada"), com o nome errado visivel.

        coord() segue ESTRITO de proposito: la um nome errado vira clique
        em lugar nenhum, entao tem que explodir.
        """
        objeto = self._objetos.get(nome)
        if objeto is None:
            return None
        r = objeto.get("regiao_ocr")
        if r is None:
            return None
        return r["x1"], r["y1"], r["x2"], r["y2"]

    def template(self, nome: str) -> str:
        objeto = self._obter_objeto(nome)
        t = objeto.get("template")
        if t is None:
            raise KeyError(f"Objeto '{nome}' nao tem 'template' definido.")
        return t

    def jab_name(self, nome: str) -> str | None:
        """
        Locator de acessibilidade (Java Access Bridge) do objeto.

        TOLERANTE por design (retorna None em vez de KeyError): o mapeamento
        de names JAB e feito campo a campo na tela real — enquanto um campo
        nao foi mapeado, a verificacao pyjab e pulada com aviso (mesmo
        padrao bootstrap das regioes_ocr nao calibradas). Nao quebra flows
        que ainda nao tem essa camada ativa.
        """
        objeto = self._obter_objeto(nome)
        return objeto.get("jab_name")