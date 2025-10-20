import logging
from fastapi.security import APIKeyHeader
from fastapi import FastAPI, Request, HTTPException, Security
from config import settings

log = logging.getLogger("app")
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    if not settings.REQUIRE_AUTH:
        return api_key
    if api_key not in settings.VALID_API_KEYS:
        log.warning("Invalid API key attempt detected")
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
