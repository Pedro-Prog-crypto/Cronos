"""Recognize explicit current-news requests without sending general conversation to search."""
import re
import unicodedata
from urllib.parse import urlsplit


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


def verified_news_fallback(outcome):
    """Report only headlines and links actually returned by the search tool."""
    result = outcome.get('result') if outcome.get('status') == 'completed' else None
    articles = result.get('articles', []) if isinstance(result, dict) else []
    lines = []
    for article in articles[:6]:
        if not isinstance(article, dict):
            continue
        title = str(article.get('title') or '').strip()
        url = str(article.get('url') or '').strip()
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if not title or parsed.scheme not in {'http', 'https'} or not parsed.hostname:
            continue
        source = str(article.get('source') or parsed.hostname).strip()
        published = str(article.get('published') or '').strip()
        label = f'{source}; {published}' if published else source
        lines.append(f'{len(lines) + 1}. {title} ({label}) — {url}')
    if lines:
        return ('Encontrei estas notícias recentes, senhor. A integração de IA demorou a responder, '
                'então estou mostrando somente os resultados efetivamente retornados pela busca, '
                'com os links para o senhor conferir:\n' + '\n'.join(lines))
    return ('Não consegui verificar as notícias de hoje agora, senhor. '
            'A busca ou a integração não concluiu; não vou inventar manchetes.')
