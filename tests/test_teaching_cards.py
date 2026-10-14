from pathlib import Path
from fastapi.testclient import TestClient
from dataclasses import replace
from test_backend import settings, AUTH
from cronos.app import create_app


def test_real_personality_and_card_capability_reach_provider(settings):
    calls=[]
    class Provider:
        async def reply(self,system,messages):
            calls.append(system)
            return {'reply':'## Contexto\nTomás de Aquino viveu no século XIII.\n\n## Exemplo\nCompare razão e fé sem confundi-las.\n\n## Sua vez\nComo você explicaria essa diferença?','topics':[],'tool_calls':[]}
    persona=Path(__file__).resolve().parents[1]/'modelos/personalidades/cronos.md'
    with TestClient(create_app(replace(settings,personality=persona),provider=Provider())) as client:
        result=client.post('/chat',headers=AUTH,json={'message':'Explique Tomás de Aquino em cards, com exemplos.'})
        assert result.status_code==200
        assert '## Contexto' in result.json()['reply']
    prompt=calls[0]
    assert 'inspirada principalmente no JARVIS e no Ultron' in prompt
    assert 'cards holográficos na tela' in prompt
    assert 'Faça uma pergunta por vez' in prompt
    assert 'não invente minha resposta' in prompt
    assert 'não presuma qual exame é “PAIS”' in prompt
    assert 'player interno de músicas e clipes' in prompt
