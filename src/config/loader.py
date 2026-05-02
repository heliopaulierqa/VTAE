"""
ConfigLoader — lê config.yaml, resolve variáveis de ambiente e retorna SystemConfig.

Uso:
    # carrega ambiente dev (padrão)
    config = ConfigLoader.carregar("sislab")

    # carrega ambiente específico
    config = ConfigLoader.carregar("sislab", ambiente="homologacao")

    # nos flows — idêntico ao uso dos *_config.py antigos
    ctx = FlowContext(runner=runner, config=config)

Resolução de variáveis:
    O YAML pode referenciar variáveis de ambiente no formato ${VAR_NAME}.
    O ConfigLoader tenta resolver nesta ordem:
        1. Variáveis de ambiente do sistema (os.environ)
        2. Arquivo .env em configs/<sistema>/.env
        3. Arquivo .env raiz do projeto (.env)
    Se não encontrar, lança ConfigError com mensagem clara.

Estrutura esperada:
    configs/
    └── sislab/
        ├── config.yaml     ← configuração do sistema
        └── .env            ← credenciais locais (gitignore)
"""

import os
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    raise ImportError(
        "PyYAML não instalado. Execute: pip install pyyaml"
    )

from src.core.types import ConfigError
from src.config.schema import (
    SystemConfig,
    AmbienteConfig,
    CredenciaisConfig,
    DadoFakerConfig,
)


