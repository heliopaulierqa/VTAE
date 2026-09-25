# vtae/cli/mapear.py
"""
vtae mapear <objects/.../tela.yaml> [--templates templates/.../tela]

Mapeia os elementos de UMA tela de QUALQUER sistema, sem escrever YAML
nem coordenada a mao (decisao 26, 24/09/2026).

Como funciona:
  1. Voce roda o comando e tem 5 segundos para deixar a tela do sistema
     na frente, maximizada.
  2. O VTAE tira um screenshot e o mostra em tela cheia.
  3. Voce arrasta um retangulo em volta de um elemento e responde:
     nome e tipo. Repete para cada elemento. ESC termina.
  4. O VTAE grava, para cada elemento:
       - botao ............ recorte (template) + coordenada do centro
       - texto/data/
         resultado ........ coordenada do centro + regiao_ocr (o retangulo)
       - lov/lov_lista .... idem texto; as chaves extras (btn_ok...) o
                            'vtae executar' cobra com mensagem clara
     no arquivo de objetos, e o recorte na pasta de templates.
  5. Todo recorte e MEDIDO na hora: se a imagem aparece mais de uma vez
     na tela, o VTAE avisa — template ambiguo clica no lugar errado.

Os recortes saem de pyautogui.screenshot() + PIL.crop(), a regra do
projeto: nunca recorte colado de outra ferramenta.
"""
import time
from pathlib import Path

import yaml

TIPOS = ("texto", "data", "lov", "lov_lista", "botao", "resultado")
TIPOS_COM_TEMPLATE = ("botao",)
ESPERA_INICIAL = 5
LIMIAR_AMBIGUIDADE = 0.85
# Retangulo maior que isto (fracao da tela) quase sempre e engano: o
# elemento e pequeno. Medido no primeiro uso real (25/09): um retangulo
# da tela inteira virou 'tela_login' sem imagem e sem utilidade.
FRACAO_MAXIMA_DA_TELA = 0.25


# ── logica pura (testavel sem tela) ──────────────────────────────────
def montar_entrada(tipo: str, x1: int, y1: int, x2: int, y2: int,
                   template: str | None = None) -> dict:
    if tipo not in TIPOS:
        raise ValueError(f"tipo '{tipo}' desconhecido — use um de {TIPOS}")
    x1, x2 = sorted((int(x1), int(x2)))
    y1, y2 = sorted((int(y1), int(y2)))
    entrada = {"tipo": tipo,
               "coordenada": {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2}}
    if template:
        entrada["template"] = template
    if tipo != "botao":
        entrada["regiao_ocr"] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
    return entrada


def _inline(d: dict) -> str:
    # regra do projeto: espaco apos os dois pontos em { x1: 27, y1: 145 }
    return "{ " + ", ".join(f"{k}: {v}" for k, v in d.items()) + " }"


def bloco_yaml(nome: str, entrada: dict) -> str:
    linhas = [f"  {nome}:"]
    for chave, valor in entrada.items():
        linhas.append(f"    {chave}: {_inline(valor) if isinstance(valor, dict) else valor}")
    return "\n".join(linhas) + "\n"


def preparar_arquivo(caminho: Path, titulo_janela: str = "") -> None:
    """Cria o arquivo de objetos se nao existir; garante 'objetos:' no fim."""
    if caminho.exists():
        conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
        chaves = list(conteudo)
        if chaves and chaves[-1] != "objetos":
            raise ValueError(
                f"{caminho}: a secao 'objetos:' precisa ser a ultima do arquivo "
                f"para o mapear acrescentar elementos no fim.")
        return
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        "# Gerado por 'vtae mapear'. Pode editar a mao.\n"
        "tela:\n"
        f"  titulo_janela: \"{titulo_janela}\"\n"
        "\n"
        "objetos:\n", encoding="utf-8")


