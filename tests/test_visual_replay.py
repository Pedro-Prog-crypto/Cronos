import json
import subprocess
from dataclasses import replace
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from cronos.app import create_app
from test_backend import AUTH, settings
from test_audio_conversation import wav


def test_repeat_images_command_is_distinct_from_new_image_request():
    source=Path('frontend/src/studyIntent.ts').resolve().as_uri()
    script='''import assert from 'node:assert/strict';
import {asksToReplayImages,isStudyQuestion,studyPanelTitle} from SOURCE;
for(const text of ['Cronos, mostre as imagens novamente', 'me mostra as fotos de novo', 'reabra o mural de imagens', 'imagens outra vez'])
  assert.equal(asksToReplayImages(text),true,text);
for(const text of ['mostre imagens de Sócrates', 'explique as imagens da Guerra', 'mostre um texto novamente'])
  assert.equal(asksToReplayImages(text),false,text);
assert.equal(isStudyQuestion('Mostre fotos de Sócrates'),true);
assert.equal(studyPanelTitle('Mostre fotos de Sócrates novamente'),'Sócrates');
'''.replace('SOURCE',json.dumps(source))
    result=subprocess.run(['node','--experimental-strip-types','--input-type=module','-e',script],capture_output=True,text=True,timeout=5)
    assert result.returncode==0,result.stderr


def test_model_receives_confirmed_visual_state_without_inventing_loaded_images(settings):
    systems=[]
    class Provider:
        async def reply(self,system,messages):
            systems.append(system)
            return {'reply':'Vou conferir as imagens exibidas.','topics':[],'tool_calls':[]}
    with TestClient(create_app(settings,Provider())) as client:
        for count in (6,0):
            response=client.post('/chat/stream',headers=AUTH,json={
                'message':'O que você está mostrando na tela?',
                'visual_context':{'topic':'Sócrates','status':'ready' if count else 'failed',
                                  'loaded_images':count,'image_titles':['Busto de Sócrates'] if count else [],'visible':True}})
            assert response.status_code==200
            assert json.loads(response.text.splitlines()[-1])['type']=='result'
    assert '"loaded_images": 6' in systems[0]
    assert 'Busto de Sócrates' in systems[0]
    assert '"loaded_images": 0' in systems[1]
    assert 'não diga que carregaram' in systems[1]


def test_spoken_followup_receives_visible_image_titles(settings):
    systems=[]
    class Provider:
        async def reply(self,system,messages):
            systems.append(system)
            return {'recognized_text':'Mostre as imagens novamente',
                    'reply':'As imagens estão disponíveis no mural.','topics':[],'tool_calls':[]}
    context={'topic':'Sócrates','status':'ready','loaded_images':6,
             'image_titles':['Busto de Sócrates'],'visible':True}
    headers={**AUTH,'Content-Type':'audio/wav',
             'X-Cronos-Visual-Context':quote(json.dumps(context,ensure_ascii=False),safe='')}
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        response=client.post('/chat/audio/stream',headers=headers,content=wav())
    assert response.status_code==200
    assert 'Busto de Sócrates' in systems[0]
