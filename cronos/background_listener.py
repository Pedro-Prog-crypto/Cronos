"""Native microphone ownership and bounded recording, separate from UI launch."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import io
import json
import math
import os
import queue
import struct
import subprocess
import threading
import time
import wave


def rms(frame):
    if not frame or len(frame)%2:return 0
    values=struct.unpack('<'+'h'*(len(frame)//2),frame)
    return math.sqrt(sum(value*value for value in values)/len(values))


class Capture:
    """Retain an entire spoken turn; silence endpoint and manual submit coexist."""
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.frames=[];self.armed=False;self.started=0;self.last_voice=None;self.bytes=0
    def arm(self,initial=()):
        self.frames=list(initial);self.bytes=sum(map(len,self.frames));self.armed=True;self.started=self.clock();self.last_voice=None
    def feed(self,frame,recognized=False):
        if not self.armed:return None
        self.frames.append(frame);self.bytes+=len(frame)
        if rms(frame)>180 or recognized and self.last_voice is None:self.last_voice=self.clock()
        silence=self.last_voice is not None and self.clock()-self.last_voice>1.3
        if silence or self.bytes>=16000*2*180:return self.submit()
        if self.last_voice is None and self.clock()-self.started>20:self.clear()
        return None
    def submit(self):
        if not self.armed:return None
        raw=b''.join(self.frames);self.clear()
        if len(raw)<3200:return None
        output=io.BytesIO()
        with wave.open(output,'wb') as target:target.setnchannels(1);target.setsampwidth(2);target.setframerate(16000);target.writeframes(raw)
        return output.getvalue()
    def clear(self):self.frames=[];self.armed=False;self.bytes=0;self.last_voice=None


def launch_window():
    from pathlib import Path
    from cronos.wake import app_launch_module,python_windowless,independent_environment
    return subprocess.Popen([str(python_windowless()),'-m',app_launch_module()],cwd=Path(__file__).resolve().parents[1],
        shell=False,env=independent_environment(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def hide_window():
    import ctypes
    from ctypes import wintypes
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR];user.FindWindowW.restype=wintypes.HWND
    window=user.FindWindowW(None,'Cronos')
    if window:
        # Close the UI, not the resident backend; it releases its microphone.
        user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
        user.PostMessageW(window,0x0010,0,0)


def run(ui=None):
    started_at=float(os.environ.get('CRONOS_WAKE_STARTED') or time.time())
    from pathlib import Path
    from cronos import wake
    from cronos.resident import ensure,request_stop
    from cronos.background_conversation import NativeConversation
    from cronos.desktop_overlay import Overlay
    from cronos.persistent_data import activate
    activate(Path(__file__).resolve().parents[1])
    with wake.single_instance('CronosVoiceLauncher') as acquired:
        if not acquired:return
        model_path=wake.verify_model()
        connection=ensure();ui=ui or Overlay();conversation=NativeConversation(connection,ui)
        stopped=threading.Event();failures=[];executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='cronos-background-turn')
        def worker():
            import sounddevice
            from vosk import KaldiRecognizer,Model,SetLogLevel
            SetLogLevel(-1);model=Model(str(model_path))
            ui_owned=threading.Event()
            frames=queue.Queue(maxsize=30);capture=Capture();history=deque(maxlen=1800)
            config=wake.settings();trigger=wake.Trigger(config)
            def recognizer():
                value=KaldiRecognizer(model,16000,json.dumps([*wake.command_phrases(config),'[unk]'],ensure_ascii=False));value.SetWords(True);return value
            keyword=recognizer();full=KaldiRecognizer(model,16000)
            stop_file=wake.root()/'stop.request'
            try:
                if stop_file.stat().st_mtime<=started_at:stop_file.unlink(missing_ok=True)
            except FileNotFoundError:pass
            heartbeat=0;owned=False;greeting=None;screen_on=False;maintenance=None;last_voice_at=None
            maintenance_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='cronos-screen-lease')
            def renew_screen():
                nonlocal screen_on
                try:
                    if config['background_enabled'] and config['screen_enabled'] and not wake.ui_is_listening():
                        connection.client.post('/assistant/screen',json={'consent':True,'enabled':True},timeout=4).raise_for_status();screen_on=True
                    elif not config['screen_enabled'] or not config['background_enabled']:
                        connection.client.post('/assistant/screen',json={'consent':True,'enabled':False},timeout=4);screen_on=False
                except Exception:screen_on=False
            def audio(data,count,timing,status):
                if conversation.playing.is_set() or ui_owned.is_set():return
                try:frames.put_nowait(bytes(data))
                except queue.Full:
                    try:frames.get_nowait()
                    except queue.Empty:pass
                    try:frames.put_nowait(bytes(data))
                    except queue.Full:pass
            def submit(value):
                if value and not conversation.processing.is_set():executor.submit(conversation.run,value)
            def route_control(text):
                from cronos.desktop_state import control_intent
                action=control_intent(text,wake.settings())
                if action=='show':launch_window()
                elif action=='hide':hide_window()
                elif action in {'paused','resumed'}:
                    wake.set_paused(action=='paused');capture.clear()
                elif action in {'screen_on','screen_off'}:
                    enabled=action=='screen_on';wake.save_settings({'screen_enabled':enabled})
                    connection.client.post('/assistant/screen',json={'consent':True,'enabled':enabled},timeout=4).raise_for_status()
                else:return False
                return True
            conversation.on_control=route_control
            input_stream=None
            try:
                while not stopped.is_set() and not stop_file.exists():
                    wants_ui=wake.ui_owns_microphone()
                    if wants_ui and input_stream is not None:
                        input_stream.__exit__(None,None,None);input_stream=None
                    elif not wants_ui and input_stream is None:
                        input_stream=sounddevice.RawInputStream(samplerate=16000,blocksize=1600,dtype='int16',channels=1,callback=audio)
                        input_stream.__enter__();ui.phase('Na escuta')
                    if input_stream is not None and not getattr(input_stream,'active',True):raise OSError('O microfone foi desconectado.')
                    next_config=wake.settings()
                    if next_config!=config:
                        config=next_config;trigger=wake.Trigger(config);keyword=recognizer();capture.clear()
                    if time.monotonic()-heartbeat>4:
                        wake._write_status('paused' if wake.paused() else 'listening')
                        if maintenance is None or maintenance.done():maintenance=maintenance_pool.submit(renew_screen)
                        heartbeat=time.monotonic()
                    try:
                        action=ui.actions.get_nowait()
                        if action=='exit':stopped.set();request_stop();break
                        if action=='show':launch_window()
                        if action=='pause':wake.set_paused(not wake.paused());capture.clear();conversation.stop();ui.phase('Pausado' if wake.paused() else 'Na escuta')
                        if action=='screen':wake.save_settings({'screen_enabled':not config['screen_enabled']});heartbeat=0
                        if action=='cancel':conversation.stop();capture.clear()
                        if action=='submit':submit(capture.submit())
                        if action=='retry':
                            if conversation.pending:submit(conversation.pending)
                            else:
                                directory=__import__('cronos.resident',fromlist=['folder']).folder()
                                path=directory/'pending-recording.wav'
                                try:
                                    previous=json.loads((directory/'last-delivery.json').read_text())
                                    if previous.get('stage')!='completed' and path.stat().st_size<=6*1024*1024:submit(path.read_bytes())
                                except (OSError,ValueError):pass
                    except queue.Empty:pass
                    if greeting is not None and greeting.done():
                        try:greeting.result()
                        except Exception:ui.card('Voz indisponível','O chamado foi reconhecido, mas não consegui reproduzir a confirmação. Confira a saída de som.')
                        greeting=None
                        if not wake.paused() and not wake.ui_is_listening():
                            capture.arm();full=KaldiRecognizer(model,16000);keyword=recognizer();ui.phase('Ouvindo sua pergunta')
                        while not frames.empty():
                            try:frames.get_nowait()
                            except queue.Empty:break
                    if conversation.playing.is_set():
                        history.clear();capture.clear();time.sleep(.05);continue
                    if wake.ui_owns_microphone():
                        ui_owned.set()
                        if not owned:capture.clear();history.clear();keyword=recognizer();owned=True
                        time.sleep(.1);continue
                    ui_owned.clear()
                    if owned:
                        while not frames.empty():
                            try:frames.get_nowait()
                            except queue.Empty:break
                        keyword=recognizer();owned=False
                    try:frame=frames.get(timeout=.1)
                    except queue.Empty:continue
                    if capture.armed:
                        recognized=full.AcceptWaveform(frame)
                        if recognized:recognized=bool(json.loads(full.Result()).get('text','').strip())
                        value=capture.feed(frame,recognized)
                        if value:submit(value);keyword=recognizer();history.clear()
                        elif not capture.armed:ui.phase('Na escuta')
                        continue
                    history.append(frame)
                    if rms(frame)>180:last_voice_at=time.monotonic()
                    if not keyword.AcceptWaveform(frame):continue
                    heard=json.loads(keyword.Result());action=trigger.action(heard)
                    if not action:
                        text=wake.normalize_phrase(heard.get('text',''))
                        # A single utterance "Cronos, [question]" retains the
                        # original audio; the command grammar's [unk] text
                        # is never treated as the user's actual question.
                        name=wake.normalize_phrase(config['activation_phrase']);names={name}
                        if name in {'cronos','kronos','chronos'}:names.update({'cronos','cromos','kronos','chronos'})
                        if config['background_enabled'] and not wake.paused() and any(text.startswith(name+' ') for name in names):
                            capture.arm(history);capture.last_voice=last_voice_at or time.monotonic()
                            full=KaldiRecognizer(model,16000);ui.phase('Ouvindo sua pergunta')
                        history.clear();continue
                    wake._write_status('paused' if wake.paused() else 'listening',last_heard=trigger.last_heard,last_action=action,last_confidence=trigger.last_confidence)
                    if action=='show':launch_window()
                    elif action=='hide':hide_window()
                    elif action=='activate' and config['background_enabled'] and greeting is None and not conversation.processing.is_set():
                        greeting=executor.submit(conversation.say_notice,wake.WAKE_GREETING)
                    elif action=='paused':capture.clear();conversation.stop();ui.phase('Pausado')
                    elif action=='resumed':ui.phase('Na escuta')
                    history.clear();keyword=recognizer()
            except Exception as exc:
                failures.append(exc)
                wake._write_status('error',reason='microphone_unavailable' if exc.__class__.__name__=='PortAudioError' else 'unknown')
                ui.card('Escuta interrompida','Não consegui manter a entrada de áudio. Confira o microfone e sua permissão no Windows. A janela principal não foi aberta.')
                ui.phase('Microfone indisponível');stopped.wait(3)
            finally:
                if input_stream is not None:
                    try:input_stream.__exit__(None,None,None)
                    except OSError:pass
                conversation.stop()
                if screen_on and not wake.ui_is_listening():
                    try:connection.client.post('/assistant/screen',json={'consent':True,'enabled':False},timeout=3)
                    except Exception:pass
                maintenance_pool.shutdown(wait=False,cancel_futures=True)
                connection.close();ui.close()
                if not failures:wake._write_status('stopped')
        thread=threading.Thread(target=worker,daemon=True,name='cronos-native-listener');thread.start()
        try:ui.run()
        finally:stopped.set();conversation.stop();thread.join(timeout=6);executor.shutdown(wait=False,cancel_futures=True)
        if failures:raise failures[0]
