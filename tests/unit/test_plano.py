"""
Unitarios do plano de flow — peca 4 do motor.

Formato do Projeto v1.1 §4 (linhas 63-76). Aqui, ao contrario das
pecas 2 e 3, o comportamento esperado e EXPLODIR: YAML de flow
malformado e defeito de escrita do teste, nao ambiente.
"""
import pytest

from vtae.core.exceptions import ConfigError
from vtae.core.motor.plano import Campo, Step, carregar, montar


def _cru(*steps):
    return {"flow": "cadastro_paciente_min",
            "objetos": "objects/si3/cadastro_min.yaml",
            "steps": list(steps) or [{"salvar": "f10"}]}


# ── cabecalho ────────────────────────────────────────────────────────
@pytest.mark.parametrize("chave", ["flow", "objetos", "steps"])
def test_cabecalho_ausente_explode(chave):
    cru = _cru()
    del cru[chave]
    with pytest.raises(ConfigError, match=chave):
        montar(cru)


def test_steps_vazio_explode():
    cru = _cru()
    cru["steps"] = []
    with pytest.raises(ConfigError, match="steps"):
        montar(cru)


# ── forma do step ────────────────────────────────────────────────────
def test_step_com_duas_chaves_explode():
    with pytest.raises(ConfigError, match="UMA chave"):
        montar(_cru({"salvar": "f10", "abrir_modulo": "X"}))


def test_step_que_nao_e_dicionario_explode():
    with pytest.raises(ConfigError, match="UMA chave"):
        montar(_cru("salvar"))


# ── verbos escalares do motor ────────────────────────────────────────
@pytest.mark.parametrize("verbo", ["salvar", "ler_resultado"])
def test_verbo_escalar_guarda_o_argumento(verbo):
    plano = montar(_cru({verbo: "ARG"}))
    assert plano.steps[0] == Step(1, verbo, "ARG")


@pytest.mark.parametrize("verbo", ["salvar", "ler_resultado"])
def test_verbo_escalar_sem_argumento_explode(verbo):
    with pytest.raises(ConfigError, match="exige um texto"):
        montar(_cru({verbo: None}))


# ── preencher ────────────────────────────────────────────────────────
def test_preencher_vira_campo():
    plano = montar(_cru({"preencher": {"campo": "nome",
                                       "valor": "{faker:nome}"}}))
    assert plano.steps[0].argumento == Campo("nome", "{faker:nome}")


def test_preencher_guarda_a_string_crua_sem_interpolar():
    # a interpolacao e do executor, que tem o config.DADOS
    plano = montar(_cru({"preencher": {"campo": "sexo",
                                       "valor": "{sorteio:sexo_opcoes}"}}))
    assert plano.steps[0].argumento.valor == "{sorteio:sexo_opcoes}"


@pytest.mark.parametrize("faltando", ["campo", "valor"])
def test_preencher_incompleto_explode(faltando):
    arg = {"campo": "nome", "valor": "X"}
    del arg[faltando]
    with pytest.raises(ConfigError, match=faltando):
        montar(_cru({"preencher": arg}))


def test_preencher_com_chave_estranha_explode():
    # 'elemento' era o nome do desenho abandonado — se sobrar num YAML,
    # explode nominalmente em vez de ser ignorado em silencio
    with pytest.raises(ConfigError, match="chave desconhecida"):
        montar(_cru({"preencher": {"campo": "nome", "valor": "X",
                                   "elemento": "nome"}}))


def test_preencher_escalar_explode():
    with pytest.raises(ConfigError, match="campo"):
        montar(_cru({"preencher": "nome"}))


# ── step nomeado ─────────────────────────────────────────────────────
def test_chave_desconhecida_vira_step_nomeado():
    plano = montar(_cru({"preencher_nacionalidade": "{sorteio:opcoes}"}))
    step = plano.steps[0]
    assert step.nomeado is True
    assert step.verbo == "preencher_nacionalidade"
    assert step.argumento == "{sorteio:opcoes}"


def test_abrir_modulo_e_step_nomeado():
    # SI3 e menu+popup, MSI3 seria URL — nada em comum medido (regra 50)
    plano = montar(_cru({"abrir_modulo": "CADASTRO DE PACIENTE"}))
    assert plano.steps[0].nomeado is True


def test_step_nomeado_sem_argumento_e_valido():
    plano = montar(_cru({"sair": None}))
    assert plano.steps[0].nomeado is True


# ── id e descricao ───────────────────────────────────────────────────
def test_id_vem_da_ordem():
    plano = montar(_cru({"salvar": "f10"}, {"ler_resultado": "matricula"}))
    assert [s.id for s in plano.steps] == ["S01", "S02"]


def test_descricao_de_preencher_cita_o_campo():
    plano = montar(_cru({"preencher": {"campo": "nome", "valor": "X"}}))
    assert plano.steps[0].descricao == "preencher nome"


# ── disco ────────────────────────────────────────────────────────────
def test_carregar_le_o_formato_do_v1_1(tmp_path):
    arquivo = tmp_path / "cadastro_min.yaml"
    arquivo.write_text(
        "flow: cadastro_paciente_min\n"
        "objetos: objects/si3/cadastro_min.yaml\n"
        "steps:\n"
        "  - abrir_modulo: CADASTRO DE PACIENTE\n"
        "  - preencher: { campo: nome, valor: \"{faker:nome}\" }\n"
        "  - preencher_nacionalidade: \"{sorteio:nacionalidade_opcoes}\"\n"
        "  - salvar: f10\n"
        "  - ler_resultado: matricula\n",
        encoding="utf-8",
    )
    plano = carregar(str(arquivo))
    assert plano.flow == "cadastro_paciente_min"
    assert [s.verbo for s in plano.steps] == [
        "abrir_modulo", "preencher", "preencher_nacionalidade",
        "salvar", "ler_resultado"]
    assert [s.nomeado for s in plano.steps] == [
        True, False, True, False, False]


def test_yaml_vazio_explode(tmp_path):
    arquivo = tmp_path / "vazio.yaml"
    arquivo.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        carregar(str(arquivo))


# ── steps_python ─────────────────────────────────────────────────────
def test_steps_python_e_lido_do_cabecalho():
    cru = _cru()
    cru["steps_python"] = "vtae.flows.si3.cadastro_min.steps"
    assert montar(cru).steps_python == "vtae.flows.si3.cadastro_min.steps"


def test_sem_steps_python_o_plano_fica_com_none():
    assert montar(_cru()).steps_python is None


# ── verificar ────────────────────────────────────────────────────────
def test_verificar_usa_o_mesmo_argumento_do_preencher():
    plano = montar(_cru({"verificar": {"campo": "nome", "valor": "MARIA"}}))
    assert plano.steps[0] == Step(1, "verificar", Campo("nome", "MARIA"))


def test_verificar_nao_e_step_nomeado():
    plano = montar(_cru({"verificar": {"campo": "nome", "valor": "MARIA"}}))
    assert plano.steps[0].nomeado is False


def test_verificar_sem_valor_explode():
    with pytest.raises(ConfigError, match="verificar"):
        montar(_cru({"verificar": {"campo": "nome"}}))