# tests/unit/test_verificacao.py
"""
Unitarios da peca 3 do motor (Projeto v1.1, Fase 2).

Fakes em vez de MagicMock: o fake devolve o que foi programado e registra
a FORMA da chamada. Mock devolveria truthy para qualquer coisa e o teste
passaria sem provar nada (regra 42).
"""
from vtae.core.motor.verificacao import (
    DIVERGENTE,
    NAO_VERIFICAVEL,
    OK,
    VAZIO,
    Verificador,
)


class FakeObjects:
    def __init__(self, objetos, camada_exata="nenhuma"):
        self._objetos = objetos
        self._camada = camada_exata

    def elemento(self, nome):
        objeto = self._objetos.get(nome)
        return dict(objeto) if objeto is not None else None

    def camada_exata(self):
        return self._camada

    def regiao_ocr(self, nome):
        objeto = self._objetos.get(nome) or {}
        regiao = objeto.get("regiao_ocr")
        return tuple(regiao) if regiao else None


class FakeRunner:
    def __init__(self, texto="", ok=True):
        self._texto = texto
        self._ok = ok
        self.chamadas = []

    def verify_lov(self, nome, region=None, timeout=None):
        self.chamadas.append({"nome": nome, "region": region,
                              "timeout": timeout})
        return self._ok, self._texto


class FakeLeitor:
    def __init__(self, valores):
        self._valores = valores
        self.pedidos = []

    def ler(self, locator):
        self.pedidos.append(locator)
        return self._valores.get(locator)


REGIAO = (10, 20, 30, 40)


class TestNaoVerificavel:
    def test_elemento_nao_declarado(self):
        v = Verificador(FakeObjects({}), FakeRunner()).verificar("fantasma", "X")
        assert v.status == NAO_VERIFICAVEL
        assert "nao declarado" in v.motivo

    def test_tipo_botao_nao_tem_valor(self):
        objects = FakeObjects({"btn_ok": {"tipo": "botao"}})
        v = Verificador(objects, FakeRunner()).verificar("btn_ok")
        assert v.status == NAO_VERIFICAVEL

    def test_lov_sem_jab_name_com_camada_declarada_e_erro_de_config(self):
        """Regra 54: campo declarado nao e pulado em silencio."""
        objects = FakeObjects(
            {"sexo": {"tipo": "lov", "regiao_ocr": REGIAO}},
            camada_exata="pyjab")
        v = Verificador(objects, FakeRunner("FEMININO")).verificar(
            "sexo", "FEMININO")
        assert v.status == NAO_VERIFICAVEL
        assert "calibrar" in v.motivo

    def test_sem_regiao_e_sem_camada_exata(self):
        objects = FakeObjects({"nome": {"tipo": "texto"}})
        v = Verificador(objects, FakeRunner()).verificar("nome", "MARIA")
        assert v.status == NAO_VERIFICAVEL


class TestCamadaExata:
    def _montar(self, lido_jab, texto_ocr="", esperado="FEMININO"):
        objects = FakeObjects(
            {"sexo": {"tipo": "lov", "jab_name": "Descricao do Sexo.",
                      "regiao_ocr": REGIAO}},
            camada_exata="pyjab")
        leitor = FakeLeitor({"Descricao do Sexo.": lido_jab})
        runner = FakeRunner(texto_ocr)
        verificador = Verificador(objects, runner, leitor_exato=leitor)
        return verificador.verificar("sexo", esperado), leitor, runner

    def test_valor_correto(self):
        v, _, _ = self._montar("FEMININO", "FEMININO")
        assert v.status == OK
        assert v.camada_decisora == "exata"
        assert v.divergencia is False

    def test_valor_errado(self):
        v, _, _ = self._montar("MASCULINO", "MASCULINO")
        assert v.status == DIVERGENTE
        assert v.lido_exato == "MASCULINO"

    def test_campo_vazio(self):
        v, _, _ = self._montar("", "")
        assert v.status == VAZIO

    def test_divergencia_entre_camadas_passa_mas_registra(self):
        """Decisao: divergencia e aviso, nao falha — mas para de sumir."""
        v, _, _ = self._montar("FEMININO", "MASCULINO")
        assert v.status == OK
        assert v.divergencia is True
        assert "divergencia" in v.motivo

    def test_pede_ao_leitor_o_jab_name_do_yaml(self):
        _, leitor, _ = self._montar("FEMININO")
        assert leitor.pedidos == ["Descricao do Sexo."]


