"""
Testes unitários do ConfigLoader — src/config/loader.py

Testa carregamento de YAML, resolução de variáveis de ambiente,
múltiplos ambientes, defaults e erros de validação.
Sem acesso ao disco real — usa tmp_path do pytest.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from src.config.loader import ConfigLoader
from src.config.schema import SystemConfig
from src.core.types import ConfigError


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

YAML_MINIMO = """
sistema: sislab
tipo: desktop
runner: opencv

ambientes:
  dev:
    url: http://127.0.0.1:5000
    confidence: 0.8

credenciais:
  usuario: admin
  senha: admin123

flows:
  - login
  - cadastro_funcionario
"""

YAML_COMPLETO = """
sistema: sislab
tipo: desktop
runner: opencv

ambientes:
  dev:
    url: http://127.0.0.1:5000
    confidence: 0.8
    headless: false
    timeout: 30.0
  homologacao:
    url: http://sislab.hom.interno
    confidence: 0.85
    headless: true
    timeout: 60.0
  producao:
    url: http://sislab.prod.interno
    confidence: 0.9
    headless: true
    timeout: 60.0

credenciais:
  usuario: ${SISLAB_USER:-admin}
  senha: ${SISLAB_PASS:-admin123}

flows:
  - login
  - cadastro_funcionario

dados_faker:
  - campo: nome
    tipo: faker
    metodo: name
    transformacao: sem_prefixo_upper
    locale: pt_BR

  - campo: cargo
    tipo: fixo
    valor: "ANALISTA DE RH"

  - campo: cpf
    tipo: faker
    metodo: cpf
    transformacao: sem_pontuacao
"""

YAML_COM_ENV_VARS = """
sistema: msi3
tipo: web
runner: playwright

ambientes:
  dev:
    url: http://msi3.dev.interno
    confidence: 0.7

credenciais:
  usuario: ${MSI3_USER}
  senha: ${MSI3_PASS}
"""

YAML_SEM_AMBIENTES = """
sistema: sislab
tipo: desktop
runner: opencv

credenciais:
  usuario: admin
  senha: admin123
"""

YAML_SEM_CREDENCIAIS = """
sistema: sislab
tipo: desktop
runner: opencv

ambientes:
  dev:
    url: http://127.0.0.1:5000
