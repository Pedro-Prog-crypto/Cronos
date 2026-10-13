"""Recognize explicit current-news requests without sending general conversation to search."""
import re
import unicodedata


def current_news_query(message):
    text=unicodedata.normalize('NFD',message.casefold())
    text=''.join(c for c in text if not unicodedata.combining(c)).strip()
    text=re.sub(r'^(?:cronos|kronos)[, :]+','',text)
    if re.search(r'\b(?:nao|sem)\s+(?:pesquis|busc|procur)',text):return None
    if re.search(r'\b(?:19|20)\d{2}\b|\bdo dia\s+\d|\b(?:e|tambem)\s+(?:abra|abrir|execute|executar|salve|salvar|apague|enviar)',text):return None
    match=re.fullmatch(r'(?:(?:me )?(?:diga|conte|mostre|traga|fale|busque|pesquise|procure)(?: me)?(?: sobre)?(?: as)? |quais (?:sao|foram) (?:as )?)?(?:as )?(?:principais |ultimas )?(noticias (?:do dia|de hoje|atuais|de agora)(?:\b.*)?)',text)
    if not match:return None
    query=re.sub(r'[, ]+por favor[.!?]*$','',match[1]).strip(' .!?')
    return re.sub(r'^noticias (?:do dia|de hoje|atuais|de agora)','noticias hoje',query)
