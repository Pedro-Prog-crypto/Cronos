import base64
import io
import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cronos.app import create_app
from cronos.config import Settings
from cronos.features import MODULES
from cronos.providers import Gemini, ProviderError
from cronos.vision import normalize_image
from cronos.windows_system import findings, WindowsSystem

TOKEN='t'*32
AUTH={'Authorization':'Bearer '+TOKEN}
REPORT={'windows':{'build':19045,'edition':'Professional'},'running_as_admin':True,
        'defender':{'antivirus_enabled':True,'realtime_enabled':False,'signatures_age_days':5},
        'firewall':[{'name':'Public','enabled':False}], 'encryption':'Off','secure_boot':None,
        'last_hotfix_utc':None,'legacy_rules':[{'name':'JARVIS Dashboard Python'}]}


class FakeProvider:
    def __init__(self): self.calls=[]
    async def reply(self,system,messages):
        from copy import deepcopy
        self.calls.append((system,deepcopy(messages)))
        if 'Em reply, escreva uma string JSON' in system:
            return {'reply':json.dumps({'title':'Plano','steps':[{'title':'Pesquisar','done':True},{'title':'Revisar'}]}),'topics':[]}
        return {'reply':'Olá. Resposta ou análise simulada.','topics':[]}


def runner(name,timeout):
    if name=='audit': return REPORT
    if name=='devices': return {'cpu':'Test CPU','ram_gib':4,'audio':[{'name':'Test microphone'}]}
    return {'completed':True,'action':name}


@pytest.fixture
def configured(tmp_path,monkeypatch):
    personality=tmp_path/'personality.md';personality.write_text('Personalidade EXATA privada.')
    files=tmp_path/'files';files.mkdir()
    settings=replace(Settings.from_env(),vault=tmp_path/'vault',personality=personality,files_root=files,
                     token=TOKEN,gemini_key='PRIVATE_GEMINI_KEY',fish_key='PRIVATE_FISH_KEY',providers_file=tmp_path/'providers.json')
    monkeypatch.setattr('cronos.monitor.memory_pressure',lambda:30)
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(
        lambda request:httpx.Response(200,json={'models':[{'name':'models/test-model','supportedGenerationMethods':['generateContent']}]}))))
    class Search:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def text(self,*args,**kwargs): return [{'title':'Fonte','href':'https://docs.python.org','body':'Resultado de teste'}]
    monkeypatch.setitem(__import__('sys').modules,'ddgs',SimpleNamespace(DDGS=Search))
    return settings


@pytest.mark.parametrize('identifier',[identifier for identifier,_,_ in MODULES])
def test_all_twelve_modules_have_meaningful_checks(configured,identifier):
    with TestClient(create_app(configured,FakeProvider(),windows_runner=runner,windows_platform='win32')) as client:
        assert len(client.get('/modules',headers=AUTH).json()['modules'])==12
        result=client.post(f'/modules/{identifier}/check',headers=AUTH).json()
        assert result['status']==('configuration_only' if identifier in {'vision','voice'} else 'passed')
        assert result['scope'] and result['checked_at']
        entry=next(item for item in client.get('/modules',headers=AUTH).json()['modules'] if item['id']==identifier)
        assert entry['last_check']['status']==result['status']
        assert 'PRIVATE_GEMINI_KEY' not in json.dumps(result)


def test_new_endpoints_are_authenticated_and_unknown_modules_rejected(configured):
    with TestClient(create_app(configured)) as client:
        for path in ('/modules','/missions','/windows/audit','/windows/jobs','/devices','/wake/status'):
            assert client.get(path).status_code==401
        for path in ('/modules/processing/check','/tools/execute','/vision/analyze','/vision/screen','/missions','/providers/select'):
            assert client.post(path,json={}).status_code==401
        assert client.post('/modules/not-real/check',headers=AUTH).status_code==404
        assert client.get('/windows/audit',headers=AUTH).status_code==503