class TestOcrDecide:
    def test_lov_com_match_parcial_reprova(self):
        """Caso ALLIANZ: containment desligado quando OCR decide LOV."""
        objects = FakeObjects(
            {"provedor": {"tipo": "lov", "regiao_ocr": REGIAO}})
        v = Verificador(objects, FakeRunner("ALLIANZ SAUDE")).verificar(
            "provedor", "ALLIANZ")
        assert v.status == DIVERGENTE
        assert v.camada_decisora == "ocr"

    def test_texto_livre_aceita_containment(self):
        objects = FakeObjects({"obs": {"tipo": "texto", "regiao_ocr": REGIAO}})
        v = Verificador(objects, FakeRunner("OBSERVACAO GERAL DO PACIENTE")
                        ).verificar("obs", "OBSERVACAO GERAL")
        assert v.status == OK

    def test_texto_sem_jab_name_nao_e_bloqueado(self):
        """O erro corrigido no diff E: texto livre nao exige camada exata."""
        objects = FakeObjects(
            {"nome": {"tipo": "texto", "regiao_ocr": REGIAO}},
            camada_exata="pyjab")
        v = Verificador(objects, FakeRunner("MARIA")).verificar("nome", "MARIA")
        assert v.status == OK
        assert v.degradado is False

    def test_ruido_de_ocr_tolerado(self):
        objects = FakeObjects({"nome": {"tipo": "texto", "regiao_ocr": REGIAO}})
        v = Verificador(objects, FakeRunner("3RUNA")).verificar("nome", "BRUNA")
        assert v.status == OK

    def test_leitor_ausente_degrada_mas_nao_mata(self):
        objects = FakeObjects(
            {"sexo": {"tipo": "lov", "jab_name": "Descricao do Sexo.",
                      "regiao_ocr": REGIAO}},
            camada_exata="pyjab")
        v = Verificador(objects, FakeRunner("FEMININO")).verificar(
            "sexo", "FEMININO")
        assert v.status == OK
        assert v.degradado is True
        assert v.camada_decisora == "ocr"

    def test_forma_da_chamada_ao_runner(self):
        objects = FakeObjects({"nome": {"tipo": "texto", "regiao_ocr": REGIAO}})
        runner = FakeRunner("MARIA")
        Verificador(objects, runner).verificar("nome", "MARIA")
        assert runner.chamadas == [
            {"nome": "nome", "region": REGIAO, "timeout": 3.0}]

    def test_ocr_nao_leu_nada(self):
        objects = FakeObjects({"nome": {"tipo": "texto", "regiao_ocr": REGIAO}})
        v = Verificador(objects, FakeRunner("", ok=False)).verificar(
            "nome", "MARIA")
        assert v.status == VAZIO


class TestMascara:
    def _verificar(self, texto_ocr):
        objects = FakeObjects(
            {"data_nascimento": {"tipo": "data", "regiao_ocr": REGIAO}})
        return Verificador(objects, FakeRunner(texto_ocr)).verificar(
            "data_nascimento", "01011990")

    def test_data_completa_passa(self):
        assert self._verificar("01/01/1990").status == OK

    def test_formato_trocado_tambem_passa(self):
        """Contagem de digitos e imune a AAAA/DD/MM."""
        assert self._verificar("1990/01/01").status == OK

    def test_digitos_de_menos_reprova(self):
        assert self._verificar("01/01").status == DIVERGENTE


class TestResultado:
    def test_valor_gerado_sem_esperado(self):
        objects = FakeObjects(
            {"matricula": {"tipo": "resultado", "regiao_ocr": REGIAO}})
        v = Verificador(objects, FakeRunner("123456")).verificar("matricula")
        assert v.status == OK
        assert "123456" in v.motivo

    def test_valor_gerado_vazio(self):
        objects = FakeObjects(
            {"matricula": {"tipo": "resultado", "regiao_ocr": REGIAO}})
        v = Verificador(objects, FakeRunner("")).verificar("matricula")
        assert v.status == VAZIO