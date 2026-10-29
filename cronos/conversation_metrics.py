"""Bounded timing history: no prompts, keys, or conversation content."""
import json
import threading
from datetime import datetime, timezone
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
        rows=read_client_history()
        index=next((i for i,row in enumerate(rows) if row.get('turn_id')==timings.get('turn_id')),None)
        old=rows[index] if index is not None else read_client()
        if old.get('turn_id')==timings.get('turn_id'):
            # Requests may finish out of order; a late 'waiting' event must not
            # erase a measured start or a cancellation.
            if timings.get('sequence') is not None and old.get('sequence',-1)>timings['sequence']:
                return
            timings={**old,**{key:value for key,value in timings.items() if value is not None}}
        timings.setdefault('recorded_at',datetime.now(timezone.utc).isoformat())
        if index is None: rows.append(timings)
        else: rows[index]=timings
        rows=rows[-200:]
        history=usage.ROOT/'client-latency-history.json'
        temporary=history.with_suffix('.tmp')
        temporary.write_text(json.dumps(rows),encoding='utf-8');temporary.replace(history)
        path=usage.ROOT/'last-client-latency.json'
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(rows[-1]),encoding='utf-8');temporary.replace(path)


def read_client_history():
    try:
        rows=json.loads((usage.ROOT/'client-latency-history.json').read_text(encoding='utf-8'))
        return rows[-200:] if isinstance(rows,list) else []
    except (OSError,ValueError):return []


def read_client():
    try:return json.loads((usage.ROOT/'last-client-latency.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}
