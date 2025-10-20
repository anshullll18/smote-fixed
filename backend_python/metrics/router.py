from __future__ import annotations
from typing import Annotated, List
from fastapi import APIRouter, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from metrics.schemas import MetricsResult, ImageMetrics
from metrics.service import compute_basic_metrics
from config import settings
from auth import verify_api_key

router = APIRouter(prefix="/metrics", tags=["metrics"])
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


class MetricsRequest(BaseModel):
    asset_ids: List[str] = Field(..., min_items=1)


@router.post("/basic", response_model=MetricsResult)
def post_basic_metrics(
    req: MetricsRequest, key: Annotated[str, Security(verify_api_key)]
) -> MetricsResult:
    items, summary = compute_basic_metrics(req.asset_ids)
    return MetricsResult(count=len(items), items=items, summary=summary)
