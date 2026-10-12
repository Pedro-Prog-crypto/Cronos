"""Compatibilidade limitada com o pedido JSON do cliente Fish legado."""
import io
import wave
import json
import re
import httpx
from fishaudio.exceptions import APIError


def safe_error_detail(raw, secrets=()):
    try:
        data=json.loads(raw)
    except (ValueError, UnicodeError):
        return 'O provedor não retornou um motivo JSON reconhecível.'
    messages=[]
    def collect(value, depth=0):
        if depth>3 or len(messages)>=3:return
        if isinstance(value,str):messages.append(value)
        elif isinstance(value,list):
            for item in value[:3]:collect(item,depth+1)
        elif isinstance(value,dict):
            for name in ('message','msg','detail','error'):
                if name in value:collect(value[name],depth+1)
    collect(data)
    text=' | '.join(messages)
    for secret in secrets:
        if secret:text=text.replace(secret,'[oculto]')
    text=re.sub(r'Bearer\s+[^\s"<>]+','Bearer [oculto]',text,flags=re.I)
    text=re.sub(r'[A-Za-z0-9_-]{24,}(?:\.[A-Za-z0-9_-]+)*','[oculto]',text)
    text=' '.join(text.split())[:500]
    return text or 'O provedor não retornou um motivo JSON reconhecível.'


def finalize_wav(audio):
    # Fish streaming WAV may advertise 0xffffffff data bytes until closed.
    # Preserve PCM samples, rebuild finite RIFF lengths for browser/Windows players.
    try:
        with wave.open(io.BytesIO(audio),'rb') as reader:
            channels,width,rate=reader.getnchannels(),reader.getsampwidth(),reader.getframerate()
            frames=reader.readframes(len(audio)//max(1,channels*width))
        output=io.BytesIO()
        with wave.open(output,'wb') as writer:
            writer.setnchannels(channels);writer.setsampwidth(width);writer.setframerate(rate);writer.writeframes(frames)
        return output.getvalue()
    except (wave.Error,EOFError,ValueError,OverflowError):
        raise ValueError('O provedor retornou WAV inválido.') from None


async def synthesize_json(api_key, *, text, reference_id=None, format='mp3',
                          speed=1.0, latency='balanced', transport=None):
    payload={'text':text,'format':format,'latency':latency,'normalize':True}
    if format in {'wav','pcm'}:
        payload['sample_rate']=24000
    if reference_id:
        payload['reference_id']=reference_id
    if abs(speed-1.0)>.01:
        payload['prosody']={'speed':speed,'volume':0,'normalize_loudness':True}
    async with httpx.AsyncClient(timeout=30,follow_redirects=False,transport=transport) as client:
        async with client.stream('POST','https://api.fish.audio/v1/tts',
            headers={'Authorization':'Bearer '+api_key,'model':'s2.1-pro-free','Content-Type':'application/json'},
            json=payload) as response:
            if response.status_code!=200:
                raw=bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk[:max(0,8192-len(raw))])
                    if len(raw)>=8192:break
                error=APIError(response.status_code,'Pedido JSON legado recusado pelo provedor.')
                error.safe_detail=safe_error_detail(bytes(raw),(api_key,reference_id))
                raise error
            chunks=[];size=0
            async for chunk in response.aiter_bytes():
                size+=len(chunk)
                if size>16*1024*1024:
                    raise ValueError('Áudio ultrapassa o limite de 16 MiB.')
                chunks.append(chunk)
            if not size:
                raise ValueError('O provedor retornou áudio vazio.')
            audio=b''.join(chunks)
            return finalize_wav(audio) if format=='wav' else audio
