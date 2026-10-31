"""Explicit cancellation for voice requests whose HTTP body was already read."""
import asyncio
import time
from uuid import UUID
from fastapi import HTTPException


def registries(app):
    if not hasattr(app.state,'voice_tasks'):app.state.voice_tasks={};app.state.voice_cancelled={}
    return app.state.voice_tasks,app.state.voice_cancelled


def cancel(app,turn):
    tasks,cancelled=registries(app);key=str(UUID(str(turn)))
    cancelled[key]=time.monotonic()+60
    while len(cancelled)>128:cancelled.pop(next(iter(cancelled)))
    pending=list(tasks.get(key,()))
    for task in pending:task.cancel()
    return len(pending)


async def voice_operation(request,operation):
    try:key=str(UUID(request.headers.get('x-cronos-turn','')))
    except ValueError:return await (operation() if callable(operation) else operation)
    tasks,cancelled=registries(request.app)
    for ident,until in tuple(cancelled.items()):
        if until<time.monotonic():cancelled.pop(ident,None)
    if key in cancelled:
        if not callable(operation):operation.close()
        raise HTTPException(499,'Pedido interrompido pelo senhor.')
    task=asyncio.create_task(operation() if callable(operation) else operation);tasks.setdefault(key,set()).add(task)
    try:return await task
    except asyncio.CancelledError:
        if key in cancelled:raise HTTPException(499,'Pedido interrompido pelo senhor.') from None
        raise
    finally:
        tasks.get(key,set()).discard(task)
        if not tasks.get(key):tasks.pop(key,None)
