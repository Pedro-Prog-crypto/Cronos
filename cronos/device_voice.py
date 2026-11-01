"""Portuguese Windows SAPI fallback rendered as WAV for the existing player."""
import asyncio
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import wave


SCRIPT = (
    "[Console]::InputEncoding=[Text.Encoding]::UTF8;"
    "$ErrorActionPreference='Stop';"
    "$data=[Console]::In.ReadToEnd()|ConvertFrom-Json;"
    "$v=New-Object -ComObject SAPI.SpVoice;$found=$false;"
    "foreach($voice in $v.GetVoices()){if($voice.GetAttribute('Language') -match '(^|;)0?416($|;)|(^|;)0?816($|;)'){$v.Voice=$voice;$found=$true;break}};"
    "if(-not $found){exit 2};"
    "$stream=New-Object -ComObject SAPI.SpMemoryStream;$stream.Format.Type=18;"
    "$v.AudioOutputStream=$stream;$v.Rate=[Math]::Min(5,[Math]::Max(-5,[int]$data.rate));"
    "$null=$v.Speak([string]$data.text);"
    "[Console]::Write([Convert]::ToBase64String([byte[]]$stream.GetData()));$stream.Close()"
)


def _render(text, speed, cancelled):
    if sys.platform != 'win32': raise RuntimeError('A voz de reserva do Windows não está disponível neste sistema.')
    executable=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    payload=json.dumps({'text':text,'rate':round((speed-1)*5)},ensure_ascii=False).encode('utf-8')
    process=subprocess.Popen([str(executable),'-NoLogo','-NoProfile','-NonInteractive','-Command',SCRIPT],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,shell=False,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        deadline=time.monotonic()+30
        while True:
            if cancelled.is_set() or time.monotonic()>deadline:raise RuntimeError('A síntese local foi interrompida ou não concluiu.')
            try:
                output,_=process.communicate(input=payload,timeout=.1)
                break
            except subprocess.TimeoutExpired:payload=None
        if process.returncode:raise RuntimeError('Não há uma voz em português disponível no Windows. Instale Português em Configurações → Hora e idioma → Fala.')
        if len(output)>16*1024*1024:raise RuntimeError('A voz local devolveu áudio acima do limite.')
        try:audio=base64.b64decode(output.strip(),validate=True)
        except ValueError:raise RuntimeError('A voz local não devolveu áudio válido.') from None
        if not audio:raise RuntimeError('A voz local devolveu áudio vazio.')
        if audio[:4]!=b'RIFF':
            result=io.BytesIO()
            with wave.open(result,'wb') as target:
                target.setnchannels(1);target.setsampwidth(2);target.setframerate(16000);target.writeframes(audio)
            audio=result.getvalue()
        return audio
    finally:
        if process.poll() is None:
            process.kill();process.communicate()


async def synthesize(text, speed=1):
    cancelled=threading.Event()
    try:return await asyncio.to_thread(_render,text,speed,cancelled)
    finally:cancelled.set()
