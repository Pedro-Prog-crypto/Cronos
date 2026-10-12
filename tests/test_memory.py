import json
from pathlib import Path
from uuid import uuid4

import pytest

from cronos.memory import Memory


def test_storage_does_not_trim_large_history(tmp_path):
    memory = Memory(tmp_path / "vault")
    session = uuid4()
    for i in range(12):
        memory.record(session, f"{i}:" + "pergunta " * 1500, "resposta " * 1500, [])
    history = Memory(memory.vault).history(session)
    assert len(history) == 24
    assert sum(len(m["content"]) for m in history) > 200000
    assert history[0]["content"] == "0:" + "pergunta " * 1500
    assert history[-1]["content"] == "resposta " * 1500


def test_recall_indexes_manual_content_and_updates(tmp_path):
    memory = Memory(tmp_path / "vault")
    manual = memory.vault / "Estudos"
    manual.mkdir()
    note = manual / "aula.md"
    note.write_text("# Anotações\nMinha mãe se chama Helena.\n", encoding="utf-8")
    matches = memory.search("como minha mae se chama")
    assert matches[0]["path"] == "Estudos/aula.md"
    assert "Helena" in matches[0]["excerpt"]
    note.write_text("# Anotações\nMinha mãe se chama Maria Helena.\n", encoding="utf-8")
    assert "Maria Helena" in memory.recall("mãe")
    note.unlink()
    assert memory.search("mãe") == []


def test_aliases_and_existing_manual_notes_are_preserved(tmp_path):
    vault = tmp_path / "vault"
    (vault / "Temas").mkdir(parents=True)
    old = vault / "Temas/Sócrates.md"
    original = "# Sócrates\nMeu texto pessoal que deve continuar intacto.\n"
    old.write_text(original, encoding="utf-8")
    memory = Memory(vault)
    first = memory.record(uuid4(), "Sócrates?", "Resposta", [{"title": "Socrates", "summary": "Discussão filosófica.", "aliases": ["Sócrates de Atenas"]}])
    second = memory.record(uuid4(), "E Sócrates?", "Resposta", [{"title": "Sócrates de Atenas", "summary": "Novas ideias.", "aliases": []}])
    assert first == second == ["Temas/Sócrates.md"]
    assert old.read_text().startswith(original)
    assert "Discussão filosófica" in old.read_text() and "Novas ideias" in old.read_text()
    assert len(list((vault / "Temas").glob("*.md"))) == 1
    assert memory.search("Socrates")


def test_failed_markdown_export_is_recoverable_and_idempotent(tmp_path, monkeypatch):
    memory = Memory(tmp_path / "vault")
    session = uuid4()
    original = Path.write_text
    def blocked(path, *args, **kwargs):
        if path.name.startswith("tema-") and path.name.endswith(".cronos-tmp"):
            raise PermissionError("Simulação: arquivo temporariamente bloqueado pelo editor")
        return original(path, *args, **kwargs)
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "write_text", blocked)
        files = memory.record(session, "Mensagem", "Resposta", [{"title": "Tema", "summary": "Registro específico"}])
        assert memory.stats()["pending_exports"] == 1
        assert memory.warnings
        assert len(memory.history(session)) == 2
    recovered = Memory(memory.vault)
    assert recovered.stats()["pending_exports"] == 0
    assert (memory.vault / files[0]).read_text().count("Registro específico") == 1
    recovered.flush_exports()
    assert (memory.vault / files[0]).read_text().count("Registro específico") == 1


def test_old_json_history_is_imported_once_without_changes(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".cronos").mkdir(parents=True)
    session = uuid4()
    original = json.dumps([{"role": "user", "content": "Histórico antigo"}, {"role": "assistant", "content": "Resposta antiga"}])
    source = vault / ".cronos" / f"{session}.json"
    source.write_text(original)
    assert len(Memory(vault).history(session)) == 2
    assert len(Memory(vault).history(session)) == 2
    assert source.read_text() == original


def test_read_note_rejects_traversal_and_internal_database(tmp_path):
    memory = Memory(tmp_path / "vault")
    with pytest.raises(ValueError):
        memory.read_note("../external.md")
    with pytest.raises(ValueError):
        memory.read_note(".cronos/memory.sqlite3")
    assert memory.search('" OR *; DROP TABLE turns; --') == []
    assert memory.stats()["messages"] == 0


def test_recent_topic_update_is_retrieved_after_a_long_history(tmp_path):
    memory = Memory(tmp_path / "vault")
    memory.record(uuid4(), "Projeto", "Resposta", [{"title": "Projeto Cronos", "summary": "Status anterior: planejado. " * 500}])
    memory.record(uuid4(), "Atualização", "Resposta", [{"title": "Projeto Cronos", "summary": "Status atual: primeira versão funcionando."}])
    recall = memory.recall("Projeto Cronos")
    assert "Status atual: primeira versão funcionando" in recall


def test_legacy_cronos_topic_folder_is_reused_without_duplicate(tmp_path):
    vault = tmp_path / "vault"
    old_folder = vault / "CRONOS/Temas"
    old_folder.mkdir(parents=True)
    original = old_folder / "Sócrates.md"
    original.write_text("# Sócrates\nTexto da versão antiga.\n", encoding="utf-8")
    memory = Memory(vault)
    files = memory.record(uuid4(), "Socrates?", "Resposta", [{"title": "Socrates", "summary": "Discussão nova"}])
    assert files == ["CRONOS/Temas/Sócrates.md"]
    assert original.read_text().startswith("# Sócrates\nTexto da versão antiga.")
    assert not list((vault / "Temas").glob("*.md"))