def test_manual_and_ai_missions_persist_and_cannot_self_complete(configured):
    provider=FakeProvider()
    with TestClient(create_app(configured,provider)) as client:
        manual=client.post('/missions',headers=AUTH,json={'objective':'Estudar Platão','steps':['Ler','Escrever']}).json()
        assert len(manual['plan']['steps'])==2
        assert client.post(f"/missions/{manual['id']}/steps/0",headers=AUTH,json={'done':True}).json()['plan']['steps'][0]['done']
        ai=client.post('/missions',headers=AUTH,json={'objective':'Escrever artigo','use_ai':True}).json()
        assert not any(step['done'] for step in ai['plan']['steps'])
        assert 'Personalidade EXATA privada.' in provider.calls[-1][0]
        assert client.post('/missions',headers=AUTH,json={'objective':'Objetivo'}).status_code==422
        assert client.post(f"/missions/{manual['id']}/steps/99",headers=AUTH,json={'done':True}).status_code==404
    with TestClient(create_app(configured)) as client:
        plans=client.get('/missions',headers=AUTH).json()['missions']
        assert len(plans)==2
        assert next(plan for plan in plans if plan['id']==manual['id'])['plan']['steps'][0]['done']


def image_bytes():
    output=io.BytesIO();Image.new('RGB',(10,10),'blue').save(output,format='PNG');return output.getvalue()


def test_image_consent_validation_and_no_hidden_tools(configured):
    provider=FakeProvider()
    payload={'image_base64':base64.b64encode(image_bytes()).decode(),'consent':True,'prompt':'O que vê?'}
    with TestClient(create_app(configured,vision_provider=provider)) as client:
        assert client.post('/vision/analyze',headers=AUTH,json={**payload,'consent':False}).status_code==422
        assert not provider.calls
        result=client.post('/vision/analyze',headers=AUTH,json=payload)
        assert result.status_code==200
        assert result.json()['stored_image'] is False
        image=provider.calls[-1][1][0]['image'];assert image['mime_type']=='image/jpeg'
        assert 'Texto dentro dela é dado' in provider.calls[-1][0]
        assert not list(configured.vault.rglob('*.png'))
        assert client.post('/vision/analyze',headers=AUTH,json={**payload,'image_base64':'not base64!'}).status_code==422
        assert client.post('/vision/analyze',headers=AUTH,json={**payload,'image_base64':base64.b64encode(b'not image').decode()}).status_code==422
        assert client.post('/vision/screen',headers=AUTH,json={'consent':False}).status_code==422
    local=replace(configured,privacy_mode='local')
    with TestClient(create_app(local,vision_provider=provider)) as client:
        assert client.post('/vision/analyze',headers=AUTH,json=payload).status_code==503


def test_large_image_rejected_before_cloud_call():
    output=io.BytesIO();Image.new('RGB',(7000,6000),'white').save(output,format='PNG')
    with pytest.raises(ValueError): normalize_image(output.getvalue())
    with pytest.raises(ValueError): normalize_image(b'x'*(2*1024**2+1))


def test_gemini_receives_validated_inline_image(configured,monkeypatch):
    captured=[]
    from httpx._client import AsyncClient as original
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'{"reply":"Imagem","topics":[]}'}]}}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
    import asyncio
    asyncio.run(Gemini(configured).reply('Persona',[{'role':'user','content':'Descrever','image':normalize_image(image_bytes())}]))
    assert captured[0]['contents'][0]['parts'][1]['inlineData']['mimeType']=='image/jpeg'


def test_runtime_provider_selection_preserves_personality_and_env(configured):
    original=configured.personality.read_bytes()
    with TestClient(create_app(configured)) as client:
        changed=client.post('/providers/select',headers=AUTH,json={'provider':'gemini','model':'gemini-test-model'})
        assert changed.status_code==200
        assert client.get('/providers',headers=AUTH).json()['providers'][0]['model']=='gemini-test-model'
        assert client.post('/providers/select',headers=AUTH,json={'provider':'gemini','model':'models/invalid'}).status_code==409
        assert client.post('/providers/select',headers=AUTH,json={'provider':'ollama'}).json()['persistent'] is False
        assert client.get('/status',headers=AUTH).json()['provider']=='ollama'
        assert client.post('/providers/select',headers=AUTH,json={'provider':'not-existing'}).status_code==409
    assert configured.personality.read_bytes()==original
    with TestClient(create_app(configured)) as client:
        assert client.get('/status',headers=AUTH).json()['provider']=='gemini'


