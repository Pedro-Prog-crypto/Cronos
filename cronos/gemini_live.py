"""Live transport adapted from core/gemini.py in the user's original Kronos.

Original: Copyright (c) 2026 FatihMakes, MARK LV — JARVIS, CC BY-NC 4.0.
Adaptation: new settings/history/structured-output integration for Kronos.
See licenses/ORIGINAL-KRONOS-LICENSE.txt for the original license.

Keep the original connect/send/transcription workflow, not its persona suppression,
proactive messages, OS commands, or microphone/speaker ownership.
"""
import asyncio
from contextlib import AsyncExitStack
import hashlib
import re
import time
from cronos import conversation_metrics
from cronos import usage
from cronos.reply_stream import ready_reply,deliver,ready_intro,deliver_intro,deliver_transcript
from cronos.providers import OUTPUT_RULES,ProviderError,record_gemini_error
from cronos.live_output import parse_live_output

ORIGINAL_MODELS=('models/gemini-3.1-flash-live-preview','models/gemini-2.5-flash-native-audio-preview-12-2025')
# A detailed answer may take longer than a short response. Silence has its own
# deadline, so an inactive connection does not consume the full answer budget.
LIVE_ATTEMPT_TIMEOUT_SECONDS=180
LIVE_TOTAL_TIMEOUT_SECONDS=180
LIVE_CONNECT_TIMEOUT_SECONDS=8
LIVE_FIRST_EVENT_TIMEOUT_SECONDS=10
LIVE_IDLE_TIMEOUT_SECONDS=15

def make_client(key):
    from google import genai
    return genai.Client(api_key=key,http_options={'api_version':'v1beta'})

async def turn(client,model,system,messages,thinking_budget=0):
    from google.genai import types
    started=time.perf_counter();metrics={}
    delivered=False;intro_delivered=False;turn_finished=False;input_finished=False
    audio=messages[-1].get('audio_pcm') if messages else None
    config=types.LiveConnectConfig(response_modalities=['AUDIO'],output_audio_transcription={},thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),system_instruction=system+'\n'+OUTPUT_RULES,**({'input_audio_transcription':{},'realtime_input_config':{'automatic_activity_detection':{'disabled':True}}} if audio is not None else {}))
    async with AsyncExitStack() as stack:
        session = await asyncio.wait_for(stack.enter_async_context(client.aio.live.connect(model=model,config=config)), LIVE_CONNECT_TIMEOUT_SECONDS)
        metrics['connection_ms']=round((time.perf_counter()-started)*1000)
        turns=[]
        for message in (messages[:-1] if audio is not None else messages):
            parts=[{'text':message['content']}]
            if message.get('image'):
                image=message['image'];parts.append({'inline_data':{'mime_type':image['mime_type'],'data':image['data']}})
            turns.append({'role':'model' if message['role']=='assistant' else 'user','parts':parts})
        if audio is None:
            await session.send_client_content(turns=turns,turn_complete=True)
        else:
            if messages[-1].get('image'):
                image=messages[-1]['image'];turns.append({'role':'user','parts':[{'text':'Captura atual compartilhada pelo senhor; use somente se relevante à pergunta falada.'},{'inline_data':{'mime_type':image['mime_type'],'data':image['data']}}]})
            if turns:await session.send_client_content(turns=turns,turn_complete=False)
            await session.send_realtime_input(activity_start=types.ActivityStart())
            for offset in range(0,len(audio),8192):
                await session.send_realtime_input(audio=types.Blob(data=audio[offset:offset+8192],mime_type='audio/pcm;rate=16000'))
            await session.send_realtime_input(activity_end=types.ActivityEnd())
        sent=time.perf_counter();chunks=[];input_chunks=[];transcript_delivered=False
        async def drain():
            nonlocal delivered,intro_delivered,transcript_delivered,turn_finished,input_finished
            iterator = session.receive().__aiter__()
            while True:
                try:
                    response = await asyncio.wait_for(anext(iterator), LIVE_IDLE_TIMEOUT_SECONDS if chunks or input_chunks else LIVE_FIRST_EVENT_TIMEOUT_SECONDS)
                except StopAsyncIteration:
                    break
                content=getattr(response,'server_content',None)
                recognized=getattr(content,'input_transcription',None)
                if getattr(recognized,'text',None):input_chunks.append(recognized.text)
                if audio is not None and getattr(recognized,'finished',False) and input_chunks and not transcript_delivered:
                    input_finished=True
                    await deliver_transcript(''.join(input_chunks).strip());transcript_delivered=True
                transcription=getattr(content,'output_transcription',None)
                if getattr(transcription,'text',None):
                    if not chunks:metrics['first_transcription_ms']=round((time.perf_counter()-sent)*1000)
                    chunks.append(transcription.text)
                    candidate=re.sub(r'^```(?:json)?\s*|\s*```$','', ''.join(chunks).strip(),flags=re.I)
                    if not intro_delivered and (audio is None or transcript_delivered):
                        intro=ready_intro(candidate)
                        if intro:
                            await deliver_intro(intro);intro_delivered=True
                            metrics['intro_ready_ms']=round((time.perf_counter()-sent)*1000)
                    if not delivered and (audio is None or transcript_delivered):
                        early=ready_reply(candidate)
                        if early:
                            await deliver(early);delivered=True
                            metrics['reply_ready_ms']=round((time.perf_counter()-sent)*1000)
                    if candidate.endswith('}'):
                        try:parse_live_output(candidate)
                        except ProviderError:pass
                        else:
                            if audio is None or transcript_delivered:return True  # Full payload and actual spoken question are available.
                if getattr(content,'turn_complete',False):
                    turn_finished=True
                    return audio is None or transcript_delivered
            return False
        complete=await drain()
        if not complete:
            try:complete=await asyncio.wait_for(drain(),1.5)
            except asyncio.TimeoutError:pass
        raw=''.join(chunks).strip()
        # Some Live models wrap valid structured output in markdown fences.
        raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw,flags=re.I)
        if audio is not None:
            recognized=''.join(input_chunks).strip()
            if not recognized or len(recognized)>16000 or not input_finished:
                raise ProviderError('Gemini não retornou uma transcrição válida da pergunta falada.',502,kind='audio_transcription_missing')
        result,recovered=parse_live_output(raw,complete=complete,allow_plain=turn_finished)
        metrics['format_recovered']=recovered
        if audio is not None:
            result['recognized_text']=recognized
            if not transcript_delivered:await deliver_transcript(recognized)
            if not delivered:await deliver(result['reply']);delivered=True
        metrics['response_ready_ms']=round((time.perf_counter()-sent)*1000)
        conversation_metrics.save_live(metrics)
        return result

