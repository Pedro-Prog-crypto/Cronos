"""Last backend phase durations only: no prompts, keys, or conversation content."""
import json
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
