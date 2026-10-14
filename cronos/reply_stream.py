"""Optional per-request delivery of a complete reply before memory metadata."""
from contextvars import ContextVar
import json

reply_sink = ContextVar('reply_sink', default=None)


def ready_reply(raw):
    # Only accept the exact leading fields. Tool requests must never be spoken
    # as completed actions. JSONDecoder handles escaped quotes and braces.
    decoder=json.JSONDecoder()
    try:
        index=0
        def space():
            nonlocal index
            while index<len(raw) and raw[index].isspace():index+=1
        space()
        if raw[index]!='{':return None
        index+=1
        for expected in ('tool_calls','reply'):
            space();key,end=decoder.raw_decode(raw,index);index=end;space()
            if key!=expected or raw[index]!=':':return None
            index+=1;space();value,end=decoder.raw_decode(raw,index);index=end;space()
            if expected=='tool_calls':
                if value!=[] or raw[index]!=',':return None
                index+=1
            elif isinstance(value,str) and value.strip():
                if raw[index] not in ',}':return None
                return value
    except (ValueError,IndexError):pass
    return None


async def deliver(reply):
    sink=reply_sink.get()
    if sink is not None:await sink(reply)


def ready_intro(raw):
    """One short, complete sentence while the rest of reply is generated."""
    import re
    decoder=json.JSONDecoder()
    try:
        # No regex matching inside user text: decode the leading tool field.
        if not raw.lstrip().startswith('{'):return None
        index=raw.index('{')+1
        while raw[index].isspace():index+=1
        key,index=decoder.raw_decode(raw,index)
        if key!='tool_calls':return None
        while raw[index].isspace():index+=1
        if raw[index]!=':':return None
        index+=1
        while raw[index].isspace():index+=1
        calls,index=decoder.raw_decode(raw,index)
        if calls!=[]:return None
        while raw[index].isspace():index+=1
        if raw[index]!=',':return None
        index+=1
        while raw[index].isspace():index+=1
        key,index=decoder.raw_decode(raw,index)
        if key!='reply':return None
        while raw[index].isspace():index+=1
        if raw[index]!=':':return None
        index+=1
        while raw[index].isspace():index+=1
        if raw[index]!='"':return None
        start=index+1;index=start;escaped=False
        while index<len(raw):
            char=raw[index]
            if char=='"' and not escaped:break
            if char=='\\' and not escaped:escaped=True
            else:escaped=False
            index+=1
        segment=raw[start:index]
        if escaped:segment=segment[:-1]
        segment=re.sub(r'\\u[0-9a-fA-F]{0,3}$','',segment)
        text=json.loads('"'+segment+'"')
        match=re.search(r'[.!?](?:\s|$)',text[:140])
        if match and any(char.isalnum() for char in text[:match.start()]):return text[:match.end()]
        if len(text)>=100:
            end=text.rfind(' ',0,80)
            if end>=24:return text[:end+1]
    except (ValueError,IndexError):pass
    return None


intro_sink=ContextVar('intro_sink',default=None)
async def deliver_intro(text):
    sink=intro_sink.get()
    if sink is not None:await sink(text)

transcript_sink=ContextVar('transcript_sink',default=None)
async def deliver_transcript(text):
    sink=transcript_sink.get()
    if sink is not None:await sink(text)
