"""Apply the ZIP appended to instalador.bat directly to an installed Cronos.

This script is executed from the BAT's ZIP by the existing Cronos Python. It
never extracts a second ZIP or a second complete application directory.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import time
import uuid
from zipfile import ZipFile


PRIVATE = {'providers.json', 'api_keys.json', 'credentials.json', 'token.json',
           'fish_audio.json', 'ai_council.json'}
REVISION = 'cronos-interface-referencia-2026-11-15-r58'


def regular(path: Path) -> Path:
    path = Path(path).absolute()
    for component in (path, *path.parents):
        if not component.exists() and not component.is_symlink():
            continue
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
            raise ValueError('Caminho com link ou junction recusado.')
    return path


def digest_stream(source) -> str:
    digest = hashlib.sha256()
    while part := source.read(1024 * 1024):
        digest.update(part)
    return digest.hexdigest()


def digest_path(path: Path) -> str:
    with path.open('rb') as source:
        return digest_stream(source)


def validate_name(name: str) -> None:
    path = PurePosixPath(name)
    image = path.suffix in {'.jpg', '.png', '.webp'} and str(path.parent) in {'cronos/studio/media', 'cronos/ui/assets'}
    hand = str(path.parent) == 'cronos/ui/assets' and path.suffix in {'.wasm', '.data', '.tflite', '.binarypb'}
    reference = (name.startswith('cronos/studio/mistral_original/') and path.suffix in {'.txt', '.json'}) or (str(path.parent) == 'cronos/studio/threed/vendor' and path.suffix in {'.txt', '.json'})
    runtime = name.startswith(('cronos/ui/assets/', 'cronos/ui/cesium/', 'cronos/ui/licenses/')) and path.suffix.lower() in {'.js', '.mjs', '.cjs', '.css', '.html', '.json', '.txt', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.wasm', '.data', '.tflite', '.binarypb', '.woff', '.woff2', '.xml'}
    if (not name.startswith('cronos/') or '\\' in name or ':' in name
            or any(part.startswith('.') for part in path.parts) or path.name.lower() in PRIVATE
            or not (path.suffix in {'.py', '.js', '.css', '.html'} or image or hand or reference or runtime)):
        raise ValueError('O pacote inclui um destino fora do codigo permitido: ' + name)


@contextmanager
def stopped(target: Path):
    folder = regular(target / '.cronos-local/updater')
    folder.mkdir(parents=True, exist_ok=True)
    lock = regular(folder / 'supervisor.lock').open('a+b')
    locked = False
    deadline = time.monotonic() + 20
    try:
        while not locked:
            try:
                if os.name == 'nt':
                    import msvcrt
                    lock.seek(0)
                    lock.write(b'0')
                    lock.flush()
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                (folder / 'stop.request').write_text('stop', encoding='ascii')
                if time.monotonic() > deadline:
                    raise ValueError('Feche o Cronos e tente novamente. O servidor ainda esta ativo.')
                time.sleep(.25)
        yield
    finally:
        if locked and os.name == 'nt':
            import msvcrt
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        lock.close()


def apply(archive_path: Path, target: Path) -> tuple[Path | None, int]:
    archive_path = regular(archive_path).resolve(strict=True)
    target = regular(target).resolve(strict=True)
    if not (target / 'cronos/app.py').is_file() or not (target / '.env').is_file():
        raise ValueError('Escolha a pasta Cronos-R50 instalada, com .env e a subpasta cronos.')
    with ZipFile(archive_path) as package:
        if package.testzip() is not None:
            raise ValueError('Download incompleto ou alterado; nada foi atualizado.')
        manifest_bytes = package.read('tools/interface_update_manifest.json')
        manifest = json.loads(manifest_bytes)
        if manifest.get('revision') != REVISION:
            raise ValueError('Esta nao e a revisao R58 verificada.')
        files = manifest['files']
        if 'cronos/ui/index.html' not in files:
            raise ValueError('Pacote sem a interface do Cronos.')
        infos = {info.filename: info for info in package.infolist()}
        for name, expected in files.items():
            validate_name(name)
            if name not in infos or not isinstance(expected, str) or len(expected) != 64:
                raise ValueError('Pacote incompleto: ' + name)
            with package.open(name) as source:
                if digest_stream(source) != expected:
                    raise ValueError('Arquivo alterado no pacote: ' + name)
            if name.endswith('.py'):
                compile(package.read(name), name, 'exec')
            regular(target / name)
        before = {name: digest_path(target / name) if (target / name).is_file() else None for name in files}
        changed = [name for name, expected in files.items() if before[name] != expected]
        current_manifest = target / 'tools/interface_update_manifest.json'
        regular(current_manifest)
        manifest_changed = not current_manifest.is_file() or current_manifest.read_bytes() != manifest_bytes
        if not changed and not manifest_changed:
            return None, 0

        # Only changed code is backed up or written. The large, unchanged R50
        # runtime never takes a second copy on the user's disk.
        backup_bytes = sum((target / name).stat().st_size for name in changed if before[name] is not None)
        if manifest_changed and current_manifest.is_file():
            backup_bytes += current_manifest.stat().st_size
        growth = sum(infos[name].file_size for name in changed if before[name] is None)
        growth += sum(max(0, infos[name].file_size - (target / name).stat().st_size)
                      for name in changed if before[name] is not None)
        largest = max((infos[name].file_size for name in changed), default=0)
        required = backup_bytes + growth + largest + 8 * 1024 * 1024
        available = shutil.disk_usage(target).free
        if available < required:
            needed_mb = (required - available + 1048575) // 1048576
            raise ValueError(f'Espaco insuficiente na unidade do Cronos. Libere pelo menos {needed_mb} MB e tente novamente; nenhum arquivo foi alterado.')

        with stopped(target):
            backup = regular(target / '.cronos-local/manual-updates' / datetime.now().strftime('%Y%m%d-%H%M%S') / uuid.uuid4().hex[:8])
            backup.mkdir(parents=True)
            for name in changed:
                if before[name] is None:
                    continue
                saved = backup / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target / name, saved)
                if digest_path(saved) != before[name]:
                    raise ValueError('Falha no backup; nenhum codigo foi substituido.')
            if manifest_changed and current_manifest.is_file():
                saved = backup / 'tools/interface_update_manifest.json'
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current_manifest, saved)
            journal = {'revision': REVISION, 'files': {name: before[name] for name in changed}, 'state': 'prepared'}
            (backup / 'journal.json').write_text(json.dumps(journal, indent=2), encoding='utf-8')
            replaced = []
            manifest_replaced = False
            try:
                for name in changed:
                    destination = target / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    temporary = destination.with_name(destination.name + '.update-' + uuid.uuid4().hex)
                    try:
                        with package.open(name) as source, temporary.open('wb') as output:
                            shutil.copyfileobj(source, output, 1024 * 1024)
                        if digest_path(temporary) != files[name]:
                            raise ValueError('Arquivo alterado durante a copia: ' + name)
                        os.replace(temporary, destination)
                        replaced.append(name)
                    finally:
                        temporary.unlink(missing_ok=True)
                if manifest_changed:
                    current_manifest.parent.mkdir(parents=True, exist_ok=True)
                    temporary = current_manifest.with_name(current_manifest.name + '.update-' + uuid.uuid4().hex)
                    try:
                        temporary.write_bytes(manifest_bytes)
                        os.replace(temporary, current_manifest)
                        manifest_replaced = True
                    finally:
                        temporary.unlink(missing_ok=True)
                journal['state'] = 'completed'
            except BaseException:
                if manifest_replaced:
                    saved = backup / 'tools/interface_update_manifest.json'
                    if saved.is_file():
                        shutil.copy2(saved, current_manifest)
                    else:
                        current_manifest.unlink(missing_ok=True)
                for name in reversed(replaced):
                    destination = target / name
                    if before[name] is None:
                        destination.unlink(missing_ok=True)
                    else:
                        shutil.copy2(backup / name, destination)
                journal['state'] = 'restored'
                (backup / 'journal.json').write_text(json.dumps(journal, indent=2), encoding='utf-8')
                raise
            (backup / 'journal.json').write_text(json.dumps(journal, indent=2), encoding='utf-8')
            return backup, len(changed)


def main() -> int:
    try:
        archive = Path(os.environ['CRONOS_PATCH_SELF'])
        target = Path(os.environ['CRONOS_PATCH_TARGET'])
        backup, count = apply(archive, target)
        if backup is None:
            print('O Cronos R58 ja esta atualizado; nenhum arquivo foi copiado.')
        else:
            print(f'Atualizacao concluida: {count} arquivos de codigo. Backup em {backup}.')
        print('Integracoes, .env, provedores, cofre e memorias preservados na pasta original.')
        return 0
    except Exception as error:
        print('Atualizacao nao concluida: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__' or 'CRONOS_PATCH_SELF' in os.environ:
    raise SystemExit(main())
