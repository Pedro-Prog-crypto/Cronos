"""Reconhecimento português local leve, sem usar créditos Fish."""
import argparse
import io
import json
import threading
import wave
import re
from array import array
from cronos import wake


def check_signal(frames):
    """Reject digital silence, not quiet voices. Browser VAD handles speech/noise."""
    samples=array('h');samples.frombytes(frames)
    import sys
    if sys.byteorder!='little':samples.byteswap()
    if not samples or max(map(abs,samples))<32 or sum(abs(v)>=12 for v in samples)<min(160,len(samples)//20):
        raise ValueError('Não há sinal de voz suficiente nesta gravação. Nada foi enviado à IA; tente falar novamente.')


def read_pcm(audio):
    try:
        with wave.open(io.BytesIO(audio),'rb') as reader:
            if (reader.getnchannels(),reader.getsampwidth(),reader.getframerate())!=(1,2,16000):
                raise ValueError('Áudio requer WAV mono, PCM 16 bits, 16 kHz.')
            if not 1<=reader.getnframes()<=61*16000:raise ValueError('Gravação deve conter áudio e durar no máximo 61 segundos.')
            frames=reader.readframes(reader.getnframes())
            if len(frames)!=reader.getnframes()*2:raise ValueError('Áudio WAV incompleto.')
            return frames
    except (wave.Error,EOFError):raise ValueError('Áudio WAV inválido.') from None


class LocalRecognizer:
    def __init__(self):
        self.model=None
        self.lock=threading.Lock()

    def _load(self):
        try:
            from vosk import Model,KaldiRecognizer,SetLogLevel
        except ImportError:
            raise ValueError('Execute Instalar-Cronos.bat para instalar o reconhecimento local.') from None
        if self.model is None:
            try:folder=wake.verify_model()
            except ValueError:
                raise ValueError('Modelo português ausente. Execute Instalar-Cronos.bat para prepará-lo.') from None
            SetLogLevel(-1)
            try:self.model=Model(str(folder))
            except Exception:raise ValueError('Não foi possível carregar o modelo português local.') from None
        return KaldiRecognizer

    def prepare(self):
        with self.lock:self._load()

    def keyword_listener(self):
        with self.lock:
            factory=self._load()
            words=[word for word in ('cronos','kronos','chronos') if self.model.vosk_model_find_word(word)>=0]
            # The shipped Portuguese model lacks the proper name Cronos.
            # Its closest supported pronunciation is "cromos" (validated
            # with spoken Cronos). Unknown speech stays [unk], rather than
            # forcing all input into the wake word.
            if not words:words=['cromos']
            grammar=json.dumps([*words,'[unk]'])
            recognizer=factory(self.model,16000,grammar)
        if hasattr(recognizer,'SetWords'):recognizer.SetWords(True)
        def confirm(frames):
            probe=factory(self.model,16000,grammar);probe.SetWords(True)
            probe.AcceptWaveform(frames+bytes(16000))
            data=json.loads(probe.FinalResult())
            hits=[w for w in data.get('result',[]) if w.get('word') in words]
            return any(w.get('conf',0)>=.92 and .25<=w.get('end',0)-w.get('start',0)<=1.1 for w in hits)
        return KeywordListener(recognizer,words,confirm)

    def transcribe(self,audio):
        frames=read_pcm(audio)
        check_signal(frames)
        with self.lock:
            KaldiRecognizer=self._load()
            recognizer=KaldiRecognizer(self.model,16000);parts=[];confidences=[]
            if hasattr(recognizer,'SetWords'):recognizer.SetWords(True)
            def collect(data):
                parts.append(data.get('text',''))
                confidences.extend(word['conf'] for word in data.get('result',[]) if isinstance(word,dict) and isinstance(word.get('conf'),(float,int)))
            for start in range(0,len(frames),8000):
                if recognizer.AcceptWaveform(frames[start:start+8000]):collect(json.loads(recognizer.Result()))
            collect(json.loads(recognizer.FinalResult()))
            text=' '.join(text.strip() for text in parts if text.strip())
            if not text or (confidences and sum(confidences)/len(confidences)<.55):
                raise ValueError('Não consegui reconhecer a fala com segurança. Repita a pergunta mais perto do microfone; ela não foi enviada à IA.')
            return text


class KeywordListener:
    """Stable keyword hypotheses with an explicit unknown-speech alternative."""
    def __init__(self,recognizer,words=('cronos','kronos','chronos'),confirm=None):
        self.recognizer=recognizer
        self.words=set(words)
        self.stable=0
        self.confirm=confirm
        self.frames=b''

    def feed(self,frames):
        if self.confirm:self.frames=(self.frames+frames)[-64000:]
        final=self.recognizer.AcceptWaveform(frames)
        data=json.loads(self.recognizer.Result() if final else self.recognizer.PartialResult())
        text=data.get('text' if final else 'partial','').casefold()
        found=bool(set(re.findall(r'\w+',text))&self.words)
        if final:
            self.stable=0
            words=[w for w in data.get('result',[]) if w.get('word','').casefold() in self.words]
            return found and bool(words) and all(w.get('conf',0)>=.92 for w in words)
        self.stable=self.stable+1 if found else 0
        return self.stable>=2 and (self.confirm is None or (self.stable%3==2 and self.confirm(self.frames)))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    if args.prepare:
        try:
            wake.prepare_model()
            print('Modelo português preparado. Nenhum microfone foi ativado.')
        except Exception:
            print('Falha ao preparar modelo português. Confira internet e execute a instalação novamente.')
            raise SystemExit(1) from None


if __name__=='__main__':main()
