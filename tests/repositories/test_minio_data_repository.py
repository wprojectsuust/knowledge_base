import io
import json

from src.repositories.minio_data_repository import MinioDataRepository


def _make_repo() -> MinioDataRepository:
    return MinioDataRepository(
        endpoint_url="http://minio:9000",
        access_key="access",
        secret_key="secret",
        bucket="uunit-data",
    )


def test_creates_bucket_if_missing(fake_boto3) -> None:
    fake_client, _ = fake_boto3

    _make_repo()

    fake_client.create_bucket.assert_called_once_with(Bucket="uunit-data")


def test_save_puts_json_object(sample_data, fake_boto3) -> None:
    fake_client, _ = fake_boto3
    repo = _make_repo()

    repo.save(sample_data)

    _, kwargs = fake_client.put_object.call_args
    assert kwargs["Bucket"] == "uunit-data"
    assert kwargs["Key"] == "1.json"
    assert json.loads(kwargs["Body"].decode("utf-8")) == {
        "id": sample_data.id,
        "source": sample_data.source,
        "content": sample_data.content,
    }


def test_get_returns_data_when_object_exists(sample_data, fake_boto3) -> None:
    fake_client, _ = fake_boto3
    repo = _make_repo()
    payload = json.dumps(
        {"id": sample_data.id, "source": sample_data.source, "content": sample_data.content}
    ).encode("utf-8")
    fake_client.get_object.return_value = {"Body": io.BytesIO(payload)}

    assert repo.get(sample_data.id) == sample_data


def test_get_returns_none_when_object_missing(fake_boto3) -> None:
    fake_client, FakeClientError = fake_boto3
    repo = _make_repo()
    fake_client.get_object.side_effect = FakeClientError({"Error": {"Code": "NoSuchKey"}})

    assert repo.get(999) is None


def test_delete_removes_object(fake_boto3) -> None:
    fake_client, _ = fake_boto3
    repo = _make_repo()

    repo.delete(1)

    fake_client.delete_object.assert_called_once_with(Bucket="uunit-data", Key="1.json")
