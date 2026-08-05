# vtae/core/motor/verificacao.py
"""
Verificacao — peca 3 do motor (Projeto v1.1, Fase 2).

Responde UMA pergunta: o que esta na tela e o que o teste mandou colocar?
Nao preenche, nao clica, nao espera, nao tira screenshot.

NUNCA levanta excecao: devolve Veredito e quem chama (peca 4) decide se
mata o step (regra 45). Isso e o que torna esta peca testavel inteira
sem tela.

A camada que decide sai do 'tipo:' do elemento e da 'camada_exata' da
tela — a matriz do Projeto v1 secao 6 virando tabela do motor.
"""
from dataclasses import dataclass

from vtae.core.texto import _normalizar, _similar

OK = "OK"
DIVERGENTE = "DIVERGENTE"
VAZIO = "VAZIO"
NAO_VERIFICAVEL = "NAO_VERIFICAVEL"

# Campo com mascara (data): prova-se por estrutura, nunca por valor
# exato — o Forms reformata DDMMYYYY -> DD/MM/YYYY e o OCR erra digito.
# 6 e o numero que o CM05 usa e que passou 3x em tela real.
# Imune a mudanca de formato (AAAA/DD/MM conta os mesmos digitos).
MIN_DIGITOS_MASCARA = 6

# Tipos em que a camada exata NAO e opcional: LOV sofre match parcial
# silencioso (caso ALLIANZ, medido 3x) e o OCR estruturalmente nao
# alcanca isso. Texto livre e resultado gerado ficam bem servidos por
# OCR — matriz do Projeto v1 secao 6. Exigir mais que isso reprovaria
# campos que nunca precisaram de jab_name (nome, matricula).
EXIGEM_CAMADA_EXATA = ("lov", "lov_lista")

TIMEOUT_OCR = 3.0


@dataclass(frozen=True)
class Veredito:
    status: str
    elemento: str
    esperado: str | None = None
    lido_exato: str | None = None
    lido_ocr: str | None = None
    camada_decisora: str = "nenhuma"
    degradado: bool = False      # a tela TEM camada exata e nao pudemos usar
    divergencia: bool = False    # camada exata e OCR discordam entre si
    motivo: str = ""

    @property
    def aprovado(self) -> bool:
        return self.status == OK


