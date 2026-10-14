import asyncio
import json
import secrets
from pathlib import Path
from contextlib import asynccontextmanager
from contextlib import suppress
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cronos.config import Settings
from cronos.memory import Memory
from cronos.providers import ProviderError
from cronos.engine import Engine, TurnError
from cronos.integrations import provider_catalog, available_models
from cronos.tools import create_registry, ToolError
from cronos.security import SecurityMiddleware
from cronos.monitor import Monitor
from cronos.missions import Missions
from cronos.features import Features
from cronos.windows_system import WindowsSystem
from cronos.geography import install_geography
from cronos.control import install_routes
from cronos.panels import PanelState, install_panels


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=16000)
    session_id: UUID | None = None


class SpeechInput(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    reference_id: str | None = Field(default=None, max_length=128)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)


class ApprovalInput(BaseModel):
    session_id: UUID
    accepted: bool


async def chat_until_disconnect(engine,session,message,request):
    if await request.is_disconnected():raise HTTPException(499,'Conversa interrompida.')
    task=asyncio.create_task(engine.chat(session,message))
    async def watch():
        while not task.done():
            if await request.is_disconnected():return
            await asyncio.sleep(.1)
    watcher=asyncio.create_task(watch())
    try:
        done,_=await asyncio.wait({task,watcher},return_when=asyncio.FIRST_COMPLETED)
        if task in done:return await task
        task.cancel()
        with suppress(asyncio.CancelledError):await task
        raise HTTPException(499,'Conversa interrompida antes da resposta.')
    finally:
        watcher.cancel()
        if not task.done():task.cancel()
        await asyncio.gather(task,watcher,return_exceptions=True)


class MemoryQuery(BaseModel):
    query: str = Field(min_length=1, max_length=3000)
    limit: int = Field(default=8, ge=1, le=100)


