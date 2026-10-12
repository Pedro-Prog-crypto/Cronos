import asyncio
from types import SimpleNamespace
from dataclasses import replace
from cronos.fish_account_diagnostic import report
from test_backend import settings


def test_fish_balances_are_separate_and_ids_are_not_printed(settings):
    class Fish:
        def __init__(self,**kwargs):self.account=self;self.voices=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get_credits(self,**kwargs):return SimpleNamespace(credit=0,has_free_credit=False,user_id='PRIVATE')
        async def get_package(self):return SimpleNamespace(balance=8000,total=8000,user_id='PRIVATE')
        async def get(self,reference):return {'id':'PRIVATE'}
    result='\n'.join(asyncio.run(report(replace(settings,fish_key='dummy-secret',fish_reference='private-voice'),Fish)))
    assert 'Saldo retornado pela API: 0' in result and 'Saldo do pacote: 8000/8000' in result
    assert 'dummy-secret' not in result and 'private-voice' not in result and 'PRIVATE' not in result


def test_gemini_404_lists_models_without_a_second_generation(settings,monkeypatch,capsys):
    from cronos import diagnostics
    from cronos.providers import ProviderError
    class Provider:
        async def reply(self,*args):raise ProviderError('modelo HTTP 404')
    async def models(*args):return ['modelo-real-flash']
    monkeypatch.setattr(diagnostics,'load_dotenv',lambda *args:None)
    monkeypatch.setattr(diagnostics.Settings,'from_env',lambda:settings)
    monkeypatch.setattr(diagnostics,'make_provider',lambda settings:Provider())
    monkeypatch.setattr(diagnostics,'available_models',models)
    import pytest
    with pytest.raises(SystemExit):diagnostics.main()
    assert 'Modelo disponível: modelo-real-flash' in capsys.readouterr().out
