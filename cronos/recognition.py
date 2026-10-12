"""Reconhecimento português local leve, sem usar créditos Fish."""
import argparse
import io
import json
import threading
import wave
from cronos import wake


class LocalRecognizer:
    def __init__(self):
        self.model=None
        self.lock=threading.Lock()

    def transcribe(self,audio):
        try:
            with wave.open(io.BytesIO(audio),'rb') as reader:
                if (reader.getnchannels(),reader.getsampwidth(),reader.getframerate())!=(1,2,16000):
                    raise ValueError('Reconhecimento local requer WAV mono, PCM 16 bits, 16 kHz.')
                if reader.getnframes()>61*16000:raise ValueError('Gravação local ultrapassou 60 segundos.')
                frames=reader.readframes(reader.getnframes())
        except (wave.Error,EOFError):
            raise ValueError('Áudio WAV inválido para reconhecimento local.') from None
        with self.lock:
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
            recognizer=KaldiRecognizer(self.model,16000);parts=[]
            for start in range(0,len(frames),8000):
                if recognizer.AcceptWaveform(frames[start:start+8000]):parts.append(json.loads(recognizer.Result()).get('text',''))
            parts.append(json.loads(recognizer.FinalResult()).get('text',''))
            return ' '.join(text.strip() for text in parts if text.strip())


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
