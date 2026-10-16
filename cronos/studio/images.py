"""Explicit public-image discovery; license metadata travels with the asset."""
import asyncio
import re
import httpx
from .network import public_fetch

HEADERS = {'User-Agent': 'Cronos-Studio/1.0 (https://github.com/Pedro-Prog-crypto/Cronos)'}


def plain(value): return re.sub(r'<[^>]*>', '', str(value))[:500]


async def search_images(query, limit=8):
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        response = await client.get('https://commons.wikimedia.org/w/api.php', params={
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': query + ' filetype:bitmap',
            'gsrnamespace': 6, 'gsrlimit': limit, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mime', 'iiurlwidth': 600})
        response.raise_for_status(); data = response.json()
    results = []
    for page in data.get('query', {}).get('pages', {}).values():
        info = (page.get('imageinfo') or [{}])[0]; meta = info.get('extmetadata', {})
        if info.get('mime') not in {'image/jpeg', 'image/png'}: continue
        results.append({'title': page['title'], 'source': info.get('descriptionurl'),
                        'author': plain(meta.get('Artist', {}).get('value', '')),
                        'license': plain(meta.get('LicenseShortName', {}).get('value', '')),
                        'attribution': plain(meta.get('Attribution', {}).get('value', ''))})
    return results


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


async def suggest_image(category):
    terms = {'restaurante': 'restaurant cuisine interior', 'hotel': 'hotel pool architecture', 'lava_jato': 'car detailing',
             'loja': 'retail shop interior', 'clinica': 'medical clinic interior', 'barbearia': 'barbershop interior',
             'academia': 'fitness gym interior', 'imobiliaria': 'modern house architecture', 'educacao': 'education library',
             'eventos': 'concert stage', 'portfolio': 'architecture design', 'servicos': 'office architecture', 'personalizado': 'abstract architecture'}
    entries = await search_images(terms.get(category, 'architecture'), limit=5)
    eligible = [e for e in entries if e['license'].startswith(('CC BY', 'CC0', 'Public domain', 'PD'))]
    if not eligible: raise ValueError('Nenhuma imagem com licença identificada foi encontrada.')
    entry = eligible[0]
    raw, source = await download_image(entry['title'])
    return raw, entry['title'], source
