"""Real API jobs for click-to-create, composition checks and preserved failover."""
import asyncio
import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from cronos.app import create_app
from cronos.providers import ProviderError
from cronos.studio.composition import profile,review,choose_plan
from cronos.studio.directions import parse_directions
from test_backend import settings,AUTH
from test_studio import new,generate,get,Builder
from test_studio_visuals import VisualBuilder,plans,wait


def seed(client,identifier='osm:node:123',name='Mesa da Praça'):
    lead={'id':identifier,'name':name,'category':'restaurante','city':'Brasília, DF','address':'Endereço público de teste','phone':None,'website':None,'site_status':'unverified','evidence':[{'source':'Fixture OSM','url':'https://www.openstreetmap.org/node/123','note':'Registro de teste.'}]}
    report={'id':str(uuid4()),'city':'Brasília, DF','category':'restaurante','source':'osm','leads':[lead]}
    client.app.state.prospects.reports[report['id']]=report
    return {'report_id':report['id'],'lead_id':identifier,'research_images':False}


def test_click_prepares_plans_then_builds_a_real_project_once(settings):
    builder=VisualBuilder()
    with TestClient(create_app(settings,builder)) as client:
        body=seed(client)
        assert not builder.calls
        response=client.post('/studio/opportunities',headers=AUTH,json=body)
        assert response.status_code==200,response.text
        made=wait(client,response.json())
        assert made['status']=='ready' and made['code_origin']=='generated'
        assert made['name']=='Mesa da Praça' and made['quote']['min']==200 and not made['quote']['has_3d']
        assert len(made['directions'])==3 and made['direction_id'] and made['design_comparison']['compared_projects']==0
        assert len(builder.calls)==2
        payload=json.loads(builder.calls[-1][1][-1]['content'])
        assert payload['approved_direction'] and payload['template_reference'] is None
        assert not payload['current_files'] and payload['design_policy']['unique_creation']
        assert made['current']['report']['composition'][0]['status']=='passed'
        assert [e['phase'] for e in made['events']].count('ready')==1
        same=client.post('/studio/opportunities',headers=AUTH,json=body).json()
        assert same['id']==made['id'] and len(builder.calls)==2
        # Search sessions change; the stable public lead still opens the saved proposal.
        again=seed(client)
        assert client.post('/studio/opportunities',headers=AUTH,json=again).json()['id']==made['id']
        assert len(client.get('/studio/projects',headers=AUTH).json()['projects'])==1
        assert client.get('/studio/projects',headers=AUTH).json()['projects'][0]['code_origin']=='generated'
        assert client.get('/studio/projects/'+made['id']+'/export',headers=AUTH).status_code==200


def test_unknown_expired_unconfigured_or_local_opportunity_never_creates_a_project(settings,monkeypatch):
    monkeypatch.setattr("cronos.studio.service.provider_catalog",lambda settings:[{"id":"gemini","configured":False}])
    with TestClient(create_app(settings)) as client:
        assert client.post('/studio/opportunities',json={}).status_code==401
        body=seed(client)
        assert client.post('/studio/opportunities',headers=AUTH,json={**body,'lead_id':'unknown'}).status_code==404
        assert client.post('/studio/opportunities',headers=AUTH,json=body).status_code==409
        assert client.get('/studio/projects',headers=AUTH).json()['projects']==[]
        client.app.state.engine.settings=replace(settings,privacy_mode='local')
        assert client.post('/studio/opportunities',headers=AUTH,json=body).status_code==403


def test_repeated_click_during_build_and_manual_cancel_preserve_source_and_request(settings):
    class Waiting:
        def __init__(self):self.calls=0
        async def reply(self,*args):self.calls+=1;await asyncio.Event().wait()
    builder=Waiting()
    with TestClient(create_app(settings,builder)) as client:
        body=seed(client)
        project=client.post('/studio/opportunities',headers=AUTH,json=body).json()
        assert get(client,project)['status']=='running'
        assert client.post('/studio/opportunities',headers=AUTH,json=body).json()['id']==project['id']
        other=seed(client,'osm:node:999','Outro negócio')
        assert client.post('/studio/opportunities',headers=AUTH,json=other).status_code==409
        assert len(client.get('/studio/projects',headers=AUTH).json()['projects'])==1
        done=client.post('/studio/projects/'+project['id']+'/cancel',headers=AUTH,json={}).json()
        assert done['status']=='cancelled' and done['last_request'] and done['opportunity']['lead_id']==body['lead_id']
        assert done['revision']==0 and len(done['history'])==1 and builder.calls==1


def test_comparison_ignores_brand_photos_fonts_and_palette_but_allows_a_new_layout():
    from cronos.studio.catalog import starter
    original=starter('restaurante','Primeiro')
    copy={key:value.replace('Primeiro','Segundo').replace('#f8f5f0','#ffffff').replace('Georgia','Arial') for key,value in original.items()}
    assert profile(original)['signature']==profile(copy)['signature']
    recent=[{'profile':profile(original)}]
    assert review(copy,recent,enabled=True)[0]['status']=='failed'
    copy['styles.css']+='\n.extra{gap:43px;padding:91px;margin:3px}'
    assert review(copy,recent,enabled=True)[0]['status']=='failed'
    copy['styles.css']+='\nmain{display:grid;grid-template-columns:1fr 2fr;gap:43px}'
    assert review(copy,recent,enabled=True)[0]['status']=='passed'
    assert review(original,recent,enabled=False)[0]['status']=='unavailable'


