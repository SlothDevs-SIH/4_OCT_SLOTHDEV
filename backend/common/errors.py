"""Shared error shape: {"error": {"code": "...", "message": "..."}} (contract section 1)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def not_found(what: str) -> ApiError:
    return ApiError(404, "not_found", f"{what} not found")


def not_implemented(feature: str) -> ApiError:
    """Raise for a documented, dropped should-have: `raise not_implemented("rfm")`."""
    return ApiError(501, "not_implemented", f"{feature} is not implemented")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(error_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(error_body("invalid_request", str(exc.errors())), status_code=422)
