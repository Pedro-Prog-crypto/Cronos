"""Explicit retry and user-selected frame review, without real provider calls."""
import asyncio
import base64
import copy
import io
import json
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cronos.app import create_app
from cronos.providers import ProviderError
from cronos.studio.catalog import starter
from cronos.studio.validation import validate
from test_backend import settings, AUTH
from test_studio import Builder, new, generate, get
from test_studio_visuals import VisualBuilder, wait
from test_studio_fallback import Failing, configured


def capture(revision=0, **kwargs):
    image=io.BytesIO();Image.new('RGB',(600,400),'#ffeeaa').save(image,'PNG')
    return {'revision':revision,'image_base64':base64.b64encode(image.getvalue()).decode(),
            'consent':True,'source':'uploaded-capture',**kwargs}


class Vision:
    def __init__(self):self.calls=[]
    async def reply(self,system,messages):
        self.calls.append((system,copy.deepcopy(messages)))
        return {'reply':json.dumps({'summary':'Os campos do formulário visível estão pequenos e sem espaço entre os rótulos.',
            'issues':[{'title':'Campos muito pequenos','detail':'O formulário visível precisa de campos mais altos e rótulos separados.','severity':'high'}],
            'correction_request':'Amplie os campos e botões do formulário e organize os rótulos em linhas separadas.'})}


def test_explicit_retry_after_every_adapter_failed_keeps_request_assets_and_revision(settings,monkeypatch):
    adapters={'gemini':Builder(),'mistral':Failing(),'ollama':Failing()}
    settings=configured(settings,monkeypatch,adapters)
    before=settings.providers_file.read_bytes(),settings.personality.read_bytes()
    with TestClient(create_app(settings)) as c:
        p=generate(c,new(c))
        asset=c.post('/studio/projects/'+p['id']+'/assets',headers=AUTH,
            json={'name':'foto.png','purpose':'image','data_base64':capture()['image_base64']}).json()['assets'][-1]
        adapters['gemini']=Failing(ProviderError('quota',429))
        failed=generate(c,p,prompt='Corrija os formulários mantendo as fotografias.')
        assert failed['status']=='failed' and 'Nenhuma integração' in failed['error']
        assert failed['revision']==p['revision'] and failed['current']==p['current']
        counts={k:len(v.calls) for k,v in adapters.items()}
        time.sleep(.08)
        assert counts=={k:len(v.calls) for k,v in adapters.items()} # no automatic repeat
        # A second failed click preserves the same request; it is not a new project.
        url='/studio/projects/'+p['id']+'/retry'
        assert c.post(url,headers=AUTH,json={}).status_code==200
        again=wait(c,p)
        assert again['status']=='failed' and again['revision']==p['revision']
        assert all(len(adapters[k].calls)>counts[k] for k in adapters)
        adapters['mistral']=Builder()
        result=c.post(url,headers=AUTH,json={});assert result.status_code==200,result.text
        done=wait(c,p)
        assert done['status']=='ready' and done['id']==p['id'] and done['revision']==p['revision']+1
        assert done['active_provider']=='mistral' and done['last_request']==failed['last_request']
        assert done['assets'][-1]==asset and len(done['history'])==len(p['history'])+1
        assert len(c.get('/studio/projects',headers=AUTH).json()['projects'])==1
        sent=json.loads(adapters['mistral'].calls[-1][1][0]['content'])
        assert sent['request']==failed['last_request'] and sent['current_files']==p['current']['files']
        assert sent['assets'][-1]['name']==asset['name']
        assert c.post(url,headers=AUTH,json={}).status_code==409 # completed is not retried
    assert before==(settings.providers_file.read_bytes(),settings.personality.read_bytes())


def test_retry_restores_reference_options_and_has_exclusive_job_lock(settings):
    class Waiting:
        async def reply(self,*args):await asyncio.Event().wait()
    with TestClient(create_app(settings,Waiting())) as c:
        p=new(c)
        body={'mode':'reference','prompt':'Use a referência para corrigir este site.','reference':'Duas colunas e navegação lateral.',
              'research_images':False,'plan_first':True}
        url='/studio/projects/'+p['id']
        assert c.post(url+'/retry',headers=AUTH,json={}).status_code==409
        assert c.post(url+'/generate',headers=AUTH,json=body).status_code==200
        assert c.post(url+'/retry',headers=AUTH,json={}).status_code==409
        c.post(url+'/cancel',headers=AUTH,json={})
        response=c.post(url+'/retry',headers=AUTH,json={})
        assert response.status_code==200,response.text
        running=response.json()
        assert all(running[k]==body[k] for k in ('mode','reference','research_images','plan_first'))
        assert running['last_request']==body['prompt'] and running['revision']==0
        c.post(url+'/cancel',headers=AUTH,json={})
        c.post(url+'/archive',headers=AUTH,json={'archived':True})
        assert c.post(url+'/retry',headers=AUTH,json={}).status_code==409
        assert c.post(url+'/retry',json={}).status_code==401


def test_retry_directions_resumes_planning_instead_of_building(settings):
    builder=VisualBuilder()
    with TestClient(create_app(settings,builder)) as c:
        p=new(c);url='/studio/projects/'+p['id']
        original=builder.reply
        async def bad(*args):raise ProviderError('quota',429)
        builder.reply=bad
        body={'mode':'autonomous','prompt':'Proponha três direções para o hotel.'}
        c.post(url+'/directions',headers=AUTH,json=body)
        assert wait(c,p)['status']=='failed'
        builder.reply=original
        assert c.post(url+'/retry',headers=AUTH,json={}).status_code==200
        done=wait(c,p)
        assert done['status']=='ideas_ready' and len(done['directions'])==3 and done['revision']==0
        assert done['current']['files']==p['current']['files'] and done['last_request']==body['prompt']


