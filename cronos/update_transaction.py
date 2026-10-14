"""Standard-library transactional code installer; also copied outside the app by the supervisor."""
import hashlib
import json
import os
import re
import shutil
import stat
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

PROTECTED = {'update_transaction.py', 'supervisor.py'}
PRIVATE_NAMES={'api_keys.json','fish_audio.json','ai_council.json','credentials.json','token.json','providers.json'}
MAX_BYTES = 512 * 1024 * 1024


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as out:
        json.dump(data, out, ensure_ascii=False)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, path)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


def regular(path):
    """Reject Windows reparse points as well as symlinks on every existing component."""
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if not part.exists() and not part.is_symlink():
            continue
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
            raise ValueError('Atualização recusada: link simbólico ou junction no caminho.')
    return path


def inventory(folder):
    folder = regular(folder)
    files = {}
    for path in folder.rglob('*'):
        regular(path)
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            relative = path.relative_to(folder).as_posix()
            with path.open('rb') as source:
                files[relative] = hashlib.file_digest(source,'sha256').hexdigest()
    return files


def dependency_contract(data):
    try:
        parsed=tomllib.loads(data.decode('utf-8'))
        project=parsed.get('project',{})
        return {key:project.get(key) for key in ('requires-python','dependencies','optional-dependencies')}|{'build-system':parsed.get('build-system')}
    except (ValueError,UnicodeDecodeError,AttributeError):
        raise ValueError('Manifesto de dependências inválido.') from None


def prepare_archive(archive, target, installed):
    """Extract code only, never .env, vault, personality, executable scripts or dependencies."""
    target, installed = regular(target), regular(installed)
    if target.exists():
        raise ValueError('A pasta de preparação já existe.')
    target.mkdir(parents=True)
    size, seen, root_name = 0, set(), None
    try:
        with zipfile.ZipFile(archive) as package:
            if len(package.infolist()) > 100000:
                raise ValueError('Pacote excede o limite de arquivos.')
            for item in package.infolist():
                name = item.filename
                parts = PurePosixPath(name).parts
                if any(p.split('.')[0].casefold() in {'con','prn','aux','nul',*[f'com{i}' for i in range(1,10)],*[f'lpt{i}' for i in range(1,10)]} for p in parts):
                    raise ValueError('Nome reservado do Windows no pacote.')
                if not parts or name.startswith('/') or '\\' in name or ':' in name or any(p in {'.', '..'} or p.endswith((' ', '.')) for p in parts):
                    raise ValueError('Caminho inválido no pacote.')
                if root_name is None: root_name = parts[0]
                if parts[0] != root_name:
                    raise ValueError('Pacote sem raiz única.')
                mode = item.external_attr >> 16
                if stat.S_ISLNK(mode): raise ValueError('Links não são aceitos no pacote.')
                relative = PurePosixPath(*parts[1:])
                if item.is_dir() or not relative.parts: continue
                key = str(relative).casefold()
                if key in seen: raise ValueError('Caminhos duplicados no pacote.')
                seen.add(key)
                size += item.file_size
                if size > MAX_BYTES: raise ValueError('Pacote excede 512 MB descompactado.')
                if str(relative) == 'pyproject.toml':
                    if item.file_size>512*1024:raise ValueError('Manifesto de dependências excessivo.')
                    if dependency_contract(package.read(item)) != dependency_contract((installed/'pyproject.toml').read_bytes()):
                        raise ValueError('Esta atualização muda dependências: requer instalador completo, não atualização automática.')
                    continue
                if relative.parts[0] != 'cronos' or len(relative.parts) < 2: continue
                if any(p.startswith('.') or p == '__pycache__' for p in relative.parts):
                    raise ValueError('Arquivo privado no código do pacote.')
                if relative.parts[1] in PROTECTED or relative.name.casefold() in PRIVATE_NAMES: continue
                destination = regular(target/Path(*relative.parts))
                destination.parent.mkdir(parents=True, exist_ok=True)
                with package.open(item) as src, destination.open('wb') as out:
                    shutil.copyfileobj(src, out, 1024*1024)
        if 'pyproject.toml' not in seen:raise ValueError('O pacote não informa as dependências.')
        validate_candidate(target)
        return inventory(target/'cronos')
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise


def validate_candidate(target):
    target = Path(target)
    for required in ('app.py', 'browser.py', 'engine.py', 'config.py', 'ui/index.html'):
        if not (target/'cronos'/required).is_file():
            raise ValueError('Pacote incompleto: falta '+required)
    for path in (target/'cronos').rglob('*.py'):
        # Compilation does not import/execute candidate code or contact a provider.
        compile(path.read_bytes(), str(path), 'exec')
    html = (target/'cronos/ui/index.html').read_text(encoding='utf-8')
    for asset in re.findall(r'(?:src|href)="(?:\./)?(assets/[^"?]+)', html):
        if not (target/'cronos/ui'/asset).is_file(): raise ValueError('Bundle da interface incompleto.')


