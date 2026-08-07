class ApiError(Exception):
    """Raised by services/routes to produce a clean JSON error response."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(ApiError):
    def __init__(self, message="Not found"):
        super().__init__(message, status_code=404)


class ForbiddenError(ApiError):
    def __init__(self, message="Forbidden"):
        super().__init__(message, status_code=403)


class ValidationError(ApiError):
    def __init__(self, message="Invalid request"):
        super().__init__(message, status_code=422)
