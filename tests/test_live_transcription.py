"""The microphone may deliver words before it sends its completed recording."""
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from cronos.app import create_app
from cronos.recognition import LiveListener, LocalRecognizer
from test_backend import settings


def test_live_listener_accumulates_partials_and_validates_final_confidence():
    class Recognizer:
        calls = 0
        def AcceptWaveform(self, _frames):
            self.calls += 1
            return self.calls == 2
        def PartialResult(self): return json.dumps({'partial': 'quem foi'})
        def Result(self): return json.dumps({'text': 'quem foi Platão', 'result': [
            {'word': 'quem', 'conf': .93}, {'word': 'Platão', 'conf': .88}]})
        def FinalResult(self): return json.dumps({'text': 'e sua Academia', 'result': [
            {'word': 'Academia', 'conf': .91}]})
    listener = LiveListener(Recognizer())
    assert listener.feed(b'00') == 'quem foi'
    assert listener.feed(b'00') == 'quem foi Platão'
    assert listener.finish() == 'quem foi Platão e sua Academia'


def test_live_transcription_socket_streams_words_and_never_calls_answer_model(settings, monkeypatch):
    class Listener:
        calls = 0
        def feed(self, frames):
            assert frames == bytes(8000)
            self.calls += 1
            return 'quem foi' if self.calls == 1 else 'quem foi Platão'
        def finish(self): return 'quem foi Platão'
    listener = Listener()
    monkeypatch.setattr(LocalRecognizer, 'live_listener', lambda self: listener)
    class Provider:
        async def reply(self, *_args): raise AssertionError('Live transcription must not call the answer model')
    headers = {'Origin': 'http://127.0.0.1'}
    with TestClient(create_app(settings, provider=Provider())) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('ws://127.0.0.1/voice/live-transcript',
                                          headers={'Origin': 'https://evil.invalid'}): pass
        with client.websocket_connect('ws://127.0.0.1/voice/live-transcript', headers=headers) as socket:
            socket.send_json({'token': 'wrong'})
            with pytest.raises(WebSocketDisconnect): socket.receive_json()
        with client.websocket_connect('ws://127.0.0.1/voice/live-transcript', headers=headers) as socket:
            socket.send_json({'token': 'test-token'})
            assert socket.receive_json() == {'type': 'ready'}
            socket.send_bytes(bytes(8000))
            assert socket.receive_json() == {'type': 'partial', 'text': 'quem foi'}
            socket.send_bytes(bytes(8000))
            assert socket.receive_json() == {'type': 'partial', 'text': 'quem foi Platão'}
            socket.send_json({'type': 'finish'})
            assert socket.receive_json() == {'type': 'final', 'text': 'quem foi Platão'}
        assert listener.calls == 2


def test_live_transcription_reports_missing_model_without_claiming_words(settings, monkeypatch):
    def missing(self): raise ValueError('model unavailable')
    monkeypatch.setattr(LocalRecognizer, 'live_listener', missing)
    with TestClient(create_app(settings)) as client:
        with client.websocket_connect('ws://127.0.0.1/voice/live-transcript',
                                      headers={'Origin': 'http://127.0.0.1'}) as socket:
            socket.send_json({'token': 'test-token'})
            assert socket.receive_json()['type'] == 'unavailable'


def test_local_browser_preview_updates_during_speech_and_sends_final_without_second_asr():
    source = Path('frontend/src/audio/localSpeechPreview.ts').resolve().as_uri()
    script = '''import assert from 'node:assert/strict';
    import {createLocalSpeechPreview} from SOURCE;
    let socket;
    class FakeSocket {
      readyState=0;onopen=null;onmessage=null;onerror=null;onclose=null;sent=[];
      constructor(url){assert.match(url,/\\/voice\\/live-transcript$/);socket=this;}
      send(value){this.sent.push(value);if(typeof value==='string'&&JSON.parse(value).type==='finish'){
        queueMicrotask(()=>this.onmessage?.({data:JSON.stringify({type:'final',text:'quem foi Platão'})}));
      }}
      close(){this.readyState=3;this.onclose?.();}
      open(){this.readyState=1;this.onopen?.();this.onmessage?.({data:JSON.stringify({type:'ready'})});}
    }
    const updates=[];
    const preview=createLocalSpeechPreview(text=>updates.push(text),'fixture-token',
      {WebSocket:FakeSocket,location:{href:'http://127.0.0.1:58805/ui/'}});
    preview.push(new Int16Array(1600));socket.open();
    assert.equal(JSON.parse(socket.sent[0]).token,'fixture-token');
    assert.equal(socket.sent[1].byteLength,3200);
    socket.onmessage({data:JSON.stringify({type:'partial',text:'quem foi'})});
    assert.deepEqual(updates,['quem foi']);
    assert.equal(await preview.finish(2),'quem foi Platão');
    assert.deepEqual(updates,['quem foi','quem foi Platão']);
    '''.replace('SOURCE', json.dumps(source))
    result = subprocess.run(['node', '--experimental-strip-types', '--input-type=module', '-e', script],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr


def test_audio_worklet_emits_live_pcm_before_completed_recording():
    source = Path('frontend/src/audio/capture.worklet.js').resolve()
    script = '''import assert from 'node:assert/strict';
    import fs from 'node:fs';
    import vm from 'node:vm';
    let Capture;
    class Base {constructor(){this.port={events:[],postMessage:(value)=>this.port.events.push(value)};}}
    const code=fs.readFileSync(SOURCE,'utf8').replace("import {createSpeechDetector} from './speechDetector.js';",'');
    vm.runInNewContext(code,{AudioWorkletProcessor:Base,sampleRate:16000,
      registerProcessor:(_,value)=>Capture=value,Int16Array,Math});
    const capture=new Capture();capture.vad={process:()=>true,mode:()=>{}};
    const frame=Float32Array.from({length:128},(_,index)=>index%2?.15:-.15);
    for(let index=0;index<70;index++)capture.process([[frame]]);
    assert(capture.port.events.some(event=>event.active===true));
    assert(capture.port.events.some(event=>event.liveFrames?.length>0));
    capture.port.onmessage({data:{flush:true}});
    assert(capture.port.events.some(event=>event.samples?.length>0));
    assert(capture.port.events.findIndex(event=>event.liveFrames)>-1);
    assert(capture.port.events.findIndex(event=>event.liveFrames)<
           capture.port.events.findIndex(event=>event.samples));
    '''.replace('SOURCE', json.dumps(str(source)))
    result = subprocess.run(['node', '--input-type=module', '-e', script],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
