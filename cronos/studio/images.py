"""Explicit public-image discovery; license metadata travels with the asset."""
import asyncio
import re
import httpx
from .network import public_fetch

HEADERS = {'User-Agent': 'Cronos-Studio/1.0 (https://github.com/Pedro-Prog-crypto/Cronos)'}


def plain(value): return re.sub(r'<[^>]*>', '', str(value))[:500]


async def search_images(query, limit=8, orientation='any'):
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        response = await client.get('https://commons.wikimedia.org/w/api.php', params={
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': query + ' filetype:bitmap',
            'gsrnamespace': 6, 'gsrlimit': min(30, limit * 3) if orientation != 'any' else limit, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mime|size', 'iiurlwidth': 600})
        response.raise_for_status(); data = response.json()
    results = []
    for page in data.get('query', {}).get('pages', {}).values():
        info = (page.get('imageinfo') or [{}])[0]; meta = info.get('extmetadata', {})
        if info.get('mime') not in {'image/jpeg', 'image/png'}: continue
        width, height = info.get('width', 0), info.get('height', 0)
        shape = 'square' if width == height else 'horizontal' if width > height else 'vertical'
        if orientation != 'any' and (not width or not height or shape != orientation): continue
        thumb = info.get('thumburl', '')
        results.append({'title': page['title'], 'source': info.get('descriptionurl'),
                        'width': width, 'height': height, 'orientation': shape,
                        'thumbnail': thumb if thumb.startswith('https://upload.wikimedia.org/') else '',
                        'author': plain(meta.get('Artist', {}).get('value', '')),
                        'license': plain(meta.get('LicenseShortName', {}).get('value', '')),
                        'attribution': plain(meta.get('Attribution', {}).get('value', ''))})
    return results[:limit]


async def download_image(title):
    if not title.startswith('File:'): raise ValueError('Selecione um arquivo do Wikimedia Commons.')
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        response = await client.get('https://commons.wikimedia.org/w/api.php', params={
            'action': 'query', 'format': 'json', 'prop': 'imageinfo', 'titles': title,
            'iiprop': 'url|extmetadata|mime|size', 'iiurlwidth': '1400'})
        response.raise_for_status(); data = response.json()
    info = (next(iter(data.get('query', {}).get('pages', {}).values()), {}).get('imageinfo') or [None])[0]
    if not info or info.get('mime') not in {'image/jpeg', 'image/png'}: raise ValueError('Imagem não disponível.')
    url = info.get('thumburl') or info.get('url', '')
    if not url.startswith('https://upload.wikimedia.org/'): raise ValueError('Origem de imagem não autorizada.')
    page = await asyncio.to_thread(public_fetch, url, max_bytes=2 * 1024 * 1024, accept='image/jpeg,image/png')
    if page['status'] != 200: raise ValueError('A imagem não foi recebida.')
    meta = info.get('extmetadata', {})
    source = {'url': info.get('descriptionurl'), 'title': title,
              'author': plain(meta.get('Artist', {}).get('value', '')),
              'license': plain(meta.get('LicenseShortName', {}).get('value', ''))}
    return page['body'], source


async def suggest_image(category, orientation='any', *, exclude=()):
    terms = {'restaurante': 'Brazilian cuisine', 'hotel': 'hotel swimming pool', 'lava_jato': 'car detailing',
             'loja': 'shop interior', 'clinica': 'physiotherapy', 'barbearia': 'barbershop interior',
             'academia': 'gym training', 'imobiliaria': 'house architecture', 'educacao': 'library',
             'eventos': 'concert stage', 'portfolio': 'architecture', 'servicos': 'office interior', 'personalizado': 'architecture'}
    entries = await search_images(terms.get(category, 'architecture'), limit=20, orientation=orientation)
    eligible = [e for e in entries if e['title'] not in exclude and e['license'].startswith(('CC BY', 'CC0', 'Public domain', 'PD')) and not re.search(r'\b(?:NC|ND)\b',e['license'])]
    if not eligible: raise ValueError('Nenhuma imagem com licença identificada foi encontrada.')
    # Prefer usable resolution rather than the first arbitrary tiny search result.
    entry = max(eligible, key=lambda e: min(e.get('width', 0), e.get('height', 0)))
    raw, source = await download_image(entry['title'])
    return raw, entry['title'], source