def janela_no_ponto(janelas, x: int, y: int) -> str:
    """
    Titulo da janela mais ao topo que contem o ponto (x, y).

    'janelas' e a lista [(titulo, esquerda, topo, largura, altura)] na
    ordem do Windows — de cima para baixo — tirada ANTES de a tela cheia
    do mapear abrir. Usar a janela ativa falhou no primeiro uso real: ela
    era o app do Claude, nao o sistema (25/09).
    """
    for titulo, esq, topo, larg, alt in janelas:
        if titulo and esq <= x < esq + larg and topo <= y < topo + alt:
            return titulo
    return ""


def grande_demais(caixa, largura_tela: int, altura_tela: int) -> bool:
    x1, y1, x2, y2 = caixa
    return (x2 - x1) * (y2 - y1) > FRACAO_MAXIMA_DA_TELA * largura_tela * altura_tela


def definir_titulo_se_vazio(caminho: Path, titulo: str) -> bool:
    """Preenche titulo_janela so se estiver vazio. Nunca sobrescreve."""
    if not titulo or not caminho.exists():
        return False
    texto = caminho.read_text(encoding="utf-8")
    vazio = 'titulo_janela: ""'
    if vazio not in texto:
        return False
    caminho.write_text(texto.replace(vazio, f'titulo_janela: "{titulo}"', 1),
                       encoding="utf-8")
    return True


def nomes_existentes(caminho: Path) -> set:
    if not caminho.exists():
        return set()
    conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return set((conteudo.get("objetos") or {}).keys())


def anexar(caminho: Path, nome: str, entrada: dict) -> None:
    if nome in nomes_existentes(caminho):
        raise ValueError(f"'{nome}' ja existe em {caminho} — escolha outro nome.")
    with caminho.open("a", encoding="utf-8") as f:
        f.write(bloco_yaml(nome, entrada))


def contar_ocorrencias(tela, recorte, limiar: float = LIMIAR_AMBIGUIDADE) -> int:
    """
    Quantas vezes o recorte aparece no screenshot. 1 = template bom.
    >1 = ambiguo. Especificidade medida, nao suposta.
    """
    import cv2
    import numpy as np
    tela_cv = cv2.cvtColor(np.array(tela), cv2.COLOR_RGB2GRAY)
    rec_cv = cv2.cvtColor(np.array(recorte), cv2.COLOR_RGB2GRAY)
    resultado = cv2.matchTemplate(tela_cv, rec_cv, cv2.TM_CCOEFF_NORMED)
    mascara = (resultado >= limiar).astype(np.uint8)
    quantidade, _ = cv2.connectedComponents(mascara)
    return quantidade - 1


