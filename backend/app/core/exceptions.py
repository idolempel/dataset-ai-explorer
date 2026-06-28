"""Custom application exceptions and FastAPI handlers."""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for expected application errors mapped to HTTP responses."""

    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class UnprocessableError(AppError):
    # 422 — use a literal to stay forward-compatible across Starlette renames of
    # the HTTP_422_* status constant.
    status_code = 422


def register_exception_handlers(app: FastAPI) -> None:
    """Attach a handler that renders :class:`AppError` as a JSON envelope."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
