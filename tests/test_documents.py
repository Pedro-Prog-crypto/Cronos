import base64
import io
import zipfile
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.documents import inspect_document
from test_backend import settings,AUTH


def packed(files):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as out:
        for name,text in files.items():out.writestr(name,text)
    return data.getvalue()


def test_zip_is_read_only_and_private_files_are_excluded():
    raw=packed({'project/main.py':'print("ok")','project/.env':'API_KEY=PRIVATE','project/config/providers.json':'PRIVATE','project/data.png':b'\0\xff'})
    result=inspect_document('project.zip',raw)
    assert [f['name'] for f in result['files']]==['project/main.py']
    assert len(result['skipped'])==3 and 'PRIVATE' not in str(result)
    redacted=inspect_document('config.txt',b'api_key="dont_send_me"\nprint(1)')
    assert 'dont_send_me' not in str(redacted) and 'print(1)' in str(redacted)


@pytest.mark.parametrize('files',[{'../escape.py':'print(1)'},{'big.py':'x'* (2*1024*1024+1)}, {f'{i}.py':'x' for i in range(121)}])
def test_zip_limits_and_paths_are_enforced(files):
    with pytest.raises(ValueError):inspect_document('project.zip',packed(files))


def test_document_unsupported_and_context_limit():
    with pytest.raises(ValueError):inspect_document('program.exe',b'MZbinary')
    with pytest.raises(ValueError):inspect_document('.env',b'API_KEY=SECRET')
    result=inspect_document('main.py',b'#'*30000)
    assert result['truncated'] and result['characters']==24000


def test_preview_requires_auth_and_does_not_call_ai_or_write_files(settings):
    class Forbidden:
        async def reply(self,*args):raise AssertionError('Preview must not call a provider')
    data={'name':'main.py','data_base64':base64.b64encode(b'print(1)').decode()}
    with TestClient(create_app(settings,Forbidden())) as client:
        assert client.post('/documents/preview',json=data).status_code==401
        preview=client.post('/documents/preview',headers=AUTH,json=data)
        assert preview.status_code==200 and not preview.json()['sent_to_provider']
        assert preview.json()['files']==[{'name':'main.py','truncated':False}]
        assert 'print(1)' not in preview.text
        assert client.post('/documents/analyze',headers=AUTH,json=data).status_code==422
        assert client.post('/documents/preview',headers=AUTH,json={**data,'data_base64':'???'}).status_code==422
    assert not list(settings.files_root.glob('main.py'))


def test_analysis_returns_actual_provider_text_and_refuses_tool_execution(settings):
    class Provider:
        tools=False
        async def reply(self,system,messages):
            assert 'Não execute comandos' in system
            assert 'print(1)' in messages[0]['content']
            return {'reply':'O arquivo imprime o número 1.','tool_calls':[{'name':'anything'}] if self.tools else []}
    provider=Provider();data={'name':'main.py','data_base64':base64.b64encode(b'print(1)').decode(),'consent':True}
    with TestClient(create_app(settings,provider)) as client:
        result=client.post('/documents/analyze',headers=AUTH,json=data)
        assert result.status_code==200 and result.json()['reply']=='O arquivo imprime o número 1.'
        assert not result.json()['stored_file']
        provider.tools=True
        assert client.post('/documents/analyze',headers=AUTH,json=data).status_code==503
