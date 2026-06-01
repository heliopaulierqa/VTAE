# src/flows/base_flow.py
"""
BaseFlow — Classe base para todos os flows do VTAE.
Versao: 0.5.10 — Onda 1 refatoracao

Centraliza os helpers que antes eram duplicados em cada flow:
    _step()        — wrapper padrao com observabilidade completa
    _dado()        — leitura segura de dado obrigatorio do config.yaml
    _coord()       — leitura de coordenada com erro claro
    _tpl_existe()  — verifica se template PNG existe antes de usar
    _focar_si3()   — foca janela Oracle Forms antes de steps criticos

Todos os flows herdam desta classe e NADA MAIS precisam definir
desses helpers. O _step() canônico foi extraido do AgendamentoFlow
(versao mais completa: confirm_template + validated + CausaFalha).

Migracao:
    Antes: class MeuFlow:
    Depois: class MeuFlow(BaseFlow):
    Remover: _step, _dado, _coord, _tpl_existe, _focar_si3 do flow
    Ajustar: _coord(coords, nome)  — nao passa mais ctx

Novo campo StepResult.description:
    O _step() agora propaga descricao -> StepResult.description
    Isso habilita nomes legíveis nos screenshots e no JSON:
    "L01 - clicar no campo usuario e digitar"
"""

import os
import time

from src.core.result import CausaFalha, StepResult


