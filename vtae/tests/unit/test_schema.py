"""
Testes unitários do Schema — src/config/schema.py

Testa transformações do Faker, validações das dataclasses,
geração de dados e cache do SystemConfig.
"""

import pytest
from unittest.mock import patch
from dataclasses import FrozenInstanceError

from src.config.schema import (
    SystemConfig,
    AmbienteConfig,
    CredenciaisConfig,
    DadoFakerConfig,
    TransformacaoTipo,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

def make_ambiente(url="http://127.0.0.1:5000", confidence=0.8) -> AmbienteConfig:
    return AmbienteConfig(url=url, confidence=confidence)

def make_credenciais(usuario="admin", senha="admin123") -> CredenciaisConfig:
    return CredenciaisConfig(usuario=usuario, senha=senha)

def make_config(dados_schema=None) -> SystemConfig:
    return SystemConfig(
        sistema="sislab",
        tipo="desktop",
        runner="opencv",
        ambiente_ativo="dev",
        ambiente=make_ambiente(),
        credenciais=make_credenciais(),
        dados_schema=dados_schema or [],
    )


# ──────────────────────────────────────────────────────────────────────────────
# AmbienteConfig
# ──────────────────────────────────────────────────────────────────────────────

class TestAmbienteConfig:

    def test_cria_com_valores_minimos(self):
        amb = AmbienteConfig(url="http://127.0.0.1:5000")
        assert amb.url == "http://127.0.0.1:5000"
        assert amb.confidence == 0.8   # default
        assert amb.headless   is False  # default

    def test_lanca_erro_url_vazia(self):
        with pytest.raises(ValueError) as exc_info:
            AmbienteConfig(url="")
        assert "url" in str(exc_info.value).lower()

    def test_lanca_erro_confidence_zero(self):
        with pytest.raises(ValueError):
            AmbienteConfig(url="http://x.com", confidence=0.0)

    def test_lanca_erro_confidence_maior_que_1(self):
        with pytest.raises(ValueError):
            AmbienteConfig(url="http://x.com", confidence=1.1)

    def test_confidence_limite_inferior_valido(self):
        """0.01 é válido (acima de 0.0)."""
        amb = AmbienteConfig(url="http://x.com", confidence=0.01)
        assert amb.confidence == 0.01

    def test_confidence_limite_superior_valido(self):
        """1.0 é válido."""
        amb = AmbienteConfig(url="http://x.com", confidence=1.0)
        assert amb.confidence == 1.0


# ──────────────────────────────────────────────────────────────────────────────
# CredenciaisConfig
# ──────────────────────────────────────────────────────────────────────────────

class TestCredenciaisConfig:

    def test_cria_com_valores_validos(self):
        cred = CredenciaisConfig(usuario="admin", senha="admin123")
        assert cred.usuario == "admin"
        assert cred.senha   == "admin123"

    def test_lanca_erro_usuario_vazio(self):
        with pytest.raises(ValueError) as exc_info:
            CredenciaisConfig(usuario="", senha="admin123")
        assert "usuario" in str(exc_info.value).lower()

    def test_lanca_erro_senha_vazia(self):
        with pytest.raises(ValueError) as exc_info:
            CredenciaisConfig(usuario="admin", senha="")
        assert "senha" in str(exc_info.value).lower()


# ──────────────────────────────────────────────────────────────────────────────
# DadoFakerConfig
# ──────────────────────────────────────────────────────────────────────────────

class TestDadoFakerConfig:

    def test_tipo_faker_requer_metodo(self):
        with pytest.raises(ValueError) as exc_info:
            DadoFakerConfig(campo="nome", tipo="faker")
        assert "metodo" in str(exc_info.value).lower()

    def test_tipo_fixo_requer_valor(self):
        with pytest.raises(ValueError) as exc_info:
            DadoFakerConfig(campo="cargo", tipo="fixo")
        assert "valor" in str(exc_info.value).lower()

    def test_tipo_random_requer_opcoes(self):
        with pytest.raises(ValueError) as exc_info:
            DadoFakerConfig(campo="sexo", tipo="random")
        assert "opcoes" in str(exc_info.value).lower()

    def test_tipo_faker_valido(self):
        cfg = DadoFakerConfig(campo="nome", tipo="faker", metodo="name")
        assert cfg.metodo == "name"

    def test_tipo_fixo_valido(self):
        cfg = DadoFakerConfig(campo="cargo", tipo="fixo", valor="ANALISTA")
        assert cfg.valor == "ANALISTA"

    def test_tipo_random_valido(self):
        cfg = DadoFakerConfig(campo="sexo", tipo="random",
                              opcoes=["M", "F"])
        assert "M" in cfg.opcoes
        assert "F" in cfg.opcoes


# ──────────────────────────────────────────────────────────────────────────────
# Transformações
# ──────────────────────────────────────────────────────────────────────────────

class TestTransformacoes:

    def _aplicar(self, valor: str, transformacao: str) -> str:
        return SystemConfig._aplicar_transformacao(valor, transformacao)

    def test_none_retorna_original(self):
        assert self._aplicar("João Silva", None) == "João Silva"

    def test_upper(self):
        assert self._aplicar("joão silva", "upper") == "JOÃO SILVA"

    def test_lower(self):
        assert self._aplicar("JOÃO SILVA", "lower") == "joão silva"

    def test_truncar_50(self):
        valor = "A" * 60
        resultado = self._aplicar(valor, "truncar_50")
        assert len(resultado) == 50

    def test_truncar_50_valor_curto(self):
        """Valor menor que 50 não deve ser alterado."""
        assert self._aplicar("curto", "truncar_50") == "curto"

    def test_sem_pontuacao_cpf(self):
        assert self._aplicar("123.456.789-00", "sem_pontuacao") == "12345678900"

    def test_sem_pontuacao_cnpj(self):
        assert self._aplicar("12.345.678/0001-90", "sem_pontuacao") == "12345678000190"

    def test_sem_pontuacao_sem_pontos(self):
        """Valor sem pontuação deve ser retornado igual."""
        assert self._aplicar("12345678900", "sem_pontuacao") == "12345678900"

    def test_sem_prefixo_sr(self):
        assert self._aplicar("Sr. João Silva", "sem_prefixo") == "João Silva"

    def test_sem_prefixo_sra(self):
        assert self._aplicar("Sra. Maria Costa", "sem_prefixo") == "Maria Costa"

    def test_sem_prefixo_dr(self):
        assert self._aplicar("Dr. Carlos Mendes", "sem_prefixo") == "Carlos Mendes"

    def test_sem_prefixo_dra(self):
        assert self._aplicar("Dra. Ana Lima", "sem_prefixo") == "Ana Lima"

    def test_sem_prefixo_prof(self):
        assert self._aplicar("Prof. Pedro Souza", "sem_prefixo") == "Pedro Souza"

    def test_sem_prefixo_sem_prefixo(self):
        """Nome sem prefixo não deve ser alterado."""
        assert self._aplicar("João Silva", "sem_prefixo") == "João Silva"

    def test_sem_prefixo_upper_remove_e_maiuscula(self):
        """sem_prefixo_upper deve remover prefixo E converter para maiúsculas."""
        resultado = self._aplicar("Sr. João Silva", "sem_prefixo_upper")
        assert resultado == "JOÃO SILVA"

    def test_sem_prefixo_upper_dra(self):
        resultado = self._aplicar("Dra. Ana Lima", "sem_prefixo_upper")
        assert resultado == "ANA LIMA"

    def test_sem_prefixo_upper_sem_prefixo(self):
        """Nome sem prefixo deve só virar maiúsculas."""
        resultado = self._aplicar("João Silva", "sem_prefixo_upper")
        assert resultado == "JOÃO SILVA"

    def test_sem_prefixo_upper_ja_maiusculo(self):
        """Já em maiúsculas sem prefixo — deve manter."""
        resultado = self._aplicar("JOÃO SILVA", "sem_prefixo_upper")
        assert resultado == "JOÃO SILVA"

    def test_transformacao_desconhecida_retorna_original(self):
        """Transformação não reconhecida deve retornar o valor original."""
        resultado = SystemConfig._aplicar_transformacao("teste", "transformacao_inexistente")
        assert resultado == "teste"


# ──────────────────────────────────────────────────────────────────────────────
# Geração de dados — SystemConfig.DADOS
# ──────────────────────────────────────────────────────────────────────────────

class TestGeracaoDados:

    def test_campo_fixo(self):
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="cargo", tipo="fixo", valor="ANALISTA DE RH")
        ])
        assert cfg.DADOS["cargo"] == "ANALISTA DE RH"

    def test_campo_faker_name(self):
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="nome", tipo="faker", metodo="name")
        ])
        nome = cfg.DADOS["nome"]
        assert isinstance(nome, str)
        assert len(nome) > 0

    def test_campo_faker_com_transformacao_upper(self):
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="nome", tipo="faker", metodo="name",
                            transformacao="upper")
        ])
        nome = cfg.DADOS["nome"]
        assert nome == nome.upper()

    def test_campo_faker_cpf_sem_pontuacao(self):
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="cpf", tipo="faker", metodo="cpf",
                            transformacao="sem_pontuacao")
        ])
        cpf = cfg.DADOS["cpf"]
        assert "." not in cpf
        assert "-" not in cpf
        assert len(cpf) == 11

    def test_campo_random(self):
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="sexo", tipo="random", opcoes=["M", "F"])
        ])
        sexo = cfg.DADOS["sexo"]
        assert sexo in ["M", "F"]

    def test_campo_faker_sem_prefixo_upper(self):
        """Nome gerado pelo Faker com sem_prefixo_upper não deve ter prefixo."""
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="nome", tipo="faker", metodo="name",
                            transformacao="sem_prefixo_upper")
        ])
        nome = cfg.DADOS["nome"]
        assert nome == nome.upper()
        # não deve começar com prefixos conhecidos
        prefixos = ("DR.", "DRA.", "SR.", "SRA.", "PROF.")
        assert not any(nome.startswith(p) for p in prefixos)

    def test_multiplos_campos(self):
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="nome",  tipo="faker", metodo="name"),
            DadoFakerConfig(campo="cargo", tipo="fixo",  valor="ANALISTA"),
            DadoFakerConfig(campo="cpf",   tipo="faker", metodo="cpf",
                            transformacao="sem_pontuacao"),
        ])
        dados = cfg.DADOS
        assert "nome"  in dados
        assert "cargo" in dados
        assert "cpf"   in dados

    def test_dados_cache_retorna_mesmo_objeto(self):
        """Segunda chamada a DADOS deve retornar exatamente os mesmos valores."""
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="nome", tipo="faker", metodo="name")
        ])
        dados1 = cfg.DADOS
        dados2 = cfg.DADOS
        assert dados1["nome"] == dados2["nome"]

    def test_resetar_dados_limpa_cache(self):
        """Após resetar_dados, DADOS deve ser um novo objeto."""
        cfg = make_config(dados_schema=[
            DadoFakerConfig(campo="cargo", tipo="fixo", valor="ANALISTA")
        ])
        dados1 = cfg.DADOS
        cfg.resetar_dados()
        dados2 = cfg.DADOS
        # campo fixo deve ser igual — confirma que o reset funcionou
        assert dados1["cargo"] == dados2["cargo"]
        # são objetos diferentes (novo dict foi criado)
        assert dados1 is not dados2

    def test_dados_vazio_quando_sem_schema(self):
        """SystemConfig sem dados_schema deve retornar dict vazio."""
        cfg = make_config(dados_schema=[])
        assert cfg.DADOS == {}


# ──────────────────────────────────────────────────────────────────────────────
# Propriedades do SystemConfig
# ──────────────────────────────────────────────────────────────────────────────

class TestSystemConfigPropriedades:

    def test_user_property(self):
        cfg = make_config()
        assert cfg.USER == "admin"

    def test_password_property(self):
        cfg = make_config()
        assert cfg.PASSWORD == "admin123"

    def test_url_property(self):
        cfg = make_config()
        assert cfg.url == "http://127.0.0.1:5000"

    def test_confidence_property(self):
        cfg = make_config()
        assert cfg.confidence == 0.8

    def test_headless_property(self):
        cfg = make_config()
        assert cfg.headless is False

    def test_timeout_property(self):
        cfg = make_config()
        assert cfg.timeout == 30.0
