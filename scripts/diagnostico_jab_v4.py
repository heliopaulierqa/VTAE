# diagnostico_jab_v4.py
# Acessa o Java Access Bridge via ctypes direto — sem depender do pyjab
# python scripts/diagnostico_jab_v4.py
# Rodar com SI3 aberto e maximizado, APOS jabswitch /enable + logoff/logon

import ctypes
import ctypes.wintypes
import os
import glob
import sys

# ── 1. Localizar DLLs disponíveis ────────────────────────────────────
print("=" * 60)
print("1. DLLs WindowsAccessBridge encontradas")
print("=" * 60)

dlls = []
# JRE 1.8 primeiro — é o que o jabswitch gerencia
jre8 = r"C:\Program Files\Java\jre1.8.0_431\bin\WindowsAccessBridge-64.dll"
if os.path.exists(jre8):
    dlls.append(jre8)

# JDK 25 e 26 como fallback
dlls += glob.glob(r"C:\Program Files\Java\jdk*\bin\WindowsAccessBridge-64.dll",
                  recursive=False)
dlls += glob.glob(r"C:\Program Files\Eclipse Adoptium\**\WindowsAccessBridge-64.dll",
                  recursive=True)

java_home = os.environ.get("JAVA_HOME", "")
if java_home:
    c = os.path.join(java_home, "bin", "WindowsAccessBridge-64.dll")
    if os.path.exists(c) and c not in dlls:
        dlls.append(c)

for d in dlls:
    print(f"  {d}")

if not dlls:
    print("Nenhuma DLL encontrada.")
    sys.exit(1)

# ── 2. Tentar carregar a DLL via ctypes ───────────────────────────────
print("\n" + "=" * 60)
print("2. Carregando DLL via ctypes")
print("=" * 60)

jab = None
dll_usada = None
for dll_path in dlls:
    try:
        jab = ctypes.WinDLL(dll_path)
        dll_usada = dll_path
        print(f"OK: {dll_path}")
        break
    except Exception as e:
        print(f"FALHOU {dll_path}: {e}")

if jab is None:
    print("Nenhuma DLL carregou com sucesso.")
    sys.exit(1)

# ── 3. Inicializar o JAB ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. Inicializando Java Access Bridge")
print("=" * 60)

try:
    # Windows_run() inicializa o JAB — retorna True se OK
    jab.Windows_run.restype = ctypes.c_bool
    result = jab.Windows_run()
    print(f"Windows_run() = {result}")
    if not result:
        print("JAB nao inicializou. Verifique se jabswitch /enable foi rodado")
        print("e se a sessao Windows foi reiniciada (logoff/logon).")
        sys.exit(1)
except Exception as e:
    print(f"Erro Windows_run: {e}")
    sys.exit(1)

# ── 4. Listar janelas acessíveis ──────────────────────────────────────
print("\n" + "=" * 60)
print("4. Janelas acessíveis via JAB")
print("=" * 60)

try:
    # getAccessibleWindowsCount
    jab.getAccessibleWindowsCount.restype = ctypes.c_int
    count = jab.getAccessibleWindowsCount()
    print(f"Janelas acessíveis: {count}")
except Exception as e:
    print(f"getAccessibleWindowsCount erro: {e}")
    count = 0

# ── 5. Abordagem alternativa — isJavaWindow para cada HWND ───────────
print("\n" + "=" * 60)
print("5. Procurando janelas Java por HWND")
print("=" * 60)

import ctypes.wintypes

user32 = ctypes.windll.user32

try:
    jab.isJavaWindow.argtypes = [ctypes.wintypes.HWND]
    jab.isJavaWindow.restype  = ctypes.c_bool
except Exception as e:
    print(f"isJavaWindow nao disponivel: {e}")
    sys.exit(1)

java_hwnds = []

