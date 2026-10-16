"""Local code-only overlay. No network, credential parsing or memory migration."""
import contextlib
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import sys
import time
import uuid

PRIVATE={'providers.json','api_keys.json','credentials.json','token.json','fish_audio.json','ai_council.json'}


def regular(path):
    path=Path(path).absolute()
    for component in (path,*path.parents):
        if not component.exists() and not component.is_symlink():continue
        info=component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:
            raise ValueError('Caminho com link ou junction recusado.')
    return path


def digest(path):
    with Path(path).open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()


def entries(source):
    manifest=json.loads((source/'tools/interface_update_manifest.json').read_text(encoding='utf-8'))
    result={}
    for name,expected in manifest['files'].items():
        path=PurePosixPath(name)
        bundled_image = path.suffix == '.jpg' and str(path.parent) in {'cronos/studio/media', 'cronos/ui/assets'}
        bundled_reference = (name.startswith('cronos/studio/mistral_original/') and path.suffix in {'.txt','.json'}) or (str(path.parent) == 'cronos/studio/threed/vendor' and path.suffix in {'.txt','.json'})
        if (not name.startswith('cronos/') or '\\' in name or ':' in name or any(p.startswith('.') for p in path.parts)
            or path.name.lower() in PRIVATE or not (path.suffix in {'.py','.js','.css','.html'} or bundled_image or bundled_reference)):
            raise ValueError('O manifesto inclui um destino fora do codigo permitido.')
        origin=regular(source/name)
        if not origin.is_file() or digest(origin)!=expected:raise ValueError('Pacote incompleto ou alterado: '+name)
        if path.suffix=='.py':compile(origin.read_bytes(),name,'exec')
        result[name]=expected
    if not result or 'cronos/ui/index.html' not in result:raise ValueError('Pacote sem interface.')
    return result


@contextlib.contextmanager
def stopped(target):
    folder=regular(target/'.cronos-local/updater');folder.mkdir(parents=True,exist_ok=True)
    lock=regular(folder/'supervisor.lock').open('a+b');locked=False
    deadline=time.monotonic()+20
    try:
        while not locked:
            try:
                if os.name=='nt':
                    import msvcrt
                    lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
                    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                locked=True
            except OSError:
                (folder/'stop.request').write_text('stop',encoding='ascii')
                if time.monotonic()>deadline:raise ValueError('Feche o Cronos e tente novamente. O servidor ainda esta ativo.')
                time.sleep(.25)
        yield
    finally:
        if locked and os.name=='nt':
            import msvcrt
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
        lock.close()


def apply(source,target):
    source,target=regular(source),regular(target)
    if source==target:raise ValueError('Escolha a instalacao antiga que ja possui suas configuracoes, nao a pasta baixada.')
    if not (target/'cronos/app.py').is_file() or not (target/'.env').is_file():
        raise ValueError('Escolha a pasta do Cronos que voce ja usa, com .env e a pasta cronos. Nao selecione uma pasta nova.')
    files=entries(source)
    # All destinations and existing components checked before making any replacements.
    for name in files:regular(target/name)
    with stopped(target):
        backup=regular(target/'.cronos-local/manual-updates'/time.strftime('%Y%m%d-%H%M%S')/uuid.uuid4().hex[:8]);backup.mkdir(parents=True)
        before={name:digest(target/name) if (target/name).is_file() else None for name in files}
        for name,previous in before.items():
            if previous is not None:
                saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target/name,saved)
                if digest(saved)!=previous:raise ValueError('Falha ao verificar backup; codigo original preservado.')
        journal={'files':before,'state':'prepared'}
        (backup/'journal.json').write_text(json.dumps(journal,indent=2),encoding='utf-8')
        replaced=[]
        try:
            for name,expected in files.items():
                dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
                temporary=dest.with_name(dest.name+'.update-'+uuid.uuid4().hex)
                try:
                    shutil.copy2(source/name,temporary)
                    if digest(temporary)!=expected:raise ValueError('Falha ao verificar arquivo: '+name)
                    os.replace(temporary,dest);replaced.append(name)
                finally:temporary.unlink(missing_ok=True)
            for name,expected in files.items():
                if digest(target/name)!=expected:raise ValueError('Verificacao final falhou: '+name)
            journal['state']='completed'
        except BaseException:
            for name in reversed(replaced):
                if before[name] is None:(target/name).unlink(missing_ok=True)
                else:shutil.copy2(backup/name,target/name)
            journal['state']='restored'
            (backup/'journal.json').write_text(json.dumps(journal,indent=2),encoding='utf-8')
            raise
        (backup/'journal.json').write_text(json.dumps(journal,indent=2),encoding='utf-8')
        return backup


if __name__=='__main__':
    try:
        if len(sys.argv)!=2:raise ValueError('Informe a pasta da instalacao atual.')
        saved=apply(Path(__file__).resolve().parents[1],Path(sys.argv[1]))
        print('Atualizacao concluida. APIs, .env, config, cofre, preferencias e memorias nao foram substituidos.')
        print('Backup dos arquivos de codigo alterados: '+str(saved))
        print('Abra pelo Iniciar-Cronos-Web.bat da instalacao atual e pressione Ctrl+F5 no navegador.')
    except Exception as error:
        print('Nao foi possivel atualizar: '+str(error));sys.exit(1)
