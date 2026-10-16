import asyncio
import base64
import io
import json
import time
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cronos.app import create_app
from cronos.studio.directions import parse_directions
from cronos.studio.image_generation import image_providers, generate_image
from cronos.studio.service import prepare_asset
from test_backend import settings, AUTH
from test_studio import Builder, new, generate, get


def plans():
    return [{'name': name, 'concept': 'Direção específica para uma cozinha brasileira que trabalha o ingrediente e o fogo.',
             'composition': composition, 'typography': 'Georgia para a narrativa e Arial para navegação legível.',
             'palette': ['#efe9dc', '#251d19', '#ca4025'],
             'sections': ['Abertura', 'Cardápio', 'Cozinha', 'Solicitar mesa'],
             'horizontal_image': 'Fotografia ampla do prato saindo da cozinha, com fundo escuro e luz lateral.',
             'vertical_image': 'Retrato das mãos do cozinheiro finalizando o prato, sem distorcer a imagem.',
             'interaction': 'Filtros do cardápio e navegação por teclado; movimento leve, sem 3D obrigatório.'}
            for name, composition in [('Caderno da cozinha', 'Composição editorial assimétrica com fotografia vertical, notas marginais e cardápio lateral.'),
                                      ('O fogo em primeiro plano', 'Abertura horizontal imersiva com fotografia ocupando a tela e menu no rodapé da abertura.'),
                                      ('À mesa, sem rodeios', 'Composição tipográfica centrada no cardápio, com navegação por categorias e imagens intercaladas.')]]


class VisualBuilder(Builder):
    async def reply(self, system, messages):
        if 'EXATAMENTE três direções' in system:
            self.calls.append((system, messages))
            return {'reply': json.dumps({'directions': plans()})}
        return await super().reply(system, messages)


def wait(c, p):
    for _ in range(150):
        result = get(c, p)
        if result['status'] != 'running': return result
        time.sleep(.01)
    raise AssertionError('Job did not finish')


def test_directions_are_reviewed_before_code_and_approved_direction_reaches_builder(settings):
    builder = VisualBuilder()
    with TestClient(create_app(settings, builder)) as c:
        p = new(c, category='restaurante', name='Mesa do senhor')
        original = p['current']['files']
        response = c.post('/studio/projects/'+p['id']+'/directions', headers=AUTH,
                          json={'mode':'autonomous','provider':'gemini','prompt':'Proponha três sites distintos para minha cozinha.'})
        assert response.status_code == 200
        done = wait(c, p)
        assert done['status'] == 'ideas_ready' and len(done['directions']) == 3
        assert done['revision'] == 0 and done['current']['files'] == original
        assert len(builder.calls) == 1
        assert c.post('/studio/projects/'+p['id']+'/direction', headers=AUTH, json={'direction_id':'missing'}).status_code == 422
        chosen = c.post('/studio/projects/'+p['id']+'/direction', headers=AUTH, json={'direction_id':'2'}).json()
        assert chosen['direction_id'] == '2'
        generated = generate(c, chosen)
        assert generated['status'] == 'ready' and generated['code_origin'] == 'generated'
        sent = json.loads(builder.calls[-1][1][-1]['content'])
        assert sent['approved_direction']['name'] == 'O fogo em primeiro plano'
        assert sent['current_files'] == {} and sent['current_summary'] == ''
        assert not any(a.get('source',{}).get('kind') == 'demo' for a in sent['assets'])
        assert generated['current']['report']['visual_content']


def test_bad_or_failed_proposals_do_not_replace_previous_plans_or_code(settings):
    builder = VisualBuilder()
    with TestClient(create_app(settings, builder)) as c:
        p = new(c)
        body = {'mode':'autonomous','prompt':'Três propostas, por favor.'}
        c.post('/studio/projects/'+p['id']+'/directions',headers=AUTH,json=body)
        first = wait(c,p)
        async def bad(*args): return {'reply':'{"directions":[]}'}
        builder.reply = bad
        c.post('/studio/projects/'+p['id']+'/directions',headers=AUTH,json=body)
        failed = wait(c,p)
        assert failed['status'] == 'failed' and failed['directions'] == first['directions']
        assert failed['current']['files'] == first['current']['files'] and failed['revision'] == 0
        assert failed['last_request'] == body['prompt']
        assert c.get('/studio/projects/'+p['id']+'/export',headers=AUTH).status_code == 409


def test_cancel_is_explicit_and_preserves_request(settings):
    class Waiting:
        async def reply(self,*args): await asyncio.Event().wait()
    with TestClient(create_app(settings, Waiting())) as c:
        p = new(c)
        body = {'mode':'autonomous','prompt':'Quero uma proposta editorial de restaurante.'}
        c.post('/studio/projects/'+p['id']+'/directions',headers=AUTH,json=body)
        assert get(c,p)['status'] == 'running'
        assert c.post('/studio/projects/'+p['id']+'/direction',headers=AUTH,json={'direction_id':'1'}).status_code == 409
        cancelled = c.post('/studio/projects/'+p['id']+'/cancel',headers=AUTH,json={}).json()
        assert cancelled['status'] == 'cancelled' and cancelled['last_request'] == body['prompt']
        assert cancelled['revision'] == 0 and len(cancelled['history']) == 1


