"""Recover usable Live transcripts without another generation or guessed tools."""
import json
import re

from cronos.providers import parse_reply, ProviderError
from cronos.reply_stream import ready_reply


def parse_live_output(raw, *, complete=False):
    text=re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.I)
    try:
        return parse_reply(text), False
    except ProviderError:
        pass
    # Live returns a transcription, not a JSON-mode response. Literal line
    # breaks inside strings and a fenced object are recoverable locally.
    try:
        data=json.loads(text, strict=False)
        if isinstance(data,dict):
            # Tools remain strictly validated: never drop or invent an action.
            calls=data.get('tool_calls',[]);reply=data.get('reply')
            tool_only=bool(calls) and reply in (None,'')
            if not tool_only and (not isinstance(reply,str) or not reply.strip()):raise ValueError()
            base=parse_reply(json.dumps({'reply':'tool request' if tool_only else reply,'tool_calls':calls,'topics':[]}))
            if tool_only:base['reply']=''
            topics=data.get('topics',[])
            if isinstance(topics,list):
                for topic in topics[:100]:
                    try:base['topics'].extend(parse_reply(json.dumps({'reply':'ok','topics':[topic]}))['topics'])
                    except ProviderError:pass
            return base, True
    except (ValueError,TypeError,ProviderError):
        pass
    # Only at the end of a turn: a fully decoded reply after an explicitly
    # empty tool list can survive truncated memory metadata. Never repair tools.
    if complete:
        reply=ready_reply(text)
        if reply:return {'reply':reply,'tool_calls':[],'topics':[]}, True
    raise ProviderError('Gemini Live enviou uma resposta incompleta ou inválida. Nenhuma ferramenta foi executada.',502)
