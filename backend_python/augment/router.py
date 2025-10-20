from __future__ import annotations
import logging
from typing import Annotated, List
from fastapi import APIRouter, HTTPException, Security, Response
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from augment.schemas import AugmentRequest, ImageInfo
from augment.service import run_smote
from assets.registry import registry
from config import settings
from metrics.service import compute_quality_metrics
from auth import verify_api_key

router = APIRouter(prefix="/augment", tags=["augment"])
log = logging.getLogger(__name__)


@router.post("/smote")
async def post_smote(
    req: AugmentRequest, key: Annotated[str, Security(verify_api_key)]
):
    images_with_labels: List[ImageInfo] = []
    for imgref in req.images:
        asset = registry.get_asset(imgref.asset_id)
        if not asset:
            raise HTTPException(
                status_code=404, detail=f"Asset {imgref.asset_id} not found"
            )
        if not asset.label:
            raise HTTPException(
                status_code=400,
                detail=f"Asset {imgref.asset_id} has no class label. Upload images using nested ZIP structure: class_name/image.jpg",
            )
        path = registry.resolve_path(asset)
        images_with_labels.append(ImageInfo(path=path, label=asset.label))
    log.info(f"Running SMOTE on {len(images_with_labels)} images")
    result = run_smote(images_with_labels)
    if not result.synthetics:
        raise HTTPException(
            status_code=400,
            detail="No synthetic images generated. Check class distribution and parameters.",
        )
    log.info(f"Computing quality metrics for {len(result.synthetics)} synthetic images")
    metrics_report = compute_quality_metrics(result)
    synthetic_images_json = [
        {
            "filename": synthinfo.path.name,
            "class": synthinfo.label,
            "url": f"/assets/synthetic/{synthinfo.label}/{synthinfo.path.name}",
        }
        for synthinfo in result.synthetics
    ]
    from collections import Counter

    original_counts = Counter(o.label for o in result.originals)
    synthetic_counts = Counter(s.label for s in result.synthetics)
    all_labels = set(original_counts.keys()) | set(synthetic_counts.keys())
    classes = {
        label: {
            "original_count": original_counts.get(label, 0),
            "synthetic_count": synthetic_counts.get(label, 0),
            "total_count": original_counts.get(label, 0)
            + synthetic_counts.get(label, 0),
        }
        for label in sorted(all_labels)
    }
    quality_metrics = [
        {
            "synthetic_image": metric.synthpath.name,
            "cosine_similarity": round(metric.cossim, 4),
            "ssim": round(metric.ssim, 4),
        }
        for metric in metrics_report.metrics
    ]
    avg_cos = (
        round(
            sum(m["cosine_similarity"] for m in quality_metrics) / len(quality_metrics),
            4,
        )
        if quality_metrics
        else 0.0
    )
    avg_ssim = (
        round(sum(m["ssim"] for m in quality_metrics) / len(quality_metrics), 4)
        if quality_metrics
        else 0.0
    )
    metrics = {
        "total_synthetic_images": len(result.synthetics),
        "total_original_images": len(result.originals),
        "classes": classes,
        "quality_metrics": quality_metrics,
        "average_quality": {"cosine_similarity": avg_cos, "ssim": avg_ssim},
    }
    response_json = {
        "count": len(result.synthetics),
        "synthetic_images": synthetic_images_json,
        "metrics": metrics,
    }
    import zipfile
    import io
    import json
    from pathlib import Path

    log.info("Creating ZIP file with augmented dataset")
    zip_buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(
                "augmentation_metadata.json", json.dumps(response_json, indent=2)
            )
            log.info("Added metadata JSON to ZIP")
            log.info("Adding original images to ZIP")
            for orig_info in result.originals:
                label = orig_info.label
                orig_path = Path(orig_info.path)
                if orig_path.exists():
                    with open(orig_path, "rb") as f:
                        zipf.writestr(f"{label}/{orig_path.name}", f.read())
                    log.debug(f"Added original: {label}/{orig_path.name}")
            log.info("Adding synthetic images to ZIP")
            for synth_info in result.synthetics:
                label = synth_info.label
                synth_path = Path(synth_info.path)
                if synth_path.exists():
                    with open(synth_path, "rb") as f:
                        zipf.writestr(f"{label}/{synth_path.name}", f.read())
                    log.debug(f"Added synthetic: {label}/{synth_path.name}")
        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()
        log.info(f"ZIP file created successfully, size: {len(zip_bytes)} bytes")
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=augmented_dataset.zip",
                "Content-Type": "application/zip",
            },
        )
    except Exception as e:
        log.error(f"Failed to create ZIP file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create ZIP file: {str(e)}"
        )
