from __future__ import annotations
import json
import os
import tempfile
from typing import Any, Dict
from filelock import FileLock
from config import settings

SETTINGS_PATH = settings.PARAMSFILE


class ParamsStore:
    def __init__(self) -> None:
        self.path = settings.PARAMSFILE
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path.with_suffix(".lock")))

    def _read_unlocked(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _atomic_write_unlocked(self, payload: Dict[str, Any]) -> None:
        with tempfile.NamedTemporaryFile(
            "w", delete=False, dir=str(self.path.parent), encoding="utf-8"
        ) as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_name = tmp.name
        os.replace(tmp_name, self.path)

    def get(self) -> Dict[str, Any]:
        with self.lock:
            return self._read_unlocked()

    def set(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            self._atomic_write_unlocked(data)
            return data


store = ParamsStore()
