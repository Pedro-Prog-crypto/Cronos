import json
import sqlite3
from pathlib import Path

from tools.migrate_local_data import migrate


def _write_sqlite(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS memory (note TEXT)")
        db.execute("INSERT INTO memory(note) VALUES (?)", (text,))


def _old_install(root: Path) -> None:
    (root / "config").mkdir(parents=True)
    (root / "vault" / ".cronos").mkdir(parents=True)
    (root / ".env").write_text(
        "GEMINI_API_KEY=fake-test-secret\n"
        "CRONOS_VAULT=old-vault\n"
        "CRONOS_PROVIDERS_FILE=config/old-providers.json\n",
        encoding="utf-8",
    )
    (root / "config" / "old-providers.json").write_text('{"providers": []}\n', encoding="utf-8")
    (root / "vault" / "anotacao.md").write_text("memoria importante", encoding="utf-8")
    _write_sqlite(root / "vault" / ".cronos" / "memory.sqlite3", "registrada")


def test_migrates_env_providers_vault_and_keeps_destination_backup(tmp_path: Path) -> None:
    old = tmp_path / "old"
    new = tmp_path / "new"
    _old_install(old)
    (new / "config").mkdir(parents=True)
    (new / "config" / "providers.example.json").write_text('{}\n', encoding="utf-8")
    (new / ".env").write_text("DESTINATION_ONLY=old\n", encoding="utf-8")
    (new / "vault").mkdir()
    (new / "vault" / "old-note.md").write_text("preservar", encoding="utf-8")

    backup = migrate(old, new)

    env = (new / ".env").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=fake-test-secret" in env
    assert "CRONOS_VAULT=vault" in env
    assert "CRONOS_PROVIDERS_FILE=config/providers.json" in env
    assert "CRONOS_DATA_HOME=" not in env
    assert (new / "config" / "providers.json").read_text(encoding="utf-8") == '{"providers": []}\n'
    assert (new / "vault" / "anotacao.md").read_text(encoding="utf-8") == "memoria importante"
    assert (old / "vault" / "anotacao.md").read_text(encoding="utf-8") == "memoria importante"
    assert (backup / ".env").read_text(encoding="utf-8") == "DESTINATION_ONLY=old\n"
    assert (backup / "vault" / "old-note.md").read_text(encoding="utf-8") == "preservar"
    with sqlite3.connect(new / "vault" / ".cronos" / "memory.sqlite3") as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("SELECT note FROM memory").fetchone()[0] == "registrada"
    assert json.loads((new / ".cronos-migracao-concluida.json").read_text(encoding="utf-8"))["schema"] == 1


def test_uses_separate_data_home_from_old_install_pointer(tmp_path: Path) -> None:
    old = tmp_path / "old"
    data = tmp_path / "private-data"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    _old_install(data)
    (data / "DADOS-CRONOS.json").write_text('{"schema": 1}\n', encoding="utf-8")
    (old / ".cronos-local").mkdir()
    (old / ".cronos-local" / "data-home.json").write_text(
        json.dumps({"home": str(data)}), encoding="utf-8"
    )

    migrate(old, new)

    assert "GEMINI_API_KEY=fake-test-secret" in (new / ".env").read_text(encoding="utf-8")
    assert (new / "vault" / "anotacao.md").is_file()


def test_missing_vault_fails_without_modifying_destination(tmp_path: Path) -> None:
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    (old / ".env").write_text("GEMINI_API_KEY=untouched\n", encoding="utf-8")
    (new / ".env").write_text("KEEP=yes\n", encoding="utf-8")

    try:
        migrate(old, new)
    except ValueError as exc:
        assert "vault" in str(exc)
    else:
        raise AssertionError("migration should reject a source without a vault")
    assert (new / ".env").read_text(encoding="utf-8") == "KEEP=yes\n"
