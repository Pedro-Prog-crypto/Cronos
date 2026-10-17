"""Keep presentation/transport metadata out of speech; never modify saved notes."""
import json
import re

# A line-labelled storage footer is not part of the answer. Do not remove normal
# sentences mentioning a user, banking, Spanish, or a programming subject.
FOOTER = re.compile(r'(?im)^\s*(?:#{1,6}\s*)?(?:resumo (?:da conversa|para (?:a )?mem[oó]ria)|metadados(?: de mem[oó]ria)?|mem[oó]ria interna|topics|tool_calls)\s*[:：]')
PATH_LINE = re.compile(r'(?im)^\s*(?:\[)?(?:[A-Z]:[\\/]|/(?:home|workspace|tmp|Users)/|(?:Temas|Memorias|Conversas)/)[^\n]*(?:\n|$)')


def conversation_text(text):
    """Only remove explicit accidental wrappers, preserving requested code in UI."""
    if not isinstance(text,str):return ''
    stripped=text.strip()
    if stripped.startswith('{'):
        try:
            data=json.loads(stripped)
            # Unwrap a nested answer only when no action could be discarded.
            if isinstance(data,dict) and data.get('tool_calls',[])==[] and isinstance(data.get('reply'),str):
                stripped=data['reply'].strip()
        except (ValueError,TypeError):pass
    # Strip an accidental source prefix only; examples/code later in the answer
    # remain unchanged in the visual response.
    stripped=re.sub(r'\A\s*(?:(?:\[)?(?:[A-Z]:[\\/]|/(?:home|workspace|tmp|Users)/|(?:Temas|Memorias|Conversas)/)[^\n]*(?:\n|$)\s*)+','',stripped)
    match=FOOTER.search(stripped)
    if match and stripped[:match.start()].strip():stripped=stripped[:match.start()].rstrip()
    # Some audio transcripts append the memory summary without a label. Only a
    # new trailing paragraph, never an in-line quotation or the entire answer.
    stripped=re.sub(r'\n\s*\n(?:O usu[aá]rio|A usu[aá]ria) (?:disse|falou|mencionou|relatou|afirmou|perguntou)\b[^\n]*(?:\n[^\n]+)*\s*$', '', stripped, flags=re.I)
    return stripped.strip()


def speech_text(text):
    """Plain spoken prose. Code and links stay available visually, not read aloud."""
    text=conversation_text(text)
    text=re.sub(r'```[^\n]*\n[\s\S]*?(?:```|$)', ' O código está disponível na tela. ',text)
    text=re.sub(r'!\[([^\]]*)\]\([^\n)]*\)',r'\1',text)
    text=re.sub(r'\[([^\]]+)\]\([^\n)]*\)',r'\1',text)
    text=re.sub(r'https?://[^\s<>]+','',text)
    text=re.sub(r'(?<!\w)[A-Z]:[\\/][^\s<>]+','',text)
    text=re.sub(r'(?m)^\s*#{1,6}\s*','',text)
    text=text.replace('**','').replace('__','').replace('`','')
    return re.sub(r'\s+',' ',text).strip()
