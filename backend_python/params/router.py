from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Security, HTTPException
from fastapi.security import APIKeyHeader
from params.schemas import ParamsPayload
from params.service import store
from config import settings
from auth import verify_api_key

router = APIRouter(prefix="/params", tags=["params"])
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


@router.get("")
def get_params() -> dict:
    return store.get()


@router.post("")
def set_params(
    payload: ParamsPayload, key: Annotated[str, Security(verify_api_key)]
) -> dict:
    return store.set(payload.data)
