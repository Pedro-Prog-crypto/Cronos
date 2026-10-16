"""Code overlay must preserve real installation data and recover changed code."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('local_update',Path(__file__).resolve().parents[1]/'tools/apply_interface_update.py')
updater=importlib.util.module_from_spec(spec);spec.loader.exec_module(updater)


def fixture(tmp_path):
    source=tmp_path/'new';target=tmp_path/'installed'
    for root in (source,target):(root/'cronos/ui').mkdir(parents=True)
    (source/'tools').mkdir()
    (target/'cronos/app.py').write_text('old=True\n')
    (target/'cronos/ui/index.html').write_text('old interface')
    (source/'cronos/app.py').write_text('new=True\n')
    (source/'cronos/documents.py').write_text('new_document=True\n')
    (source/'cronos/ui/index.html').write_text('new interface')
    personal={'.env':b'PRIVATE_KEY=unchanged','config/providers.json':b'{"private":"kept"}','vault/.cronos/memory.sqlite3':b'private-memory','vault/Temas/math.md':b'Notas do usuario','cronos/unknown-personal-data.txt':b'keep even data inside code folder','.cronos-local/preferences.json':b'{"custom":true}', 'vault/.cronos/studio/projects.sqlite3':b'private-studio-projects', 'modelos/personalidades/cronos.md':b'personalidade personalizada'}
    for name,data in personal.items():
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    files={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/'cronos').rglob('*') if p.is_file()}
    (source/'tools/interface_update_manifest.json').write_text(json.dumps({'files':files}))
    return source,target,personal


def test_installer_changes_only_manifest_code_preserving_all_personal_data(tmp_path):
    source,target,personal=fixture(tmp_path)
    backup=updater.apply(source,target)
    assert (target/'cronos/app.py').read_text()=='new=True\n'
    assert (target/'cronos/documents.py').exists()
    assert (backup/'cronos/app.py').read_text()=='old=True\n'
    assert json.loads((backup/'journal.json').read_text())['state']=='completed'
    assert all((target/name).read_bytes()==data for name,data in personal.items())
    assert not (backup/'.env').exists()


def test_incomplete_or_changed_package_is_rejected_before_install(tmp_path):
    source,target,personal=fixture(tmp_path)
    (source/'cronos/app.py').write_text('tampered=True\n')
    with pytest.raises(ValueError,match='incompleto ou alterado'):updater.apply(source,target)
    assert (target/'cronos/app.py').read_text()=='old=True\n'
    assert all((target/name).read_bytes()==data for name,data in personal.items())


def test_failure_during_overlay_restores_old_code_and_removes_only_new_files(tmp_path,monkeypatch):
    source,target,personal=fixture(tmp_path)
    replace=updater.os.replace
    def fail_on_html(src,dest):
        if str(dest).endswith('index.html'):raise OSError('simulated disk failure')
        replace(src,dest)
    monkeypatch.setattr(updater.os,'replace',fail_on_html)
    with pytest.raises(OSError,match='simulated'):updater.apply(source,target)
    assert (target/'cronos/app.py').read_text()=='old=True\n'
    assert (target/'cronos/ui/index.html').read_text()=='old interface'
    assert not (target/'cronos/documents.py').exists()
    assert all((target/name).read_bytes()==data for name,data in personal.items())


@pytest.mark.parametrize('name',['.env','config/providers.json','cronos/../.env','cronos/providers.json'])
def test_manifest_cannot_replace_private_data(tmp_path,name):
    source,target,personal=fixture(tmp_path)
    manifest=source/'tools/interface_update_manifest.json'
    manifest.write_text(json.dumps({'files':{name:'0'*64}}))
    with pytest.raises(ValueError):updater.apply(source,target)
    assert all((target/key).read_bytes()==data for key,data in personal.items())


def test_wrong_installation_or_same_folder_is_rejected(tmp_path):
    source,target,_=fixture(tmp_path)
    with pytest.raises(ValueError):updater.apply(source,source)
    (target/'.env').unlink()
    with pytest.raises(ValueError,match='pasta do Cronos'):updater.apply(source,target)


def test_shipped_manifest_verifies_real_payload():
    root=Path(__file__).resolve().parents[1]
    payload=updater.entries(root)
    assert {'cronos/app.py','cronos/documents.py','cronos/security.py','cronos/engine.py','cronos/prospects.py','cronos/studio/__init__.py','cronos/studio/service.py','cronos/studio/routes.py','cronos/studio/runtime.py','cronos/studio/catalog.py','cronos/studio/store.py','cronos/studio/validation.py','cronos/studio/network.py','cronos/studio/images.py','cronos/studio/bridge.js','cronos/studio/product-3d.js','cronos/ui/index.html'} <= payload.keys()
    assert any(name.startswith('cronos/ui/assets/SiteStudio-') for name in payload)
    assert {'cronos/studio/directions.py','cronos/studio/image_generation.py','cronos/studio/restaurant.py','cronos/studio/media/restaurant-fire.jpg'} <= payload.keys()


def test_downloadable_package_runs_as_a_standalone_updater(tmp_path):
    import subprocess,sys,zipfile
    root=Path(__file__).resolve().parents[1]
    package=tmp_path/'download';package.mkdir()
    with zipfile.ZipFile(root/'releases/CRONOS-Atualizacao-Preservando-Dados.zip') as archive:archive.extractall(package)
    _,target,personal=fixture(tmp_path/'installation')
    result=subprocess.run([sys.executable,str(package/'tools/apply_interface_update.py'),str(target)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
    assert (target/'cronos/documents.py').is_file()
    assert (target/'cronos/ui/index.html').read_bytes()==(root/'cronos/ui/index.html').read_bytes()
    assert all((target/name).read_bytes()==data for name,data in personal.items())