async def reply(settings,system,messages):
    primary=settings.gemini_live_model
    if not re.fullmatch(r'(?:models/)?[\w.-]+',primary):raise ProviderError('GEMINI_LIVE_MODEL inválido.')
    models=list(dict.fromkeys((primary,*ORIGINAL_MODELS))) if primary in ORIGINAL_MODELS else [primary]
    characters=len(system)+len(OUTPUT_RULES)+sum(len(m['content']) for m in messages)
    last=None;loop=asyncio.get_running_loop();deadline=loop.time()+LIVE_TOTAL_TIMEOUT_SECONDS
    for model in models:
        remaining_budget=deadline-loop.time()
        if remaining_budget<=0:break
        identity=hashlib.sha256((settings.gemini_key.strip()+'|live|'+model).encode()).hexdigest()
        remaining=usage.remaining(identity)
        if remaining>0:raise ProviderError(f'Gemini Live: pausa ativa por {int(remaining)+1} segundos. Nenhuma sessão nova foi aberta.',429)
        client=None
        try:
            client=make_client(settings.gemini_key.strip())
            timeout=min(float(settings.provider_timeout),LIVE_ATTEMPT_TIMEOUT_SECONDS,remaining_budget)
            result=await asyncio.wait_for(turn(client,model,system,messages,settings.gemini_live_thinking_budget),timeout)
            usage.audit(model,200,characters);usage.clear_pause(identity)
            return result
        except ImportError:
            raise ProviderError('Instale a integração Gemini original: execute Instalar-Cronos.bat novamente.') from None
        except ProviderError as exc:
            usage.audit(model,502,characters)
            message='Gemini Live: '+str(exc)
            record_gemini_error(502,message)
            raise ProviderError(message,502,kind=exc.kind) from None
        except asyncio.TimeoutError:
            usage.audit(model,504,characters)
            last=ProviderError('Gemini Live: tempo de resposta esgotado; verificando a próxima rota Live disponível.',504)
            continue
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
                try:await asyncio.wait_for(client.aio.aclose(),2)
                except Exception:pass
    if last and last.status==504:
        raise ProviderError('Gemini Live demorou demais; nenhuma rota Live concluiu a resposta dentro do prazo.',504) from None
    raise last or ProviderError('Gemini Live indisponível.')