def test_initial_example_requires_explicit_draft_export_even_after_restore(settings):
    with TestClient(create_app(settings,Builder())) as c:
        p = new(c)
        assert c.get('/studio/projects/'+p['id']+'/export',headers=AUTH).status_code == 409
        assert c.get('/studio/projects/'+p['id']+'/export?draft=true',headers=AUTH).status_code == 200
        done = generate(c,p)
        assert done['status']=='ready'
        restored = c.post('/studio/projects/'+p['id']+'/restore',headers=AUTH,json={'revision':0}).json()
        assert restored['revision']==2 and restored['code_origin']=='starter'
        assert c.get('/studio/projects/'+p['id']+'/export',headers=AUTH).status_code == 409


def test_unchanged_example_is_not_accepted_as_generated_site(settings):
    builder = Builder()
    with TestClient(create_app(settings,builder)) as c:
        p = new(c)
        builder.outputs = [{'reply':json.dumps({'summary':'Pronto','files':p['current']['files']})}]
        done = generate(c,p)
        assert done['status']=='failed' and done['revision']==0 and len(builder.calls)==2
        assert done['code_origin']=='starter'


def configure_images(settings, monkeypatch):
    settings.providers_file.parent.mkdir(parents=True,exist_ok=True)
    settings.providers_file.write_text(json.dumps({'providers':[{'id':'my-openai','kind':'openai','model':'gpt-4o-mini',
        'base_url':'https://api.openai.com/v1','key_env':'STUDIO_TEST_IMAGE_KEY'}]}))
    monkeypatch.setenv('STUDIO_TEST_IMAGE_KEY','test-only-not-a-real-key')


def test_image_provider_is_official_only_and_never_enabled_in_local_mode(settings,monkeypatch):
    configure_images(settings,monkeypatch)
    assert image_providers(settings)==[{'id':'my-openai','models':['gpt-image-1']}]
    assert image_providers(replace(settings,privacy_mode='local'))==[]
    data=json.loads(settings.providers_file.read_text());data['providers'][0]['base_url']='https://api.mistral.ai/v1'
    settings.providers_file.write_text(json.dumps(data))
    assert image_providers(settings)==[]


@pytest.mark.parametrize('orientation,dimensions',[('horizontal',(1536,1024)),('vertical',(1024,1536))])
def test_image_generation_saves_preview_and_dimensions_without_code_change(settings,monkeypatch,orientation,dimensions):
    configure_images(settings,monkeypatch)
    image=io.BytesIO();Image.new('RGB',dimensions,'#123456').save(image,'JPEG')
    calls=[]
    async def fake(settings,provider,prompt,shape,model):
        calls.append((provider,shape,model));return image.getvalue()
    monkeypatch.setattr('cronos.studio.image_generation.generate_image',fake)
    with TestClient(create_app(settings,Builder())) as c:
        p=new(c);old=p['current']['files']
        body={'provider':'my-openai','orientation':orientation,'purpose':'reference','prompt':'Crie uma proposta visual editorial para este site.'}
        assert c.post('/studio/projects/'+p['id']+'/images/generate',headers=AUTH,json=body).status_code==409
        body['approved']=True
        assert c.post('/studio/projects/'+p['id']+'/images/generate',headers=AUTH,json=body).status_code==200
        done=wait(c,p)
        assert done['status']=='draft' and done['revision']==0 and done['current']['files']==old
        asset=done['assets'][-1]
        assert asset['orientation']==orientation and (asset['width'],asset['height'])==dimensions
        assert asset['purpose']=='reference' and asset['source']['kind']=='ai_mockup'
        assert c.get('/studio/projects/'+p['id']+'/assets/'+asset['name'],headers=AUTH).status_code==200
        assert len(calls)==1


def test_official_image_request_uses_correct_size_and_never_retries_429(settings,monkeypatch):
    configure_images(settings,monkeypatch);calls=[]
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,**kwargs):
            calls.append((url,kwargs))
            return httpx.Response(429,request=httpx.Request('POST',url),json={'error':{'message':'private error'}})
    monkeypatch.setattr('cronos.studio.image_generation.httpx.AsyncClient',Client)
    from cronos.providers import ProviderError
    with pytest.raises(ProviderError,match='429'):
        asyncio.run(generate_image(settings,'my-openai','Proposta visual','vertical'))
    assert len(calls)==1 and calls[0][0]=='https://api.openai.com/v1/images/generations'
    assert calls[0][1]['json']['size']=='1024x1536'
    assert calls[0][1]['json']['n']==1


