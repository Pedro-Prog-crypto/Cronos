"""Build one complete public source/runtime ZIP without local user data."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CURRENT_REPORTS=['CRONOS_AUDIT_REPORT.md','CRONOS_FIX_LOG.md','CRONOS_TEST_RESULTS.md','CRONOS_PERFORMANCE_REPORT.md','CRONOS_REMAINING_ISSUES.md','docs/VOZ-E-STUDIO-2026-11-04-R38.md','docs/TRANSCRICAO-AO-VIVO-2026-11-04-R37.md','docs/RESERVAS-E-RESPOSTAS-2026-11-04-R36.md','docs/STUDIO-COMERCIAL-2026-11-04-R35.md','docs/RESPOSTAS-2026-11-01-R13.md','docs/VERIFICACAO-2026-11-01-R13.json','docs/SIMULACOES-RESPOSTAS-2026-11-01-R13.json','ENCERRAR-CRONOS.bat','docs/SEGUNDO-PLANO-2026-10-31-R12.md','docs/VERIFICACAO-2026-10-31-R12.json','docs/JANELA-ABERTA-E-VOZ-2026-10-31-R11.md','docs/VERIFICACAO-2026-10-31-R11.json']
EXTRA=['docs/ENTREGA-REAL-2026-10-30-R10.md','docs/VERIFICACAO-2026-10-30-R10.json','docs/RECONHECIMENTO-2026-10-30-R9.md','docs/VERIFICACAO-2026-10-30-R9.json','docs/ENTREGA-DE-VOZ-2026-10-29-R8.md','docs/VERIFICACAO-2026-10-29-R8.json','docs/RESPOSTAS-2026-10-29-R7.md','docs/VERIFICACAO-2026-10-29-R7.json','docs/VELOCIDADE-2026-10-29.md','docs/VERIFICACAO-VELOCIDADE-2026-10-29.json','docs/VERIFICACAO-2026-10-28.json','docs/REVISAO-2026-10-28.md','docs/INTEGRACAO-MISTRAL-3D.md','docs/STUDIO_DE_SITES.md','ABRIR-CRONOS.bat','Instalar-Cronos.bat','MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat','IMPORTAR-DADOS-PARA-CRONOS.bat','Criar-Atalho-Cronos.vbs','LEIA-PRIMEIRO.txt','tools/migrate_local_data.py','tools/import_vault_folder.py','tools/apply_interface_update.py','tools/start_bundle.py','tools/launch_bundle.vbs','tools/interface_update_manifest.json']


def build_patch():
    manifest=json.loads((ROOT/'tools/interface_update_manifest.json').read_text())
    names=[*manifest['files'],'tools/apply_interface_update.py','tools/interface_update_manifest.json','Atualizar-Cronos-Preservando-Dados.bat','Criar-Atalho-Cronos.vbs']
    output=ROOT/'releases/CRONOS-Atualizacao-Preservando-Dados.zip';output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as package:
        for name in names:package.write(ROOT/name,name)
        package.writestr('LEIA-PRIMEIRO.txt',(ROOT/'docs/ATUALIZAR_SEM_RECADASTRAR.md').read_text())


def build():
    build_patch()
    # A "complete" download must also contain the editable frontend, tests,
    # scripts and vendored sources. Earlier releases bundled only the runtime.
    # Release artifacts are excluded to avoid nesting old installers in this one.
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    manifest=json.loads((ROOT/'tools/interface_update_manifest.json').read_text())
    ui_assets={p.relative_to(ROOT).as_posix() for p in (ROOT/'cronos/ui/assets').rglob('*') if p.is_file()}
    names=sorted(name for name in set(filter(None,tracked))|set(EXTRA)|set(CURRENT_REPORTS)|ui_assets|set(manifest['files'])|{'tools/restore_existing_data.py'} if not name.startswith('releases/') and (ROOT/name).is_file())
    names=sorted(set(names)|{p.relative_to(ROOT).as_posix() for p in (ROOT/'examples/3d-product-demo').rglob('*') if p.is_file()})
    for name in names:
        parts=Path(name).parts
        if any(p in {'.env','.venv','vault','.cronos-local','__pycache__','node_modules','.git'} for p in parts):raise ValueError('Arquivo local privado recusado: '+name)
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
