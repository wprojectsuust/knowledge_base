import io
import json
import sys
import types
from unittest.mock import MagicMock


def _install_fake_boto3() -> tuple[MagicMock, type[Exception]]:
    fake_client = MagicMock()
    fake_client.list_buckets.return_value = {"Buckets": []}

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = MagicMock(return_value=fake_client)
    sys.modules["boto3"] = fake_boto3

    class FakeClientError(Exception):
        def __init__(self, error_response: dict) -> None:
            super().__init__(error_response)
            self.response = error_response

    fake_botocore = types.ModuleType("botocore")
    fake_botocore_exceptions = types.ModuleType("botocore.exceptions")
    fake_botocore_exceptions.ClientError = FakeClientError
    fake_botocore.exceptions = fake_botocore_exceptions
    sys.modules["botocore"] = fake_botocore
    sys.modules["botocore.exceptions"] = fake_botocore_exceptions

    return fake_client, FakeClientError


def _make_repo():
    from src.repositories.minio_data_repository import MinioDataRepository

    return MinioDataRepository(
        endpoint_url="http://minio:9000",
        access_key="access",
        secret_key="secret",
        bucket="uunit-data",
    )


def test_creates_bucket_if_missing() -> None:
    fake_client, _ = _install_fake_boto3()

    _make_repo()

    fake_client.create_bucket.assert_called_once_with(Bucket="uunit-data")


def test_save_puts_json_object() -> None:
    fake_client, _ = _install_fake_boto3()
    repo = _make_repo()
    from src.domain.data import Data

    data = Data(id=1, source="example.com", content="Деканат находится в корпусе 2")

    repo.save(data)

    _, kwargs = fake_client.put_object.call_args
    assert kwargs["Bucket"] == "uunit-data"
    assert kwargs["Key"] == "1.json"
    assert json.loads(kwargs["Body"].decode("utf-8")) == {
        "id": 1,
        "source": "example.com",
        "content": "Деканат находится в корпусе 2",
    }


def test_get_returns_data_when_object_exists() -> None:
    fake_client, _ = _install_fake_boto3()
    repo = _make_repo()
    payload = json.dumps({"id": 1, "source": "example.com", "content": "Деканат находится в корпусе 2"}).encode("utf-8")
    fake_client.get_object.return_value = {"Body": io.BytesIO(payload)}

    from src.domain.data import Data

    assert repo.get(1) == Data(id=1, source="example.com", content="Деканат находится в корпусе 2")


def test_get_returns_none_when_object_missing() -> None:
    fake_client, FakeClientError = _install_fake_boto3()
    repo = _make_repo()
    fake_client.get_object.side_effect = FakeClientError({"Error": {"Code": "NoSuchKey"}})

    assert repo.get(999) is None


def test_delete_removes_object() -> None:
    fake_client, _ = _install_fake_boto3()
    repo = _make_repo()

    repo.delete(1)

    fake_client.delete_object.assert_called_once_with(Bucket="uunit-data", Key="1.json")