"""


def criar_config(tmp_path: Path, sistema: str, conteudo: str,
                 env_content: str = None) -> Path:
    """Cria estrutura de config temporária para testes."""
    configs_dir = tmp_path / "configs"
    sistema_dir = configs_dir / sistema
    sistema_dir.mkdir(parents=True)

    (sistema_dir / "config.yaml").write_text(conteudo, encoding="utf-8")

    if env_content:
        (sistema_dir / ".env").write_text(env_content, encoding="utf-8")

    return configs_dir


# ──────────────────────────────────────────────────────────────────────────────
# Carregamento básico
# ──────────────────────────────────────────────────────────────────────────────

class TestCarregamentoBasico:

    def test_carrega_yaml_minimo(self, tmp_path):
        """YAML mínimo deve carregar sem erros."""
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert isinstance(config, SystemConfig)
        assert config.sistema == "sislab"

    def test_retorna_system_config(self, tmp_path):
        """carregar() deve retornar SystemConfig."""
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert isinstance(config, SystemConfig)

    def test_sistema_correto(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.sistema == "sislab"

    def test_tipo_correto(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.tipo == "desktop"

    def test_runner_correto(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.runner == "opencv"

    def test_url_do_ambiente_dev(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.url == "http://127.0.0.1:5000"

    def test_flows_carregados(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert "login" in config.flows
        assert "cadastro_funcionario" in config.flows

    def test_credenciais_literais(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.USER == "admin"
        assert config.PASSWORD == "admin123"


# ──────────────────────────────────────────────────────────────────────────────
# Múltiplos ambientes
# ──────────────────────────────────────────────────────────────────────────────

class TestAmbientes:

    def test_ambiente_dev_padrao(self, tmp_path):
        """Sem especificar ambiente, deve usar dev."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.ambiente_ativo == "dev"
        assert config.url == "http://127.0.0.1:5000"

    def test_ambiente_homologacao(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)
        config = ConfigLoader.carregar("sislab", ambiente="homologacao",
                                       configs_dir=configs)
        assert config.ambiente_ativo == "homologacao"
        assert config.url == "http://sislab.hom.interno"

    def test_ambiente_producao(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)
        config = ConfigLoader.carregar("sislab", ambiente="producao",
                                       configs_dir=configs)
        assert config.ambiente_ativo == "producao"
        assert config.url == "http://sislab.prod.interno"

    def test_confidence_por_ambiente(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        dev  = ConfigLoader.carregar("sislab", ambiente="dev",
                                     configs_dir=configs)
        hom  = ConfigLoader.carregar("sislab", ambiente="homologacao",
                                     configs_dir=configs)
        prod = ConfigLoader.carregar("sislab", ambiente="producao",
                                     configs_dir=configs)

        assert dev.confidence  == 0.8
        assert hom.confidence  == 0.85
        assert prod.confidence == 0.9

    def test_headless_por_ambiente(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        dev = ConfigLoader.carregar("sislab", ambiente="dev",
                                    configs_dir=configs)
        hom = ConfigLoader.carregar("sislab", ambiente="homologacao",
                                    configs_dir=configs)

        assert dev.headless  is False
        assert hom.headless  is True

    def test_timeout_por_ambiente(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        dev = ConfigLoader.carregar("sislab", ambiente="dev",
                                    configs_dir=configs)
        hom = ConfigLoader.carregar("sislab", ambiente="homologacao",
                                    configs_dir=configs)

        assert dev.timeout  == 30.0
        assert hom.timeout  == 60.0

    def test_vtae_env_define_ambiente(self, tmp_path):
        """VTAE_ENV deve definir o ambiente quando não passado como parâmetro."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        with patch.dict(os.environ, {"VTAE_ENV": "homologacao"}):
            config = ConfigLoader.carregar("sislab", configs_dir=configs)

        assert config.ambiente_ativo == "homologacao"

    def test_parametro_tem_prioridade_sobre_vtae_env(self, tmp_path):
        """Parâmetro ambiente= tem prioridade sobre VTAE_ENV."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        with patch.dict(os.environ, {"VTAE_ENV": "homologacao"}):
            config = ConfigLoader.carregar("sislab", ambiente="producao",
                                           configs_dir=configs)

        assert config.ambiente_ativo == "producao"


# ──────────────────────────────────────────────────────────────────────────────
# Resolução de variáveis de ambiente
# ──────────────────────────────────────────────────────────────────────────────

class TestResolucaoVariaveis:

    def test_resolve_variavel_do_ambiente(self, tmp_path):
        """${VAR} deve ser resolvido de os.environ."""
        configs = criar_config(tmp_path, "msi3", YAML_COM_ENV_VARS)

        with patch.dict(os.environ, {"MSI3_USER": "usuario_real",
                                      "MSI3_PASS": "senha_real"}):
            config = ConfigLoader.carregar("msi3", configs_dir=configs)

        assert config.USER     == "usuario_real"
        assert config.PASSWORD == "senha_real"

    def test_resolve_default_quando_var_ausente(self, tmp_path):
        """${VAR:-default} deve usar o default quando VAR não está definida."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        # garante que as variáveis não estão no ambiente
        env_sem_vars = {k: v for k, v in os.environ.items()
                        if k not in ("SISLAB_USER", "SISLAB_PASS")}

        with patch.dict(os.environ, env_sem_vars, clear=True):
            config = ConfigLoader.carregar("sislab", configs_dir=configs)

        assert config.USER     == "admin"
        assert config.PASSWORD == "admin123"

    def test_variavel_do_env_tem_prioridade_sobre_default(self, tmp_path):
        """Valor de os.environ tem prioridade sobre o default :- do YAML."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        with patch.dict(os.environ, {"SISLAB_USER": "usuario_env",
                                      "SISLAB_PASS": "senha_env"}):
            config = ConfigLoader.carregar("sislab", configs_dir=configs)

        assert config.USER     == "usuario_env"
        assert config.PASSWORD == "senha_env"

    def test_resolve_variavel_do_arquivo_env(self, tmp_path):
        """${VAR} deve ser resolvido do arquivo .env do sistema."""
        env_content = "SISLAB_USER=usuario_env_file\nSISLAB_PASS=senha_env_file\n"
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO,
                               env_content=env_content)

        # garante que não estão no ambiente do sistema
        env_sem_vars = {k: v for k, v in os.environ.items()
                        if k not in ("SISLAB_USER", "SISLAB_PASS")}

        with patch.dict(os.environ, env_sem_vars, clear=True):
            config = ConfigLoader.carregar("sislab", configs_dir=configs)

        assert config.USER     == "usuario_env_file"
        assert config.PASSWORD == "senha_env_file"

    def test_lanca_erro_quando_var_obrigatoria_ausente(self, tmp_path):
        """${VAR} sem default deve lançar ConfigError quando var não existe."""
        configs = criar_config(tmp_path, "msi3", YAML_COM_ENV_VARS)

        env_sem_vars = {k: v for k, v in os.environ.items()
                        if k not in ("MSI3_USER", "MSI3_PASS")}

        with patch.dict(os.environ, env_sem_vars, clear=True):
            with pytest.raises(ConfigError) as exc_info:
                ConfigLoader.carregar("msi3", configs_dir=configs)

        assert "MSI3_USER" in str(exc_info.value) or "MSI3_PASS" in str(exc_info.value)


# ──────────────────────────────────────────────────────────────────────────────
# Erros de validação
# ──────────────────────────────────────────────────────────────────────────────