# ── interface (tkinter, vem com o Python) ────────────────────────────
def mapear(arquivo_objetos: str, pasta_templates: str | None = None) -> None:
    import tkinter as tk
    from tkinter import simpledialog, messagebox

    import pyautogui                     # torna o processo DPI-aware no Windows
    from PIL import ImageTk

    caminho = Path(arquivo_objetos)
    templates = Path(pasta_templates) if pasta_templates else (
        Path("templates") / caminho.parent.name / caminho.stem)

    print(f"[mapear] Deixe a tela do sistema na frente, maximizada. "
          f"Screenshot em {ESPERA_INICIAL}s...")
    time.sleep(ESPERA_INICIAL)
    # Mouse para longe: botao com o mouse em cima muda de cor, e o recorte
    # sairia diferente do botao 'normal' que o teste vai procurar (25/09).
    largura_tela, altura_tela = pyautogui.size()
    pyautogui.moveTo(largura_tela - 2, altura_tela // 2)
    time.sleep(0.3)
    janelas = []
    try:
        import pygetwindow as gw
        for j in gw.getAllWindows():
            if j.visible and not j.isMinimized and j.title.strip():
                janelas.append((j.title, j.left, j.top, j.width, j.height))
    except Exception:
        pass
    tela = pyautogui.screenshot()
    preparar_arquivo(caminho)

    raiz = tk.Tk()
    raiz.attributes("-fullscreen", True)
    raiz.attributes("-topmost", True)
    canvas = tk.Canvas(raiz, width=tela.width, height=tela.height,
                       highlightthickness=0, cursor="crosshair")
    canvas.pack()
    foto = ImageTk.PhotoImage(tela)
    canvas.create_image(0, 0, image=foto, anchor="nw")
    canvas.create_text(12, 12, anchor="nw", fill="red",
                       font=("Arial", 14, "bold"),
                       text="Arraste um retangulo em volta de um elemento. ESC termina.")

    estado = {"inicio": None, "ret": None, "mapeados": 0}

    def pressionar(evento):
        estado["inicio"] = (evento.x, evento.y)
        estado["ret"] = canvas.create_rectangle(evento.x, evento.y, evento.x,
                                                evento.y, outline="red", width=2)

    def arrastar(evento):
        if estado["ret"]:
            x0, y0 = estado["inicio"]
            canvas.coords(estado["ret"], x0, y0, evento.x, evento.y)

    def soltar(evento):
        x0, y0 = estado["inicio"]
        x1, y1 = evento.x, evento.y
        if abs(x1 - x0) < 4 or abs(y1 - y0) < 4:
            canvas.delete(estado["ret"])
            return
        nome = simpledialog.askstring("Elemento", "Nome do elemento (ex: btn_salvar):",
                                      parent=raiz)
        if not nome:
            canvas.delete(estado["ret"])
            return
        tipo = simpledialog.askstring(
            "Tipo", f"Tipo de '{nome}' — um de: {', '.join(TIPOS)}", parent=raiz)
        if tipo not in TIPOS:
            messagebox.showerror("Tipo invalido", f"Use um de: {TIPOS}", parent=raiz)
            canvas.delete(estado["ret"])
            return

        caixa = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        if grande_demais(caixa, tela.width, tela.height) and not messagebox.askyesno(
                "Retangulo muito grande",
                "Este retangulo cobre mais de um quarto da tela. Elementos sao "
                "pequenos: marque so o botao, so a caixa do campo.\n\n"
                "Gravar assim mesmo?", parent=raiz):
            canvas.delete(estado["ret"])
            return
        template = None
        if tipo in TIPOS_COM_TEMPLATE:
            recorte = tela.crop(caixa)
            templates.mkdir(parents=True, exist_ok=True)
            destino = templates / f"{nome}.png"
            recorte.save(destino)
            template = destino.as_posix()
            vezes = contar_ocorrencias(tela, recorte)
            if vezes != 1:
                messagebox.showwarning(
                    "Template ambiguo",
                    f"O recorte de '{nome}' aparece {vezes}x nesta tela. "
                    f"Recorte de novo, mais apertado, ou o clique pode ir para o "
                    f"lugar errado.", parent=raiz)
        try:
            anexar(caminho, nome, montar_entrada(tipo, *caixa, template=template))
        except ValueError as erro:
            messagebox.showerror("Nao gravado", str(erro), parent=raiz)
            canvas.delete(estado["ret"])
            return
        estado["mapeados"] += 1
        titulo = janela_no_ponto(janelas, (caixa[0] + caixa[2]) // 2,
                                 (caixa[1] + caixa[3]) // 2)
        if definir_titulo_se_vazio(caminho, titulo):
            print(f"[mapear] janela do sistema: '{titulo}'")
        canvas.itemconfig(estado["ret"], outline="green")
        canvas.create_text(caixa[0], caixa[1] - 4, anchor="sw", fill="green",
                           font=("Arial", 11, "bold"), text=f"{nome} ({tipo})")
        estado["ret"] = None

    canvas.bind("<ButtonPress-1>", pressionar)
    canvas.bind("<B1-Motion>", arrastar)
    canvas.bind("<ButtonRelease-1>", soltar)
    raiz.bind("<Escape>", lambda e: raiz.destroy())
    raiz.mainloop()
    print(f"[mapear] {estado['mapeados']} elemento(s) gravado(s) em {caminho}")
