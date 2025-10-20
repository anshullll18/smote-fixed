from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Tuple
import logging
import numpy as np
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
from skimage.metrics import structural_similarity as ssim
from .schemas import ImageInfo, SyntheticImages, MetricsReport, Metric, ImageMetrics
from assets.registry import registry

log = logging.getLogger(__name__)


def _vec(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img)
    return arr.reshape(-1).astype(np.float32)


def compute_quality_metrics(data: SyntheticImages) -> MetricsReport:
    by_label: dict[str, list[tuple[ImageInfo, np.ndarray, np.ndarray]]] = {}
    for o in data.originals:
        try:
            with Image.open(o.path) as oi:
                o_arr = np.asarray(oi)
                by_label.setdefault(o.label, []).append((o, _vec(oi), o_arr))
        except Exception as e:
            log.warning(f"Failed to load original image {o.path}: {e}")
            continue
    results: list[Metric] = []
    for s in data.synthetics:
        originals = by_label.get(s.label, [])
        if not originals:
            log.debug(f"No originals found for label {s.label}")
            continue
        try:
            with Image.open(s.path) as si:
                s_arr = np.asarray(si)
                s_vec = _vec(si)
        except Exception as e:
            log.warning(f"Failed to load synthetic image {s.path}: {e}")
            continue
        best_cos = -1.0
        best_o_arr = None
        for _, o_vec, o_arr in originals:
            try:
                cos = float(cosine_similarity(s_vec[None, :], o_vec[None, :])[0, 0])
                if cos > best_cos:
                    best_cos = cos
                    best_o_arr = o_arr
            except Exception as e:
                log.warning(f"Failed to compute similarity: {e}")
                continue
        ssim_val = 0.0
        if best_o_arr is not None:
            try:
                ssim_val = float(ssim(s_arr, best_o_arr, channel_axis=2))
            except Exception as e:
                log.warning(f"Failed to compute SSIM: {e}")
        results.append(Metric(synthpath=s.path, cossim=best_cos, ssim=ssim_val))
    return MetricsReport(metrics=results)


def compute_basic_metrics(
    asset_ids: List[str],
) -> Tuple[List[ImageMetrics], Dict[str, float]]:
    items: List[ImageMetrics] = []
    for asset_id in asset_ids:
        asset = registry.get_asset(asset_id)
        if not asset:
            log.warning(f"Asset not found: {asset_id}")
            continue
        try:
            path = registry.resolve_path(asset)
            with Image.open(path) as img:
                metrics = ImageMetrics(
                    asset_id=asset_id,
                    width=img.width,
                    height=img.height,
                    mode=img.mode,
                    file_size=asset.size,
                )
                items.append(metrics)
        except Exception as e:
            log.error(f"Failed to compute metrics for {asset_id}: {e}")
            continue
    if items:
        summary = {
            "avg_width": sum(m.width for m in items) / len(items),
            "avg_height": sum(m.height for m in items) / len(items),
            "avg_file_size": sum(m.file_size for m in items) / len(items),
            "total_size": sum(m.file_size for m in items),
        }
    else:
        summary = {
            "avg_width": 0.0,
            "avg_height": 0.0,
            "avg_file_size": 0.0,
            "total_size": 0.0,
        }
    return items, summary
