"""Bounded Gemini SSE reception for long Studio outputs (conversation is unchanged)."""
import json
from contextvars import ContextVar

import httpx

progress_sink=ContextVar('studio_generation_progress',default=None)
checkpoint_sink=ContextVar('studio_delivery_checkpoint',default=None)
MAX_OUTPUT=700_000


async def receive(client,url,headers,payload):
    from cronos.providers import ProviderError
    text=[];characters=0;latest={};usage={};feedback={}
    try:
        async with client.stream('POST',url.replace(':generateContent',':streamGenerateContent')+'?alt=sse',headers=headers,json=payload) as response:
            if not response.is_success:
                error=bytearray()
                async for chunk in response.aiter_bytes():
                    error.extend(chunk[:max(0,131072-len(error))])
                    if len(error)>=131072:break
                httpx.Response(response.status_code,headers=response.headers,content=bytes(error),request=response.request).raise_for_status()
            response.raise_for_status()
            # JSON responses are accepted for gateways and deterministic tests.
            if 'text/event-stream' not in response.headers.get('content-type',''):
                raw=bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw)>4*MAX_OUTPUT:raise ProviderError('Entrega estruturada acima do limite permitido.',502,kind='format')
                return httpx.Response(response.status_code,headers=response.headers,content=bytes(raw),request=response.request)
            data=[]
            async def event():
                nonlocal characters,latest,usage,feedback
                if not data:return
                value='\n'.join(data);data.clear()
                if value=='[DONE]':return
                obj=json.loads(value)
                if not isinstance(obj,dict):raise ValueError('invalid event')
                if obj.get('error'):raise ProviderError('A integração interrompeu o fluxo estruturado.',503,kind='output_interrupted',partial_output=''.join(text))
                feedback=obj.get('promptFeedback',feedback);usage=obj.get('usageMetadata',usage)
                candidates=obj.get('candidates') or []
                if candidates:
                    latest=candidates[0]
                    chunk=''.join(part.get('text','') for part in latest.get('content',{}).get('parts',[]) if not part.get('thought'))
                    text.append(chunk);characters+=len(chunk)
                    if characters>MAX_OUTPUT:raise ProviderError('Entrega estruturada acima do limite permitido.',502,kind='format')
                    sink=progress_sink.get()
                    if chunk and sink:await sink(characters,lambda:''.join(text))
            async for line in response.aiter_lines():
                if len(line)>4*MAX_OUTPUT:raise ValueError('oversized event')
                if not line:await event()
                elif line.startswith('data:'):data.append(line[5:].lstrip())
            await event()
            obj={'candidates':[{**latest,'content':{'parts':[{'text':''.join(text)}]}}], 'usageMetadata':usage,'promptFeedback':feedback}
            return httpx.Response(200,json=obj,request=response.request)
    except (httpx.RequestError,ValueError) as exc:
        if text:raise ProviderError('O fluxo da integração foi interrompido após receber parte da entrega.',502,kind='output_interrupted',partial_output=''.join(text)) from None
        raise
