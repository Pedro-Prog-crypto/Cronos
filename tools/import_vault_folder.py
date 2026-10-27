"""Merge a copied memory vault into this installation without overwriting notes."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

from cronos.storage import Memory


def _same_bytes(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as a, right.open("rb") as b:
        while True:
            aa, bb = a.read(1024 * 1024), b.read(1024 * 1024)
            if aa != bb:
                return False
            if not aa:
                return True


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _destination_name(target: Path, source: Path) -> Path:
    digest = _digest(source)[:10]
    return target.with_name(f"{target.stem}-importado-{digest}{target.suffix}")


def _vault_root(source: Path) -> Path:
    nested = source / "vault"
    if nested.is_dir():
        return nested.resolve(strict=True)
    return source


def merge_vault(source: Path, target: Path) -> dict[str, int | bool]:
    source = source.expanduser().resolve(strict=True)
    target = target.expanduser().resolve()
    source = _vault_root(source)
    if not source.is_dir() or source == target or source in target.parents or target in source.parents:
        raise ValueError("Selecione a pasta do vault; a origem e o vault ativo precisam ser pastas diferentes.")

    files: list[Path] = []
    skipped_sqlite = 0
    for folder, dirs, filenames in os.walk(source, followlinks=False):
        parent = Path(folder)
        for name in list(dirs):
            if (parent / name).is_symlink():
                raise ValueError("A origem contém um link de pasta. Remova-o e tente novamente; nenhum arquivo foi importado.")
        for name in filenames:
            path = parent / name
            if path.is_symlink():
                raise ValueError("A origem contém um link de arquivo. Remova-o e tente novamente; nenhum arquivo foi importado.")
            if name.lower().endswith(("-wal", "-shm", ".sqlite", ".sqlite3", ".db")):
                skipped_sqlite += 1
                continue
            files.append(path)

    if not files and not skipped_sqlite:
        raise ValueError("A pasta nao contem arquivos para importar. Copie o vault para Dados-Para-Importar.")

    target.mkdir(parents=True, exist_ok=True)
    added = unchanged = renamed = 0
    for original in files:
        relative = original.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.is_file() and _same_bytes(original, destination):
                unchanged += 1
                continue
            base = _destination_name(destination, original)
            destination = base
            suffix = 2
            identical_alternate = False
            while destination.exists():
                if destination.is_file() and _same_bytes(original, destination):
                    unchanged += 1
                    identical_alternate = True
                    break
                destination = base.with_name(f"{base.stem}-{suffix}{base.suffix}")
                suffix += 1
            if identical_alternate:
                continue
            renamed += 1  # Keep both versions; never overwrite a conflict.
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".cronos-import-", dir=destination.parent, delete=False) as temp:
                temporary_name = Path(temp.name)
            shutil.copy2(original, temporary_name)
            os.replace(temporary_name, destination)
            added += 1
        finally:
            if temporary_name is not None:
                temporary_name.unlink(missing_ok=True)

    memory = Memory(target)
    memory.sync_notes()
    return {"added": added, "unchanged": unchanged, "renamed": renamed,
            "indexed_notes": memory.stats()["indexed_notes"], "sqlite_skipped": skipped_sqlite}


def main() -> int:
    parser = argparse.ArgumentParser(description="Mescla arquivos de um vault sem sobrescrever as notas atuais.")
    parser.add_argument("--source", type=Path, required=True, help="Pasta Dados-Para-Importar ou seu subdiretorio vault")
    parser.add_argument("--target", type=Path, default=Path("vault"), help="Vault ativo do Cronos")
    args = parser.parse_args()
    try:
        report = merge_vault(args.source, args.target)
    except (OSError, ValueError) as exc:
        print("Importacao nao concluida: " + str(exc))
        return 1
    print(f"Memorias mescladas: {report['added']} arquivos novos; {report['renamed']} conflitos preservados com outro nome.")
    print(f"Notas indexadas: {report['indexed_notes']}; arquivos ja existentes: {report['unchanged']}.")
    if report["sqlite_skipped"]:
        print("Banco de dados SQLite antigo preservado na origem, mas nao mesclado. Para migrar historico e integracoes, use MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat.")
    print("A origem foi mantida. O Cronos ja pode buscar as notas Markdown importadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
