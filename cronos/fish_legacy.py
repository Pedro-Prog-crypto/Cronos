"""Compatibilidade limitada com o pedido JSON do cliente Fish legado."""
import httpx
from fishaudio.exceptions import APIError


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
                # Do not copy server bodies/credentials to errors or logs.
                raise APIError(response.status_code,'Pedido JSON legado recusado pelo provedor.')
            chunks=[];size=0
            async for chunk in response.aiter_bytes():
                size+=len(chunk)
                if size>16*1024*1024:
                    raise ValueError('Áudio ultrapassa o limite de 16 MiB.')
                chunks.append(chunk)
            if not size:
                raise ValueError('O provedor retornou áudio vazio.')
            return b''.join(chunks)
