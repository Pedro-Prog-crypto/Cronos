"""Audio -> explicit ASR -> normal conversation -> configured voice, without UI."""
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from uuid import uuid4
import wave

import httpx

from cronos.desktop_state import session_id,needs_screen,wants_card
from cronos.resident import Connection,folder,write_json
from cronos.spoken_text import speech_text


def chunks(text,limit=360):
    remaining=speech_text(text)
    while remaining:
        end=len(remaining) if len(remaining)<=limit else remaining.rfind(' ',0,limit)
        if end<1:end=min(limit,len(remaining))
        yield remaining[:end]
        remaining=remaining[end:].lstrip()


class WindowsSpeaker:
    """No browser, shell expansion, visible player, or interpolated commands."""
    def __init__(self,cancel):self.cancel=cancel;self.process=None
    def stop(self):
        self.cancel.set()
        if self.process and self.process.poll() is None:self.process.terminate()
        try:
            import winsound
            winsound.PlaySound(None,0)
        except (ImportError,RuntimeError):pass
    def wav(self,audio,volume=1):
        if self.cancel.is_set():return False
        from cronos.fish_legacy import finalize_wav
        audio=finalize_wav(audio)
        if not 44<=len(audio)<=12*1024*1024:raise ValueError('Áudio da resposta inválido.')
        if volume<=0:raise ValueError('O volume da voz está em zero.')
        if volume<1:
            import array,sys
            with wave.open(io.BytesIO(audio),'rb') as source:
                if source.getsampwidth()==2:
                    parameters=source.getparams();samples=array.array('h',source.readframes(source.getnframes()))
                    if sys.byteorder!='little':samples.byteswap()
                    samples=array.array('h',(int(value*volume) for value in samples))
                    if sys.byteorder!='little':samples.byteswap()
                    out=io.BytesIO()
                    with wave.open(out,'wb') as target:target.setparams(parameters);target.writeframes(samples.tobytes())
                    audio=out.getvalue()
        import winsound
        stopped=threading.Event()
        def watch():
            while not stopped.wait(.05):
                if self.cancel.is_set():winsound.PlaySound(None,0);break
        watcher=threading.Thread(target=watch,daemon=True);watcher.start()
        try:winsound.PlaySound(audio,winsound.SND_MEMORY|winsound.SND_NODEFAULT)
        finally:stopped.set();watcher.join(timeout=.3)
        return not self.cancel.is_set()
    def local(self,text,volume=1):
        if self.cancel.is_set():return False
        if volume<=0:raise ValueError('O volume da voz está em zero.')
        # Text goes through stdin, never through executable command text. The
        # process has no console, including a fallback after cloud TTS fails.
        system=Path(os.environ.get('SystemRoot','C:/Windows'))
        executable=system/'System32/WindowsPowerShell/v1.0/powershell.exe'
        script=("[Console]::InputEncoding=[Text.Encoding]::UTF8;$data=[Console]::In.ReadToEnd()|ConvertFrom-Json;"
                "$v=New-Object -ComObject SAPI.SpVoice;$found=$false;"
                "foreach($voice in $v.GetVoices()){if($voice.GetAttribute('Language') -match '(^|;)0?416($|;)|(^|;)0?816($|;)'){$v.Voice=$voice;$found=$true;break}};"
                "if(-not $found){exit 2};$v.Volume=[Math]::Min(100,[Math]::Max(0,[int]$data.volume));$null=$v.Speak([string]$data.text)")
        self.process=subprocess.Popen([str(executable),'-NoLogo','-NoProfile','-NonInteractive','-Command',script],
            stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,shell=False,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            self.process.stdin.write(json.dumps({'text':text,'volume':int(volume*100)},ensure_ascii=False).encode('utf-8'));self.process.stdin.close()
            deadline=time.monotonic()+max(30,len(text)*.4)
            while self.process.poll() is None:
                if self.cancel.wait(.05) or time.monotonic()>deadline:
                    self.process.terminate();self.process.wait(timeout=3)
                    if self.cancel.is_set():return False
                    raise RuntimeError('A voz local parou de responder.')
            if self.process.returncode:raise RuntimeError('Nenhuma voz local em português conseguiu ler a resposta.')
            return not self.cancel.is_set()
        finally:
            if self.process.poll() is None:self.process.kill()
            self.process=None


class NativeConversation:
    def __init__(self,connection,ui,speaker_factory=WindowsSpeaker,on_control=None):
        self.connection=connection;self.ui=ui;self.speaker_factory=speaker_factory
        self.session=session_id();self.cancel=threading.Event();self.speaker=None;self.response=None
        self.processing=threading.Event();self.playing=threading.Event();self.pending=None
        self.turn=None
        self.on_control=on_control

    def stop(self):
        self.cancel.set()
        if self.turn:
            try:self.connection.client.post('/assistant/cancel',json={'turn_id':self.turn},timeout=2)
            except (httpx.HTTPError,RuntimeError):pass
        if self.speaker:self.speaker.stop()
        if self.response:
            try:self.response.close()
            except (httpx.HTTPError,RuntimeError):pass

    def say_notice(self,text):
        from cronos.wake import speak_activation_greeting
        try:
            if speak_activation_greeting(self.playing,respect_ui=True)=='unavailable':raise RuntimeError('A voz de confirmação não respondeu.')
        finally:self.playing.clear()

    def run(self,audio):
        if self.processing.is_set():return False
        self.processing.set();self.cancel=threading.Event();cancel=self.cancel
        self.pending=audio;started=time.perf_counter();turn=str(uuid4());recognition_ms=0
        self.turn=turn
        pending_file=folder()/'pending-recording.wav'
        try:
            pending_file.parent.mkdir(parents=True,exist_ok=True)
            pending_file.write_bytes(audio);pending_file.chmod(0o600)
        except OSError:pass # The current recording stays available in RAM.
        self.ui.phase('Transcrevendo a pergunta')
        client=self.connection.client
        speech_queue=queue.Queue(maxsize=2);speaker_error=[];playback_completed=None;voice_source=None;question=None;full_reply=None;stage='recognition'
        self.speaker=self.speaker_factory(self.cancel)
        def metric(status):
            data={'turn_id':turn,'source':'voice','chat_ms':round((time.perf_counter()-started)*1000),
                  'recognition_ms':recognition_ms,'status':status}
            if playback_completed is not None:data.update(playback_completed_ms=playback_completed,voice_source=voice_source)
            try:client.post('/panels/latency',json=data,timeout=3)
            except (httpx.HTTPError,RuntimeError,ValueError):pass
        def record(value):
            try:write_json(folder()/'last-delivery.json',value)
            except OSError:pass
        record({'stage':'captured','turn_id':turn})
        def enqueue(part):
            while not cancel.is_set() and not speaker_error:
                try:speech_queue.put(part,timeout=.1);return
                except queue.Full:continue
        def speak():
            nonlocal playback_completed,voice_source
            try:
                preferences=client.get('/panels').raise_for_status().json().get('preferences',{})
                volume=preferences.get('voice_volume',1);speed=preferences.get('voice_speed',1)
                local_only=False
                while not cancel.is_set():
                    try:part=speech_queue.get(timeout=.1)
                    except queue.Empty:continue
                    if part is None:return
                    self.playing.set();self.ui.phase('Respondendo')
                    source='fish'
                    try:
                        if local_only:raise RuntimeError('Device voice selected for this answer')
                        result=client.post('/voice/speech',json={'text':part,'format':'wav','speed':speed},headers={'X-Cronos-Turn':turn},timeout=10).raise_for_status()
                        if cancel.is_set():return
                        played=self.speaker.wav(result.content,volume)
                    except (httpx.HTTPError,ValueError,RuntimeError,OSError):
                        if cancel.is_set():return
                        source='device';local_only=True;played=self.speaker.local(part,volume)
                    if played and playback_completed is None:
                        # The native driver has completed actual playback, not
                        # just received TTS bytes. No fake wake greeting counts.
                        playback_completed=round((time.perf_counter()-started)*1000);voice_source=source;metric('responding')
                    self.playing.clear()
            except Exception as exc:
                speaker_error.append(type(exc).__name__)
            finally:
                if self.cancel is cancel:self.playing.clear()
        speaker_thread=threading.Thread(target=speak,daemon=True,name='cronos-answer-voice')
        try:
            if cancel.is_set():return False
            result=client.post('/voice/transcribe',content=audio,headers={'Content-Type':'audio/wav','X-Cronos-Turn':turn},timeout=55).raise_for_status().json()
            question=result.get('text','').strip()
            if not question:raise ValueError('A gravação não retornou uma pergunta reconhecida.')
            recognition_ms=round((time.perf_counter()-started)*1000)
            if self.cancel.is_set():return False
            if self.on_control and self.on_control(question):
                self.pending=None
                try:pending_file.unlink(missing_ok=True)
                except OSError:pass
                record({'stage':'control_dispatched','turn_id':turn});metric('completed');return True
            stage='answer';metric('waiting');self.ui.phase('Preparando a resposta');speaker_thread.start()
            introduced='';delivered=False;completed=False
            from cronos.wake import settings
            body={'message':question,'session_id':self.session,'screen_context':needs_screen(question) and settings()['screen_enabled']}
            if body['screen_context']:
                try:client.post('/assistant/screen',json={'consent':True,'enabled':True},timeout=4)
                except httpx.HTTPError:pass
                from cronos.desktop_page import page_context
                source=page_context()
                if source:body['page_context']=json.dumps(source,ensure_ascii=False)
            try:
                with client.stream('POST','/chat/stream',json=body,headers={'X-Cronos-Turn':turn},timeout=120) as response:
                    self.response=response;response.raise_for_status()
                    for line in response.iter_lines():
                        if self.cancel.is_set():return False
                        if not line.strip():continue
                        event=json.loads(line)
                        if event.get('type')=='error':
                            detail=str(event.get('detail',''))
                            if full_reply and 'não corresponde' not in detail and 'divergiu' not in detail:break
                            raise RuntimeError('A integração não concluiu a resposta; a gravação foi preservada.')
                        if event.get('type')=='intro' and not introduced:
                            introduced=event['reply']
                            for part in chunks(introduced):enqueue(part)
                        if event.get('type') in {'reply','result'}:
                            reply=event.get('reply') if event['type']=='reply' else event['result']['reply']
                            if not delivered:
                                if introduced and not reply.startswith(introduced):raise ValueError('A resposta inicial divergiu da resposta completa.')
                                full_reply=reply;delivered=True
                                if wants_card(question):self.ui.card('Resumo da tela' if needs_screen(question) else 'Resposta do Cronos',reply)
                                for part in chunks(reply[len(introduced):]):enqueue(part)
                            if event['type']=='result':
                                if full_reply!=reply:raise ValueError('O resultado final divergiu da resposta transmitida.')
                                completed=True
            except httpx.HTTPError:
                if not full_reply:raise
            if not full_reply:raise RuntimeError('A conversa terminou sem resposta completa.')
            stage='voice'
            enqueue(None)
            while speaker_thread.is_alive() and not self.cancel.wait(.1):pass
            if self.cancel.is_set():metric('cancelled');return False
            if speaker_error:raise RuntimeError('A resposta chegou, mas a voz não pôde ser reproduzida. Confira a saída de som e a voz em português.')
            if playback_completed is None:raise RuntimeError('Nenhum áudio de resposta foi reproduzido.')
            try:pending_file.unlink(missing_ok=True)
            except OSError:pass
            self.pending=None
            record({'stage':'completed','turn_id':turn,'voice':voice_source,'memory_confirmed':completed,'elapsed_ms':round((time.perf_counter()-started)*1000)})
            metric('completed');return True
        except Exception as exc:
            if self.cancel.is_set():metric('cancelled');return False
            metric('failed')
            if full_reply:self.ui.card('Resposta recebida · confira o áudio',full_reply)
            else:
                label={'recognition':'reconhecer sua gravação','answer':'obter a resposta da IA','voice':'reproduzir a voz'}[stage]
                status=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None
                suffix=f' Código HTTP {status}.' if status else ''
                self.ui.card('A pergunta foi preservada',f'Não consegui {label}.{suffix} No indicador, escolha “Tentar novamente” para reenviar a gravação. As etapas e tempos estão em Entendimento de linguagem → Entrega da última pergunta.')
            record({'stage':'failed','failed_stage':stage,'error_type':type(exc).__name__,'http_status':exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None,'turn_id':turn,'question_recognized':bool(question),'answer_received':bool(full_reply)})
            return False
        finally:
            if cancel.is_set():record({'stage':'cancelled','turn_id':turn})
            self.response=None;self.turn=None;self.cancel.set()
            if self.speaker:self.speaker.stop()
            speaker_thread.join(timeout=1) if speaker_thread.ident else None
            self.playing.clear();self.processing.clear();self.ui.phase('Na escuta')
