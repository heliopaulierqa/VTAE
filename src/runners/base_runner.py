from abc import ABC, abstractmethod


class BaseRunner(ABC):
    """
    Contrato base para qualquer runner do VTAE.
    Implementações: OpenCVRunner (desktop), PlaywrightRunner (web), MockRunner (testes).
    """

    @abstractmethod
    def click_template(self, template: str, threshold: float = 0.8) -> bool:
        """Clica em um elemento da tela via template matching. Retorna True se encontrou."""
        ...

    @abstractmethod
    def type_text(self, text: str) -> None:
        """Digita texto no campo ativo."""
        ...

    @abstractmethod
    def screenshot(self, name: str) -> str:
        """Captura screenshot e retorna o caminho do arquivo salvo."""
        ...

    @abstractmethod
    def wait_template(self, template: str, timeout: float = 10.0, threshold: float = 0.8) -> bool:
        """Aguarda um template aparecer na tela. Retorna True se apareceu dentro do timeout."""
        ...

    def safe_click(self, template: str, threshold: float = 0.8, retries: int = 3) -> bool:
        """Click com retry automático. Pode ser sobrescrito por implementações específicas."""
        for attempt in range(1, retries + 1):
            if self.click_template(template, threshold):
                return True
            print(f"[safe_click] Tentativa {attempt}/{retries} falhou para '{template}'")
        return False
