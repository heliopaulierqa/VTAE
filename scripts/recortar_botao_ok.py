from PIL import Image

img = Image.open("plano_nao_contratado.png")  # ajuste para o nome do arquivo que voce abriu no Paint
botao = img.crop((182, 120, 235, 146))          # troque pelos 4 numeros que voce anotou
botao.save("templates/si3/common/btn_ok_popup.png")
print("Recorte salvo:", botao.size)