# scripts/testar_regiao_ocr.py
"""
Testa uma regiao OCR isolada — sem rodar a jornada inteira (~90s).

Uso:
    python scripts/testar_regiao_ocr.py <imagem.png> <x1> <y1> <x2> <y2>

Exemplo:
    python scripts/testar_regiao_ocr.py evidence/2026-06-11/test_admissao_ambulatorio_jornada/AB15_validacao.png 38 132 124 154

O que faz:
  1. Recorta a regiao (x1,y1,x2,y2) da imagem
  2. Salva o recorte CRU em _crop_raw.png (o que o OCR receberia hoje)
  3. Salva o recorte AMPLIADO 3x + cinza em _crop_proc.png (pre-processamento)
  4. Roda o EasyOCR nos dois e imprime o que leu

Assim voce ve em segundos se a regiao esta certa e se o upscale ajuda,
sem gastar um ciclo de jornada por tentativa.
"""

import sys
import cv2
import easyocr


def main():
    if len(sys.argv) != 6:
        print("Uso: python scripts/testar_regiao_ocr.py <imagem.png> <x1> <y1> <x2> <y2>")
        sys.exit(1)

    img_path = sys.argv[1]
    x1, y1, x2, y2 = (int(sys.argv[i]) for i in range(2, 6))

    altura = y2 - y1
    largura = x2 - x1
    print(f"[regiao] x1={x1} y1={y1} x2={x2} y2={y2}  ->  {largura}x{altura}px")
    if altura < 18:
        print(f"[AVISO] altura {altura}px e baixa para EasyOCR — mire >= 18px "
              f"(sobe y1 / desce y2)")

    img = cv2.imread(img_path)
    if img is None:
        print(f"[ERRO] nao consegui abrir a imagem: {img_path}")
        sys.exit(1)

    h, w = img.shape[:2]
    print(f"[imagem] {w}x{h}px")
    if x2 > w or y2 > h:
        print(f"[AVISO] regiao ultrapassa a imagem ({w}x{h}) — coordenadas erradas?")

    # 1) recorte cru
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        print("[ERRO] recorte vazio — verifique x1<x2 e y1<y2 e dentro da imagem")
        sys.exit(1)
    cv2.imwrite("_crop_raw.png", crop)

    # 2) recorte pre-processado: upscale 3x cubico + cinza (item Fase 2 do roadmap)
    proc = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    proc = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("_crop_proc.png", proc)

    print("[ocr] carregando EasyOCR (pode demorar na primeira vez)...")
    reader = easyocr.Reader(["pt"], gpu=False)

    raw = reader.readtext(crop, detail=0)
    pro = reader.readtext(proc, detail=0)

    print("\n================ RESULTADO ================")
    print(f"  CRU         -> {raw}")
    print(f"  PRE-PROCESS -> {pro}")
    print("===========================================")
    print("Recortes salvos: _crop_raw.png e _crop_proc.png — abra para conferir "
          "se o campo esta enquadrado.")


if __name__ == "__main__":
    main()