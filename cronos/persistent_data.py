"""Permanent local data, independent of the selected code installation.

Stdlib only: also loaded by the single-file Windows importer before dependencies
are installed. No credentials or file contents go into its public status files.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
from uuid import uuid4

MARKER = 'DADOS-CRONOS.json'
POINTER = '.cronos-local/data-home.json'


def checked(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.stat(), 'st_file_attributes', 0) & 1024):
            raise ValueError('A pasta de dados precisa ser uma pasta real, sem links ou junctions.')
    return path


def write_json(path, value):
    path = checked(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def validate(home):
    home = checked(home)
    try:
        info = json.loads(checked(home / MARKER).read_text(encoding='utf-8'))
        if info.get('schema') != 1 or info.get('complete') is not True:
            raise ValueError()
        if not checked(home / '.env').is_file() or not checked(home / 'vault').is_dir():
            raise ValueError()
    except (OSError, ValueError):
        raise ValueError('A pasta permanente esta incompleta. Mantenha os originais; nao sera criado um cofre vazio por cima.') from None
    return home


@contextmanager
def locked(path):
    path = checked(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        try:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0); handle.write(b'0'); handle.flush(); handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise BlockingIOError('Outra abertura/importacao do Cronos esta em andamento. Aguarde e tente novamente.') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def default_home():
    documents = Path.home() / 'Documents'
    if os.name == 'nt':
        # Windows redirects Documents to OneDrive or another drive. Do not guess.
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
            documents = Path(buffer.value)
    return documents / 'Cronos-Dados'


def selected_home(root, default=None):
    pointer = checked(Path(root) / POINTER)
    if pointer.exists():
        return validate(json.loads(pointer.read_text(encoding='utf-8'))['home'])
    return checked(default if default is not None else default_home())


def activate(root):
    """Run all relative .env/config writes against the permanent data folder."""
    explicit = os.getenv('CRONOS_DATA_HOME')
    pointer = checked(Path(root) / POINTER)
    if not explicit and not pointer.exists():
        return None
    home = validate(explicit) if explicit else selected_home(root)
    os.environ['CRONOS_DATA_HOME'] = str(home)
    os.chdir(home)
    return home


def import_data(root, home, rescue):
    """Snapshot first, publish once; never merge an old installation over live data."""
    root, home = checked(root), checked(home)
    if root == home or home.is_relative_to(root) or root.is_relative_to(home):
        raise ValueError('Cronos-Dados deve ficar fora das pastas de versao do programa.')
    with locked(home.parent / ('.' + home.name + '-import.lock')):
        if (home / MARKER).exists():
            validate(home)
            write_json(root / POINTER, {'home': str(home)})
            return home, None
        if home.exists() and any(home.iterdir()):
            raise ValueError('Ja existe uma pasta Cronos-Dados sem registro de importacao completa. Nada foi substituido.')
        configured = dict(rescue.env_paths(root))
        originals = {
            'CRONOS_VAULT': root / 'vault',
            'CRONOS_PROVIDERS_FILE': root / 'config/providers.json',
            'CRONOS_PERSONALITY': root / 'modelos/personalidades/cronos.md',
        }
        originals.update(configured)
        if not originals['CRONOS_VAULT'].is_dir():
            raise ValueError('Nao encontrei o cofre de memorias da pasta escolhida. Selecione a instalacao que contem seus dados atuais.')
        for key, path in originals.items():
            checked(path)
            if key in configured and not path.exists():
                raise ValueError('Um caminho configurado nao existe: ' + key + '. Confira a pasta original; importacao interrompida.')
        backup, report = rescue.snapshot(root)
        if not report.get('complete'):
            raise ValueError('O backup nao foi concluido. A importacao foi interrompida.')
        stage = home.with_name(home.name + '-importando-' + uuid4().hex[:8])
        stage.mkdir(mode=0o700)
        try:
            # Copy only from the verified snapshot, including consistent SQLite/WAL.
            for name in ('config', 'modelos'):
                source = backup / 'instalacao' / name
                if source.exists(): shutil.copytree(source, stage / name)
            destinations = {'CRONOS_VAULT': 'vault', 'CRONOS_PROVIDERS_FILE': 'config/providers.json',
                            'CRONOS_PERSONALITY': 'modelos/personalidades/cronos.md'}
            for key, origin in originals.items():
                source = (backup / 'instalacao' / origin.relative_to(root) if origin.is_relative_to(root)
                          else backup / 'dados-externos' / key)
                destination = stage / destinations[key]
                if source.is_dir(): shutil.copytree(source, destination, dirs_exist_ok=True)
                elif source.is_file():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            (stage / 'vault').mkdir(exist_ok=True)
            env = (backup / 'instalacao/.env').read_text(encoding='utf-8-sig')
            # Preserve every API/model setting; change only data locations.
            env = '\n'.join(line for line in env.splitlines() if not re.match(
                r'^\s*(?:export\s+)?(?:CRONOS_VAULT|CRONOS_PROVIDERS_FILE|CRONOS_PERSONALITY|CRONOS_DATA_HOME)\s*=', line))
            for key, relative in destinations.items():
                env += '\n' + key + '=' + json.dumps((home / relative).as_posix(), ensure_ascii=False)
            (stage / '.env').write_text(env + '\n', encoding='utf-8')
            if os.name != 'nt': (stage / '.env').chmod(0o600)
            local = backup / 'instalacao/.cronos-local'
            if local.exists():
                shutil.copytree(local, stage / '.cronos-local', ignore=shutil.ignore_patterns(
                    'updater', 'manual-updates', 'data-launcher', 'data-home.json'))
            write_json(stage / MARKER, {'schema': 1, 'complete': True, 'imported_from': str(root), 'backup': str(backup)})
            (stage / 'LEIA-ME.txt').write_text(
                'DADOS PERMANENTES DO CRONOS\nAPIs: .env e config. Memorias e projetos: vault.\n'
                'Use ABRIR-CRONOS-COM-MEUS-DADOS.bat para escolher a versao do programa.\n'
                'Novas versoes reutilizam esta pasta sem importar dados antigos por cima.\n'
                'Nao apague nem compartilhe esta pasta: ela contem suas chaves e memorias.\n'
                'Os originais e o backup completo foram mantidos.\n', encoding='utf-8')
            if home.exists(): home.rmdir()  # Only an empty, previously checked folder.
            os.replace(stage, home)
        except Exception:
            # Leave failed imports clearly separate; never publish or delete originals.
            (stage / 'IMPORTACAO-INCOMPLETA.txt').write_text('Nao use esta pasta. Originais e backup preservados.\n', encoding='utf-8')
            raise
        write_json(root / POINTER, {'home': str(home)})
        return validate(home), backup
