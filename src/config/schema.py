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

    # Dados fixos — passados diretamente ao flow via config.DADOS
    # Suporta qualquer estrutura: strings, listas, dicts aninhados
    dados:
      unidade_funcional: 'SC AMBULATORIO'
      procedimentos:
        - codigo: 'CARDIO'
          complemento: 'CASO NOVO'
"""

from dataclasses import dataclass, field
from typing import Literal


# ----------------------------------------------------------------
# Ambiente
# ----------------------------------------------------------------

@dataclass
class AmbienteConfig:
    """
    Configuracao de um ambiente especifico (dev, homologacao, producao).
    Contem apenas o que muda entre ambientes — principalmente a URL.
    """
    url: str
    timeout: float = 30.0
    headless: bool = False
    slow_mo: int = 100
    confidence: float = 0.8

    def __post_init__(self):
        if not (0.0 < self.confidence <= 1.0):
            raise ValueError(
                f"AmbienteConfig.confidence deve estar entre 0.0 e 1.0, "
                f"recebido: {self.confidence}"
            )


# ----------------------------------------------------------------
# Credenciais
# ----------------------------------------------------------------

@dataclass
class CredenciaisConfig:
    """
    Credenciais do sistema.
    Os valores sao resolvidos pelo ConfigLoader — podem ser valores literais
    ou referencias a variaveis de ambiente no formato ${VAR_NAME}.
    """
    usuario: str
    senha: str

    def __post_init__(self):
        if not self.usuario:
            raise ValueError("CredenciaisConfig.usuario nao pode ser vazio.")
        if not self.senha:
            raise ValueError("CredenciaisConfig.senha nao pode ser vazio.")


# ----------------------------------------------------------------
# Dados Faker
# ----------------------------------------------------------------

TransformacaoTipo = Literal[
    "sem_pontuacao",      # remove . e - (ex: CPF "123.456.789-00" -> "12345678900")
    "upper",              # maiusculas
    "lower",              # minusculas
    "truncar_50",         # limita a 50 caracteres
    "sem_prefixo",        # remove Dr., Dra., Sr., Sra., Prof. etc.
    "sem_prefixo_upper",  # remove prefixo E converte para maiusculas
]


@dataclass
class DadoFakerConfig:
    """
    Configuracao de um campo de dados dinamicos.

    Tipos:
        faker  — usa metodo do Faker (ex: fake.name(), fake.cpf())
        fixo   — valor literal fixo (ex: "ANALISTA DE RH")
        random — valor aleatorio de uma lista
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


# ----------------------------------------------------------------
# Configuracao completa do sistema
# ----------------------------------------------------------------

@dataclass
class SystemConfig:
    """
    Configuracao completa de um sistema — resultado do ConfigLoader.

    Compativel com FlowContext — expoe USER, PASSWORD, url, confidence, DADOS.

    DADOS retorna a mesclagem de:
      - dados_fixos: secao 'dados:' do config.yaml (strings, listas, dicts)
      - dados gerados pelo Faker via dados_schema (secao 'dados_faker:')
      O Faker sobrescreve dados_fixos quando ha conflito de chave.
    """
    sistema: str
    tipo: Literal["desktop", "web", "api"]
    runner: Literal["opencv", "playwright"]
    ambiente_ativo: str
    ambiente: AmbienteConfig
    credenciais: CredenciaisConfig
    flows: list[str] = field(default_factory=list)
    dados_schema: list[DadoFakerConfig] = field(default_factory=list)
    # Coordenadas diretas de campos — lidas da secao `coordenadas:` do config.yaml.
    coordenadas: dict = field(default_factory=dict)
    # Regioes OCR — lidas da secao `regioes_ocr:` do config.yaml.
    regioes_ocr: dict = field(default_factory=dict)
    # Engine OCR — padrão: "easyocr" (v0.5.11 — Tesseract removido).
    # Controla qual engine verify_fill e verify_lov usam.
    # Definir no config.yaml: ocr_engine: easyocr
    ocr_engine: str = "easyocr"
    # Dados fixos — lidos da secao `dados:` do config.yaml.
    # Suporta qualquer estrutura: strings, listas, dicts aninhados.
    # Retrocompativel: sistemas sem secao `dados:` recebem {} por padrao.
    dados_fixos: dict = field(default_factory=dict)
    # ID do paciente — lido do .env via ${SI3_PACIENTE_ID:-}.
    # Vazio = cadastrar novo paciente automaticamente.
    # Preenchido = reutilizar paciente existente (pula o cadastro).
    # Cada jornada tem seu proprio .env — isolamento garantido.
    paciente_id: str = ""
    _dados_cache: dict | None = field(default=None, repr=False)

    # -- Compatibilidade com FlowContext --

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

    @property
    def PACIENTE_ID(self) -> str:
        """ID do paciente lido do .env. Vazio = cadastrar novo automaticamente."""
        return self.paciente_id

    # -- Dados dinamicos --

    @property
    def DADOS(self) -> dict:
        """
        Retorna dados mesclados: dados_fixos (config.yaml secao dados:)
        + dados gerados pelo Faker (config.yaml secao dados_faker:).

        Prioridade: Faker sobrescreve dados_fixos quando ha conflito de chave.
        Cache por instancia — mesmos dados durante toda a execucao do flow.

        Exemplos de uso no flow:
            dados["unidade_funcional"]      # string do dados:
            dados["procedimentos"]          # lista do dados:
            dados["cenario_provedor"]       # string do dados:
            dados["nome"]                   # gerado pelo Faker
        """
        if self._dados_cache is None:
            faker_gerados = self._gerar_dados()
            # dados_fixos como base, faker sobrescreve conflitos
            self._dados_cache = {**self.dados_fixos, **faker_gerados}
        return self._dados_cache

    def resetar_dados(self) -> None:
        """Limpa o cache — proximo acesso a DADOS gera novos valores."""
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
        """Aplica a transformacao ao valor gerado pelo Faker."""
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
                r'^(Dr\.|Dra\.|Sr\.|Sra\.|Prof\.|Profa\.|Profº\.|Mr\.|Mrs\.|Ms\.)\s*',
                '', valor
            ).strip()

        if transformacao == "sem_prefixo_upper":
            import re
            valor = re.sub(
                r'^(Dr\.|Dra\.|Sr\.|Sra\.|Prof\.|Profa\.|Profº\.|Mr\.|Mrs\.|Ms\.)\s*',
                '', valor
            ).strip()
            return valor.upper()

        return valor