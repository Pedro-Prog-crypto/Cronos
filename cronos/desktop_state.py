"""Native assistant state: session identifiers only, never stored screen frames."""
import json
from uuid import UUID, uuid4
from cronos.resident import folder,write_json


def session_id():
    path=folder()/'conversation-session.json'
    try:return str(UUID(json.loads(path.read_text())['session_id']))
    except (OSError,ValueError,KeyError,TypeError):
        value=str(uuid4());write_json(path,{'session_id':value});return value


def needs_screen(text):
    from cronos.wake import normalize_phrase
    value=normalize_phrase(text)
    import re
    return bool(re.search(r'\b(?:tela|pagina|materia|artigo|wikipedia|slide|aba atual|isso aqui|esta noticia|essa noticia)\b',value))


def wants_card(text):
    from cronos.wake import normalize_phrase
    import re
    return bool(re.search(r'\b(?:resum\w*|cards?|na tela|mostr\w*|exib\w*|texto)\b',normalize_phrase(text)))


def control_intent(text,config):
    from cronos.wake import normalize_phrase,command_phrases
    import re
    value=normalize_phrase(text);commands=command_phrases(config)
    action=commands.get(value)
    if action in {'show','hide','paused','resumed'}:return action
    name=normalize_phrase(config['activation_phrase'])
    for prefix in (name,'cronos','kronos','chronos'):
        if value.startswith(prefix+' '):value=value[len(prefix)+1:];break
    action=commands.get(value)
    if action in {'show','hide','paused','resumed'}:return action
    if re.fullmatch(r'(?:abra|abre|abrir|mostre|mostrar|quero abrir) (?:a janela do |o )?(?:cronos|kronos|chronos)',value):return 'show'
    if re.fullmatch(r'(?:feche|fechar|oculte|ocultar|minimize|minimizar) (?:a janela do |o )?(?:cronos|kronos|chronos)',value):return 'hide'
    if re.match(r'^(?:pare|parar|desligue|desligar|encerre)\b',value) and re.search(r'\btela\b',value) and not re.search(r'\b(?:falar|explicar)\b',value):return 'screen_off'
    if re.match(r'^(?:veja|ver|olhe|acompanhe|ative)\b',value) and re.search(r'\b(?:minha tela|a tela)\b',value):return 'screen_on'
    return None


def install(app,authenticate):
    from ipaddress import ip_address
    from fastapi import Depends,HTTPException,Request
    from pydantic import BaseModel,ConfigDict
    from typing import Literal
    from cronos.wake import settings,ui_is_listening
    auth=[Depends(authenticate)]
    def local(request):
        try:return ip_address(request.client.host).is_loopback
        except (ValueError,AttributeError):return False
    class Screen(BaseModel):
        model_config=ConfigDict(extra='forbid')
        consent:Literal[True]
        enabled:bool=True
    class Cancel(BaseModel):
        model_config=ConfigDict(extra='forbid')
        turn_id:UUID
    @app.post('/assistant/cancel',dependencies=auth)
    async def stop_turn(body:Cancel):
        from cronos.turn_cancellation import cancel
        return {'cancelled_requests':cancel(app,body.turn_id)}
    @app.post('/assistant/shutdown',dependencies=auth)
    async def shutdown(request:Request):
        if not local(request):raise HTTPException(403,'Encerramento disponível somente no computador local.')
        stop=getattr(app.state,'resident_shutdown',None)
        if stop is None:raise HTTPException(409,'Este servidor não foi iniciado como assistente residente.')
        stop();return {'requested':True}
    @app.get('/assistant/state',dependencies=auth)
    async def state(request:Request):
        config=settings()
        return {'native_available':app.state.windows.platform=='win32' and local(request),
                'session_id':session_id(),'screen_enabled':config['screen_enabled'],
                'background_enabled':config['background_enabled'],'opens_on_name':False}
    @app.post('/assistant/screen',dependencies=auth)
    async def screen(body:Screen,request:Request):
        if not local(request) or app.state.windows.platform!='win32':raise HTTPException(403,'Acesso à tela disponível somente na instalação local do Windows.')
        manager=app.state.live_screen;ident=session_id()
        if not body.enabled:
            if manager.session==ident:await manager.stop(ident)
            return {'active':False}
        if not settings()['screen_enabled']:raise HTTPException(403,'A visão em segundo plano foi desativada nas configurações.')
        if manager.session and manager.session!=ident and manager.active(manager.session):
            if ui_is_listening():raise HTTPException(409,'A tela já está em uso pela conversa aberta.')
            await manager.stop(manager.session)
        if manager.session==ident and manager.source!='local':await manager.stop(ident)
        try:return await manager.start(ident,'local')
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
    @app.post('/assistant/vision-setting',dependencies=auth)
    async def vision_preference(body:Screen,request:Request):
        if not local(request) or app.state.windows.platform!='win32':raise HTTPException(403,'Configuração disponível somente no Windows local.')
        from cronos.wake import save_settings
        save_settings({'screen_enabled':body.enabled})
        manager=app.state.live_screen
        if not body.enabled and manager.session:await manager.stop(manager.session)
        return {'screen_enabled':body.enabled}