def test_planner_rejects_same_composition_with_different_names_and_selects_less_repeated_direction():
    alternatives=plans()
    recent=[{'direction':alternatives[0]}]
    selected,comparison=choose_plan(alternatives,recent)
    assert selected['name']!=alternatives[0]['name'] and comparison['compared_projects']==1
    alternatives[1]['composition']=alternatives[0]['composition']
    with pytest.raises(ValueError):parse_directions({'reply':json.dumps({'directions':alternatives})})


def test_recoloured_delivery_is_repaired_before_saving_and_other_clients_stay_private(settings):
    builder=VisualBuilder()
    with TestClient(create_app(settings,builder)) as client:
        first=new(client,name='Cliente particular',contact='private@example.com')
        assert generate(client,first)['status']=='ready'
        second=new(client,name='Outro cliente')
        base=Builder()
        calls=[]
        async def reply(system,messages):
            calls.append((system,messages))
            if 'EXATAMENTE três direções' in system:return {'reply':json.dumps({'directions':plans()})}
            result=await base.reply(system,messages)
            if len([s for s,m in calls if 'EXATAMENTE três direções' not in s])>1:
                data=json.loads(result['reply']);data['files']['styles.css']+='\nmain{display:grid;grid-template-columns:1fr 2fr;gap:43px}'
                result['reply']=json.dumps(data)
            return result
        builder.reply=reply
        done=generate(client,second,plan_first=True)
        assert done['status']=='ready' and done['revision']==1
        assert len(calls)==3 and any(e['phase']=='repair' for e in done['events'])
        assert done['rejected_report']['composition'][0]['status']=='failed'
        for _,messages in calls:
            text=json.dumps(json.loads(messages[-1]['content']).get('recent_designs'))
            assert 'Cliente particular' not in text and 'private@example.com' not in text


def test_same_provider_pool_continues_from_planning_to_code_and_falls_back_again(settings,monkeypatch):
    import cronos.studio.service as service
    settings=replace(settings,gemini_key='fixture-not-real')
    monkeypatch.setenv('STUDIO_RESERVE','fixture-not-real')
    settings.providers_file.write_text(json.dumps({'providers':[{'id':name,'kind':'openai','model':'fixture','base_url':'https://example.com/v1','key_env':'STUDIO_RESERVE'} for name in ('mistral','groq')]}))
    class Adapter(VisualBuilder):
        def __init__(self,name):super().__init__();self.name=name
        async def reply(self,system,messages):
            if self.name in {'gemini','ollama'}:raise ProviderError('quota',429)
            if self.name=='mistral' and 'EXATAMENTE três direções' not in system:raise ProviderError('temporary',503)
            return await super().reply(system,messages)
    adapters={name:Adapter(name) for name in ('gemini','mistral','groq','ollama')}
    monkeypatch.setattr(service,'make_provider',lambda configuration:adapters[configuration.provider])
    with TestClient(create_app(settings)) as client:
        response=client.post('/studio/opportunities',headers=AUTH,json=seed(client))
        done=wait(client,response.json())
        assert done['status']=='ready' and done['active_provider']=='groq' and done['revision']==1, (done.get('error'),done['events'])
        assert len(done['directions'])==3
        assert len([e for e in done['events'] if e['phase']=='fallback'])==2
        assert not any(e['phase']=='failed' for e in done['events'])
        assert len(adapters['mistral'].calls)==1 and len(adapters['groq'].calls)==1


def test_basic_2d_requests_do_not_become_3d_just_because_they_say_without_3d():
    from cronos.studio.catalog import quote
    from cronos.studio.threed.integration import reference_id
    for text in ('Não quero 3D. Faça um site básico.','Site sem visualizador 3D','Sem modelo em 3D','Não use 3D','Não quero um site em 3D'):
        result=quote('imobiliaria',text,tier='economy')
        assert not result['has_3d'] and result['min']==200
        assert reference_id('imobiliaria',text)=='imobiliaria'
    assert quote('imobiliaria','Quero uma apresentação em 3D',tier='premium_3d')['has_3d']


def test_photo_selection_excludes_previous_images_and_noncommercial_licenses(monkeypatch):
    import cronos.studio.images as images
    selected=[]
    async def search(*args,**kwargs):
        return [{'title':title,'license':license,'width':width,'height':width} for title,license,width in [('File:Old.jpg','CC0',6000),('File:NC.jpg','CC BY-NC 4.0',9000),('File:ND.jpg','CC BY-ND 4.0',8000),('File:New.jpg','CC BY-SA 4.0',1800)]]
    async def download(title):selected.append(title);return b'image',{'title':title,'license':'CC BY-SA 4.0'}
    monkeypatch.setattr(images,'search_images',search);monkeypatch.setattr(images,'download_image',download)
    result=asyncio.run(images.suggest_image('restaurante','horizontal',exclude={'File:Old.jpg'}))
    assert result[1]=='File:New.jpg' and selected==['File:New.jpg']


def test_advanced_scope_does_not_force_unrelated_earbuds_into_a_restaurant():
    from cronos.studio.threed.integration import suggested_model
    assert suggested_model('restaurante','Uma apresentação da cozinha em 3D') is None
    assert suggested_model('loja','Joias e acessórios') is None
    assert suggested_model('loja','Apresentação do fone Buds')=='earbuds'
    assert suggested_model('imobiliaria','Apresentar o prédio')=='hotel'
    assert suggested_model('restaurante','Modelo escolhido pelo senhor',requested='earbuds')=='earbuds'
