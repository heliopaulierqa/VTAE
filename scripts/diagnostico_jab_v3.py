# diagnostico_jab_v3.py
# python scripts/diagnostico_jab_v3.py
# Rodar com SI3 aberto e maximizado

from pywinauto import Desktop

def dump_tree(elem, depth=0, max_depth=6):
    if depth > max_depth:
        return
    try:
        indent = "  " * depth
        ctrl_type = elem.element_info.control_type
        name      = elem.element_info.name or ""
        auto_id   = getattr(elem.element_info, "automation_id", "") or ""
        print(f"{indent}[{ctrl_type}] name='{name}' id='{auto_id}'")
    except Exception as e:
        print(f"{'  '*depth}(erro: {e})")
        return
    try:
        for child in elem.children():
            dump_tree(child, depth + 1, max_depth)
    except Exception:
        pass

# ── Localizar janela Java ─────────────────────────────────────────────
print("Buscando SunAwtFrame (Menu Principal)...\n")
wins = Desktop(backend="uia").windows()
java_wins = [w for w in wins if "SunAwt" in w.class_name()]

if not java_wins:
    print("Nenhuma janela Java encontrada.")
    raise SystemExit(1)

for w in java_wins:
    print(f"[{w.class_name()}] '{w.window_text()}'")

app = java_wins[0]
print(f"\nExplorando: '{app.window_text()}'\n")
print("=" * 60)
dump_tree(app, max_depth=6)

# ── Filhos diretos com bounds ─────────────────────────────────────────
print("\n" + "=" * 60)
print("Filhos diretos com bounds:")
print("=" * 60)
try:
    for child in app.children():
        try:
            info = child.element_info
            rect = child.rectangle()
            print(f"  [{info.control_type:20s}] name='{info.name}' "
                  f"bounds=({rect.left},{rect.top},{rect.right},{rect.bottom})")
        except Exception as e:
            print(f"  (erro filho: {e})")
except Exception as e:
    print(f"Erro: {e}")

# ── Buscar DLL do JAB e tentar pyjab ─────────────────────────────────
print("\n" + "=" * 60)
print("Buscando WindowsAccessBridge-64.dll...")
print("=" * 60)
import os, glob

dll_found = None
patterns = [
    r"C:\Program Files\Java\jdk*\bin\WindowsAccessBridge-64.dll",
    r"C:\Program Files\Eclipse Adoptium\*\bin\WindowsAccessBridge-64.dll",
    r"C:\Program Files\Microsoft\jdk*\bin\WindowsAccessBridge-64.dll",
    r"C:\Program Files\Java\jre*\bin\WindowsAccessBridge-64.dll",
]
for p in patterns:
    m = glob.glob(p)
    if m:
        dll_found = m[0]
        break

java_home = os.environ.get("JAVA_HOME", "")
if not dll_found and java_home:
    c = os.path.join(java_home, "bin", "WindowsAccessBridge-64.dll")
    if os.path.exists(c):
        dll_found = c

if not dll_found:
    # busca rapida em Program Files
    for root, dirs, files in os.walk(r"C:\Program Files"):
        for f in files:
            if f.lower() == "windowsaccessbridge-64.dll":
                dll_found = os.path.join(root, f)
                break
        dirs[:] = [d for d in dirs if d not in
                   ["node_modules", "Git", "Mozilla Firefox", "Google"]]
        if dll_found:
            break

if dll_found:
    print(f"DLL encontrada: {dll_found}")
    os.environ["WINDOWSACCESSBRIDGE_DLL"] = dll_found
    try:
        from pyjab.jabdriver import JABDriver
        driver = JABDriver()
        wins_jab = driver.get_windows()
        print(f"\nJanelas via JAB: {len(wins_jab)}")
        for w in wins_jab:
            print(f"\n  Janela: {w}")
            try:
                children = w.get_accessible_children()
                for c in children[:15]:
                    print(f"    role={getattr(c,'accessible_role','?'):25s} "
                          f"name='{getattr(c,'accessible_name','')}'")
            except Exception as ce:
                print(f"  (filhos: {ce})")
    except Exception as e:
        print(f"pyjab erro mesmo com DLL: {e}")
else:
    print("DLL nao encontrada. Verifique onde o JDK esta instalado.")
    print("Rode no PowerShell:")
    print('  Get-ChildItem "C:\\" -Recurse -Filter "WindowsAccessBridge-64.dll" -ErrorAction SilentlyContinue')