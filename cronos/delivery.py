"""Per-turn delivery receipts. No audio, prompts, answers or credentials retained."""
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import threading
import time
from uuid import UUID,uuid4

current=ContextVar('delivery_receipt',default=None)

class DeliveryLog:
    def __init__(self):self.rows=OrderedDict();self.lock=threading.Lock()
    def record(self,turn,stage,**fields):
        with self.lock:
            row=self.rows.setdefault(turn,{'turn_id':turn,'started':time.time(),'events':[]})
            if stage=='playback_started' and any(event['stage']==stage for event in row['events']):return
            allowed={k:v for k,v in fields.items() if k in {'provider','bytes','characters','http_status','error_type','response_ms'} and isinstance(v,(str,int,float))}
            row['events'].append({'stage':stage,'elapsed_ms':round((time.time()-row['started'])*1000),**allowed})
            row['events']=row['events'][-40:]
            while len(self.rows)>40:self.rows.popitem(last=False)
    def snapshot(self):
        with self.lock:return deepcopy(list(self.rows.values())[-10:][::-1])

@contextmanager
def scope(log,turn=None):
    try:turn=str(UUID(str(turn)))
    except (ValueError,TypeError):turn=str(uuid4())
    token=current.set((log,turn))
    try:yield turn
    except Exception as exc:
        log.record(turn,'failed',error_type=type(exc).__name__,**({'http_status':exc.status_code} if isinstance(getattr(exc,'status_code',None),int) else {}))
        raise
    finally:current.reset(token)

def mark(stage,**fields):
    active=current.get()
    if active:active[0].record(active[1],stage,**fields)
