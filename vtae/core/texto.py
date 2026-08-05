# vtae/core/texto.py
"""
Comparacao de texto do VTAE.

Extraido de vtae/flows/base_flow.py sem mudanca de comportamento, para
que vtae/core/ nao precise importar vtae/flows/ (peca 3 do motor).

_similar ganhou permitir_containment: quando o OCR e a camada DECISORA
de um LOV (sistema sem camada exata — Citrix, web sem adaptador), o
containment aprova o match parcial silencioso do Oracle Forms
('ALLIANZ' contido em 'ALLIANZ SAUDE'). Nesse caso ele e desligado.
"""
import unicodedata


def _normalizar(texto: str) -> str:
    """
    Remove acentos, separadores de data e converte para maiusculo.
    - EasyOCR perde acentos em fontes Oracle Forms (CAMARA vs CAMARA)
    - Oracle Forms exibe DD/MM/YYYY mas o flow digita DDMMYYYY
    - / - . removidos para comparar apenas os digitos
    """
    sem_acento = (
        unicodedata.normalize("NFD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    sem_separadores = sem_acento.replace("/", "").replace("-", "").replace(".", "")
    return sem_separadores.upper().strip()


def _similar(lido: str, esperado: str, tolerancia: float = 0.230,
             permitir_containment: bool = True) -> bool:
    """
    Compara dois textos com tolerancia a erros de OCR (distancia de edicao).

    tolerancia=0.230 — valor que passou os gates em tela real.
    Exemplos observados no SI3 (Oracle Forms via Edge, CPU):
      BRUNA  (5 chars)  -> 1 erro permitido  -> '3RUNA' passa  (B/3)
      OLIVIA COSTA (11) -> 2 erros permitidos -> 'DLIIA COSTA' passa

    permitir_containment=False desliga o atalho "um contem o outro".
    Usar quando o OCR decide sozinho um LOV — ver Verificador.

    NAO usar em leitura exata (pyjab/Playwright): sem ruido de OCR, a
    tolerancia so perderia precisao (regra 30).
    """
    if not lido or not esperado:
        return False
    if permitir_containment and (esperado in lido or lido in esperado):
        return True
    a, b = lido, esperado
    if len(a) > len(b):
        a, b = b, a
    distancias = range(len(a) + 1)
    for c2 in b:
        distancias_ = [distancias[0] + 1]
        for c1, d0, d1 in zip(a, distancias, distancias[1:]):
            distancias_.append(min(d1 + 1, d0 + 1, d0 + (c1 != c2)))
        distancias = distancias_
    dist = distancias[-1]
    max_erros = max(1, int(len(esperado) * tolerancia))
    return dist <= max_erros