class TestErros:

    def test_arquivo_nao_encontrado(self, tmp_path):
        """Sistema inexistente deve lançar ConfigError."""
        configs = tmp_path / "configs"
        configs.mkdir()

        with pytest.raises(ConfigError) as exc_info:
            ConfigLoader.carregar("sistema_inexistente", configs_dir=configs)

        assert "não encontrado" in str(exc_info.value)

    def test_ambiente_invalido(self, tmp_path):
        """Ambiente não definido no YAML deve lançar ConfigError."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        with pytest.raises(ConfigError) as exc_info:
            ConfigLoader.carregar("sislab", ambiente="staging",
                                  configs_dir=configs)

        assert "staging" in str(exc_info.value)

    def test_yaml_sem_ambientes(self, tmp_path):
        """YAML sem seção ambientes deve lançar ConfigError."""
        configs = criar_config(tmp_path, "sislab", YAML_SEM_AMBIENTES)

        with pytest.raises(ConfigError) as exc_info:
            ConfigLoader.carregar("sislab", configs_dir=configs)

        assert "ambientes" in str(exc_info.value).lower()

    def test_yaml_sem_credenciais(self, tmp_path):
        """YAML sem seção credenciais deve lançar ConfigError."""
        configs = criar_config(tmp_path, "sislab", YAML_SEM_CREDENCIAIS)

        with pytest.raises(ConfigError) as exc_info:
            ConfigLoader.carregar("sislab", configs_dir=configs)

        assert "credenciais" in str(exc_info.value).lower()

    def test_yaml_invalido(self, tmp_path):
        """YAML com sintaxe inválida deve lançar ConfigError."""
        configs_dir = tmp_path / "configs" / "sislab"
        configs_dir.mkdir(parents=True)
        (configs_dir / "config.yaml").write_text(
            "{\ninvalido: yaml: aqui\n", encoding="utf-8"
        )

        with pytest.raises((ConfigError, Exception)):
            ConfigLoader.carregar("sislab",
                                  configs_dir=tmp_path / "configs")


# ──────────────────────────────────────────────────────────────────────────────
# Listagem de sistemas e ambientes
# ──────────────────────────────────────────────────────────────────────────────

class TestListagem:

    def test_listar_sistemas(self, tmp_path):
        """listar_sistemas deve retornar sistemas com config.yaml."""
        criar_config(tmp_path, "sislab", YAML_MINIMO)
        criar_config(tmp_path, "si3", YAML_MINIMO.replace("sislab", "si3"))

        # cria pasta sem config.yaml — não deve aparecer
        (tmp_path / "configs" / "sem_config").mkdir()

        sistemas = ConfigLoader.listar_sistemas(
            configs_dir=tmp_path / "configs"
        )

        assert "sislab" in sistemas
        assert "si3" in sistemas
        assert "sem_config" not in sistemas

    def test_listar_sistemas_pasta_inexistente(self, tmp_path):
        """Pasta inexistente deve retornar lista vazia."""
        resultado = ConfigLoader.listar_sistemas(
            configs_dir=tmp_path / "nao_existe"
        )
        assert resultado == []

    def test_listar_ambientes(self, tmp_path):
        """listar_ambientes deve retornar os ambientes do YAML."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)

        # patch necessário porque listar_ambientes chama carregar internamente
        with patch.dict(os.environ, {"SISLAB_USER": "u", "SISLAB_PASS": "p"}):
            ambientes = ConfigLoader.listar_ambientes(
                "sislab", configs_dir=configs
            )

        assert "dev"          in ambientes
        assert "homologacao"  in ambientes
        assert "producao"     in ambientes


# ──────────────────────────────────────────────────────────────────────────────
# Propriedades do SystemConfig
# ──────────────────────────────────────────────────────────────────────────────

class TestSystemConfig:

    def test_user_property(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.USER == config.credenciais.usuario

    def test_password_property(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.PASSWORD == config.credenciais.senha

    def test_url_property(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.url == config.ambiente.url

    def test_confidence_property(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_MINIMO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.confidence == config.ambiente.confidence

    def test_dados_retorna_dict(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        dados = config.DADOS
        assert isinstance(dados, dict)

    def test_dados_tem_campos_configurados(self, tmp_path):
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        dados = config.DADOS
        assert "nome"  in dados
        assert "cargo" in dados
        assert "cpf"   in dados

    def test_dados_cargo_fixo(self, tmp_path):
        """Campo tipo fixo deve ter o valor exato do YAML."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        assert config.DADOS["cargo"] == "ANALISTA DE RH"

    def test_dados_cache(self, tmp_path):
        """DADOS deve retornar os mesmos valores em chamadas consecutivas."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)
        dados1 = config.DADOS
        dados2 = config.DADOS
        assert dados1 == dados2

    def test_resetar_dados_gera_novos_valores(self, tmp_path):
        """resetar_dados deve limpar o cache e gerar novos valores no próximo acesso."""
        configs = criar_config(tmp_path, "sislab", YAML_COMPLETO)
        config = ConfigLoader.carregar("sislab", configs_dir=configs)

        dados1 = config.DADOS
        config.resetar_dados()
        dados2 = config.DADOS

        # cargo é fixo — deve ser igual
        assert dados1["cargo"] == dados2["cargo"]
        # CPF é faker — pode ser diferente (não é garantido mas testa o reset)
        assert dados2 is not dados1  # objetos diferentes após reset