def managed_files(root):
    return {name: digest for name, digest in inventory(Path(root)/'cronos').items()
            if name.split('/')[0] not in PROTECTED and not any(p.startswith('.') for p in Path(name).parts) and Path(name).name.casefold() not in PRIVATE_NAMES}


def apply(root, transaction):
    root, transaction = regular(root), regular(transaction)
    metadata = read_json(transaction/'prepared.json')
    if not metadata or inventory(transaction/'candidate/cronos') != metadata['candidate']:
        raise ValueError('A cópia preparada mudou depois da verificação.')
    if managed_files(root) != metadata['baseline']:
        raise ValueError('A instalação mudou desde a preparação. Prepare novamente antes de atualizar.')
    folded={p.casefold():p for p in metadata['baseline']}
    if any(p.casefold() in folded and folded[p.casefold()]!=p for p in metadata['candidate']):
        raise ValueError('Renomeação apenas de maiúsculas/minúsculas requer instalador completo.')
    before = metadata['baseline']
    backup = transaction/'backup/cronos'
    if backup.exists(): raise ValueError('Esta transação já possui backup; não pode ser reutilizada.')
    if shutil.disk_usage(root).free < sum((root/'cronos'/p).stat().st_size for p in before)*2 + 64*1024*1024:
        raise ValueError('Espaço livre insuficiente para backup e instalação.')
    for relative in before:
        source = regular(root/'cronos'/relative)
        destination = regular(backup/relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    if inventory(backup) != before: raise ValueError('A verificação do backup falhou; instalação preservada.')
    write_json(transaction/'journal.json', {'phase': 'applying', 'before': before, 'after': metadata['candidate']})
    for relative in metadata['candidate']:
        destination = regular(root/'cronos'/relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = regular(transaction/'install-file.tmp')
        shutil.copy2(transaction/'candidate/cronos'/relative, temporary)
        os.replace(temporary, destination)
    for relative in before.keys()-metadata['candidate'].keys():
        regular(root/'cronos'/relative).unlink()
    for path in (root/'cronos').rglob('*.pyc'): regular(path).unlink()
    write_json(transaction/'journal.json', {'phase': 'testing', 'before': before, 'after': metadata['candidate']})


def restore(root, transaction):
    root, transaction = regular(root), regular(transaction)
    journal = read_json(transaction/'journal.json')
    if not journal: return False
    backup = transaction/'backup/cronos'
    if inventory(backup) != journal['before']:
        raise ValueError('Backup inconsistente; arquivos preservados para recuperação manual.')
    for relative in journal['before']:
        destination = regular(root/'cronos'/relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = regular(transaction/'restore-file.tmp')
        shutil.copy2(backup/relative, temporary)
        os.replace(temporary, destination)
    for relative in journal['after'].keys()-journal['before'].keys():
        regular(root/'cronos'/relative).unlink(missing_ok=True)
    # Never let stale bytecode mask the restored source.
    for path in (root/'cronos').rglob('*.pyc'): regular(path).unlink()
    write_json(transaction/'journal.json', {**journal, 'phase':'restored'})
    return True


def snapshot_private(root, transaction):
    """Local recovery copies, never included in model context or downloaded packages."""
    root, transaction = regular(root), regular(transaction)
    paths = ['.env']
    config=regular(root/'config')
    if config.exists():paths += [str(p.relative_to(root)) for p in config.glob('*.json') if p.is_file()]
    saved=[]
    for relative in paths:
        source=regular(root/relative)
        if source.is_file():
            destination=regular(transaction/'private-snapshot'/relative)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,destination)
            if os.name!='nt':destination.chmod(0o600)
            saved.append(relative)
    write_json(transaction/'private-snapshot.json',saved)


def restore_private(root, transaction):
    for relative in read_json(Path(transaction)/'private-snapshot.json',[]):
        if relative!='.env' and not re.fullmatch(r'config/[^/\\]+\.json',relative):
            raise ValueError('Destino privado de recuperação inválido.')
        destination=regular(Path(root)/relative)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(regular(Path(transaction)/'private-snapshot'/relative),destination)


def restore_memory(transaction):
    """Restore only the app-created consistent snapshot, with the app fully stopped."""
    info=read_json(Path(transaction)/'memory-backup.json')
    if not info:return
    vault=regular(info['vault'])
    if not re.fullmatch(r'memory-[0-9-]+-[0-9a-f]{8}\.zip',info['name']):
        raise ValueError('Nome de backup inválido.')
    archive=regular(vault/'.cronos/backups'/info['name'])
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            relative=PurePosixPath(item.filename)
            if item.is_dir():continue
            if (relative.is_absolute() or '..' in relative.parts or '\\' in item.filename or ':' in item.filename
                    or (str(relative)!='.cronos/memory.sqlite3' and relative.suffix!='.md')):
                raise ValueError('Caminho inválido no backup da memória.')
            destination=regular(vault/Path(*relative.parts));destination.parent.mkdir(parents=True,exist_ok=True)
            with package.open(item) as source,destination.open('wb') as output:shutil.copyfileobj(source,output)
    for suffix in ('-wal','-shm'):
        regular(vault/'.cronos'/('memory.sqlite3'+suffix)).unlink(missing_ok=True)
