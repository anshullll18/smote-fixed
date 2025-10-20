from __future__ import annotations
import io
import os
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple
import logging
from fastapi import HTTPException, UploadFile
from PIL import Image
from assets.registry import registry
from config import settings

log = logging.getLogger(__name__)
MAX_IMAGE_DIMENSION = 10000
MAX_IMAGE_PIXELS = 50_000_000
MINIMUM_IMAGE_RESOLUTION = settings.MINIMUM_IMAGE_RESOLUTION
MAXIMUM_IMAGE_DIMENSION = settings.MAXIMUM_IMAGE_DIMENSION
MAXIMUM_IMAGE_PIXELS = settings.MAXIMUM_IMAGE_PIXELS


def is_allowed_image(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in settings.ALLOWEDIMAGEEXTS


def validate_and_save_temp(img_bytes: bytes, original_filename: str) -> Path:
    try:
        with Image.open(io.BytesIO(img_bytes)) as im:
            im.verify()
        
        with Image.open(io.BytesIO(img_bytes)) as im:
            if im.format and im.format.lower() not in ("jpeg", "jpg", "png", "webp"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image format for {original_filename}: {im.format}",
                )
            
            width, height = im.size
            
            if width > MAXIMUM_IMAGE_DIMENSION or height > MAXIMUM_IMAGE_DIMENSION:
                raise HTTPException(
                    status_code=413,
                    detail=f"Image dimensions too large ({width}x{height}). "
                    f"Maximum dimension: {MAXIMUM_IMAGE_DIMENSION}px",
                )
            
            if width * height > MAXIMUM_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413,
                    detail=f"Image resolution too high ({width * height} pixels). "
                    f"Maximum: {MAXIMUM_IMAGE_PIXELS} pixels",
                )
            
            if width < 32 or height < 32:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image resolution too low ({width}x{height}). "
                    f"Minimum resolution: 32x32 pixels",
                )
    
    except HTTPException:
        raise
    except Exception as e:
        log.warning(f"Invalid image {original_filename}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid or corrupted image {original_filename} - {str(e)}",
        )
    
    tmp_dir = settings.DATAPATH / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    tmp = tempfile.NamedTemporaryFile(
        delete=False, dir=str(tmp_dir), prefix="upload_", suffix=".tmp"
    )
    try:
        tmp.write(img_bytes)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        return Path(tmp.name)
    except Exception as e:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")



def validate_zip_limits(zf: zipfile.ZipFile) -> None:
    infos = zf.infolist()
    if len(infos) > settings.UPLOADMAXFILES:
        raise HTTPException(
            status_code=413,
            detail=f"Too many files (limit is {settings.UPLOADMAXFILES})",
        )
    total_unzipped = sum(i.file_size for i in infos)
    max_bytes = settings.UPLOADMAXUNZIPPEDMB * 1024 * 1024
    if total_unzipped > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Unzipped size exceeds {settings.UPLOADMAXUNZIPPEDMB} MB",
        )
    total_compressed = sum(i.compress_size for i in infos if not i.is_dir())
    if total_compressed > 0:
        compression_ratio = total_unzipped / total_compressed
        if compression_ratio > 100:
            log.warning(f"Suspicious ZIP compression ratio: {compression_ratio:.2f}")
            raise HTTPException(
                status_code=400,
                detail="ZIP file has suspicious compression ratio (possible zip bomb)",
            )


def safe_member_name(member: zipfile.ZipInfo) -> str:
    name = member.filename
    if member.is_dir():
        raise ValueError(f"Directory entry not allowed: {name}")
    normalized = os.path.normpath(name)
    if (
        normalized.startswith("..")
        or normalized.startswith("/")
        or normalized.startswith("\\")
    ):
        raise ValueError(f"Path traversal attempt detected: {name}")
    if ".." in normalized.split(os.sep):
        raise ValueError(f"Path traversal attempt detected: {name}")
    return normalized


def ingest_zip(file: UploadFile) -> List[Tuple[str, str, str]]:
    file.file.seek(0, os.SEEK_SET)
    try:
        with zipfile.ZipFile(file.file) as zf:
            validate_zip_limits(zf)
            created: List[Tuple[str, str, str]] = []
            for info in zf.infolist():
                if info.is_dir():
                    continue
                try:
                    safepath = safe_member_name(info)
                except ValueError as e:
                    log.warning(f"Skipping unsafe file: {e}")
                    continue
                path_parts = Path(safepath).parts
                if len(path_parts) < 2:
                    log.warning(f"Skipping file not in class folder: {info.filename}")
                    continue
                class_label = path_parts[0]
                filename = path_parts[-1]
                if not is_allowed_image(filename):
                    log.debug(f"Skipping non-image file: {filename}")
                    continue
                try:
                    with zf.open(info, "r") as fp:
                        data = fp.read()
                    tmppath = validate_and_save_temp(data, filename)
                    asset = registry.add_file(
                        tmppath, original_filename=filename, label=class_label
                    )
                    created.append((asset.id, asset.filename, class_label))
                except HTTPException:
                    raise
                except Exception as e:
                    log.error(f"Failed to process {filename}: {e}")
                    continue
            if not created:
                raise HTTPException(
                    status_code=400, detail="No valid images found in archive"
                )
            log.info(f"Ingested {len(created)} images from ZIP with class labels")
            return created
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP")
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Unexpected error during ZIP ingestion: {e}")
        raise HTTPException(status_code=500, detail="Failed to process ZIP file")