def create_app(settings: Settings | None = None, provider=None, fish_factory=None, vision_provider=None,
               windows_runner=None, windows_platform=None):
    settings = settings or Settings.from_env()
    from cronos.recognition import LocalRecognizer
    local_recognizer=LocalRecognizer()

    @asynccontextmanager
    async def lifespan(app):
        app.state.memory = Memory(settings.vault)
        app.state.lock = asyncio.Lock()
        app.state.monitor = Monitor(settings, app.state.memory)
        app.state.windows = WindowsSystem(windows_runner, app.state.monitor, windows_platform, settings.privacy_mode)
        app.state.missions = Missions(app.state.memory)
        app.state.registry = create_registry(settings, app.state.memory, app.state.monitor, app.state.windows, app.state.missions, app.state.prospects)
        app.state.engine = Engine(settings, app.state.memory, app.state.registry, provider)
        app.state.vision_provider = vision_provider
        app.state.features = Features(app)
        app.state.panels = PanelState(app)
        panel_task = asyncio.create_task(app.state.panels.maintain())
        await asyncio.to_thread(app.state.monitor.collect)
        task = asyncio.create_task(app.state.monitor.run())
        windows_task = asyncio.create_task(app.state.windows.watch())
        async def warm_recognition():
            if settings.transcription_provider!='vosk' or (settings.privacy_mode=='online' and settings.provider=='gemini' and settings.gemini_transport=='live'):return
            try:await asyncio.to_thread(local_recognizer.prepare)
            except ValueError:pass # The transcription endpoint reports configuration errors on use.
        recognition_task=asyncio.create_task(warm_recognition())
        try:
            yield
        finally:
            panel_task.cancel()
            with suppress(asyncio.CancelledError):await panel_task
            recognition_task.cancel()
            with suppress(asyncio.CancelledError):await recognition_task
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            windows_task.cancel()
            with suppress(asyncio.CancelledError):
                await windows_task
            await app.state.windows.close()

    app = FastAPI(title="Cronos", version="0.5.0", lifespan=lifespan, docs_url=None, redoc_url=None)
    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")
    ui = Path(__file__).parent / "ui"
    if ui.is_dir():
        app.mount("/ui", StaticFiles(directory=ui), name="ui")

    @app.get("/", include_in_schema=False)
    async def interface():
        return FileResponse(ui / "index.html" if (ui / "index.html").is_file() else static / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/world/view", include_in_schema=False)
    async def world_view():
        return FileResponse(ui / "world.html", headers={"Cache-Control": "no-store"})

    @app.get("/tests", include_in_schema=False)
    async def workbench():
        return FileResponse(static / "index.html", headers={"Cache-Control": "no-store"})

    if settings.origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.origins),
                           allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])
    app.add_middleware(SecurityMiddleware, settings=settings)

    async def authenticate(authorization: str | None = Header(default=None)):
        if not settings.token:
            raise HTTPException(503, "Configure CRONOS_API_TOKEN antes de acessar os dados.")
        if not secrets.compare_digest((authorization or "").encode('utf-8'), ("Bearer " + settings.token).encode('utf-8')):
            raise HTTPException(401, "Autenticação necessária.")

    from cronos.music import install_music
    install_music(app, authenticate)
    from cronos.prospects import install_prospects
    install_prospects(app, authenticate)

    @app.middleware('http')
    async def panel_metrics(request, call_next):
        measured = request.url.path in {'/chat', '/voice/speech', '/voice/transcribe', '/vision/analyze'}
        panels = getattr(request.app.state, 'panels', None)
        if measured and panels:panels.active += 1
        try:return await call_next(request)
        finally:
            if measured and panels:
                panels.active -= 1
                panels.requests += 1
                if request.url.path=='/chat':request.app.state.engine.phase="idle"

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/monitor", dependencies=[Depends(authenticate)])
    async def monitor(request: Request, after: int = Query(default=0, ge=0)):
        return request.app.state.monitor.snapshot(after)

    @app.post("/monitor/alerts/{alert_id}/ack", dependencies=[Depends(authenticate)])
    async def acknowledge_alert(alert_id: int, request: Request):
        if not request.app.state.monitor.acknowledge(alert_id):
            raise HTTPException(404, "Alerta ativo não encontrado.")
        return {"acknowledged": True}

    @app.get("/status", dependencies=[Depends(authenticate)])
    async def status():
        current = app.state.engine.settings
        warning = None
        try:
            configured = next((p['configured'] for p in provider_catalog(current) if p['id'] == current.provider), False)
        except ProviderError as exc:
            configured = bool(settings.gemini_key) if settings.provider == 'gemini' else settings.provider == 'ollama'
            warning = str(exc)
        return {"provider": current.provider, "gemini_configured": bool(settings.gemini_key),
                "provider_model": next((item['model'] for item in provider_catalog(current) if item['id'] == current.provider), None) if warning is None else None,
                "provider_configured": configured, "configuration_warning": warning,
                "privacy_mode": settings.privacy_mode,
                "fish_configured": bool(settings.fish_key) and settings.privacy_mode == 'online',
                "transcription_provider": settings.transcription_provider,
                "direct_audio_chat":current.privacy_mode=="online" and current.provider=="gemini" and current.gemini_transport=="live",
                "fish_model_in_use": active_fish_model,
                "fish_pcm_streaming": active_fish_model=="s2.1-pro-free" and settings.privacy_mode=="online",
                "fish_speech_configured": bool(settings.fish_key and settings.fish_model) and settings.privacy_mode == "online",
                "custom_voice_configured": bool(settings.fish_reference),
                "personality_available": settings.personality.is_file()}

    @app.post("/chat", dependencies=[Depends(authenticate)])
    async def chat(body: ChatInput, request: Request):
        if not body.message.strip():
            raise HTTPException(422, "A mensagem não pode ser vazia.")
        session = body.session_id or uuid4()
        # Uma instância/worker: protege ordem das conversas e arquivos compartilhados.
        async with request.app.state.lock:
            try:
                result = await chat_until_disconnect(request.app.state.engine,session,body.message,request)
            except TurnError as exc:
                raise HTTPException(exc.status, {"message": str(exc), "session_id": str(exc.session), "tool_results": exc.results}) from exc
            except ProviderError as exc:
                raise HTTPException(exc.status, str(exc)) from exc
            except (OSError, ValueError):
                raise HTTPException(500, "Não foi possível ler ou salvar personalidade/memória.")
        request.app.state.features.record("language", "passed", "Uma conversa foi processada e salva. Não certifica precisão de todas as respostas.")
        return result

    async def conversation_stream(session,message,request,audio=None):
        from cronos.reply_stream import reply_sink,intro_sink,transcript_sink
        async def events():
            panels=request.app.state.panels;panels.active+=1
            queue=asyncio.Queue(maxsize=4);spoken=None;intro_text=None;recognized_question=None
            def may_speak():
                import re
                return audio is None or not panels.preferences.called_only or bool(recognized_question and re.search(r'\b(?:cronos|kronos|chronos)\b',recognized_question,re.I))
            async def ready(reply):
                nonlocal spoken
                if spoken is None and may_speak():
                    spoken=reply
                    await queue.put({'type':'reply','reply':reply,'session_id':str(session)})
            async def intro(text):
                nonlocal intro_text
                if intro_text is not None or not may_speak():return
                intro_text=text
                await queue.put({'type':'intro','reply':text,'session_id':str(session)})
            async def transcript(text):
                nonlocal recognized_question
                recognized_question=text
                await queue.put({'type':'transcript','text':text})
            async def run():
                token=reply_sink.set(ready);intro_token=intro_sink.set(intro);transcript_token=transcript_sink.set(transcript)
                try:
                    async with request.app.state.lock:
                        try:result=await request.app.state.engine.chat(session,message,**({'audio':audio} if audio is not None else {}))
                        finally:request.app.state.engine.phase='idle'
                    if not result.get('ignored') and ((spoken is not None and spoken!=result['reply']) or (intro_text is not None and not result['reply'].startswith(intro_text))):
                        raise ProviderError('A resposta transmitida não corresponde ao resultado final.',502)
                    request.app.state.features.record('language','passed','Conversa processada e salva.')
                    await queue.put({'type':'result','result':result})
                except ProviderError as exc:
                    detail={'message':str(exc)}
                    if isinstance(exc,TurnError):detail.update(session_id=str(exc.session),tool_results=exc.results)
                    await queue.put({'type':'error','status':exc.status,'detail':detail})
                except (OSError,ValueError):
                    await queue.put({'type':'error','status':500,'detail':{'message':'Não foi possível ler ou salvar personalidade/memória.'}})
                except Exception:
                    await queue.put({'type':'error','status':500,'detail':{'message':'Falha ao concluir a conversa.'}})
                finally:
                    reply_sink.reset(token);intro_sink.reset(intro_token);transcript_sink.reset(transcript_token)
            task=asyncio.create_task(run())
            try:
                while True:
                    event=await queue.get()
                    yield json.dumps(event,ensure_ascii=False)+'\n'
                    if event['type'] in {'result','error'}:break
            finally:
                task.cancel()
                with suppress(asyncio.CancelledError):await task
                panels.active-=1;panels.requests+=1
        return StreamingResponse(events(),media_type='application/x-ndjson',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})

    @app.post("/chat/stream", dependencies=[Depends(authenticate)])
    async def stream_chat(body: ChatInput, request: Request):
        if not body.message.strip():raise HTTPException(422,"A mensagem não pode ser vazia.")
        return await conversation_stream(body.session_id or uuid4(),body.message,request)

    @app.post('/chat/audio/stream',dependencies=[Depends(authenticate)])
    async def stream_audio(request: Request,session_id: UUID | None = None):
        current=request.app.state.engine.settings
        if current.privacy_mode!='online' or current.provider!='gemini' or current.gemini_transport!='live':
            raise HTTPException(503,'Conversa por áudio direto requer o Gemini Live já configurado e modo online.')
        if request.headers.get('content-type','').split(';')[0]!='audio/wav':raise HTTPException(415,'Envie áudio WAV PCM mono de 16 kHz.')
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>2*1024*1024:raise HTTPException(413,'Áudio ultrapassa o limite de 2 MiB.')
            chunks.append(chunk)
        from cronos.recognition import read_pcm
        try:pcm=read_pcm(b''.join(chunks))
        except ValueError as exc:raise HTTPException(422,str(exc)) from None
        return await conversation_stream(session_id or uuid4(),'Pergunta falada',request,pcm)

    @app.get("/conversations/{session_id}", dependencies=[Depends(authenticate)])
    async def conversation(session_id: UUID, request: Request):
        events = request.app.state.memory.tool_history(session_id)
        resolved = {event.get('approval_id') for event in events if event['status'] != 'pending_confirmation'}
        for event in events:
            if event['status'] == 'pending_confirmation' and event.get('approval_id') not in request.app.state.registry.pending:
                event['status'] = 'resolved' if event.get('approval_id') in resolved else 'expired'
        return {"session_id": str(session_id), "messages": request.app.state.memory.history(session_id),
                "tool_results": events}

    @app.get("/providers", dependencies=[Depends(authenticate)])
    async def providers():
        try:
            return {"providers": provider_catalog(app.state.engine.settings), "selected": app.state.engine.settings.provider}
        except ProviderError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/providers/{provider_id}/models", dependencies=[Depends(authenticate)])
    async def models(provider_id: str):
        try:
            return {"provider": provider_id, "models": await available_models(app.state.engine.settings, provider_id)}
        except ProviderError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/tools", dependencies=[Depends(authenticate)])
    async def tools(request: Request):
        return {"tools": request.app.state.registry.catalog(), "plugin_errors": request.app.state.registry.load_errors}

    @app.post("/tools/approvals/{approval_id}", dependencies=[Depends(authenticate)])
    async def approve(approval_id: UUID, body: ApprovalInput, request: Request):
        async with request.app.state.lock:
            try:
                result = await request.app.state.registry.resolve(str(approval_id), body.accepted, body.session_id)
                request.app.state.memory.log_tool(body.session_id, result)
                return result
            except ToolError as exc:
                raise HTTPException(409, str(exc)) from exc

    @app.post("/memory/search", dependencies=[Depends(authenticate)])
    async def memory_search(body: MemoryQuery, request: Request):
        async with request.app.state.lock:
            return {"notes": request.app.state.memory.search(body.query, body.limit)}

    @app.get("/memory/graph", dependencies=[Depends(authenticate)])
    async def memory_graph(request: Request, offset: int = Query(0, ge=0), limit: int = Query(600, ge=1, le=1000)):
        return await asyncio.to_thread(request.app.state.memory.graph, offset, limit)

    @app.get("/memory/note", dependencies=[Depends(authenticate)])
    async def memory_note(path: str, request: Request):
        try:
            return {"path": path, "content": request.app.state.memory.read_note(path)}
        except (ValueError, OSError):
            raise HTTPException(404, "Nota não encontrada ou caminho inválido.")

    @app.post("/memory/sync", dependencies=[Depends(authenticate)])
    async def memory_sync(request: Request):
        async with request.app.state.lock:
            memory = request.app.state.memory
            def sync():
                memory.flush_exports()
                memory.sync_notes()
                return {**memory.stats(), "warnings": memory.warnings}
            return await asyncio.to_thread(sync)

    @app.get("/memory/status", dependencies=[Depends(authenticate)])
    async def memory_status(request: Request):
        return request.app.state.memory.stats()

    async def fish_client():
        if settings.privacy_mode != 'online':
            raise HTTPException(503, "Modo local: Fish Audio está desabilitado porque envia áudio/texto a um serviço externo.")
        if not settings.fish_key:
            raise HTTPException(503, "Configure FISH_API_KEY.")
        if fish_factory:
            return fish_factory()
        from fishaudio import AsyncFishAudio
        return AsyncFishAudio(api_key=settings.fish_key, timeout=30.0)

    active_fish_model = settings.fish_model

    async def fish_tts(client, method, **arguments):
        nonlocal active_fish_model
        model = active_fish_model

        async def request(selected):
            if selected == 's2.1-pro-free' and fish_factory is None:
                from cronos.fish_legacy import synthesize_json,stream_json
                if method=='stream':return stream_json(settings.fish_key,**arguments)
                return await synthesize_json(settings.fish_key, **arguments)
            return await getattr(client.tts, method)(model=selected, **arguments)

        return await request(model)

    @app.post("/voice/speech", dependencies=[Depends(authenticate)])
    async def speech(body: SpeechInput, request: Request):
        if not body.text.strip():
            raise HTTPException(422, "Informe um texto para sintetizar.")
        reference = body.reference_id or settings.fish_reference
        if not settings.fish_model:
            raise HTTPException(503, "Configure FISH_MODEL com o modelo liberado para API na sua conta Fish Audio.")
        client = await fish_client()
        try:
            async with client:
                audio = await fish_tts(client, "convert", text=body.text, reference_id=reference or None,
                                                 format=settings.fish_format,
                                                 speed=body.speed or settings.fish_speed, latency=settings.fish_latency)
            request.app.state.features.record("voice", "passed", "Síntese retornou áudio; reprodução física no dispositivo não foi certificada.")
            return Response(content=audio, media_type="audio/wav" if settings.fish_format == "wav" else "audio/mpeg")
        except Exception as exc:
            raise HTTPException(502, fish_error(exc, "síntese")) from exc

    @app.post('/voice/pcm',dependencies=[Depends(authenticate)])
    async def speech_pcm(body: SpeechInput):
        if settings.privacy_mode!='online' or not settings.fish_key:raise HTTPException(503,'Configure a voz Fish Audio em modo online.')
        if active_fish_model!='s2.1-pro-free':raise HTTPException(503,'Streaming PCM não habilitado para este modelo. Nenhum modelo foi trocado.')
        if not body.text.strip():raise HTTPException(422,'Informe um texto para sintetizar.')
        from cronos.fish_legacy import stream_json
        iterator=stream_json(settings.fish_key,text=body.text,reference_id=body.reference_id or settings.fish_reference or None,format='pcm',speed=body.speed or settings.fish_speed,latency=settings.fish_latency)
        try:
            first=await anext(iterator)
            while len(first)<4:first+=await anext(iterator)
            if first.startswith(b'RIFF'):raise ValueError('A síntese não retornou PCM bruto.')
        except Exception as exc:
            await iterator.aclose()
            raise HTTPException(502,fish_error(exc,'síntese')) from exc
        async def chunks():
            try:
                yield first
                async for chunk in iterator:yield chunk
            finally:await iterator.aclose()
        return StreamingResponse(chunks(),media_type='audio/x-pcm',headers={'Cache-Control':'no-store','X-PCM-Sample-Rate':'24000','X-PCM-Channels':'1','X-PCM-Bits':'16'})

    @app.post("/voice/stream", dependencies=[Depends(authenticate)])
    async def speech_stream(body: SpeechInput):
        if not body.text.strip():
            raise HTTPException(422, "Informe um texto para sintetizar.")
        if not settings.fish_model:
            raise HTTPException(503, "Configure FISH_MODEL com o modelo liberado para API na sua conta Fish Audio.")
        client = await fish_client()
        entered = False
        try:
            await client.__aenter__()
            entered = True
            audio = await fish_tts(client, "stream", text=body.text, reference_id=body.reference_id or settings.fish_reference or None,
                                           format=settings.fish_format,
                                           speed=body.speed or settings.fish_speed, latency=settings.fish_latency)
            iterator = audio.__aiter__()
            first = await anext(iterator)
        except Exception as exc:
            if entered:
                await client.__aexit__(None, None, None)
            raise HTTPException(502, fish_error(exc, "síntese em streaming")) from None

        async def chunks():
            try:
                yield first
                async for chunk in iterator:
                    yield chunk
            except Exception:
                raise RuntimeError("O fluxo de áudio foi interrompido pelo provedor.") from None
            finally:
                await client.__aexit__(None, None, None)
        return StreamingResponse(chunks(), media_type="audio/wav" if settings.fish_format == "wav" else "audio/mpeg", headers={"Cache-Control": "no-store"})

    @app.post("/voice/transcribe", dependencies=[Depends(authenticate)])
    async def transcribe(request: Request):
        # Corpo binário: não precisa de multipart ou base64.
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 10 * 1024 * 1024:
                raise HTTPException(413, "Limite de áudio: 10 MiB.")
            chunks.append(chunk)
        if not size:
            raise HTTPException(422, "Envie um arquivo de áudio no corpo da requisição.")
        if settings.transcription_provider == 'vosk':
            try:
                return {'text':await asyncio.to_thread(local_recognizer.transcribe,b''.join(chunks))}
            except ValueError as exc:
                raise HTTPException(503,str(exc)) from None
        client = await fish_client()
        try:
            async with client:
                result = await client.asr.transcribe(audio=b"".join(chunks), language="pt")
            return {"text": result.text}
        except Exception as exc:
            raise HTTPException(502, fish_error(exc, "transcrição do microfone")) from exc

    install_routes(app, authenticate)
    install_panels(app, authenticate)
    install_geography(app, authenticate)
    return app


app = create_app()


def fish_error(exc, operation="voz"):
    prefix = f"Fish Audio — {operation}: "
    from fishaudio.exceptions import AuthenticationError, RateLimitError, NotFoundError, PermissionError, ValidationError
    if isinstance(exc, AuthenticationError):
        return "Fish Audio: chave rejeitada. Confira FISH_API_KEY e reinicie o Cronos."
    if isinstance(exc, RateLimitError):
        return prefix + "HTTP 429: limite de chamadas atingido. Aguarde antes de tentar novamente."
    if isinstance(exc, NotFoundError):
        return "Fish Audio: voz ou recurso não encontrado. Confira o ID da voz e o modelo."
    if isinstance(exc, PermissionError):
        return "Fish Audio: acesso negado para esta chave ou voz."
    if isinstance(exc, ValidationError):
        return "Fish Audio: parâmetros ou áudio não aceitos. Confira formato, voz e velocidade."
    if getattr(exc, "status", None) == 402:
        return prefix + "HTTP 402: o provedor recusou esta chamada por cobrança ou acesso. Isso não confirma saldo zerado. Confira se a chave pertence à conta com créditos e se esse recurso da API está liberado."
    return "Fish Audio indisponível; confira conexão, voz, modelo e conta."
