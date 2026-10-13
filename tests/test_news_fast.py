import asyncio
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos.news import current_news_query
from cronos.tools import Tool,Query
from test_backend import settings,AUTH


@pytest.mark.parametrize('message',['Notícias do dia','Cronos, me diga as notícias de hoje','Quais são as principais notícias do dia no Brasil?','Me fale sobre notícias atuais da Europa'])
def test_explicit_news_requests(message):
    assert current_news_query(message)


@pytest.mark.parametrize('message',['Quem foi Sócrates?','O que significa notícias do dia?','Escreva um texto chamado notícias do dia','Notícias do dia 10 de junho de 2015','Notícias de hoje sem pesquisar','Notícias do dia e abra meus downloads'])
def test_general_conversation_and_private_commands_do_not_go_to_search(message):
    assert current_news_query(message) is None


class Provider:
    def __init__(self):self.calls=[]
    async def reply(self,system,messages):
        self.calls.append((system,messages))
        assert 'BUSCA DE NOTÍCIAS JÁ REALIZADA' in messages[-1]['content']
        return {'reply':'Resumo com fontes recentes.','topics':[],'tool_calls':[]}


def test_daily_news_searches_before_one_model_call_and_keeps_tool_history(settings):
    provider=Provider();searches=[]
    with TestClient(create_app(settings,provider)) as client:
        registry=client.app.state.registry
        registry.tools['web_news']=Tool('web_news','Noticias',Query,lambda args:(searches.append(args.query) or {'articles':[{'title':'Fonte atual','url':'https://example.org/news','published':'Hoje'}]}))
        client.app.state.memory.recall=lambda *args:(_ for _ in ()).throw(AssertionError('Old notes are not live news'))
        r=client.post('/chat',headers=AUTH,json={'message':'Cronos, notícias do dia no Brasil'})
        assert r.status_code==200 and len(provider.calls)==1 and len(searches)==1
        assert r.json()['tool_results'][0]['name']=='web_news'
        assert r.json()['timings_ms']['provider_calls']==1
        assert r.json()['timings_ms']['search']>=0
        assert client.app.state.memory.tool_history(r.json()['session_id'])[0]['name']=='web_news'


def test_search_failure_is_supplied_to_model_without_inventing_results(settings):
    class FailProvider(Provider):
        async def reply(self,system,messages):
            assert 'notícias não disponíveis' in messages[-1]['content']
            return {'reply':'Não consegui consultar notícias agora.','topics':[],'tool_calls':[]}
    with TestClient(create_app(settings,FailProvider())) as client:
        def fail(args):raise ValueError('notícias não disponíveis')
        client.app.state.registry.tools['web_news']=Tool('web_news','Noticias',Query,fail)
        r=client.post('/chat',headers=AUTH,json={'message':'Notícias de hoje'})
        assert r.status_code==200 and r.json()['tool_results'][0]['status']=='failed'


def test_permissions_and_confirmation_disable_automatic_search(settings):
    class NoPrefetch:
        async def reply(self,system,messages):
            assert 'BUSCA DE NOTÍCIAS JÁ REALIZADA' not in messages[-1]['content']
            return {'reply':'Sem busca automática.','topics':[],'tool_calls':[]}
    with TestClient(create_app(settings,NoPrefetch())) as client:
        def forbidden(args):raise AssertionError('Must not prefetch')
        client.app.state.registry.tools['web_news']=Tool('web_news','Noticias',Query,forbidden)
        for prefs in ({'web_enabled':False},{'web_enabled':True,'confirm_tools':True}):
            client.patch('/panels/preferences',headers=AUTH,json=prefs)
            assert client.post('/chat',headers=AUTH,json={'message':'Notícias do dia'}).status_code==200


def test_news_search_uses_recent_filter_and_short_cache(settings,monkeypatch):
    calls=[]
    class Search:
        def __init__(self,**kwargs):assert kwargs['timeout']==3 and kwargs['verify']
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def news(self,query,**kwargs):
            calls.append(kwargs)
            return [{'title':'Fonte','url':'https://example.org/news','body':'Conteúdo','date':'Hoje','source':'Fonte'}]
    monkeypatch.setitem(__import__('sys').modules,'ddgs',SimpleNamespace(DDGS=Search))
    with TestClient(create_app(settings)) as client:
        async def run():
            first=await client.app.state.registry.execute('web_news',{'query':'notícias de hoje','limit':6},uuid4())
            second=await client.app.state.registry.execute('web_news',{'query':'notícias de hoje','limit':6},uuid4())
            assert first['status']=='completed' and second['result']['cached'] is True
            assert first['result']['fetched_at']==second['result']['fetched_at']
        asyncio.run(run())
        assert len(calls)==1 and calls[0]['timelimit']=='d'
        client.patch('/panels/preferences',headers=AUTH,json={'web_enabled':False})
        r=client.post('/tools/execute',headers=AUTH,json={'name':'web_news','arguments':{'query':'notícias de hoje'}})
        assert r.json()['status']=='failed'


def test_news_does_not_repeat_search_with_different_arguments(settings):
    class RepeatingProvider:
        def __init__(self):self.calls=0
        async def reply(self,system,messages):
            self.calls+=1
            if self.calls==1:
                return {'reply':'','topics':[],'tool_calls':[{'name':'web_search','arguments':{'query':'notícias hoje outras fontes','limit':3}}]}
            assert 'já foi tentada' in messages[-1]['content']
            return {'reply':'Não foi possível obter notícias atuais.','topics':[],'tool_calls':[]}
    searches=[]
    with TestClient(create_app(settings,RepeatingProvider())) as client:
        client.app.state.registry.tools['web_news']=Tool('web_news','Noticias',Query,lambda args:(searches.append(args.query) or {'articles':[]}))
        client.app.state.registry.tools['web_search']=Tool('web_search','Busca',Query,lambda args:(_ for _ in ()).throw(AssertionError('Repeated search')))
        r=client.post('/chat',headers=AUTH,json={'message':'Notícias do dia'})
        assert r.status_code==200 and len(searches)==1
        assert r.json()['tool_results'][1]['status']=='failed'