def test_public_search_filters_actual_dimensions_and_keeps_attribution(monkeypatch):
    from cronos.studio.images import search_images
    class Client:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kw):
            return httpx.Response(200,request=httpx.Request('GET',url),json={'query':{'pages':{
                '1':{'title':'File:Landscape.jpg','imageinfo':[{'mime':'image/jpeg','width':1800,'height':1000,'thumburl':'https://upload.wikimedia.org/example.jpg','extmetadata':{'Artist':{'value':'<b>Autor</b>'},'LicenseShortName':{'value':'CC BY 4.0'}}}]},
                '2':{'title':'File:Portrait.jpg','imageinfo':[{'mime':'image/jpeg','width':900,'height':1400,'extmetadata':{}}]}}}})
    monkeypatch.setattr('cronos.studio.images.httpx.AsyncClient',Client)
    images=asyncio.run(search_images('restaurant',orientation='vertical'))
    assert len(images)==1 and images[0]['title']=='File:Portrait.jpg' and images[0]['orientation']=='vertical'
    images=asyncio.run(search_images('restaurant',orientation='horizontal'))
    assert images[0]['author']=='Autor' and images[0]['license']=='CC BY 4.0'


def test_malicious_palette_is_rejected_and_uploaded_orientation_is_real():
    values=plans();values[0]['palette'][0]='url(javascript:alert(1))'
    with pytest.raises(ValueError):parse_directions({'reply':json.dumps({'directions':values})})
    data=io.BytesIO();Image.new('RGB',(40,90),'red').save(data,'PNG')
    raw,ext,mime=prepare_asset(data.getvalue(),'image','portrait.png')
    with Image.open(io.BytesIO(raw)) as im:assert im.size==(40,90)


def test_code_output_budget_is_separate_from_conversation_and_saved_config(settings):
    config=replace(settings,output_tokens=256)
    with TestClient(create_app(config)) as c:
        provider=c.app.state.studio.code_provider(config)
        assert provider.settings.output_tokens>=8192
        assert c.app.state.engine.settings.output_tokens==256
        assert c.app.state.engine.settings.gemini_transport==config.gemini_transport


def test_design_history_uses_only_approved_visual_choices_not_other_client_contacts(settings):
    builder=VisualBuilder()
    with TestClient(create_app(settings,builder)) as c:
        first=new(c,name='Cliente privado',contact='Telefone e email privados')
        body={'mode':'autonomous','prompt':'Proponha três composições.'}
        c.post('/studio/projects/'+first['id']+'/directions',headers=AUTH,json=body);wait(c,first)
        c.post('/studio/projects/'+first['id']+'/direction',headers=AUTH,json={'direction_id':'1'})
        second=new(c,name='Outro projeto')
        c.post('/studio/projects/'+second['id']+'/directions',headers=AUTH,json=body);wait(c,second)
        data=json.loads(builder.calls[-1][1][-1]['content'])
        assert data['recent_designs'][0]['composition']==plans()[0]['composition']
        assert 'Cliente privado' not in json.dumps(data['recent_designs'])
        assert 'Telefone e email privados' not in json.dumps(data)


def test_status_does_not_dump_database_checks_into_ordinary_conversation(settings):
    from uuid import uuid4
    with TestClient(create_app(settings,Builder())) as c:
        p=new(c);generate(c,p)
        ordinary=c.portal.call(c.app.state.registry.execute,'studio_status',{'project_id':p['id']},uuid4())['result']
        assert 'verification' in ordinary and 'checks' not in ordinary
        detailed=c.portal.call(c.app.state.registry.execute,'studio_status',{'project_id':p['id'],'technical':True},uuid4())['result']
        assert 'backend' in detailed['checks']


def test_chosen_reference_is_used_and_autonomous_requests_do_not_reuse_it(settings):
    class Vision:
        def __init__(self):self.calls=[]
        async def reply(self,system,messages):
            self.calls.append(messages)
            return {'reply':'Composição com fotografia vertical e tipografia escura em fundo claro.'}
    vision=Vision();builder=Builder()
    with TestClient(create_app(settings,builder,vision_provider=vision)) as c:
        p=new(c);names=[]
        for color in ('red','blue'):
            data=io.BytesIO();Image.new('RGB',(30,50),color).save(data,'PNG')
            uploaded=c.post('/studio/projects/'+p['id']+'/assets',headers=AUTH,json={'name':color+'.png','purpose':'reference','data_base64':base64.b64encode(data.getvalue()).decode()}).json()
            names.append(uploaded['assets'][-1]['name'])
        done=generate(c,p,mode='reference',reference_asset=names[0])
        assert done['status']=='ready' and len(vision.calls)==1
        actual=base64.b64decode(vision.calls[0][0]['image']['data'])
        expected=c.get('/studio/projects/'+p['id']+'/assets/'+names[0],headers=AUTH).content
        assert actual==expected
        revised=dict(done['current']['files'])
        revised['index.html']=revised['index.html'].replace('Uma proposta construída para este projeto de teste.', 'Segunda composição criada sem usar a referência anterior.')
        builder.outputs=[{'reply':json.dumps({'summary':'Nova composição autônoma.','files':revised})}]
        done=generate(c,p,mode='autonomous',reference_asset=names[1])
        assert done['status']=='ready' and len(vision.calls)==1 and done['reference_asset']==''
