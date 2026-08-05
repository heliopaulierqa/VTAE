# vtae/core/motor/passo.py
"""
Execucao de um step — peca 4 do motor (Projeto v1.1, Fase 2).

Cronometra, avisa o observer na entrada e na saida, captura excecao,
classifica a causa, tira screenshot de diagnostico na falha e devolve um
StepResult.

E funcao, nao metodo: o motor nao e um flow. E copia do BaseFlow._step,
nao heranca: vtae/core/ nao importa vtae/flows/ (regra 58). O BaseFlow
fica intocado ate morrer inteiro na Fase 3.

Diferencas para o original:
  - sem confirm_template: quem confirma tela sao as esperas da peca 2
  - os tres holders viram um objeto so, Coleta. O motivo deles continua
    valendo — o observer loga na SAIDA do step, entao o valor tem que
    estar lido antes do StepResult nascer; atribuir depois do return
    chega tarde
  - Coleta.causa: o motor sabe o que o step estava fazendo, entao diz a
    causa. Farejar a mensagem de excecao continua existindo, mas como
    fallback, nao como regra
  - fora do farejamento: a palavra 'matricula', que era negocio do SI3
    dentro do classificador generico
"""
import time
from dataclasses import dataclass, field

from vtae.core.result import CausaFalha, StepResult


@dataclass
class Coleta:
    """
    Caixa que o fn preenche durante a execucao e o passo le depois.

    avisos usa default_factory: 'avisos: list = []' daria a MESMA lista
    para todas as instancias do processo, e os avisos de um step
    apareceriam no relatorio de outro.
    """
    ocr_lido: str | None = None
    jab_lido: str | None = None
    validated: bool | None = None
    causa: CausaFalha | None = None
    avisos: list[str] = field(default_factory=list)


def executar(step_id: str, descricao: str, fn, observer=None,
             ctx=None, coleta: Coleta | None = None) -> StepResult:
    coleta = coleta if coleta is not None else Coleta()

    if observer:
        observer.log_step_start(step_id, descricao)

    inicio = time.monotonic()
    try:
        screenshot_path = fn()
    except Exception as erro:
        passo = StepResult(
            step_id=step_id,
            success=False,
            duration_ms=_ms(inicio),
            error=str(erro),
            causa_falha=coleta.causa or _classificar(erro),
            validated=False,
            description=descricao,
            ocr_lido=coleta.ocr_lido,
            jab_lido=coleta.jab_lido,
            avisos=list(coleta.avisos),
        )
        _diagnostico(ctx, step_id)
    else:
        passo = StepResult(
            step_id=step_id,
            success=True,
            duration_ms=_ms(inicio),
            screenshot_path=screenshot_path,
            validated=coleta.validated,
            description=descricao,
            ocr_lido=coleta.ocr_lido,
            jab_lido=coleta.jab_lido,
            avisos=list(coleta.avisos),
        )

    if observer:
        observer.log_step_result(passo)
    return passo


def _ms(inicio: float) -> float:
    return (time.monotonic() - inicio) * 1000


def _diagnostico(ctx, step_id: str) -> None:
    """Melhor esforco: falhar aqui nunca pode mascarar o erro real."""
    if ctx is None:
        return
    try:
        ctx.runner.screenshot(f"{ctx.evidence_dir}{step_id}_auto_diag_001.png")
    except Exception:
        pass


def _classificar(erro: Exception) -> CausaFalha:
    """
    Fallback herdado do BaseFlow: fareja a mensagem quando o motor nao
    disse a causa. Preferir sempre Coleta.causa — ler texto de excecao e
    adivinhacao, nao medicao.
    """
    msg = str(erro).lower()
    if isinstance(erro, AssertionError):
        if "ausente no config" in msg:
            return CausaFalha.CONFIGURACAO
        if "estado_ausente" in msg:
            return CausaFalha.ESTADO_AUSENTE
        return CausaFalha.SISTEMA
    if "template" in msg or "not found" in msg:
        return CausaFalha.TEMPLATE_NAO_ENCONTRADO
    if "timeout" in msg:
        return CausaFalha.TIMEOUT
    if "coordenada" in msg or isinstance(erro, KeyError):
        return CausaFalha.COORDENADA
    if "ocr" in msg or "regiao" in msg:
        return CausaFalha.OCR_LEITURA
    if "estado_ausente" in msg:
        return CausaFalha.ESTADO_AUSENTE
    return CausaFalha.DESCONHECIDA