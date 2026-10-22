"""Build one runtime ZIP from tracked code; never copy local env, vault or venv."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXTRA=['docs/INTEGRACAO-MISTRAL-3D.md','docs/STUDIO_DE_SITES.md','ABRIR-CRONOS.bat','Instalar-Cronos.bat','MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat','Criar-Atalho-Cronos.vbs','LEIA-PRIMEIRO.txt','tools/migrate_local_data.py','tools/apply_interface_update.py','tools/interface_update_manifest.json']


def build_patch():
    manifest=json.loads((ROOT/'tools/interface_update_manifest.json').read_text())
    names=[*manifest['files'],'tools/apply_interface_update.py','tools/interface_update_manifest.json','Atualizar-Cronos-Preservando-Dados.bat','Criar-Atalho-Cronos.vbs']
    output=ROOT/'releases/CRONOS-Atualizacao-Preservando-Dados.zip';output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as package:
        for name in names:package.write(ROOT/name,name)
        package.writestr('LEIA-PRIMEIRO.txt',(ROOT/'docs/ATUALIZAR_SEM_RECADASTRAR.md').read_text())


def build():
    build_patch()
    tracked=subprocess.check_output(['git','ls-files','-z','--','cronos','modelos','config/providers.example.json','.env.example','pyproject.toml'],cwd=ROOT).decode().split('\0')
    manifest=json.loads((ROOT/'tools/interface_update_manifest.json').read_text())
    ui_assets={p.relative_to(ROOT).as_posix() for p in (ROOT/'cronos/ui/assets').rglob('*') if p.is_file()}
    names=sorted(name for name in set(filter(None,tracked))|set(EXTRA)|set(manifest['files'])|ui_assets if (ROOT/name).is_file())
    names=sorted(set(names)|{p.relative_to(ROOT).as_posix() for p in (ROOT/'examples/3d-product-demo').rglob('*') if p.is_file()})
    for name in names:
        parts=Path(name).parts
        if any(p in {'.env','.venv','vault','.cronos-local','__pycache__'} for p in parts):raise ValueError('Arquivo local privado recusado: '+name)
        if name.startswith('config/') and name!='config/providers.example.json':raise ValueError('Configuracao privada recusada.')
    output=ROOT/'releases/CRONOS-Completo-Um-Arquivo.zip';output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as package:
        for name in names:package.write(ROOT/name,name)
    with zipfile.ZipFile(output) as package:
        if package.testzip():raise ValueError('Falha de integridade do ZIP.')
        manifest=json.loads(package.read('tools/interface_update_manifest.json'))
        for name,expected in manifest['files'].items():
            if hashlib.sha256(package.read(name)).hexdigest()!=expected:raise ValueError('Pacote inconsistente: '+name)
    return output,len(names)


if __name__=='__main__':
    output,count=build();print(json.dumps({'file':str(output),'files':count,'size_bytes':output.stat().st_size}))
