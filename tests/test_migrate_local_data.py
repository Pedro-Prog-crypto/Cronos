import json
import sqlite3
from pathlib import Path

from tools.migrate_local_data import migrate
from tools.import_vault_folder import merge_vault


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


def test_imports_designated_drop_folder_inside_new_install_and_keeps_source(tmp_path: Path) -> None:
    new = tmp_path / "new"
    drop = new / "Dados-Para-Importar"
    _old_install(drop)
    (new / "config").mkdir(parents=True)
    (new / "config" / "providers.example.json").write_text('{}\n', encoding="utf-8")
    (new / ".env").write_text("DESTINATION_ONLY=preservar-no-backup\n", encoding="utf-8")
    (new / "vault").mkdir()
    (new / "vault" / "nota-atual.md").write_text("memoria atual", encoding="utf-8")

    backup = migrate(drop, new)

    assert "GEMINI_API_KEY=fake-test-secret" in (new / ".env").read_text(encoding="utf-8")
    assert "CRONOS_VAULT=vault" in (new / ".env").read_text(encoding="utf-8")
    assert (new / "vault" / "anotacao.md").read_text(encoding="utf-8") == "memoria importante"
    assert (drop / ".env").is_file()
    assert (drop / "vault" / "anotacao.md").is_file()
    assert (backup / ".env").read_text(encoding="utf-8") == "DESTINATION_ONLY=preservar-no-backup\n"
    assert (backup / "vault" / "nota-atual.md").read_text(encoding="utf-8") == "memoria atual"


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


def test_vault_drop_merges_notes_without_overwriting_and_indexes_new_notes(tmp_path: Path) -> None:
    source = tmp_path / "Dados-Para-Importar" / "vault"
    target = tmp_path / "Cronos" / "vault"
    (source / "Temas").mkdir(parents=True)
    (target / "Temas").mkdir(parents=True)
    (source / "Temas" / "Biologia.md").write_text("# Biologia\nCélulas e genética", encoding="utf-8")
    (target / "Temas" / "Biologia.md").write_text("# Biologia\nAnotação local atual", encoding="utf-8")
    (source / "Memorias").mkdir()
    (source / "Memorias" / "Estudo.md").write_text("# Estudo\nAmitose e divisão celular", encoding="utf-8")

    report = merge_vault(source.parent, target)

    assert report["added"] == 2
    assert report["renamed"] == 1
    assert report["indexed_notes"] >= 3
    assert (target / "Temas" / "Biologia.md").read_text(encoding="utf-8") == "# Biologia\nAnotação local atual"
    assert list((target / "Temas").glob("Biologia-importado-*.md"))
    assert (target / "Memorias" / "Estudo.md").is_file()
    from cronos.storage import Memory
    assert any(hit["path"] == "Memorias/Estudo.md" for hit in Memory(target).search("amitose"))

    repeated = merge_vault(source.parent, target)
    assert repeated["added"] == 0
    assert repeated["unchanged"] == 2
    assert repeated["renamed"] == 0
