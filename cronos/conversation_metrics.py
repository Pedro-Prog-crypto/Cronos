"""Last backend phase durations only: no prompts, keys, or conversation content."""
import json
import threading
_lock=threading.Lock()
from cronos import usage

def save(timings):
    try:
        usage.ROOT.mkdir(exist_ok=True)
        path=usage.ROOT/'last-conversation-timing.json'
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(timings),encoding='utf-8');temporary.replace(path)
    except OSError:pass

def read():
    try:return json.loads((usage.ROOT/'last-conversation-timing.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}


def save_live(timings):
    try:
        usage.ROOT.mkdir(exist_ok=True)
        path=usage.ROOT/'last-live-timing.json'
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(timings),encoding='utf-8');temporary.replace(path)
    except OSError:pass


def read_live():
    try:return json.loads((usage.ROOT/'last-live-timing.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}


def save_client(timings):
    with _lock:
        usage.ROOT.mkdir(exist_ok=True)
        path=usage.ROOT/'last-client-latency.json'
        old=read_client()
        if old.get('turn_id')==timings.get('turn_id'):
            timings={**old,**{key:value for key,value in timings.items() if value is not None}}
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(timings),encoding='utf-8');temporary.replace(path)


def read_client():
    try:return json.loads((usage.ROOT/'last-client-latency.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}
