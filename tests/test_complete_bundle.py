import importlib.util
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('bundle_start',ROOT/'tools/start_bundle.py')
start=importlib.util.module_from_spec(spec);spec.loader.exec_module(start)


def install(path):
    for name in ('.env','cronos/app.py','.venv/Scripts/python.exe','.venv/Scripts/pythonw.exe'):
        p=path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('private-preserved' if name=='.env' else '')
    return path


def test_unique_existing_install_is_found_without_keys_or_memory_read(tmp_path):
    source=tmp_path/'Downloads/new';source.mkdir(parents=True)
    old=install(tmp_path/'Downloads/old')
    assert start.discover(source,[tmp_path/'Downloads'])==[old]
    assert (old/'.env').read_text()=='private-preserved'


def test_multiple_installs_are_not_guessed(tmp_path):
    source=tmp_path/'new';source.mkdir()
    a=install(tmp_path/'old-a');b=install(tmp_path/'wrapped/old-b')
    assert start.discover(source,[tmp_path])==[a,b]


def test_current_configured_folder_has_priority(tmp_path):
    source=install(tmp_path/'current');install(tmp_path/'other')
    assert start.discover(source,[tmp_path])==[source]


def test_unknown_folder_rejected_before_start(tmp_path):
    with pytest.raises(ValueError):start.update_and_launch(tmp_path/'new',tmp_path/'unknown',launch=lambda *a,**k:None)


def test_old_installation_is_updated_and_opened_with_its_own_environment(tmp_path,monkeypatch):
    source=tmp_path/'new';target=install(tmp_path/'old');calls=[]
    monkeypatch.setattr(start,'apply',lambda a,b:calls.append(('apply',a,b)))
    start.update_and_launch(source,target,launch=lambda args,**kw:calls.append(('launch',args,kw)))
    assert calls[0]==('apply',source,target)
    assert calls[1][1]==[str(target/'.venv/Scripts/pythonw.exe'),'-m','cronos.supervisor']
    assert calls[1][2]['cwd']==str(target) and 'shell' not in calls[1][2]
    assert (target/'.env').read_text()=='private-preserved'


def test_cached_supervisor_is_reused_and_current_folder_not_overlaid(tmp_path,monkeypatch):
    target=install(tmp_path/'current');runner=target/'.cronos-local/updater/runner.py';runner.parent.mkdir(parents=True);runner.write_text('')
    monkeypatch.setattr(start,'apply',lambda *a:pytest.fail('do not update source onto itself'))
    calls=[];start.update_and_launch(target,target,launch=lambda args,**kw:calls.append(args))
    assert calls[0]==[str(target/'.venv/Scripts/pythonw.exe'),str(runner),'--run',str(target)]


def test_complete_zip_has_runtime_and_starts_using_existing_data(tmp_path):
    import json,subprocess,zipfile
    archive_path=ROOT/'releases/CRONOS-Completo-Um-Arquivo.zip'
    package=tmp_path/'complete';package.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        names=set(archive.namelist())
        assert {'ABRIR-CRONOS.bat','Criar-Atalho-Cronos.vbs','tools/start_bundle.py','tools/launch_bundle.vbs','cronos/app.py','cronos/ui/index.html','cronos/documents.py','cronos/eye-ui/index.html','cronos/studio/service.py','cronos/studio/product-3d.js','cronos/studio/bridge.js'}<=names
        assert {'cronos/studio/directions.py','cronos/studio/image_generation.py','cronos/studio/restaurant.py','cronos/studio/media/restaurant-fire.jpg'}<=names
        assert {'cronos/studio/provider_pool.py','cronos/integrations.py','cronos/providers.py'}<=names
        assert {'cronos/studio/composition.py','cronos/studio/references.py','cronos/studio/threed/config.py','cronos/studio/threed/models.py',
                'cronos/studio/threed/generator.py','cronos/studio/threed/pricing_config.py','cronos/studio/threed/integration.py',
                'cronos/studio/threed/templates/basic.html','cronos/studio/threed/templates/standard.html','cronos/studio/threed/templates/premium.html',
                'cronos/studio/threed/vendor/three-0.128.0.min.js','cronos/studio/threed/vendor/orbit-controls-0.128.0.js','cronos/studio/threed/vendor/gsap-3.11.4.min.js',
                'cronos/studio/mistral_original/generator.py.txt','cronos/studio/mistral_original/SHA256.json',
                'examples/3d-product-demo/index.html','examples/3d-product-demo/vendor/three-0.128.0.min.js','docs/INTEGRACAO-MISTRAL-3D.md'} <= names
        assert not any(p.endswith('.zip') or p=='.env' or p.startswith(('vault/','.venv/','.cronos-local/','config/providers.json')) for p in names)
        archive.extractall(package)
    target=install(tmp_path/'old-with-data');memory=target/'vault/Temas/notas.md';memory.parent.mkdir(parents=True);memory.write_text('saved notes')
    integrations=target/'config/providers.json';integrations.parent.mkdir();integrations.write_text('{"saved":true}')
    code="""import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tools'))
import start_bundle
calls=[]
start_bundle.update_and_launch(Path(sys.argv[1]),Path(sys.argv[2]),launch=lambda args,**kw:calls.append(args))
assert len(calls)==1 and calls[0][0].endswith('pythonw.exe')
print('PASS: complete package updated the selected installation and requested launch without shell')
"""
    result=subprocess.run([sys.executable,'-c',code,str(package),str(target)],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    assert (target/'.env').read_text()=='private-preserved'
    assert memory.read_text()=='saved notes' and integrations.read_text()=='{"saved":true}'
    assert (target/'cronos/documents.py').is_file()
