from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    logger.warning("not_found", path=request.url.path, detail=str(exc))
    return JSONResponse(
        status_code=404, content={"detail": str(exc), "error_code": "NOT_FOUND"}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
    )