class Verificador:
    """
    leitor_exato: qualquer objeto com .ler(locator) -> str | None.
    Adaptador pyjab hoje; Playwright na peca 5. O motor nunca importa
    nenhum dos dois — so recebe quem sabe ler.
    """

    def __init__(self, objects, runner, leitor_exato=None, logger=None):
        self._objects = objects
        self._runner = runner
        self._leitor = leitor_exato
        self._logger = logger

    def _log(self, msg: str) -> None:
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)

    # ------------------------------------------------------------------
    def verificar(self, nome: str, valor_esperado=None) -> Veredito:
        elemento = self._objects.elemento(nome)
        if elemento is None:
            return self._reprovar(nome, valor_esperado, NAO_VERIFICAVEL,
                                  "nao declarado em objects/")

        tipo = elemento.get("tipo", "texto")
        if tipo == "botao":
            return self._reprovar(nome, valor_esperado, NAO_VERIFICAVEL,
                                  "tipo 'botao' nao tem valor a verificar")

        camada = self._objects.camada_exata()
        exige_exata = tipo in EXIGEM_CAMADA_EXATA
        lido_exato, degradado, impedimento = self._ler_exato(
            elemento, camada, exige_exata)
        if impedimento:
            return self._reprovar(nome, valor_esperado, NAO_VERIFICAVEL,
                                  impedimento)

        lido_ocr = self._ler_ocr(nome)

        veredito = self._decidir(nome, tipo, valor_esperado,
                                 lido_exato, lido_ocr, degradado)
        self._log(f"[verificacao] {veredito.status} '{nome}' "
                  f"(decisor: {veredito.camada_decisora}) — {veredito.motivo}")
        return veredito

    # ------------------------------------------------------------------
    def _ler_exato(self, elemento, camada, exige_exata):
        """
        Devolve (lido, degradado, impedimento).

        impedimento != None e erro de CONFIGURACAO: a tela declara camada
        exata, o tipo do campo EXIGE essa camada, e o locator nao foi
        calibrado. Regra 54 — nunca pular em silencio.

        Quando o tipo nao exige (texto, resultado), a ausencia do locator
        e normal: OCR da conta, sem degradacao. Degradar ali pintaria de
        amarelo campos que nunca precisaram de pyjab.
        """
        if camada == "nenhuma":
            return None, False, None

        chave = "jab_name" if camada == "pyjab" else "seletor"
        locator = elemento.get(chave)
        if not locator:
            if not exige_exata:
                return None, False, None
            return None, False, (f"tela declara camada_exata '{camada}' mas o "
                                 f"elemento nao tem '{chave}' — calibrar")

        if self._leitor is None:
            return None, exige_exata, None

        lido = self._leitor.ler(locator)
        if lido is None:
            return None, exige_exata, None
        return lido, False, None

    def _ler_ocr(self, nome):
        regiao = self._objects.regiao_ocr(nome)
        if not (isinstance(regiao, tuple) and len(regiao) == 4 and any(regiao)):
            return None
        ok, lido = self._runner.verify_lov(nome, region=regiao,
                                           timeout=TIMEOUT_OCR)
        if not ok:
            return ""
        return lido

    # ------------------------------------------------------------------
    def _decidir(self, nome, tipo, esperado, lido_exato, lido_ocr, degradado):
        if lido_exato is not None:
            return self._decidir_exato(nome, esperado, lido_exato, lido_ocr)
        if lido_ocr is None:
            return self._reprovar(
                nome, esperado, NAO_VERIFICAVEL,
                "sem regiao_ocr calibrada e sem leitura exata", degradado)
        return self._decidir_ocr(nome, tipo, esperado, lido_ocr, degradado)

    def _decidir_exato(self, nome, esperado, lido, lido_ocr):
        """Leitura exata: sem tolerancia Levenshtein (regra 30)."""
        base = dict(elemento=nome, esperado=esperado, lido_exato=lido,
                    lido_ocr=lido_ocr, camada_decisora="exata")
        if not lido.strip():
            return Veredito(status=VAZIO, motivo="campo vazio", **base)
        if esperado is None:
            return Veredito(status=OK, motivo=f"preenchido: '{lido}'", **base)

        acertou = _normalizar(lido) == _normalizar(str(esperado))
        divergencia = (lido_ocr is not None
                       and not _similar(_normalizar(lido_ocr),
                                        _normalizar(lido)))
        if acertou:
            return Veredito(status=OK, divergencia=divergencia,
                            motivo=(f"'{lido}' confere"
                                    + (f" (OCR leu '{lido_ocr}' — divergencia "
                                       f"entre camadas)" if divergencia else "")),
                            **base)
        return Veredito(status=DIVERGENTE, divergencia=divergencia,
                        motivo=f"esperado '{esperado}', leitura exata '{lido}'",
                        **base)

    def _decidir_ocr(self, nome, tipo, esperado, lido, degradado):
        base = dict(elemento=nome, esperado=esperado, lido_ocr=lido,
                    camada_decisora="ocr", degradado=degradado)
        if not lido.strip():
            return Veredito(status=VAZIO, motivo="OCR nao leu nada", **base)

        if tipo == "data":
            digitos = sum(c.isdigit() for c in lido)
            if digitos >= MIN_DIGITOS_MASCARA:
                return Veredito(status=OK,
                                motivo=f"{digitos} digitos em '{lido}'", **base)
            return Veredito(status=DIVERGENTE,
                            motivo=(f"'{lido}' tem {digitos} digitos, minimo "
                                    f"{MIN_DIGITOS_MASCARA}"), **base)

        if tipo == "resultado" and esperado is None:
            return Veredito(status=OK, motivo=f"gerado: '{lido}'", **base)

        if esperado is None:
            return Veredito(status=OK, motivo=f"preenchido: '{lido}'", **base)

        # LOV decidida por OCR: containment desligado. 'ALLIANZ' esta
        # contido em 'ALLIANZ SAUDE' — e exatamente assim que o match
        # parcial silencioso do Forms passaria verde sem camada exata.
        containment = tipo not in ("lov", "lov_lista")
        if _similar(_normalizar(lido), _normalizar(str(esperado)),
                    permitir_containment=containment):
            return Veredito(status=OK, motivo=f"'{lido}' confere", **base)
        return Veredito(status=DIVERGENTE,
                        motivo=f"esperado '{esperado}', OCR leu '{lido}'",
                        **base)

    # ------------------------------------------------------------------
    def _reprovar(self, nome, esperado, status, motivo, degradado=False):
        self._log(f"[verificacao] {status} '{nome}' — {motivo}")
        return Veredito(status=status, elemento=nome, esperado=esperado,
                        motivo=motivo, degradado=degradado)