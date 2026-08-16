from fastapi import HTTPException, status


class ExternalServiceNotConfigured(RuntimeError):
    pass


class ExternalServiceUnavailable(RuntimeError):
    pass


def service_not_configured(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


def service_unavailable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