def enum_callback(hwnd, lParam):
    try:
        if jab.isJavaWindow(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            titulo = buf.value
            java_hwnds.append((hwnd, titulo))
            print(f"  HWND={hwnd} titulo='{titulo}'")
    except Exception:
        pass
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                  ctypes.wintypes.HWND,
                                  ctypes.wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

if not java_hwnds:
    print("Nenhuma janela Java encontrada via isJavaWindow.")
    print("Possível causa: JAB não está ativo nesta sessão.")
    print("Execute: jabswitch /enable  → logoff → logon → abrir SI3 → rodar script")
    sys.exit(1)

# ── 6. Inspecionar componentes da janela Forms ────────────────────────
print("\n" + "=" * 60)
print("6. Componentes acessíveis — Menu Principal")
print("=" * 60)

# Estruturas JAB
class AccessibleContextInfo(ctypes.Structure):
    _fields_ = [
        ("name",          ctypes.c_wchar * 1024),
        ("description",   ctypes.c_wchar * 1024),
        ("role",          ctypes.c_wchar * 256),
        ("role_en_US",    ctypes.c_wchar * 256),
        ("states",        ctypes.c_wchar * 256),
        ("states_en_US",  ctypes.c_wchar * 256),
        ("indexInParent", ctypes.c_int),
        ("childrenCount", ctypes.c_int),
        ("x",             ctypes.c_int),
        ("y",             ctypes.c_int),
        ("width",         ctypes.c_int),
        ("height",        ctypes.c_int),
        ("accessibleComponent",  ctypes.c_bool),
        ("accessibleAction",     ctypes.c_bool),
        ("accessibleSelection",  ctypes.c_bool),
        ("accessibleText",       ctypes.c_bool),
        ("accessibleValue",      ctypes.c_bool),
    ]

try:
    jab.getAccessibleContextFromHWND.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.POINTER(ctypes.c_long),   # vmID
        ctypes.POINTER(ctypes.c_long),   # ac
    ]
    jab.getAccessibleContextFromHWND.restype = ctypes.c_bool

    jab.getAccessibleContextInfo.argtypes = [
        ctypes.c_long,                   # vmID
        ctypes.c_long,                   # ac
        ctypes.POINTER(AccessibleContextInfo),
    ]
    jab.getAccessibleContextInfo.restype = ctypes.c_bool

    jab.getAccessibleChildFromContext.argtypes = [
        ctypes.c_long,  # vmID
        ctypes.c_long,  # ac
        ctypes.c_int,   # index
    ]
    jab.getAccessibleChildFromContext.restype = ctypes.c_long

except Exception as e:
    print(f"Erro configurando funções JAB: {e}")
    sys.exit(1)


def inspecionar(vmid, ac, depth=0, max_depth=5):
    if depth > max_depth:
        return
    info = AccessibleContextInfo()
    ok = jab.getAccessibleContextInfo(vmid, ac, ctypes.byref(info))
    if not ok:
        return
    indent = "  " * depth
    print(f"{indent}role='{info.role_en_US}' name='{info.name}' "
          f"pos=({info.x},{info.y}) size={info.width}x{info.height} "
          f"filhos={info.childrenCount}")
    for i in range(min(info.childrenCount, 30)):
        child_ac = jab.getAccessibleChildFromContext(vmid, ac, i)
        if child_ac:
            inspecionar(vmid, child_ac, depth + 1, max_depth)


for hwnd, titulo in java_hwnds:
    if any(t in titulo for t in ["Menu Principal", "SI3", "Oracle", "Cadastro",
                                  "Admiss", "Paciente"]):
        print(f"\nInspecionando: '{titulo}' (HWND={hwnd})\n")
        vmid  = ctypes.c_long(0)
        ac    = ctypes.c_long(0)
        ok = jab.getAccessibleContextFromHWND(hwnd,
                                               ctypes.byref(vmid),
                                               ctypes.byref(ac))
        if ok:
            inspecionar(vmid.value, ac.value, max_depth=5)
        else:
            print(f"  getAccessibleContextFromHWND falhou para HWND={hwnd}")