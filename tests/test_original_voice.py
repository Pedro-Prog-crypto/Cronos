import json
from pathlib import Path
from zipfile import ZipFile
from dotenv import dotenv_values
from cronos.import_original_voice import read_voice,import_voice
import pytest
from test_backend import settings


def archive(tmp_path,url='https://api.fish.audio/v1/tts'):
    path=tmp_path/'original.zip'
    with ZipFile(path,'w') as z:
        z.writestr('config/fish_audio.json',json.dumps({'api_key':'dummy-secret','reference_id':'a'*32,'model':'s2.1-pro-free','format':'wav','api_url':url,'speed':1,'latency':'balanced'}))
    return path


def test_original_voice_import_replaces_voice_only_and_backs_up(tmp_path):
    source=archive(tmp_path);env=tmp_path/'.env'
    env.write_text('GEMINI_API_KEY=keep\nCRONOS_VAULT=keep-vault\nFISH_MODEL=wrong\n')
    import_voice(source,env)
    data=dotenv_values(env)
    assert data['FISH_MODEL']=='s2.1-pro-free' and data['FISH_FORMAT']=='wav'
    assert data['FISH_REFERENCE_ID']=='a'*32 and data['FISH_API_KEY']=='dummy-secret'
    assert data['GEMINI_API_KEY']=='keep' and data['CRONOS_VAULT']=='keep-vault'
    assert len(list((tmp_path/'.cronos-local').glob('*.bak')))==1


def test_original_voice_rejects_foreign_endpoint(tmp_path):
    with pytest.raises(ValueError):read_voice(archive(tmp_path,'https://untrusted.example/v1/tts'))


def test_streaming_wav_header_is_finalized_without_changing_samples():
    import io,struct,wave
    from cronos.fish_legacy import finalize_wav
    pcm=b'\x01\0\x02\0'*100
    output=io.BytesIO()
    with wave.open(output,'wb') as writer:
        writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(24000);writer.writeframes(pcm)
    source=bytearray(output.getvalue())
    struct.pack_into('<I',source,4,0xffffffff);struct.pack_into('<I',source,40,0xffffffff)
    fixed=finalize_wav(bytes(source))
    with wave.open(io.BytesIO(fixed),'rb') as reader:
        assert reader.getnframes()==200
        assert reader.readframes(200)==pcm
    assert struct.unpack_from('<I',fixed,4)[0]==len(fixed)-8


def test_local_recognizer_reuses_model_and_decodes_pcm(monkeypatch):
    import io,sys,wave
    from types import SimpleNamespace
    from cronos.recognition import LocalRecognizer
    calls=[]
    class Recognizer:
        def __init__(self,model,rate):assert rate==16000
        def AcceptWaveform(self,frames):return False
        def FinalResult(self):return json.dumps({'text':'abrir cronos'})
    monkeypatch.setitem(sys.modules,'vosk',SimpleNamespace(Model=lambda folder:calls.append(folder) or object(),KaldiRecognizer=Recognizer,SetLogLevel=lambda value:None))
    monkeypatch.setattr('cronos.recognition.wake.verify_model',lambda:Path('local-model'))
    output=io.BytesIO()
    with wave.open(output,'wb') as writer:
        writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(16000);writer.writeframes(b'\0\0'*1600)
    service=LocalRecognizer()
    assert service.transcribe(output.getvalue())=='abrir cronos'
    assert service.transcribe(output.getvalue())=='abrir cronos'
    assert len(calls)==1
    with pytest.raises(ValueError):service.transcribe(b'not-wav')


def test_official_portuguese_flat_layout_is_supported(tmp_path,monkeypatch):
    import hashlib
    from cronos import wake
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    model=wake.root()/wake.MODEL_NAME;model.mkdir(parents=True)
    hashes={}
    for name in ('final.mdl','mfcc.conf','HCLr.fst','Gr.fst'):
        (model/name).write_bytes(b'fixture')
        hashes[name]=hashlib.sha256(b'fixture').hexdigest()
    (wake.root()/'model-hashes.json').write_text(json.dumps(hashes))
    assert wake.verify_model()==model
    assert wake.status()['model_installed']


def test_voice_import_preserves_configured_gemini_key_and_model(tmp_path):
    path=archive(tmp_path)
    with ZipFile(path,'a') as z:z.writestr('config/api_keys.json',json.dumps({'gemini_api_key':'dummy-original-key'}))
    env=tmp_path/'.env';env.write_text('GEMINI_API_KEY=old\nGEMINI_MODEL=selected-model\n')
    import_voice(path,env)
    values=dotenv_values(env)
    assert values['GEMINI_API_KEY']=='old'
    assert values['GEMINI_MODEL']=='selected-model'


def test_gemini_retries_only_transient_503_without_switching_model(settings,monkeypatch):
    import asyncio,httpx
    from dataclasses import replace
    from cronos.providers import Gemini
    calls=[];original=httpx.AsyncClient
    def handler(request):
        calls.append(request)
        if len(calls)==1:return httpx.Response(503,json={'error':{'message':'busy'}})
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':json.dumps({'reply':'Olá','topics':[]})}]}}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
    result=asyncio.run(Gemini(replace(settings,gemini_key='dummy')).reply('Teste',[{'role':'user','content':'Olá'}]))
    assert result['reply']=='Olá' and len(calls)==2
    assert calls[0].url==calls[1].url and calls[0].content==calls[1].content