class BaseFlow:
    """
    Classe base para todos os flows do VTAE.
    Nao instanciar diretamente — usar sempre uma subclasse concreta.
    """

    # ----------------------------------------------------------------
    # _step() — wrapper canonico de execucao de step
    # Versao mais completa: confirm_template + validated + CausaFalha
    # Fonte: AgendamentoFlow v0.5.9 (melhor versao encontrada)
    # ----------------------------------------------------------------

    def _step(
        self,
        step_id: str,
        descricao: str,
        fn,
        observer,
        confirm_template: str = None,
        validated: bool = None,
        ctx=None,
    ) -> StepResult:
        """
        Wrapper padrao para todos os steps do VTAE.

        Args:
            step_id:          ID do step (ex: "AB01")
            descricao:        Descricao legivel (ex: "abrir modulo Ambulatorio")
                              Gravada em StepResult.description — aparece no
                              nome do screenshot e no execution.json
            fn:               Funcao lambda sem argumentos que executa o step
            observer:         ExecutionObserver ou None
            confirm_template: Caminho do template PNG que deve aparecer apos
                              a acao — validated=True automatico se encontrar
            validated:        True explicito quando fn() executou verify_lov
                              ou verify_fill internamente
            ctx:              FlowContext — obrigatorio quando confirm_template
                              esta sendo usado

        Returns:
            StepResult com success, duration_ms, description, causa_falha

        Comportamento:
            - confirm_template ausente: tira screenshot, nao verifica tela
            - confirm_template presente: wait_template(8s) + validated=True
            - Falha: classifica CausaFalha automaticamente pelo tipo de excecao
            - Auto-screenshot de diagnostico em caso de falha
        """
        if observer:
            observer.log_step_start(step_id, descricao)
        start = time.monotonic()
        _validated = None
        try:
            screenshot_path = fn()

            # confirm_template: verifica tela destino e marca validated
            if confirm_template and ctx:
                if not ctx.runner.wait_template(confirm_template, timeout=8, threshold=0.7):
                    raise StepError(
                        f"[{step_id}] Tela nao confirmada — template nao encontrado: "
                        f"{confirm_template}"
                    )

            _validated = True if (confirm_template or validated) else None
            step = StepResult(
                step_id=step_id,
                success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                screenshot_path=screenshot_path,
                validated=_validated,
                description=descricao,
            )
        except AssertionError as e:
            msg = str(e).lower()
            if "ausente no config" in msg:
                causa = CausaFalha.CONFIGURACAO
            elif "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            else:
                causa = CausaFalha.SISTEMA
            step = StepResult(
                step_id=step_id,
                success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
                causa_falha=causa,
                validated=False,
                description=descricao,
            )
            # auto-screenshot de diagnostico
            if ctx:
                try:
                    ctx.runner.screenshot(
                        f"{ctx.evidence_dir}{step_id}_auto_diag_001.png"
                    )
                except Exception:
                    pass
        except Exception as e:
            msg = str(e).lower()
            if "template" in msg or "not found" in msg:
                causa = CausaFalha.TEMPLATE_NAO_ENCONTRADO
            elif "timeout" in msg:
                causa = CausaFalha.TIMEOUT
            elif "coordenada" in msg or isinstance(e, KeyError):
                causa = CausaFalha.COORDENADA
            elif "ocr" in msg or "matricula" in msg or "regiao" in msg:
                causa = CausaFalha.OCR_LEITURA
            elif "estado_ausente" in msg:
                causa = CausaFalha.ESTADO_AUSENTE
            else:
                causa = CausaFalha.DESCONHECIDA
            step = StepResult(
                step_id=step_id,
                success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(e),
                causa_falha=causa,
                validated=False,
                description=descricao,
            )
            if ctx:
                try:
                    ctx.runner.screenshot(
                        f"{ctx.evidence_dir}{step_id}_auto_diag_001.png"
                    )
                except Exception:
                    pass
        if observer:
            observer.log_step_result(step)
        return step

    # ----------------------------------------------------------------
    # _dado() — leitura segura de dado obrigatorio
    # ----------------------------------------------------------------

    def _dado(self, dados: dict, chave: str, step_id: str):
        """
        Le um dado obrigatorio do config.yaml.
        Falha imediatamente com mensagem clara se a chave nao existir.

        Regra 19: dados.get("chave", "DEFAULT") e PROIBIDO nos flows.
        Todo acesso a dado de teste passa por _dado().

        Raises:
            AssertionError: com mensagem indicando qual chave falta e onde.
        """
        if chave not in dados:
            raise AssertionError(
                f"[{step_id}] Dado obrigatorio ausente no config.yaml: '{chave}'\n"
                f"Adicione '{chave}: <valor>' na secao dados: do config.yaml.\n"
                f"Chaves disponiveis: {list(dados.keys())}"
            )
        return dados[chave]

    # ----------------------------------------------------------------
    # _coord() — leitura de coordenada com erro claro
    # ----------------------------------------------------------------

    def _coord(self, coords: dict, nome: str) -> tuple:
        """
        Le coordenada do dicionario coords (ctx.config.coordenadas).
        Lanca KeyError com mensagem clara se nao configurada.

        Assinatura: _coord(coords, nome) — nao passa ctx.
        Uso: x, y = self._coord(coords, "campo_nome")
        """
        if nome not in coords:
            raise KeyError(
                f"Coordenada '{nome}' nao encontrada em config.yaml -> coordenadas:\n"
                f"Configure com posicao_mouse.py e adicione ao config.yaml."
            )
        c = coords[nome]
        return (c["x"], c["y"])

    # ----------------------------------------------------------------
    # _tpl_existe() — verifica existencia de template antes de usar
    # ----------------------------------------------------------------

    @staticmethod
    def _tpl_existe(path: str) -> bool:
        """
        Verifica se template PNG existe antes de usar wait_template.
        Evita TemplateNotFoundError por arquivo ainda nao capturado.

        Uso obrigatorio antes de qualquer wait_template com template
        que pode nao existir (templates condicionais, em calibracao).
        """
        return os.path.exists(path)

    # ----------------------------------------------------------------
    # _focar_si3() — foca janela Oracle Forms
    # ----------------------------------------------------------------

    @staticmethod
    def _focar_si3() -> bool:
        """
        Tenta focar a janela do SI3 (Oracle Forms).
        Tolerante — nunca para o flow se falhar.

        Chamar antes de steps criticos que dependem de foco:
        digitacao em campo, cliques em popup, LOV.

        Requer: pip install pygetwindow
        Fallback: retorna False e o flow continua normalmente.
        """
        try:
            import pygetwindow as gw
            janelas = gw.getWindowsWithTitle("FUNDA")
            if not janelas:
                janelas = gw.getWindowsWithTitle("FZ -")
            if janelas:
                w = janelas[0]
                if w.isMinimized:
                    w.restore()
                    time.sleep(0.3)
                w.activate()
                time.sleep(0.5)
                return True
            print("[_focar_si3] AVISO: janela SI3 nao encontrada pelo titulo")
            return False
        except ImportError:
            print("[_focar_si3] AVISO: pygetwindow nao instalado — pip install pygetwindow")
            return False
        except Exception as e:
            print(f"[_focar_si3] AVISO: {e}")
            return False


# Import local para evitar dependencia circular — StepError usado no _step()
try:
    from src.core.types import StepError
except ImportError:
    # Fallback se types nao existir — usa AssertionError
    StepError = AssertionError