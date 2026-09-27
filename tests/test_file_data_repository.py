import tempfile

from src.domain.data import Data
from src.repositories.file_data_repository import FileDataRepository

sample_data = Data(id=1, source="example.com", content="Деканат находится в корпусе 2")


def test_save_and_get_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = FileDataRepository(tmp_dir)

        repo.save(sample_data)

        assert repo.get(1) == sample_data


def test_get_missing_returns_none() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = FileDataRepository(tmp_dir)

        assert repo.get(999) is None


def test_get_many_returns_only_existing() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = FileDataRepository(tmp_dir)
        repo.save(sample_data)

        result = repo.get_many([1, 2, 3])

        assert result == [sample_data]


def test_delete_removes_data() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = FileDataRepository(tmp_dir)
        repo.save(sample_data)

        repo.delete(1)

        assert repo.get(1) is None
