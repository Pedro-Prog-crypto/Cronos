"""Local request counts and persisted backoff; never store keys or conversation text."""
import json
import time
from pathlib import Path
from contextlib import contextmanager
from contextvars import ContextVar

ROOT=Path('.cronos-local')
scope=ContextVar('gemini_request_scope',default=('operation',''))

@contextmanager
def request_scope(source,turn=''):
    token=scope.set((source,turn))
    try:yield
    finally:scope.reset(token)

def audit(model,status,characters,metadata=None):
    source,turn=scope.get()
    row={'time':time.time(),'source':source,'turn':turn,'model':model,'http':status,'input_characters':characters}
    metadata=metadata or {}
    for name in ('promptTokenCount','candidatesTokenCount','totalTokenCount'):
        value=metadata.get(name)
        if isinstance(value,int) and value>=0:row[name]=value
    try:
        ROOT.mkdir(exist_ok=True)
        path=ROOT/'gemini-requests.jsonl'
        if path.exists() and path.stat().st_size>1024*1024:
            path.replace(ROOT/'gemini-requests.previous.jsonl')
        with path.open('a',encoding='utf-8') as output:output.write(json.dumps(row)+'\n')
    except OSError:pass

def pause_path(identity):return ROOT/('gemini-pause-'+identity+'.json')

def remaining(identity):
    try:
        value=json.loads(pause_path(identity).read_text(encoding='utf-8'))['until']
        return max(0,min(3600,float(value)-time.time()))
    except (OSError,ValueError,TypeError,KeyError):return 0

def pause(identity,seconds):
    try:
        ROOT.mkdir(exist_ok=True)
        target=pause_path(identity);temporary=target.with_suffix('.tmp')
        temporary.write_text(json.dumps({'until':time.time()+seconds}),encoding='utf-8')
        temporary.replace(target)
    except OSError:pass

def clear_pause(identity):
    try:pause_path(identity).unlink(missing_ok=True)
    except OSError:pass
