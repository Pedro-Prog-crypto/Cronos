import json
from dataclasses import replace
from uuid import uuid4
import pytest
import httpx
from fastapi.testclient import TestClient
from test_backend import settings, AUTH
from cronos.app import create_app
from cronos.prospects import osm_lead, recommendation, website

REAL_ASYNC_CLIENT=httpx.AsyncClient

PLACE={'display_name':'Manaus, Amazonas, Brasil','osm_type':'relation','osm_id':123,'address':{'country_code':'br','city':'Manaus'},'boundingbox':['-3.2','-2.9','-60.2','-59.8']}
ITEMS=[{'type':'node','id':1,'tags':{'name':'Cantina Aurora','amenity':'restaurant','capacity:seats':'30'}},
       {'type':'node','id':2,'tags':{'name':'Grande Rede','amenity':'restaurant','capacity:seats':'180','brand':'Rede','website':'https://grandeficticia.example'}},
       {'type':'way','id':3,'tags':{'name':'Cantina Sem Porte','amenity':'restaurant','contact:website':'https://instagram.com/cantina'}}]


def mock_sources(monkeypatch,places=None):
    original=REAL_ASYNC_CLIENT;requests=[]
    def handle(r):
        requests.append(r)
        if r.url.host=='nominatim.openstreetmap.org':return httpx.Response(200,json=places if places is not None else [PLACE])
        if r.url.host=='overpass-api.de':return httpx.Response(200,json={'elements':ITEMS})
        if r.url.host=='places.googleapis.com':return httpx.Response(200,json={'places':[{'id':'abc','displayName':{'text':'Cantina Aurora'},'rating':4.6,'userRatingCount':70,'formattedAddress':'Manaus, Brasil','googleMapsUri':'https://maps.google.com/?cid=1'}]})
        raise AssertionError('Unexpected network destination')
    monkeypatch.setattr('cronos.prospects.httpx.AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),trust_env=False,**kw))
    return requests


def test_portes_and_sites_are_evidence_not_guesses():
    small=osm_lead(ITEMS[0],'Manaus');big=osm_lead(ITEMS[1],'Manaus');unknown=osm_lead(ITEMS[2],'Manaus')
    assert small['size']=='pequeno' and small['site_status']=='unverified'
    assert big['size']=='grande' and big['project']['difficulty']=='alta'
    assert unknown['size']=='desconhecido' and unknown['website'] is None
    assert unknown['rating'] is None
    assert website('javascript:alert(1)') is None
    assert website('https://user:password@example.org') is None


def test_search_auth_brazil_categories_and_cache(settings,monkeypatch):
    requests=mock_sources(monkeypatch)
    with TestClient(create_app(settings)) as c:
        assert c.post('/prospects/search',json={'city':'Manaus'}).status_code==401
        for city in ['Manaus, AM','Brasília, DF','Rio de Janeiro, RJ']:
            response=c.post('/prospects/search',headers=AUTH,json={'city':city,'category':'pizzaria'})
            assert response.status_code==200,response.text
            assert len(response.json()['leads'])==3
        query=requests[-1].content.decode()
        assert '3600000123' in query and 'pizza' in query and '100' in query
        geo=[r for r in requests if r.url.host=='nominatim.openstreetmap.org']
        assert all(r.url.params['countrycodes']=='br' for r in geo)
        count=len(requests)
        cached=c.post('/prospects/search',headers=AUTH,json={'city':'Manaus, AM','category':'pizzaria'}).json()
        assert cached['cached'] and len(requests)==count
        c.patch('/panels/preferences',headers=AUTH,json={'web_enabled':False})
        assert c.post('/prospects/search',headers=AUTH,json={'city':'Manaus'}).status_code==403


def test_no_foreign_city_or_silent_ambiguous_selection(settings,monkeypatch):
    mock_sources(monkeypatch,places=[{**PLACE,'address':{'country_code':'pt'}}])
    with TestClient(create_app(settings)) as c:
        assert c.post('/prospects/search',headers=AUTH,json={'city':'Lisboa'}).status_code==404
    mock_sources(monkeypatch,places=[PLACE,{**PLACE,'display_name':'Outra Manaus, Brasil'}])
    with TestClient(create_app(settings)) as c:
        assert c.post('/prospects/search',headers=AUTH,json={'city':'Manaus'}).status_code==409


def test_google_ratings_and_local_permission(settings,monkeypatch):
    monkeypatch.setenv('GOOGLE_PLACES_API_KEY','fake-test-only')
    requests=mock_sources(monkeypatch)
    with TestClient(create_app(settings)) as c:
        result=c.post('/prospects/search',headers=AUTH,json={'city':'Manaus, AM','source':'google'})
        assert result.status_code==200,result.text
        assert result.json()['leads'][0]['rating']==4.6
        assert 'fake-test-only' not in result.text
        body=json.loads(requests[-1].content)
        assert body['pageSize']<=20 and 'locationRestriction' in body
    with TestClient(create_app(replace(settings,privacy_mode='local'))) as c:
        assert c.post('/prospects/search',headers=AUTH,json={'city':'Manaus'}).status_code==403


def test_verification_never_promises_absence_and_detects_candidates(settings,monkeypatch):
    mock_sources(monkeypatch)
    with TestClient(create_app(settings)) as c:
        result=c.post('/prospects/search',headers=AUTH,json={'city':'Manaus, AM'}).json()
        calls=[]
        async def search(name,args,session):
            calls.append(args['query'])
            return {'status':'completed','result':[{'title':'Cantina Aurora perfil','href':'https://instagram.com/cantina','body':'Manaus'}]}
        monkeypatch.setattr(c.app.state.registry,'execute',search)
        payload={'report_id':result['id'],'lead_id':result['leads'][0]['id']}
        verified=c.post('/prospects/verify',headers=AUTH,json=payload).json()
        assert verified['site_status']=='no_site_found'
        assert 'Nenhum processo' in verified['verification_note'] and len(calls)==2
        assert len(verified['evidence'])>=2
        async def candidate(name,args,session):
            return {'status':'completed','result':[{'title':'Cantina Aurora','href':'https://auroraficticia.example','body':'Restaurante Manaus'}]}
        monkeypatch.setattr(c.app.state.registry,'execute',candidate)
        verified=c.post('/prospects/verify',headers=AUTH,json=payload).json()
        assert verified['site_status']=='candidate'
        assert verified['website']=='https://auroraficticia.example'
        assert c.post('/prospects/verify',headers=AUTH,json={**payload,'lead_id':'missing'}).status_code==404


def test_source_failure_not_empty_success(settings,monkeypatch):
    original=httpx.AsyncClient
    def handle(r):raise httpx.ConnectError('unavailable',request=r)
    monkeypatch.setattr('cronos.prospects.httpx.AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),trust_env=False,**kw))
    with TestClient(create_app(settings)) as c:
        result=c.post('/prospects/search',headers=AUTH,json={'city':'Manaus, AM'})
        assert result.status_code==502
        assert 'leads' not in result.json()


def test_google_never_auto_enabled_by_model_tool(settings,monkeypatch):
    with TestClient(create_app(settings)) as client:
        tool=client.app.state.registry.tools['prospect_restaurants']
        from pydantic import ValidationError
        with pytest.raises(ValidationError):tool.arguments.model_validate({'city':'Manaus','source':'google'})
        client.app.state.panels.preferences.web_enabled=False
        assert not client.app.state.registry.permission_policy('prospect_restaurants')[0]
        monkeypatch.delenv('GOOGLE_PLACES_API_KEY',raising=False)
        client.app.state.panels.preferences.web_enabled=True
        result=client.post('/prospects/search',headers=AUTH,json={'city':'Manaus','source':'google'})
        assert result.status_code==503


def test_restaurant_source_failover(settings,monkeypatch):
    original=REAL_ASYNC_CLIENT;seen=[]
    def handle(r):
        seen.append(r.url.host)
        if r.url.host=='nominatim.openstreetmap.org':return httpx.Response(200,json=[PLACE])
        if r.url.host=='overpass-api.de':return httpx.Response(503,text='busy')
        if r.url.host=='overpass.kumi.systems':return httpx.Response(200,json={'elements':ITEMS})
        raise AssertionError('Unexpected source')
    monkeypatch.setattr('cronos.prospects.httpx.AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),trust_env=False,**kw))
    with TestClient(create_app(settings)) as client:
        result=client.post('/prospects/search',headers=AUTH,json={'city':'Manaus, AM'})
        assert result.status_code==200,result.text
        assert len(result.json()['leads'])==3
        assert seen[-2:]==['overpass-api.de','overpass.kumi.systems']