def test_frame_analysis_is_explicit_does_not_change_site_or_persist_pixels(settings):
    vision=Vision();code=Builder()
    with TestClient(create_app(settings,code,vision_provider=vision)) as c:
        p=new(c);url='/studio/projects/'+p['id']+'/screen-review';body=capture()
        assert c.post(url,json=body).status_code==401
        assert c.post(url,headers=AUTH,json={k:v for k,v in body.items() if k!='consent'}).status_code==422
        assert c.post(url,headers=AUTH,json={**body,'consent':False}).status_code==422
        assert c.post(url,headers=AUTH,json={**body,'image_base64':'invalid!'}).status_code==422
        assert c.post(url,headers=AUTH,json=capture(1)).status_code==409
        assert not vision.calls and not code.calls
        response=c.post(url,headers=AUTH,json=body);assert response.status_code==200,response.text
        done=wait(c,p)
        assert done['status']=='draft' and done['revision']==0 and done['current']==p['current']
        assert len(done['screen_reviews'])==1 and not code.calls and not done['assets']
        assert vision.calls[0][1][0]['image']['mime_type']=='image/jpeg'
        assert body['image_base64'] not in json.dumps(done) and 'image_base64' not in json.dumps(done)
        assert 'screen_reviews' not in c.get('/studio/projects',headers=AUTH).json()['projects'][0]
        archive=c.get('/studio/projects/'+p['id']+'/export?draft=true',headers=AUTH).content
        assert body['image_base64'].encode() not in archive
        assert not list(c.app.state.studio.store.directory(p).glob('*.png'))


def test_screen_observations_drive_code_revision_and_keep_original(settings):
    class RepairBuilder(Builder):
        async def reply(self,system,messages):
            data=json.loads(messages[0]['content'])
            if data.get('screen_observations'):
                self.calls.append((system,messages))
                files=data['current_files'].copy();files['styles.css']+='\nform label{margin-bottom:12px}form input,form button{min-height:48px}'
                return {'reply':json.dumps({'summary':'Senhor, formulários corrigidos a partir da captura.','files':files})}
            return await super().reply(system,messages)
    vision=Vision();code=RepairBuilder()
    with TestClient(create_app(settings,code,vision_provider=vision)) as c:
        first=generate(c,new(c));old=first['current']['files']
        response=c.post('/studio/projects/'+first['id']+'/screen-review',headers=AUTH,json=capture(first['revision'],repair=True))
        assert response.status_code==200,response.text
        done=wait(c,first)
        assert done['status']=='ready' and done['revision']==first['revision']+1
        sent=json.loads(code.calls[-1][1][0]['content'])
        assert sent['screen_observations'][-1]['issues'][0]['title']=='Campos muito pequenos'
        assert sent['current_files']==old and 'image' not in code.calls[-1][1][0]
        assert done['screen_reviews'][0]['revision']==first['revision']
        assert len(done['history'])==len(first['history'])+1
        restored=c.post('/studio/projects/'+first['id']+'/restore',headers=AUTH,json={'revision':first['revision']}).json()
        assert restored['current']['files']==old


def test_screen_vision_fallback_and_rejection_do_not_replace_site(settings,monkeypatch):
    vision=Vision()
    adapters={'gemini':Failing(ProviderError('quota',429)),'mistral':vision,'ollama':Failing()}
    settings=configured(settings,monkeypatch,adapters)
    with TestClient(create_app(settings)) as c:
        p=new(c);url='/studio/projects/'+p['id']+'/screen-review'
        assert c.post(url,headers=AUTH,json=capture()).status_code==200
        done=wait(c,p)
        assert done['status']=='draft' and done['screen_reviews'][0]['provider']=='mistral'
        assert len(adapters['gemini'].calls)==len(vision.calls)==1
        # Invalid image analysis moves to the reserve and ultimately fails safely.
        adapters['mistral']=Builder([{'reply':'not a review'}]);c.app.state.studio.vision_cooldowns.clear()
        assert c.post(url,headers=AUTH,json=capture(repair=True)).status_code==200
        failed=wait(c,p)
        assert failed['status']=='failed' and failed['current']==p['current'] and failed['revision']==0
        assert failed['screen_reviews']==done['screen_reviews']
        response=c.post('/studio/projects/'+p['id']+'/retry',headers=AUTH,json={})
        assert response.status_code==409 and 'captura' in response.text


def test_cancel_screen_review_does_not_launch_code_or_keep_image(settings):
    class Waiting:
        async def reply(self,*args):await asyncio.Event().wait()
    code=Builder()
    with TestClient(create_app(settings,code,vision_provider=Waiting())) as c:
        p=new(c);url='/studio/projects/'+p['id']
        assert c.post(url+'/screen-review',headers=AUTH,json=capture(repair=True)).status_code==200
        assert c.post(url+'/screen-review',headers=AUTH,json=capture()).status_code==409
        cancelled=c.post(url+'/cancel',headers=AUTH,json={}).json()
        assert cancelled['status']=='cancelled' and not code.calls and not cancelled.get('screen_reviews')
        assert cancelled['current']==p['current']


@pytest.mark.parametrize('replacement',[('', 'styles.css'),('rel="preload"','rel="stylesheet"'),('','app.js')])
def test_generated_html_must_load_both_files_once(replacement):
    files=starter();new_value,old_value=replacement
    files['index.html']=files['index.html'].replace(old_value,new_value)
    report=validate(files,run_syntax=False)
    assert not report['passed']
    assert next(c for c in report['checks'] if c['name']=='Estilos e interações ligados ao HTML')['status']=='failed'
