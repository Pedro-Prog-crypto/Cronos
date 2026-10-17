"""One-file bootstrap: preserve the selected data, update once, open that root.

Injected payload is a fixed, hashed code-only package. Subsequent launches never
reapply it, so this launcher cannot undo a future Cronos update.
"""
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

PAYLOAD_SHA256 = '__PAYLOAD_SHA256__'
PAYLOAD_BASE64 = '''__PAYLOAD_BASE64__'''


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def unpack(destination, encoded=PAYLOAD_BASE64, checksum=PAYLOAD_SHA256):
    raw=base64.b64decode(encoded,validate=False)
    if hashlib.sha256(raw).hexdigest()!=checksum:raise ValueError('O iniciador esta incompleto ou alterado. Baixe novamente; seus dados nao foram modificados.')
    destination=Path(destination)
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        infos=package.infolist()
        if len(infos)>300 or sum(i.file_size for i in infos)>60*1024*1024:raise ValueError('Pacote interno invalido.')
        for info in infos:
            path=PurePosixPath(info.filename)
            if path.is_absolute() or any(part in {'.','..'} or ':' in part or '\\' in part for part in path.parts):raise ValueError('Caminho interno invalido.')
            if not info.filename.startswith(('cronos/','tools/')):raise ValueError('Pacote interno fora do codigo permitido.')
            target=destination.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(package.read(info))
    updater=load('data_launcher_updater',destination/'tools/apply_interface_update.py')
    updater.entries(destination)
    return updater


def launch(root, popen=subprocess.Popen):
    root=Path(root).absolute()
    python=root/'.venv/Scripts/pythonw.exe'
    if not python.is_file():raise ValueError('Nao encontrei o ambiente Python desta instalacao. Seus dados estao preservados; execute novamente com o Python 3.11 ou mais recente instalado.')
    return popen([str(python),'-m','cronos.supervisor'],cwd=str(root),creationflags=0x08000000 if os.name=='nt' else 0)


def ensure_environment(root, run=subprocess.run):
    python=root/'.venv/Scripts/python.exe'
    if not python.is_file():
        print('Preparando o ambiente Python desta pasta. Isso nao altera suas APIs ou memorias.',flush=True)
        run([sys.executable,'-m','venv',str(root/'.venv')],check=True)
    elif not (root/'.venv/Scripts/pythonw.exe').is_file():
        raise ValueError('O ambiente .venv esta incompleto. Seus dados nao foram apagados; restaure o Python desta instalacao.')
    probe=[str(python),'-c','import fastapi,uvicorn,httpx,PIL,dotenv,fish_audio_sdk,google.genai,yt_dlp']
    result=run(probe,cwd=str(root),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    if result.returncode:
        if not (root/'pyproject.toml').is_file():raise ValueError('A pasta esta sem pyproject.toml. Escolha a pasta completa do Cronos, nao somente a pasta de dados.')
        print('Instalando dependencias que faltam; esta etapa pode precisar de internet.',flush=True)
        run([str(python),'-m','pip','install','-e',str(root)],cwd=str(root),check=True)
        run(probe,cwd=str(root),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)


def prepare(root, source, updater, backup):
    """Only the first successful use overlays code; no secrets/path settings edited."""
    root=Path(root).absolute()
    updater.regular(root)
    if not (root/'.env').is_file() or not (root/'cronos/app.py').is_file():raise ValueError('Escolha a pasta do Cronos que contem .env e a pasta cronos.')
    marker=updater.regular(root/'.cronos-local/data-launcher/installed.json')
    if marker.exists():
        saved=json.loads(marker.read_text(encoding='utf-8'))
        if saved.get('installed_once') is not True:raise ValueError('O registro do iniciador esta incompleto; seus dados foram preservados.')
        return None
    files=updater.entries(source)
    changed=any(not (root/name).is_file() or updater.digest(root/name)!=digest for name,digest in files.items())
    snapshot=None
    if changed:
        print('Salvando suas APIs, memorias e integracoes antes de atualizar. Aguarde.',flush=True)
        with updater.stopped(root):snapshot,_=backup(root)
        print('Backup dos seus dados concluido:',snapshot,flush=True)
        print('Esse backup contem dados privados; nao compartilhe.',flush=True)
        updater.apply(source,root)
    marker.parent.mkdir(parents=True,exist_ok=True)
    document={'installed_once':True,'revision':json.loads((source/'tools/interface_update_manifest.json').read_text())['revision'],
              'data_backup':str(snapshot) if snapshot else None,
              'note':'Novas memorias usam o cofre da instalacao escolhida. Este iniciador nao reaplica uma versao antiga.'}
    temporary=marker.with_suffix('.tmp');temporary.write_text(json.dumps(document,ensure_ascii=True,indent=2),encoding='utf-8');os.replace(temporary,marker)
    return snapshot


def main():
    if sys.version_info<(3,11):raise ValueError('Este iniciador precisa de Python 3.11 ou mais recente. Nenhum dado foi alterado.')
    if len(sys.argv)!=2:raise ValueError('Escolha a pasta completa do Cronos, com .env e a pasta cronos.')
    root=Path(sys.argv[1]).absolute()
    print('ABRIR CRONOS COM MEUS DADOS\nA pasta escolhida sera usada para as APIs, integracoes e novas memorias.\n',flush=True)
    with tempfile.TemporaryDirectory(prefix='cronos-data-launcher-') as folder:
        source=Path(folder);updater=unpack(source)
        rescue=load('data_launcher_backup',source/'tools/rescue_installation.py')
        prepare(root,source,updater,rescue.snapshot)
        ensure_environment(root)
    launch(root)
    print('Abrindo o Cronos atualizado com os dados desta pasta. Use sempre este iniciador.\nNao apague a pasta escolhida.',flush=True)
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        print('Nao foi possivel abrir:',str(error),flush=True)
        print('Mantenha a pasta original e os backups. Nao recadastre nem compartilhe suas chaves.',flush=True)
        sys.exit(1)
