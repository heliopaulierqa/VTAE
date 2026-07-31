# scripts/mapear_names_jab.py
"""
Mapeia os names JAB (Java Access Bridge) dos elementos de uma janela
Oracle Forms — usado para preencher o locator jab_name no YAML de objetos
(Modelo de Elemento, Projeto v1 §4).

Pre-condicoes:
    - SI3 aberto, com a TELA ALVO visivel (ex: formulario de cadastro
      ja aberto, apos clicar em Novo)
    - WindowsAccessBridge-64.dll acessivel via JAVA_HOME de mentira
      (default C:\\jab_home — mesmo esquema do flow, regra 31)

Uso:
    python scripts/mapear_names_jab.py                          # tudo -> arquivo
    python scripts/mapear_names_jab.py "Cadastro De Pacientes"
    python scripts/mapear_names_jab.py "Cadastro De Pacientes" sexo
    python scripts/mapear_names_jab.py "Cadastro De Pacientes" nacional

    2o argumento (opcional) = FILTRO: mostra no console apenas elementos
    cujo name contem o termo (sem acento, sem case). O dump COMPLETO vai
    sempre para scripts/jab_dump.txt — abrir no editor e Ctrl+F.

Saida:
    Lista role | name | text. Copiar o name EXATO (com pontuacao) para o
    jab_name do objeto correspondente em objects/<tela>.yaml.
"""

import logging
import os
import sys
import unicodedata

# JAVA_HOME de mentira ANTES do import pyjab — a DLL e procurada no import.
# Mesmo padrao do flow (nunca setx — regra 31).
os.environ.setdefault("JAVA_HOME", r"C:\jab_home")

# Silencia os WARNINGs "does not support Accessible Text" do pyjab —
# ruido esperado em itens de menu, poluia 2500+ linhas do console.
logging.getLogger("pyjab").setLevel(logging.ERROR)

from pyjab.jabdriver import JABDriver  # noqa: E402

# Roles que interessam para mapeamento de campos
_ROLES = ["text", "combo box", "label", "push button"]

_ARQUIVO_DUMP = os.path.join(os.path.dirname(__file__), "jab_dump.txt")


def _norm(s: str) -> str:
    return (unicodedata.normalize("NFD", s or "")
            .encode("ascii", "ignore").decode("ascii").lower())


def main() -> None:
    titulo = sys.argv[1] if len(sys.argv) > 1 else "Form_Pac0010"
    filtro = _norm(sys.argv[2]) if len(sys.argv) > 2 else None
    print(f"Conectando na janela: '{titulo}' ...")

    try:
        driver = JABDriver(title=titulo)
    except Exception as e:
        print(f"ERRO: JABDriver nao conectou na janela '{titulo}': {e}")
        print("Dicas:")
        print("  - A janela esta aberta e com o titulo exato? "
              "(passe o titulo como argumento se for outro)")
        print("  - A DLL WindowsAccessBridge-64.dll esta em "
              f"{os.environ['JAVA_HOME']}\\bin ?")
        sys.exit(1)

    total = 0
    exibidos = 0
    with open(_ARQUIVO_DUMP, "w", encoding="utf-8") as dump:
        for role in _ROLES:
            try:
                elementos = driver.find_elements_by_role(role)
            except Exception as e:
                print(f"[{role}] erro ao listar: {e}")
                continue
            if not elementos:
                continue
            dump.write(f"\n=== role: {role} ({len(elementos)} elementos) ===\n")
            for el in elementos:
                try:
                    name = el.name
                except Exception:
                    name = "<erro ao ler>"
                try:
                    texto = el.text
                except Exception:
                    texto = None
                total += 1
                linha = f"  name: {name!r:<55} | text: {texto!r}"
                dump.write(f"[{role}] {linha}\n")
                if filtro is None or filtro in _norm(name):
                    if filtro is not None:
                        print(f"[{role}] {linha}")
                        exibidos += 1

    if filtro is not None:
        print(f"\n{exibidos} elementos casaram com o filtro '{sys.argv[2]}' "
              f"(de {total} no total).")
    print(f"Dump completo ({total} elementos): {_ARQUIVO_DUMP}")
    print("Copie o name EXATO (aspas, acentos e pontuacao incluidos) "
          "para o jab_name do objeto no YAML.")


if __name__ == "__main__":
    main()
