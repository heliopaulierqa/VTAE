"""
Unitarios da validacao antecipada — peca 4 do motor.

Usa o ObjectRepository e o plano.montar de verdade, com dicionarios em
memoria: fake antes de mock (regra 42), e aqui nem fake e preciso —
as duas pecas ja aceitam dado em memoria.
"""
import pytest

from vtae.core.exceptions import ConfigError
from vtae.core.motor.plano import montar
from vtae.core.motor.validacao import validar
from vtae.core.object_repository import ObjectRepository

DADOS = {"nome": "MARIA DA SILVA", "sexo_opcoes": ["MASCULINO", "FEMININO"]}
REGISTRO = {"abrir_modulo": lambda ctx, motor, arg: None}


def _objetos(**trocas):
    base = {
        "nome": {"tipo": "texto", "coordenada": {"x": 1, "y": 2}},
        "sexo": {"tipo": "lov", "btn_ok": "btn_ok_lov"},
        "cor_etnia": {"tipo": "lov_lista",
                      "campo_localizar": "campo_localizar_lov",
                      "btn_ok": "btn_ok_lov",
                      "titulo_janela": "Grupo etnico"},
        "btn_ok_lov": {"tipo": "botao", "coordenada": {"x": 3, "y": 4}},
        "campo_localizar_lov": {"tipo": "texto", "coordenada": {"x": 5, "y": 6}},
        "matricula": {"tipo": "resultado"},
    }
    base.update(trocas)
    return ObjectRepository(base)


def _plano(*steps):
    return montar({"flow": "cadastro_paciente_min",
                   "objetos": "objects/si3/cadastro_min.yaml",
                   "steps": list(steps)})


def _validar(*steps, objetos=None, registro=REGISTRO, dados=DADOS):
    validar(_plano(*steps), objetos or _objetos(), registro, dados)


# ── plano bom ────────────────────────────────────────────────────────
def test_plano_completo_e_valido():
    _validar(
        {"abrir_modulo": "CADASTRO DE PACIENTE"},
        {"preencher": {"campo": "nome", "valor": "{faker:nome}"}},
        {"preencher": {"campo": "sexo", "valor": "{sorteio:sexo_opcoes}"}},
        {"preencher": {"campo": "cor_etnia", "valor": "BRANCA"}},
        {"salvar": "f10"},
        {"ler_resultado": "matricula"},
    )


# ── preencher ────────────────────────────────────────────────────────
def test_campo_nao_declarado_explode():
    with pytest.raises(ConfigError, match="nao declarado"):
        _validar({"preencher": {"campo": "fantasma", "valor": "X"}})


def test_campo_botao_nao_se_preenche():
    with pytest.raises(ConfigError, match="nao se preenche"):
        _validar({"preencher": {"campo": "btn_ok_lov", "valor": "X"}})


def test_campo_resultado_nao_se_preenche():
    with pytest.raises(ConfigError, match="nao se preenche"):
        _validar({"preencher": {"campo": "matricula", "valor": "X"}})


def test_lov_sem_btn_ok_explode():
    objetos = _objetos(sexo={"tipo": "lov"})
    with pytest.raises(ConfigError, match="exige a chave 'btn_ok'"):
        _validar({"preencher": {"campo": "sexo", "valor": "MASCULINO"}},
                 objetos=objetos)


def test_lov_lista_sem_campo_localizar_explode():
    objetos = _objetos(cor_etnia={"tipo": "lov_lista", "btn_ok": "btn_ok_lov",
                                  "titulo_janela": "Grupo etnico"})
    with pytest.raises(ConfigError, match="campo_localizar"):
        _validar({"preencher": {"campo": "cor_etnia", "valor": "BRANCA"}},
                 objetos=objetos)


def test_btn_ok_apontando_para_elemento_inexistente_explode():
    objetos = _objetos(sexo={"tipo": "lov", "btn_ok": "botao_fantasma"})
    with pytest.raises(ConfigError, match="nao existe em objects/"):
        _validar({"preencher": {"campo": "sexo", "valor": "MASCULINO"}},
                 objetos=objetos)


def test_titulo_janela_nao_precisa_ser_elemento():
    _validar({"preencher": {"campo": "cor_etnia", "valor": "BRANCA"}})


# ── step nomeado ─────────────────────────────────────────────────────
def test_step_nomeado_sem_registro_explode():
    with pytest.raises(ConfigError, match="sem funcao registrada"):
        _validar({"preencher_nacionalidade": "BRASILEIRO"})


def test_step_nomeado_registrado_passa():
    _validar({"abrir_modulo": "CADASTRO DE PACIENTE"})


# ── salvar e ler_resultado ───────────────────────────────────────────
def test_mecanica_de_salvar_desconhecida_explode():
    with pytest.raises(ConfigError, match="desconhecida"):
        _validar({"salvar": "ctrl+s"})


def test_ler_resultado_de_elemento_inexistente_explode():
    with pytest.raises(ConfigError, match="nao declarado"):
        _validar({"ler_resultado": "fantasma"})


def test_ler_resultado_de_tipo_errado_explode():
    with pytest.raises(ConfigError, match="exige tipo 'resultado'"):
        _validar({"ler_resultado": "nome"})


# ── interpolacao ─────────────────────────────────────────────────────
def test_interpolacao_com_chave_ausente_explode():
    with pytest.raises(ConfigError, match="ausente"):
        _validar({"preencher": {"campo": "nome", "valor": "{faker:sumiu}"}})


def test_interpolacao_no_argumento_de_step_nomeado_tambem_e_checada():
    with pytest.raises(ConfigError, match="ausente"):
        _validar({"abrir_modulo": "{sorteio:sumiu}"})


# ── mensagem ─────────────────────────────────────────────────────────
def test_problemas_sao_acumulados_numa_mensagem_so():
    with pytest.raises(ConfigError) as erro:
        _validar({"preencher": {"campo": "fantasma", "valor": "X"}},
                 {"salvar": "ctrl+s"})
    assert "fantasma" in str(erro.value)
    assert "ctrl+s" in str(erro.value)


def test_mensagem_cita_o_id_do_step():
    with pytest.raises(ConfigError, match="S02"):
        _validar({"salvar": "f10"},
                 {"preencher": {"campo": "fantasma", "valor": "X"}})


# ── verificar ────────────────────────────────────────────────────────
def test_verificar_campo_declarado_passa():
    _validar({"verificar": {"campo": "nome", "valor": "{faker:nome}"}})


def test_verificar_nao_exige_mecanica_de_lov():
    """Verificar so le — nao precisa de btn_ok nem campo_localizar."""
    objetos = _objetos(sexo={"tipo": "lov"})
    _validar({"verificar": {"campo": "sexo", "valor": "MASCULINO"}},
             objetos=objetos)


def test_verificar_campo_inexistente_explode():
    with pytest.raises(ConfigError, match="nao declarado"):
        _validar({"verificar": {"campo": "fantasma", "valor": "X"}})


def test_verificar_botao_explode():
    with pytest.raises(ConfigError, match="nao tem valor a verificar"):
        _validar({"verificar": {"campo": "btn_ok_lov", "valor": "X"}})


def test_verificar_resultado_e_permitido():
    _validar({"verificar": {"campo": "matricula", "valor": "123456"}})
        