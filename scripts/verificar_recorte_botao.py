from PIL import Image
import numpy as np

origem = Image.open("plano_nao_contratado.png")
recorte_salvo = Image.open("templates/si3/common/btn_ok_popup.png")

print("Origem modo:", origem.mode, "| tamanho:", origem.size)
print("Recorte modo:", recorte_salvo.mode, "| tamanho:", recorte_salvo.size)

# Ajuste estas 4 coordenadas para o MESMO retangulo que voce usou ao recortar
recorte_fresco = origem.crop((285, 128, 335, 152))

arr_fresco = np.array(recorte_fresco)
arr_salvo = np.array(recorte_salvo)

print("Shape recorte fresco:", arr_fresco.shape)
print("Shape recorte salvo: ", arr_salvo.shape)
print("Sao identicos?", np.array_equal(arr_fresco, arr_salvo))