import time
import pyautogui

print("Mova o mouse para o campo USUARIO e aguarde 4 segundos...")
time.sleep(4)
print(f"USUARIO: {pyautogui.position()}")

print("\nMova o mouse para o campo SENHA e aguarde 4 segundos...")
time.sleep(4)
print(f"SENHA: {pyautogui.position()}")

print("\nMova o mouse para o botão ENTRAR e aguarde 4 segundos...")
time.sleep(4)
print(f"ENTRAR: {pyautogui.position()}")