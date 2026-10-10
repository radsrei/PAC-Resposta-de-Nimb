"""
Exceções de domínio. Os controllers levantam estas exceções e o `app/main.py`
converte cada uma no status HTTP correspondente.
"""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404


class NoActiveConnectionError(AppError):
    status_code = 409

    def __init__(self, message: str | None = None):
        super().__init__(
            message
            or "Nenhuma conexão LLM ativa. Configure uma em 'Conexão LLM' no topo da tela."
        )


class LLMError(AppError):
    """Falha ao se comunicar com o provedor de LLM."""

    status_code = 502
