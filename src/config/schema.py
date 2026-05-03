"""
Schema do VTAE — dataclasses que representam a estrutura do config.yaml.

Cada sistema tem um arquivo config.yaml que segue este schema.
O ConfigLoader valida o YAML contra o schema e retorna um SystemConfig.

Exemplo de config.yaml:
    sistema: sislab
    tipo: desktop
    runner: opencv

    ambientes:
      dev:
        url: http://127.0.0.1:5000
      homologacao:
        url: http://sislab.hom.interno

    credenciais:
      usuario: ${SISLAB_USER}
      senha: ${SISLAB_PASS}

    flows:
      - login
      - cadastro_funcionario

    dados_faker:
      - campo: nome
        tipo: faker
        metodo: name
        transformacao: sem_prefixo_upper
      - campo: cpf
        tipo: faker
        metodo: cpf
        transformacao: sem_pontuacao
      - campo: cargo
        tipo: fixo
        valor: "ANALISTA DE RH"
"""

from dataclasses import dataclass, field
from typing import Literal


# ──────────────────────────────────────────────────────────────────────────────
# Ambiente
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class AmbienteConfig:
    """
    Configuração de um ambiente específico (dev, homologacao, producao).
    Contém apenas o que muda entre ambientes — principalmente a URL.
    """
    url: str
    timeout: float = 30.0
    headless: bool = False
    slow_mo: int = 100
    confidence: float = 0.8

    def __post_init__(self):
        if not self.url:
            raise ValueError("AmbienteConfig.url não pode ser vazio.")
        if not (0.0 < self.confidence <= 1.0):
            raise ValueError(
                f"AmbienteConfig.confidence deve estar entre 0.0 e 1.0, "
                f"recebido: {self.confidence}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Credenciais
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CredenciaisConfig:
    """
    Credenciais do sistema.
    Os valores são resolvidos pelo ConfigLoader — podem ser valores literais
    ou referências a variáveis de ambiente no formato ${VAR_NAME}.
    """
    usuario: str
    senha: str

    def __post_init__(self):
        if not self.usuario:
            raise ValueError("CredenciaisConfig.usuario não pode ser vazio.")
        if not self.senha:
            raise ValueError("CredenciaisConfig.senha não pode ser vazio.")


# ──────────────────────────────────────────────────────────────────────────────
# Dados Faker
# ──────────────────────────────────────────────────────────────────────────────

TransformacaoTipo = Literal[
    "sem_pontuacao",      # remove . e - (ex: CPF "123.456.789-00" → "12345678900")
    "upper",              # maiúsculas
    "lower",              # minúsculas
    "truncar_50",         # limita a 50 caracteres
    "sem_prefixo",        # remove Dr., Dra., Sr., Sra., Prof. etc.
    "sem_prefixo_upper",  # remove prefixo E converte para maiúsculas
]


@dataclass
class DadoFakerConfig:
    """
    Configuração de um campo de dados dinâmicos.

    Tipos:
        faker  — usa método do Faker (ex: fake.name(), fake.cpf())
        fixo   — valor literal fixo (ex: "ANALISTA DE RH")
        random — valor aleatório de uma lista
    """
    campo: str
    tipo: Literal["faker", "fixo", "random"]

    # para tipo "faker"
    metodo: str | None = None
    transformacao: TransformacaoTipo | None = None
    locale: str = "pt_BR"

    # para tipo "fixo"
    valor: str | None = None

    # para tipo "random"
    opcoes: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.tipo == "faker" and not self.metodo:
            raise ValueError(
                f"DadoFakerConfig '{self.campo}': tipo='faker' requer campo 'metodo'."
            )
        if self.tipo == "fixo" and self.valor is None:
            raise ValueError(
                f"DadoFakerConfig '{self.campo}': tipo='fixo' requer campo 'valor'."
            )
        if self.tipo == "random" and not self.opcoes:
            raise ValueError(
                f"DadoFakerConfig '{self.campo}': tipo='random' requer campo 'opcoes'."
            )


# ──────────────────────────────────────────────────────────────────────────────
# Configuração completa do sistema
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SystemConfig:
    """
    Configuração completa de um sistema — resultado do ConfigLoader.

    Compatível com FlowContext — expõe USER, PASSWORD, url, confidence, DADOS.
    """
    sistema: str
    tipo: Literal["desktop", "web", "api"]
    runner: Literal["opencv", "playwright"]
    ambiente_ativo: str
    ambiente: AmbienteConfig
    credenciais: CredenciaisConfig
    flows: list[str] = field(default_factory=list)
    dados_schema: list[DadoFakerConfig] = field(default_factory=list)
    _dados_cache: dict | None = field(default=None, repr=False)

    # ── Compatibilidade com FlowContext ──────────────────────────────────────

    @property
    def USER(self) -> str:
        return self.credenciais.usuario

    @property
    def PASSWORD(self) -> str:
        return self.credenciais.senha

    @property
    def url(self) -> str:
        return self.ambiente.url

    @property
    def confidence(self) -> float:
        return self.ambiente.confidence

    @property
    def headless(self) -> bool:
        return self.ambiente.headless

    @property
    def timeout(self) -> float:
        return self.ambiente.timeout

    # ── Dados dinâmicos ──────────────────────────────────────────────────────

    @property
    def DADOS(self) -> dict:
        """
        Gera e retorna os dados dinâmicos conforme o schema.
        Cache por instância — mesmos dados durante toda a execução do flow.
        """
        if self._dados_cache is None:
            self._dados_cache = self._gerar_dados()
        return self._dados_cache

    def resetar_dados(self) -> None:
        """Limpa o cache — próximo acesso a DADOS gera novos valores."""
        self._dados_cache = None

    def _gerar_dados(self) -> dict:
        """Gera os dados conforme o schema usando Faker."""
        from faker import Faker
        import random

        fake = Faker(self.dados_schema[0].locale if self.dados_schema else "pt_BR")
        dados = {}

        for cfg in self.dados_schema:
            if cfg.tipo == "fixo":
                dados[cfg.campo] = cfg.valor

            elif cfg.tipo == "faker":
                valor = str(getattr(fake, cfg.metodo)())
                valor = self._aplicar_transformacao(valor, cfg.transformacao)
                dados[cfg.campo] = valor

            elif cfg.tipo == "random":
                dados[cfg.campo] = random.choice(cfg.opcoes)

        return dados

    @staticmethod
    def _aplicar_transformacao(valor: str,
                                transformacao: TransformacaoTipo | None) -> str:
        """Aplica a transformação ao valor gerado pelo Faker."""
        if transformacao is None:
            return valor

        if transformacao == "sem_pontuacao":
            return valor.replace(".", "").replace("-", "").replace("/", "")

        if transformacao == "upper":
            return valor.upper()

        if transformacao == "lower":
            return valor.lower()

        if transformacao == "truncar_50":
            return valor[:50]

        if transformacao == "sem_prefixo":
            import re
            return re.sub(
                r'^(Dr\.|Dra\.|Sr\.|Sra\.|Prof\.|Profª\.|Prof°\.|Mr\.|Mrs\.|Ms\.)\s*',
                '', valor
            ).strip()

        if transformacao == "sem_prefixo_upper":
            import re
            valor = re.sub(
                r'^(Dr\.|Dra\.|Sr\.|Sra\.|Prof\.|Profª\.|Prof°\.|Mr\.|Mrs\.|Ms\.)\s*',
                '', valor
            ).strip()
            return valor.upper()  # remove prefixo E converte para maiúsculas

        return valor
