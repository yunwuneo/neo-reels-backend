from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import auth_router, feed_router, health_router, videos_router
from app.core.errors import AppError, error_payload
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="Neo Reels Backend")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(videos_router)
app.include_router(feed_router)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, exc.details),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_payload("internal_error", "Internal server error"),
    )
