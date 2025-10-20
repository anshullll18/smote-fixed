from __future__ import annotations
import logging
from typing import List
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from assets.router import router as assets_router
from upload.router import router as upload_router
from augment.router import router as augment_router
from metrics.router import router as metrics_router
from params.router import router as params_router
from config import settings
from logger.logging_config import configure_logging

configure_logging(settings.LOGLEVEL)
log = logging.getLogger("app")
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=settings.APPNAME)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


if settings.ALLOWEDHOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWEDHOSTS)
if settings.CORSORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORSORIGINS,
        allow_credentials=settings.CORSALLOWCREDENTIALS,
        allow_methods=settings.CORSALLOWMETHODS,
        allow_headers=settings.CORSALLOWHEADERS,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.exception(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
@limiter.limit("100/minute")
def health(request: Request) -> dict:
    return {"status": "ok", "app": settings.APPNAME}


@app.get("/ready")
@limiter.limit("100/minute")
def ready(request: Request) -> JSONResponse:
    from assets.registry import registry

    try:
        _ = registry.list_assets()
        return JSONResponse({"status": "ready"})
    except Exception as e:
        log.exception("Readiness check failed: %s", e)
        return JSONResponse({"status": "not_ready", "error": str(e)}, status_code=503)


app.include_router(assets_router)
app.include_router(upload_router)
app.include_router(augment_router)
app.include_router(metrics_router)
app.include_router(params_router)
