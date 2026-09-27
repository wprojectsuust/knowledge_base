from __future__ import annotations

import json
from pathlib import Path

from src.domain.data import Data


class FileDataRepository:
    """DataRepository поверх локальной файловой системы: один JSON-файл на Data.

    Данные физически живут рядом с сервером (в докере - в примонтированном volume),
    отдельный S3/MinIO-сервис на время хакатона не поднимаем."""

    def __init__(self, storage_dir: str) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, id_: int) -> Path:
        return self._storage_dir / f"{id_}.json"

    def get(self, id_: int) -> Data | None:
        path = self._path(id_)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Data(**payload)

    def get_many(self, ids: list[int]) -> list[Data]:
        return [data for data in (self.get(id_) for id_ in ids) if data is not None]

    def save(self, data: Data) -> None:
        payload = {"id": data.id, "source": data.source, "content": data.content}
        self._path(data.id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def delete(self, id_: int) -> None:
        path = self._path(id_)
        if path.exists():
            path.unlink()
