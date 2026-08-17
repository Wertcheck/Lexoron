"""Tests für app/setup/env_writer.py (Prompt 37)."""

import pytest

from app.setup.env_writer import build_env_content, write_env_file


def test_build_env_content_contains_expected_keys(tmp_path) -> None:
    content = build_env_content(
        data_dir=tmp_path, session_secret="secret123", host="127.0.0.1", port=8000
    )
    posix = tmp_path.as_posix()

    assert "APP_ENV=production" in content
    assert f'DATABASE_URL="sqlite:///{posix}/data/kanzlei_ai.db"' in content
    assert f'INTAKE_STORAGE_DIR="{posix}/data/intake"' in content
    assert f'MAIL_ATTACHMENT_STORAGE_DIR="{posix}/data/mail_attachments"' in content
    assert f'LOG_FILE_PATH="{posix}/logs/kanzlei_ai.log"' in content
    assert "SESSION_SECRET_KEY=secret123" in content
    assert "SESSION_COOKIE_SECURE=True" in content
    assert "HOST=127.0.0.1" in content
    assert "PORT=8000" in content


def test_build_env_content_uses_provided_host_and_port(tmp_path) -> None:
    content = build_env_content(
        data_dir=tmp_path, session_secret="x", host="0.0.0.0", port=9090
    )
    assert "HOST=0.0.0.0" in content
    assert "PORT=9090" in content


def test_build_env_content_is_actually_parseable_by_settings(tmp_path) -> None:
    """Integrationstest: der erzeugte Inhalt muss von Settings korrekt
    eingelesen werden - beweist, dass die Anführungszeichen/Pfadformate
    keine reine Behauptung sind."""
    from app.config.settings import Settings

    content = build_env_content(data_dir=tmp_path, session_secret="x" * 40)
    env_path = tmp_path / ".env"
    env_path.write_text(content, encoding="utf-8")

    settings = Settings(_env_file=str(env_path))  # type: ignore[call-arg]

    posix = tmp_path.as_posix()
    assert settings.app_env == "production"
    assert settings.database_url == f"sqlite:///{posix}/data/kanzlei_ai.db"
    assert settings.intake_storage_dir == f"{posix}/data/intake"
    assert settings.mail_attachment_storage_dir == f"{posix}/data/mail_attachments"
    assert settings.log_file_path == f"{posix}/logs/kanzlei_ai.log"
    assert settings.resolved_session_secret_key == "x" * 40
    assert settings.resolved_session_cookie_secure is True
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_write_env_file_creates_parent_dirs_and_file(tmp_path) -> None:
    target = tmp_path / "nested" / ".env"
    write_env_file(target, "APP_ENV=production\n")
    assert target.read_text(encoding="utf-8") == "APP_ENV=production\n"


def test_write_env_file_refuses_overwrite_without_force(tmp_path) -> None:
    target = tmp_path / ".env"
    target.write_text("original", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_env_file(target, "new content", force=False)

    assert target.read_text(encoding="utf-8") == "original"


def test_write_env_file_overwrites_with_force(tmp_path) -> None:
    target = tmp_path / ".env"
    target.write_text("original", encoding="utf-8")

    write_env_file(target, "new content", force=True)

    assert target.read_text(encoding="utf-8") == "new content"
