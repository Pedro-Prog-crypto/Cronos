"""Live transport adapted from core/gemini.py in the user's original Kronos.

Original: Copyright (c) 2026 FatihMakes, MARK LV — JARVIS, CC BY-NC 4.0.
Adaptation: new settings/history/structured-output integration for Kronos.
See licenses/ORIGINAL-KRONOS-LICENSE.txt for the original license.

Keep the original connect/send/transcription workflow, not its persona suppression,
proactive messages, OS commands, or microphone/speaker ownership.
"""
import asyncio
import hashlib
import re
import time
from cronos import conversation_metrics
from cronos import usage
from cronos.reply_stream import ready_reply,deliver,ready_intro,deliver_intro
from cronos.providers import OUTPUT_RULES,ProviderError,parse_reply,record_gemini_error

ORIGINAL_MODELS=('models/gemini-3.1-flash-live-preview','models/gemini-2.5-flash-native-audio-preview-12-2025')

def make_client(key):
    from google import genai
    return genai.Client(api_key=key,http_options={'api_version':'v1beta'})

async def turn(client,model,system,messages):
    from google.genai import types
    started=time.perf_counter();metrics={}
    delivered=False;intro_delivered=False
    config=types.LiveConnectConfig(response_modalities=['AUDIO'],output_audio_transcription={},system_instruction=system+'\n'+OUTPUT_RULES)
    async with client.aio.live.connect(model=model,config=config) as session:
        metrics['connection_ms']=round((time.perf_counter()-started)*1000)
        turns=[]
        for message in messages:
            parts=[{'text':message['content']}]
            if message.get('image'):
                image=message['image'];parts.append({'inline_data':{'mime_type':image['mime_type'],'data':image['data']}})
            turns.append({'role':'model' if message['role']=='assistant' else 'user','parts':parts})
        await session.send_client_content(turns=turns,turn_complete=True)
        sent=time.perf_counter();chunks=[]
        async def drain():
            nonlocal delivered,intro_delivered
            async for response in session.receive():
                content=getattr(response,'server_content',None)
                transcription=getattr(content,'output_transcription',None)
                if getattr(transcription,'text',None):
                    if not chunks:metrics['first_transcription_ms']=round((time.perf_counter()-sent)*1000)
                    chunks.append(transcription.text)
                    candidate=re.sub(r'^```(?:json)?\s*|\s*```$','', ''.join(chunks).strip(),flags=re.I)
                    if not intro_delivered:
                        intro=ready_intro(candidate)
                        if intro:
                            await deliver_intro(intro);intro_delivered=True
                            metrics['intro_ready_ms']=round((time.perf_counter()-sent)*1000)
                    if not delivered:
                        early=ready_reply(candidate)
                        if early:
                            await deliver(early);delivered=True
                            metrics['reply_ready_ms']=round((time.perf_counter()-sent)*1000)
                    if candidate.endswith('}'):
                        try:parse_reply(candidate)
                        except ProviderError:pass
                        else:return True  # Full validated payload; discarded audio needs no further draining.
                if getattr(content,'turn_complete',False):return True
            return False
        complete=await drain()
        if not complete:
            try:await asyncio.wait_for(drain(),1.5)
            except asyncio.TimeoutError:pass
        raw=''.join(chunks).strip()
        # Some Live models wrap valid structured output in markdown fences.
        raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw,flags=re.I)
        result=parse_reply(raw)
        metrics['response_ready_ms']=round((time.perf_counter()-sent)*1000)
        conversation_metrics.save_live(metrics)
        return result

async def reply(settings,system,messages):
    primary=settings.gemini_live_model
    if not re.fullmatch(r'(?:models/)?[\w.-]+',primary):raise ProviderError('GEMINI_LIVE_MODEL inválido.')
    models=list(dict.fromkeys((primary,*ORIGINAL_MODELS))) if primary in ORIGINAL_MODELS else [primary]
    characters=len(system)+len(OUTPUT_RULES)+sum(len(m['content']) for m in messages)
    last=None
    for model in models:
        identity=hashlib.sha256((settings.gemini_key.strip()+'|live|'+model).encode()).hexdigest()
        remaining=usage.remaining(identity)
        if remaining>0:raise ProviderError(f'Gemini Live: pausa ativa por {int(remaining)+1} segundos. Nenhuma sessão nova foi aberta.',429)
        client=None
        try:
            client=make_client(settings.gemini_key.strip())
            result=await asyncio.wait_for(turn(client,model,system,messages),settings.provider_timeout)
            usage.audit(model,200,characters);usage.clear_pause(identity)
            return result
        except ImportError:
            raise ProviderError('Instale a integração Gemini original: execute Instalar-Cronos.bat novamente.') from None
        except ProviderError as exc:
            usage.audit(model,502,characters)
            raise ProviderError('Gemini Live: '+str(exc),502) from None
        except asyncio.TimeoutError:
            usage.audit(model,504,characters)
            raise ProviderError('Gemini Live: tempo de resposta esgotado.',504) from None
        except Exception as exc:
            code=getattr(exc,'code',None)
            # Inspect privately for classification; never echo SDK bodies or websocket reasons.
            reason=str(exc).lower()
            if code==429 or 'resource_exhausted' in reason or 'quota' in reason:
                usage.audit(model,429,characters);usage.pause(identity,60)
                message='Gemini Live: o provedor informou limite de uso (429). A rota Live também possui cota; nenhum plano foi ativado.'
                record_gemini_error(429,message)
                raise ProviderError(message,429) from None
            status=code if code in {404,500,503} else 503
            usage.audit(model,status,characters)
            last=ProviderError('Gemini Live: conexão recusada ou modelo indisponível. Confira o acesso à API Live nesta chave.',503)
            if code in {401,403} or 'api_key_invalid' in reason:break
        finally:
            if client is not None:
                try:await client.aio.aclose()
                except Exception:pass
    raise last or ProviderError('Gemini Live indisponível.')
