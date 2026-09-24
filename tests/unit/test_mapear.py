"""vtae mapear — so a logica pura; a janela tkinter se testa na mao."""
import pytest
import yaml
from PIL import Image, ImageDraw

from vtae.cli.mapear import (anexar, contar_ocorrencias, montar_entrada,
                             preparar_arquivo)
from vtae.core.object_repository import ObjectRepository


def test_botao_ganha_template_e_centro_sem_regiao():
    e = montar_entrada("botao", 110, 50, 10, 30, template="t/b.png")
    assert e == {"tipo": "botao", "coordenada": {"x": 60, "y": 40},
                 "template": "t/b.png"}


def test_campo_ganha_regiao_ocr_ordenada():
    e = montar_entrada("texto", 100, 40, 20, 20)
    assert e["regiao_ocr"] == {"x1": 20, "y1": 20, "x2": 100, "y2": 40}


def test_tipo_desconhecido_explode():
    with pytest.raises(ValueError):
        montar_entrada("combo", 0, 0, 1, 1)


def test_arquivo_gerado_e_lido_pelo_object_repository(tmp_path):
    arq = tmp_path / "objects/sis/login.yaml"
    preparar_arquivo(arq, "Meu Sistema - Login")
    anexar(arq, "usuario", montar_entrada("texto", 10, 10, 90, 30))
    anexar(arq, "btn_entrar", montar_entrada("botao", 0, 0, 20, 10, template="x.png"))
    dados = yaml.safe_load(arq.read_text(encoding="utf-8"))
    assert dados["tela"]["titulo_janela"] == "Meu Sistema - Login"
    repo = ObjectRepository.from_yaml(str(arq))
    assert repo.elemento("btn_entrar")["template"] == "x.png"
    assert "{ x1: 10, y1: 10, x2: 90, y2: 30 }" in arq.read_text(encoding="utf-8")


def test_nome_repetido_nao_sobrescreve(tmp_path):
    arq = tmp_path / "o.yaml"
    preparar_arquivo(arq)
    anexar(arq, "a", montar_entrada("texto", 0, 0, 5, 5))
    with pytest.raises(ValueError, match="ja existe"):
        anexar(arq, "a", montar_entrada("texto", 0, 0, 5, 5))


def test_ambiguidade_e_medida():
    tela = Image.new("RGB", (200, 100), "white")
    d = ImageDraw.Draw(tela)
    for x in (20, 120):                       # dois botoes iguais
        d.rectangle((x, 30, x + 40, 50), outline="black", fill="gray")
        d.text((x + 8, 35), "OK", fill="black")
    recorte = tela.crop((18, 28, 62, 52))
    assert contar_ocorrencias(tela, recorte) == 2
    unico = tela.crop((0, 0, 200, 100))
    assert contar_ocorrencias(tela, unico) == 1
