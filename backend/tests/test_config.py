from pathlib import Path

from app.core.config import Settings


def test_upload_root_is_resolved_from_backend_directory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None, upload_root="data/uploads")

    expected = Path(__file__).resolve().parents[1] / "data" / "uploads"

    assert settings.get_upload_root_path() == expected


def test_absolute_upload_root_is_preserved(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, upload_root=str(tmp_path))

    assert settings.get_upload_root_path() == tmp_path.resolve()
