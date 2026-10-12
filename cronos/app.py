import asyncio
import secrets
from pathlib import Path
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
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


class MemoryQuery(BaseModel):
    query: str = Field(min_length=1, max_length=3000)
    limit: int = Field(default=8, ge=1, le=100)


def create_app(settings: Settings | None = None, provider=None, fish_factory=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        app.state.memory = Memory(settings.vault)
        app.state.lock = asyncio.Lock()
        app.state.registry = create_registry(settings, app.state.memory)
        app.state.engine = Engine(settings, app.state.memory, app.state.registry, provider)
        yield

    app = FastAPI(title="Cronos", version="0.2.0", lifespan=lifespan)
    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/", include_in_schema=False)
    async def interface():
        return FileResponse(static / "index.html", headers={"Cache-Control": "no-store"})

    if settings.origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.origins),
                           allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])

    async def authenticate(authorization: str | None = Header(default=None)):
        if not settings.token:
            raise HTTPException(503, "Configure CRONOS_API_TOKEN antes de acessar os dados.")
        if not secrets.compare_digest(authorization or "", "Bearer " + settings.token):
            raise HTTPException(401, "Autenticação necessária.")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/status", dependencies=[Depends(authenticate)])
    async def status():
        warning = None
        try:
            configured = next((p['configured'] for p in provider_catalog(settings) if p['id'] == settings.provider), False)
        except ProviderError as exc:
            configured = bool(settings.gemini_key) if settings.provider == 'gemini' else settings.provider == 'ollama'
            warning = str(exc)
        return {"provider": settings.provider, "gemini_configured": bool(settings.gemini_key),
                "provider_configured": configured, "configuration_warning": warning,
                "fish_configured": bool(settings.fish_key),
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
                result = await request.app.state.engine.chat(session, body.message)
            except TurnError as exc:
                raise HTTPException(503, {"message": str(exc), "session_id": str(exc.session), "tool_results": exc.results}) from exc
            except ProviderError as exc:
                raise HTTPException(503, str(exc)) from exc
            except (OSError, ValueError):
                raise HTTPException(500, "Não foi possível ler ou salvar personalidade/memória.")
        return result

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
            return {"providers": provider_catalog(settings)}
        except ProviderError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/providers/{provider_id}/models", dependencies=[Depends(authenticate)])
    async def models(provider_id: str):
        try:
            return {"provider": provider_id, "models": await available_models(settings, provider_id)}
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
            memory.flush_exports()
            memory.sync_notes()
            return {**memory.stats(), "warnings": memory.warnings}

    @app.get("/memory/status", dependencies=[Depends(authenticate)])
    async def memory_status(request: Request):
        return request.app.state.memory.stats()

    async def fish_client():
        if not settings.fish_key:
            raise HTTPException(503, "Configure FISH_API_KEY.")
        if fish_factory:
            return fish_factory()
        from fishaudio import AsyncFishAudio
        return AsyncFishAudio(api_key=settings.fish_key)

    @app.post("/voice/speech", dependencies=[Depends(authenticate)])
    async def speech(body: SpeechInput):
        if not body.text.strip():
            raise HTTPException(422, "Informe um texto para sintetizar.")
        reference = body.reference_id or settings.fish_reference
        client = await fish_client()
        try:
            async with client:
                audio = await client.tts.convert(text=body.text, reference_id=reference or None,
                                                 model=settings.fish_model, format="mp3",
                                                 speed=body.speed or settings.fish_speed, latency=settings.fish_latency)
            return Response(content=audio, media_type="audio/mpeg")
        except Exception as exc:
            raise HTTPException(502, fish_error(exc)) from exc

    @app.post("/voice/stream", dependencies=[Depends(authenticate)])
    async def speech_stream(body: SpeechInput):
        if not body.text.strip():
            raise HTTPException(422, "Informe um texto para sintetizar.")
        client = await fish_client()
        entered = False
        try:
            await client.__aenter__()
            entered = True
            audio = await client.tts.stream(text=body.text, reference_id=body.reference_id or settings.fish_reference or None,
                                           model=settings.fish_model, format="mp3",
                                           speed=body.speed or settings.fish_speed, latency=settings.fish_latency)
            iterator = audio.__aiter__()
            first = await anext(iterator)
        except Exception as exc:
            if entered:
                await client.__aexit__(None, None, None)
            raise HTTPException(502, fish_error(exc)) from None

        async def chunks():
            try:
                yield first
                async for chunk in iterator:
                    yield chunk
            except Exception:
                raise RuntimeError("O fluxo de áudio foi interrompido pelo provedor.") from None
            finally:
                await client.__aexit__(None, None, None)
        return StreamingResponse(chunks(), media_type="audio/mpeg", headers={"Cache-Control": "no-store"})

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
        client = await fish_client()
        try:
            async with client:
                result = await client.asr.transcribe(audio=b"".join(chunks), language="pt")
            return {"text": result.text}
        except Exception as exc:
            raise HTTPException(502, fish_error(exc)) from exc

    return app


app = create_app()


def fish_error(exc):
    from fishaudio.exceptions import AuthenticationError, RateLimitError, NotFoundError, PermissionError, ValidationError
    if isinstance(exc, AuthenticationError):
        return "Fish Audio: chave rejeitada. Confira FISH_API_KEY e reinicie o Cronos."
    if isinstance(exc, RateLimitError):
        return "Fish Audio: limite de chamadas ou créditos atingido. Confira sua conta."
    if isinstance(exc, NotFoundError):
        return "Fish Audio: voz ou recurso não encontrado. Confira o ID da voz e o modelo."
    if isinstance(exc, PermissionError):
        return "Fish Audio: acesso negado para esta chave ou voz."
    if isinstance(exc, ValidationError):
        return "Fish Audio: parâmetros ou áudio não aceitos. Confira formato, voz e velocidade."
    if getattr(exc, "status", None) == 402:
        return "Fish Audio: pagamento ou créditos necessários para este modelo. Confira sua conta; o Cronos não troca automaticamente para outro modelo."
    return "Fish Audio indisponível; confira conexão, voz, modelo e conta."
