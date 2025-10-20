from __future__ import annotations
from typing import Annotated, List
from fastapi import APIRouter, File, HTTPException, Security, UploadFile
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from config import settings
from upload.schemas import UploadResult, AssetOut
from upload.service import ingest_zip
from auth import verify_api_key

router = APIRouter(prefix="/upload", tags=["upload"])
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


class UploadResponse(UploadResult):
    pass


@router.post("/zip", response_model=UploadResponse)
async def upload_zip(
    file: UploadFile = File(...), key: Annotated[str, Security(verify_api_key)] = None
) -> UploadResult:
    created = ingest_zip(file)
    assets: List[AssetOut] = []
    for asset_id, filename, label in created:
        assets.append(
            AssetOut(
                id=asset_id,
                filename=filename,
                url=f"/assets/{asset_id}",
                label=label,
            )
        )
    return UploadResult(count=len(assets), assets=assets)
