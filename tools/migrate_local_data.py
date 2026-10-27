"""One-time local migration of a user's private Cronos data into this bundle."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
from urllib.parse import quote
import uuid

MARKER = "DADOS-CRONOS.json"


def _env(path: Path) -> tuple[str, dict[str, str]]:
    content = path.read_text(encoding="utf-8-sig")
    values: dict[str, str] = {}
    for line in content.splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if not match:
            continue
        value = match.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[match.group(1)] = value
    return content, values


def _data_root(selected: Path) -> Path:
    pointer = selected / ".cronos-local" / "data-home.json"
    if pointer.is_file():
        try:
            home = json.loads(pointer.read_text(encoding="utf-8"))["home"]
            candidate = Path(home).expanduser()
            if not candidate.is_absolute():
                candidate = selected / candidate
            candidate = candidate.resolve(strict=True)
            if (candidate / MARKER).is_file() and (candidate / ".env").is_file() and (candidate / "vault").is_dir():
                return candidate
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            raise ValueError("A pasta de dados indicada pela versão antiga está incompleta. Nada foi copiado.") from None
        raise ValueError("A pasta de dados indicada pela versão antiga não passou na verificação. Nada foi copiado.")
    return selected


def _configured_path(raw: str | None, bases: tuple[Path, ...]) -> Path | None:
    if not raw:
        return None
    value = Path(os.path.expandvars(raw)).expanduser()
    options = (value,) if value.is_absolute() else tuple(base / value for base in bases)
    for option in options:
        try:
            resolved = option.resolve(strict=True)
        except OSError:
            continue
        if resolved.exists():
            return resolved
    return None


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
        try:
            with source.open("rb") as handle:
                is_sqlite = handle.read(16) == b"SQLite format 3\x00"
        except OSError:
            is_sqlite = False
        if is_sqlite:
            uri = "file:" + quote(source.as_posix(), safe="/") + "?mode=ro"
            src = sqlite3.connect(uri, uri=True, timeout=30)
            dst = sqlite3.connect(destination, timeout=30)
            try:
                src.backup(dst, sleep=0.1)
                result = dst.execute("PRAGMA integrity_check").fetchone()[0]
                if result != "ok":
                    raise ValueError(f"O banco {source.name} não passou na verificação; migração interrompida.")
            finally:
                dst.close()
                src.close()
            return
    shutil.copy2(source, destination)


def _copy_tree(source: Path, destination: Path) -> None:
    source = source.resolve(strict=True)
    destination.mkdir(parents=True, exist_ok=True)
    for folder, dirs, files in os.walk(source, followlinks=False):
        parent = Path(folder)
        relative = parent.relative_to(source)
        target_dir = destination / relative
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in list(dirs):
            child = parent / name
            if child.is_symlink():
                raise ValueError("O vault contém um link simbólico. Migração interrompida sem alterar os originais.")
        for name in files:
            child = parent / name
            if child.is_symlink():
                raise ValueError("O vault contém um link simbólico. Migração interrompida sem alterar os originais.")
            if name.lower().endswith(("-wal", "-shm")):
                continue  # SQLite databases are copied with the online backup API.
            _copy_file(child, target_dir / name)


def migrate(selected: Path, target: Path) -> Path:
    selected = selected.expanduser().resolve(strict=True)
    target = target.expanduser().resolve(strict=True)
    # A designated drop folder inside the new installation is safe: migration
    # only replaces .env, vault, providers and personality, never this source.
    # Arbitrary nested folders remain rejected to avoid selecting live data.
    drop_folder = (target / "Dados-Para-Importar").resolve()
    if selected == target or selected in target.parents or (target in selected.parents and selected != drop_folder):
        raise ValueError("Escolha a pasta da versão antiga. Ela não pode ser a pasta nova nem conter a pasta nova.")

    data = _data_root(selected)
    env_source = data / ".env"
    if not env_source.is_file():
        env_source = selected / ".env"
    if not env_source.is_file():
        raise ValueError("Não encontrei o .env na versão antiga ou no cofre de dados dela.")
    env_text, values = _env(env_source)
    bases = (data, selected, env_source.parent)

    vault = _configured_path(values.get("CRONOS_VAULT"), bases)
    if not vault or not vault.is_dir():
        vault = next((candidate.resolve() for candidate in (data / "vault", selected / "vault") if candidate.is_dir()), None)
    if not vault or not vault.is_dir():
        raise ValueError("Não encontrei o vault da versão antiga; nada foi alterado.")

    providers = _configured_path(values.get("CRONOS_PROVIDERS_FILE"), bases)
    if not providers or not providers.is_file():
        providers = next((candidate.resolve() for candidate in (data / "config" / "providers.json", selected / "config" / "providers.json") if candidate.is_file()), None)
    personality = _configured_path(values.get("CRONOS_PERSONALITY"), bases)
    if not personality or not personality.is_file():
        personality = next((candidate.resolve() for candidate in (data / "modelos" / "personalidades" / "cronos.md", selected / "modelos" / "personalidades" / "cronos.md") if candidate.is_file()), None)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    stage = target / (".cronos-migracao-tmp-" + uuid.uuid4().hex[:8])
    backup = target / ".cronos-migracao-backups" / stamp
    stage.mkdir()
    try:
        # Stage and validate all incoming files before moving any destination data.
        cleaned = [line for line in env_text.splitlines() if not re.match(
            r"^\s*(?:export\s+)?(?:CRONOS_DATA_HOME|CRONOS_VAULT|CRONOS_PROVIDERS_FILE|CRONOS_PERSONALITY)\s*=", line, re.I)]
        cleaned.extend(("CRONOS_VAULT=vault", "CRONOS_PROVIDERS_FILE=config/providers.json",
                        "CRONOS_PERSONALITY=modelos/personalidades/cronos.md"))
        (stage / ".env").write_text("\n".join(cleaned) + "\n", encoding="utf-8")
        _copy_tree(vault, stage / "vault")
        if providers:
            _copy_file(providers, stage / "config" / "providers.json")
        else:
            example = target / "config" / "providers.example.json"
            if example.is_file() and not (target / "config" / "providers.json").exists():
                _copy_file(example, stage / "config" / "providers.json")
        if personality:
            _copy_file(personality, stage / "modelos" / "personalidades" / "cronos.md")

        destinations = [".env", "vault"]
        if (stage / "config" / "providers.json").is_file():
            destinations.append("config/providers.json")
        if (stage / "modelos" / "personalidades" / "cronos.md").is_file():
            destinations.append("modelos/personalidades/cronos.md")
        moved: list[str] = []
        backup.mkdir(parents=True, exist_ok=True)
        try:
            for relative in destinations:
                dest, incoming, saved = target / relative, stage / relative, backup / relative
                if dest.exists():
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(dest, saved)
                moved.append(relative)
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.replace(incoming, dest)
        except Exception:
            for relative in reversed(moved):
                dest, saved = target / relative, backup / relative
                if dest.is_dir():
                    shutil.rmtree(dest)
                elif dest.exists():
                    dest.unlink()
                if saved.exists():
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(saved, dest)
            raise
        marker = target / ".cronos-migracao-concluida.json"
        marker.write_text(json.dumps({"schema": 1, "completed_at": datetime.now().astimezone().isoformat()}, indent=2), encoding="utf-8")
        return backup
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Copia localmente APIs, integrações e vault para esta instalação do Cronos.")
    parser.add_argument("--source", type=Path, help="Pasta antiga; se omitida, abre o seletor de pastas do Windows.")
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1]
    try:
        source = args.source
        if source is None:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            source_name = filedialog.askdirectory(title="Escolha a versão antiga do Cronos (feche-a antes)")
            root.destroy()
            if not source_name:
                print("Migração cancelada. Nenhum arquivo foi alterado.")
                return 2
            source = Path(source_name)
        backup = migrate(source, target)
        print("Migração concluída: .env, integrações e vault copiados para esta pasta.")
        print("O backup dos dados que já estavam aqui foi guardado em .cronos-migracao-backups.")
        print("A versão antiga foi mantida intacta. Agora abra ABRIR-CRONOS.bat.")
        return 0
    except Exception as exc:
        print("Migração não concluída: " + str(exc))
        print("A pasta antiga foi mantida; confira o backup antes de tentar novamente.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
