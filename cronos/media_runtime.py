"""Verified portable JavaScript runtime for public media URL resolution."""
import hashlib,os,platform,shutil,subprocess,zipfile
from pathlib import Path
import httpx
STATE=Path(__file__).resolve().parent.parent/'.cronos-local'/'media-runtime'
VERSION='24.14.0'

def node_executable():
    candidate=shutil.which('node')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    if candidate:
        try:
            version=subprocess.check_output([candidate,'--version'],creationflags=flags,timeout=5).decode().strip()
            if int(version.lstrip('v').split('.')[0])>=20:return candidate
        except (OSError,ValueError,subprocess.SubprocessError):pass
    if os.name!='nt':raise RuntimeError('Node.js 20 ou superior é necessário para os serviços do Olho de Deus.')
    arch='arm64' if platform.machine().lower() in {'arm64','aarch64'} else 'x64'
    name=f'node-v{VERSION}-win-{arch}';target=STATE/'runtime'/name/'node.exe'
    if target.is_file():return str(target)
    STATE.mkdir(parents=True,exist_ok=True);archive=STATE/(name+'.zip');base=f'https://nodejs.org/dist/v{VERSION}/'
    try:
        with httpx.Client(timeout=60,follow_redirects=False) as client:
            sums=client.get(base+'SHASUMS256.txt');sums.raise_for_status()
            expected=next(line.split()[0] for line in sums.text.splitlines() if line.split()[-1]==name+'.zip')
            digest=hashlib.sha256()
            with client.stream('GET',base+name+'.zip') as response:
                response.raise_for_status();size=0
                with archive.open('wb') as output:
                    for chunk in response.iter_bytes():
                        size+=len(chunk)
                        if size>80*1024*1024:raise ValueError('Runtime acima do limite esperado')
                        digest.update(chunk);output.write(chunk)
            if digest.hexdigest()!=expected:raise ValueError('Checksum inválido do runtime Node')
        destination=STATE/'runtime';destination.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as package:
            for entry in package.infolist():
                path=(destination/entry.filename).resolve()
                if not path.is_relative_to(destination.resolve()):raise ValueError('Caminho inválido no runtime')
            package.extractall(destination)
        return str(target)
    finally:archive.unlink(missing_ok=True)


if __name__=='__main__':
    node_executable()
    print('Runtime de mídia preparado.')
