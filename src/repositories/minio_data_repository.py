from __future__ import annotations

import json

from src.domain.data import Data


class MinioDataRepository:
    """DataRepository поверх MinIO - self-hosted S3-совместимого хранилища через boto3.

    Работает с любым S3-совместимым эндпоинтом (endpoint_url), поэтому это может быть
    MinIO в соседнем контейнере рядом с сервером, без выхода на внешние облака вроде AWS."""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str) -> None:
        import boto3

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        existing_buckets = {b["Name"] for b in self._client.list_buckets().get("Buckets", [])}
        if bucket not in existing_buckets:
            self._client.create_bucket(Bucket=bucket)

    def _key(self, id_: int) -> str:
        return f"{id_}.json"

    def get(self, id_: int) -> Data | None:
        from botocore.exceptions import ClientError

        try:
            response = self._client.get_object(Bucket=self._bucket, Key=self._key(id_))
        except ClientError as error:
            if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            raise
        payload = json.loads(response["Body"].read().decode("utf-8"))
        return Data(**payload)

    def get_many(self, ids: list[int]) -> list[Data]:
        return [data for data in (self.get(id_) for id_ in ids) if data is not None]

    def save(self, data: Data) -> None:
        payload = json.dumps(
            {"id": data.id, "source": data.source, "content": data.content}, ensure_ascii=False
        ).encode("utf-8")
        self._client.put_object(Bucket=self._bucket, Key=self._key(data.id), Body=payload, ContentType="application/json")

    def delete(self, id_: int) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=self._key(id_))