class ConfigLoader:
    """
    Carrega e valida configurações de sistemas a partir de arquivos YAML.
    Resolve variáveis de ambiente e gera SystemConfig pronto para uso nos flows.
    """

    # Padrão para variáveis: ${VAR_NAME} ou ${VAR_NAME:-valor_default}
    _VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::-(.*?))?\}')

    # Pasta raiz dos configs — relativa à raiz do projeto
    _CONFIGS_DIR = Path("vtae/configs")

    # Ambientes válidos
    _AMBIENTES_VALIDOS = {"dev", "homologacao", "producao"}

    @classmethod
    def carregar(cls, sistema: str,
                 ambiente: str = "dev",
                 configs_dir: Path = None) -> SystemConfig:
        """
        Carrega a configuração de um sistema para um ambiente específico.

        Args:
            sistema: nome do sistema (ex: "sislab", "si3", "msi3").
            ambiente: nome do ambiente (ex: "dev", "homologacao", "producao").
            configs_dir: override da pasta de configs. None = usa configs/ na raiz.

        Returns:
            SystemConfig pronto para uso nos flows.

        Raises:
            ConfigError: se o arquivo não existir, for inválido ou variável não resolvida.

        Exemplo:
            config = ConfigLoader.carregar("sislab")
            config = ConfigLoader.carregar("msi3", ambiente="homologacao")
        """
        base_dir = configs_dir or cls._CONFIGS_DIR
        config_path = base_dir / sistema / "config.yaml"

        if not config_path.exists():
            raise ConfigError(
                f"Arquivo de configuração não encontrado: '{config_path}'\n"
                f"Crie o arquivo com base no template em configs/<sistema>/config.yaml"
            )

        # carrega variáveis de ambiente (.env local + .env raiz)
        env_vars = cls._carregar_env(base_dir / sistema)

        # lê e parseia o YAML
        try:
            raw = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ConfigError(f"Erro ao parsear '{config_path}': {e}")

        if not isinstance(data, dict):
            raise ConfigError(f"'{config_path}' deve ser um dicionário YAML.")

        # resolve variáveis de ambiente no YAML inteiro
        data = cls._resolver_variaveis(data, env_vars, config_path)

        # valida e constrói o SystemConfig
        return cls._construir(data, sistema, ambiente, config_path)

    @classmethod
    def listar_sistemas(cls, configs_dir: Path = None) -> list[str]:
        """
        Lista os sistemas disponíveis (pastas com config.yaml).

        Returns:
            Lista de nomes de sistemas encontrados.
        """
        base_dir = configs_dir or cls._CONFIGS_DIR
        if not base_dir.exists():
            return []
        return [
            p.name for p in base_dir.iterdir()
            if p.is_dir() and (p / "config.yaml").exists()
        ]

    @classmethod
    def listar_ambientes(cls, sistema: str,
                          configs_dir: Path = None) -> list[str]:
        """
        Lista os ambientes disponíveis para um sistema.

        Returns:
            Lista de nomes de ambientes definidos no config.yaml.
        """
        config = cls.carregar(sistema, configs_dir=configs_dir)
        # re-lê o YAML só para listar ambientes sem resolver Faker
        base_dir = configs_dir or cls._CONFIGS_DIR
        raw = yaml.safe_load((base_dir / sistema / "config.yaml").read_text())
        return list(raw.get("ambientes", {}).keys())

    # ──────────────────────────────────────────────
    # Internos — construção
    # ──────────────────────────────────────────────

    @classmethod
    def _construir(cls, data: dict, sistema: str,
                   ambiente: str, config_path: Path) -> SystemConfig:
        """Valida o dicionário YAML e constrói o SystemConfig."""

        # campos obrigatórios
        for campo in ("tipo", "runner", "credenciais"):
            if campo not in data:
                raise ConfigError(
                    f"'{config_path}': campo obrigatório '{campo}' não encontrado."
                )

        # ambientes
        ambientes_raw = data.get("ambientes", {})
        if not ambientes_raw:
            raise ConfigError(
                f"'{config_path}': seção 'ambientes' não encontrada ou vazia."
            )

        if ambiente not in ambientes_raw:
            disponíveis = list(ambientes_raw.keys())
            raise ConfigError(
                f"'{config_path}': ambiente '{ambiente}' não encontrado.\n"
                f"Disponíveis: {disponíveis}"
            )

        amb_data = ambientes_raw[ambiente]
        if not isinstance(amb_data, dict) or "url" not in amb_data:
            raise ConfigError(
                f"'{config_path}': ambiente '{ambiente}' deve ter campo 'url'."
            )

        ambiente_cfg = AmbienteConfig(
            url=amb_data["url"],
            timeout=float(amb_data.get("timeout", 30.0)),
            headless=bool(amb_data.get("headless", False)),
            slow_mo=int(amb_data.get("slow_mo", 100)),
            confidence=float(amb_data.get("confidence", 0.8)),
        )

        # credenciais
        cred_data = data["credenciais"]
        if not isinstance(cred_data, dict):
            raise ConfigError(
                f"'{config_path}': seção 'credenciais' deve ser um dicionário."
            )
        credenciais_cfg = CredenciaisConfig(
            usuario=str(cred_data.get("usuario", "")),
            senha=str(cred_data.get("senha", "")),
        )

        # dados faker
        dados_schema = []
        for item in data.get("dados_faker", []):
            if not isinstance(item, dict):
                continue
            try:
                dado = DadoFakerConfig(
                    campo=item["campo"],
                    tipo=item["tipo"],
                    metodo=item.get("metodo"),
                    transformacao=item.get("transformacao"),
                    locale=item.get("locale", "pt_BR"),
                    valor=item.get("valor"),
                    opcoes=item.get("opcoes", []),
                )
                dados_schema.append(dado)
            except (KeyError, ValueError) as e:
                raise ConfigError(
                    f"'{config_path}': erro em dados_faker item {item}: {e}"
                )

        return SystemConfig(
            sistema=sistema,
            tipo=data["tipo"],
            runner=data["runner"],
            ambiente_ativo=ambiente,
            ambiente=ambiente_cfg,
            credenciais=credenciais_cfg,
            flows=data.get("flows", []),
            dados_schema=dados_schema,
        )

    # ──────────────────────────────────────────────
    # Internos — variáveis de ambiente
    # ──────────────────────────────────────────────

    @classmethod
    def _carregar_env(cls, sistema_dir: Path) -> dict[str, str]:
        """
        Carrega variáveis de ambiente de arquivos .env.
        Ordem de prioridade (maior → menor):
            1. os.environ (variáveis já definidas no sistema)
            2. configs/<sistema>/.env
            3. .env na raiz do projeto
        """
        env_vars = {}

        # .env raiz
        raiz_env = Path(".env")
        if raiz_env.exists():
            env_vars.update(cls._parsear_env_file(raiz_env))

        # .env do sistema (sobrescreve raiz)
        sistema_env = sistema_dir / ".env"
        if sistema_env.exists():
            env_vars.update(cls._parsear_env_file(sistema_env))

        # os.environ tem prioridade máxima
        env_vars.update(os.environ)

        return env_vars

    @classmethod
    def _parsear_env_file(cls, path: Path) -> dict[str, str]:
        """
        Parseia um arquivo .env simples.
        Ignora linhas em branco e comentários (#).
        Suporta: VAR=valor, VAR="valor com espaços", VAR='valor'
        """
        result = {}
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    result[key] = value
        except Exception:
            pass  # .env inválido — ignorar silenciosamente
        return result

    @classmethod
    def _resolver_variaveis(cls, data: Any,
                             env_vars: dict[str, str],
                             config_path: Path) -> Any:
        """
        Resolve referências ${VAR_NAME} e ${VAR_NAME:-default} recursivamente.
        Suporta strings, dicts e listas.
        """
        if isinstance(data, str):
            return cls._resolver_string(data, env_vars, config_path)
        if isinstance(data, dict):
            return {k: cls._resolver_variaveis(v, env_vars, config_path)
                    for k, v in data.items()}
        if isinstance(data, list):
            return [cls._resolver_variaveis(item, env_vars, config_path)
                    for item in data]
        return data

    @classmethod
    def _resolver_string(cls, valor: str,
                          env_vars: dict[str, str],
                          config_path: Path) -> str:
        """
        Resolve todas as referências ${...} em uma string.
        Suporta valor default: ${VAR_NAME:-valor_default}
        """
        def substituir(match):
            var_name = match.group(1).strip()
            default = match.group(2)  # None se não tiver :-

            if var_name in env_vars:
                return env_vars[var_name]

            if default is not None:
                return default

            raise ConfigError(
                f"'{config_path}': variável de ambiente '${{{var_name}}}' "
                f"não encontrada.\n"
                f"Defina a variável no sistema ou em configs/<sistema>/.env:\n"
                f"  {var_name}=seu_valor"
            )

        return cls._VAR_PATTERN.sub(substituir, valor)