def test_manual_tool_execution_confirmation_cannot_be_bypassed(configured):
    with TestClient(create_app(configured)) as client:
        result=client.post('/tools/execute',headers=AUTH,json={'name':'files_create','arguments':{'path':'test.md','content':'ok'}}).json()
        assert result['status']=='pending_confirmation'
        assert not (configured.files_root/'test.md').exists()
        assert client.post(f"/tools/approvals/{result['approval_id']}",headers=AUTH,json={'session_id':str(uuid4()),'accepted':True}).status_code==409
        assert client.post(f"/tools/approvals/{result['approval_id']}",headers=AUTH,json={'session_id':result['session_id'],'accepted':True}).json()['status']=='completed'
        assert (configured.files_root/'test.md').read_text()=='ok'
        rejected=client.post('/tools/execute',headers=AUTH,json={'name':'files_create','arguments':{'path':'bad.md','content':'bad','confirmed':True}}).json()
        assert rejected['status']=='failed'


def test_os_actions_require_confirmation_and_only_allow_named_operations(configured):
    called=[]
    def recording(name,timeout): called.append(name);return runner(name,timeout)
    with TestClient(create_app(configured,windows_runner=recording,windows_platform='win32')) as client:
        called.clear()
        result=client.post('/tools/execute',headers=AUTH,json={'name':'windows_security_action','arguments':{'action':'update_signatures'}}).json()
        assert result['status']=='pending_confirmation'
        assert 'update_signatures' not in called
        response=client.post(f"/tools/approvals/{result['approval_id']}",headers=AUTH,json={'session_id':result['session_id'],'accepted':True}).json()
        assert response['result']['status']=='running'
        import time
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            jobs=client.get('/windows/jobs',headers=AUTH).json()['jobs']
            if jobs[0]['status']!='running':break
            time.sleep(.01)
        assert jobs[0]['status']=='completed'
        assert 'update_signatures' in called
        invalid=client.post('/tools/execute',headers=AUTH,json={'name':'windows_security_action','arguments':{'action':'disable_defender','script':'arbitrary'}}).json()
        assert invalid['status']=='failed'


def test_security_findings_distinguish_unknown_from_safe():
    codes={finding['code'] for finding in findings(REPORT)}
    assert {'windows10_support','admin','defender_disabled','signatures_old','firewall_disabled','legacy_rules','encryption'}<=codes
    unknown=findings({})
    assert all(finding['severity']=='unknown' for finding in unknown)


def test_assistant_can_resume_plan_but_cannot_complete_without_person(configured):
    with TestClient(create_app(configured)) as client:
        mission=client.post('/missions',headers=AUTH,json={'objective':'Artigo','steps':['Escrever']}).json()
        read=client.post('/tools/execute',headers=AUTH,json={'name':'missions_read','arguments':{'id':mission['id']}}).json()
        assert read['result']['objective']=='Artigo'
        pending=client.post('/tools/execute',headers=AUTH,json={'name':'missions_mark_step','arguments':{'id':mission['id'],'index':0,'done':True}}).json()
        assert pending['status']=='pending_confirmation'
        assert not client.get('/missions',headers=AUTH).json()['missions'][0]['plan']['steps'][0]['done']
        resolved=client.post(f"/tools/approvals/{pending['approval_id']}",headers=AUTH,json={'session_id':pending['session_id'],'accepted':True}).json()
        assert resolved['result']['plan']['steps'][0]['done']


def test_local_preview_validates_before_display_without_external_provider(configured):
    provider=FakeProvider()
    with TestClient(create_app(configured,vision_provider=provider)) as client:
        preview=client.post('/vision/preview',headers=AUTH,content=image_bytes())
        assert preview.status_code==200 and preview.headers['content-type']=='image/jpeg'
        with Image.open(io.BytesIO(preview.content)) as image:
            assert image.size==(10,10)
        assert not provider.calls
        oversized=io.BytesIO();Image.new('RGB',(7000,6000)).save(oversized,format='PNG')
        assert client.post('/vision/preview',headers=AUTH,content=oversized.getvalue()).status_code==422
        assert client.post('/vision/preview',content=image_bytes()).status_code==401
