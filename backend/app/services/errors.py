from ..models import ErrorDetail


class ServiceError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False, *, status: int = 500, details=None):
        self.detail = ErrorDetail(code=code, message=message, retryable=retryable, details=details or {})
        self.status = status
        super().__init__(message)
