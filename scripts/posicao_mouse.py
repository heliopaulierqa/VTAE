"""
scripts/posicao_mouse.py

Captura até 4 coordenadas do mouse usando contagem regressiva.
Uso: python scripts/posicao_mouse.py

Instruções:
  - Execute o script
  - Posicione o mouse no ponto desejado durante a contagem regressiva
  - A coordenada é capturada automaticamente ao final de cada contagem
"""

import pyautogui
import time


PONTOS = 4        # quantos pontos capturar
SEGUNDOS = 5      # segundos para posicionar o mouse em cada ponto


def capturar_ponto(numero: int) -> tuple:
    print(f"\n  [{numero}/{PONTOS}] Posicione o mouse no ponto {numero}...")
    for i in range(SEGUNDOS, 0, -1):
        x, y = pyautogui.position()
        print(f"         {i}s — posicao atual: x={x}, y={y}    ", end="\r")
        time.sleep(1)
    x, y = pyautogui.position()
    print(f"         OK Capturado: x={x}, y={y}                ")
    return x, y


def main():
    print("=" * 50)
    print("  VTAE — Captura de Coordenadas do Mouse")
    print("=" * 50)
    print(f"  Serao capturados {PONTOS} pontos.")
    print(f"  Voce tem {SEGUNDOS} segundos para posicionar o mouse.")
    print("=" * 50)

    time.sleep(2)  # pausa inicial para sair do terminal

    coordenadas = []
    for i in range(1, PONTOS + 1):
        coord = capturar_ponto(i)
        coordenadas.append(coord)
        if i < PONTOS:
            print(f"  Proximo ponto em 3 segundos...")
            time.sleep(3)

    print("\n" + "=" * 50)
    print("  Coordenadas capturadas:")
    print("=" * 50)
    for i, (x, y) in enumerate(coordenadas, 1):
        print(f"  Ponto {i}: x={x}, y={y}")
    print("=" * 50)


if __name__ == "__main__":
    main()