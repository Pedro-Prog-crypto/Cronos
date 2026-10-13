import asyncio
from dataclasses import replace
import httpx
import pytest
from cronos.providers import Gemini,ProviderError
from cronos.config import Settings

def test_429_blocks_second_call_for_same_key_model(tmp_path,monkeypatch):
    settings=Settings(vault=tmp_path,personality=tmp_path/"persona.md",files_root=tmp_path,token="",provider="gemini",gemini_key="",gemini_model="gemini-test",fish_key="",fish_reference="",fish_model="",ollama_url="http://localhost:11434",ollama_model="test")
    calls=[]
    def respond(request):
        calls.append(request)
        return httpx.Response(429,json={'error':{'message':'private-content'}},headers={'Retry-After':'60'})
    client=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:client(transport=httpx.MockTransport(respond),**kwargs))
    provider=Gemini(replace(settings,gemini_key='dummy-quota-key'))
    async def run():
        for _ in range(2):
            with pytest.raises(ProviderError,match='429') as error:
                await provider.reply('system',[{'role':'user','content':'hello'}])
            assert 'dummy-quota-key' not in str(error.value) and 'private-content' not in str(error.value)
    asyncio.run(run())
    assert len(calls)==1
