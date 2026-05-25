# diagnostico_jab_v2.py
# Rodar com SI3 aberto e maximizado, APOS jabswitch /enable + reabrir SI3
# python scripts/diagnostico_jab_v2.py

import subprocess
import sys

# ── 1. Status do JAB ─────────────────────────────────────────────────
print("=" * 60)
print("1. Java Access Bridge")
print("=" * 60)
result = subprocess.run(["jabswitch", "/version"], capture_output=True, text=True)
print(result.stdout.strip())

# ── 2. Janelas Java (SunAwtFrame) ────────────────────────────────────
print("\n" + "=" * 60)
print("2. Janelas Java abertas (SunAwtFrame)")
print("=" * 60)
try:
    from pywinauto import Desktop

    wins = Desktop(backend="uia").windows()
    java_wins = [w for w in wins if "SunAwt" in w.class_name()]

    if not java_wins:
        print("Nenhuma janela Java encontrada.")
        print("Todas as janelas abertas:")
        for w in wins:
            try:
                print(f"  [{w.class_name():30s}] {w.window_text()}")
            except Exception:
                pass
        sys.exit(1)

    for w in java_wins:
        print(f"  [{w.class_name()}] '{w.window_text()}'")

except Exception as e:
    print(f"ERRO pywinauto: {e}")
    sys.exit(1)

# ── 3. Arvore do Menu Principal (Forms) ──────────────────────────────
print("\n" + "=" * 60)
print("3. Arvore de componentes — Menu Principal (SI3)")
print("=" * 60)

app = None
# Busca por classe Java, nao por titulo
for w in java_wins:
    titulo = w.window_text()
    if any(t in titulo for t in ["Menu Principal", "SI3", "Oracle", "INCOR", "Forms"]):
        app = w
        print(f"Usando janela: '{titulo}'")
        break

# fallback: pega a primeira janela Java
if app is None and java_wins:
    app = java_wins[0]
    print(f"Usando primeira janela Java: '{app.window_text()}'")

print("\nImprimindo arvore (depth=5) — aguarde...\n")
try:
    app.print_control_identifiers(depth=5)
except Exception as e:
    print(f"ERRO arvore uia: {e}")

# ── 4. pyjab — acesso direto ao JAB ──────────────────────────────────
print("\n" + "=" * 60)
print("4. pyjab — Java Access Bridge direto")
print("=" * 60)
try:
    from pyjab.jabdriver import JABDriver
    driver = JABDriver()
    wins_jab = driver.get_windows()
    print(f"Janelas via JAB: {len(wins_jab)}")
    for w in wins_jab:
        print(f"\n  Janela: {w}")
        try:
            # tenta listar filhos de primeiro nivel
            children = w.get_accessible_children()
            print(f"  Filhos: {len(children)}")
            for c in children[:10]:
                print(f"    role={c.accessible_role:20s} name='{c.accessible_name}'")
        except Exception as ce:
            print(f"  (sem filhos listados: {ce})")

except ImportError:
    print("pyjab nao instalado: pip install pyjab")
except Exception as e:
    print(f"pyjab erro: {e}")
    if "dll not found" in str(e).lower():
        print("\n>>> JAB ainda nao esta ativo.")
        print(">>> Execute: jabswitch /enable")
        print(">>> Depois FECHE E REABRA o SI3.")
        print(">>> Entao rode este script novamente.")