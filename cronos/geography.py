"""Consulta mundial explícita, limitada, sem URLs controladas pelo modelo."""
import asyncio
import time
from collections import OrderedDict

import httpx
from fastapi import HTTPException


class Places:
    def __init__(self):
        self.cache = OrderedDict()
        self.lock = asyncio.Lock()
        self.last_request = 0.0

    async def search(self, query):
        key = query.casefold().strip()
        async with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            wait = 1.1 - (time.monotonic() - self.last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self.last_request = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
                    response = await client.get('https://nominatim.openstreetmap.org/search',
                        params={'q': query, 'format': 'jsonv2', 'limit': 5},
                        headers={'User-Agent': 'CronosDesktop/0.5 (https://github.com/Pedro-Prog-crypto/Cronos)', 'Accept-Language': 'pt-BR,en'})
                    response.raise_for_status()
                    if len(response.content) > 128_000:
                        raise ValueError('Resposta muito grande')
                    data = response.json()
                    places = [{'name': item['display_name'], 'lat': float(item['lat']), 'lon': float(item['lon'])}
                              for item in data[:5]]
                    if any(not (-90 <= item['lat'] <= 90 and -180 <= item['lon'] <= 180) for item in places):
                        raise ValueError('Coordenadas inválidas')
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                raise HTTPException(502, 'A busca de lugares está indisponível. Tente novamente mais tarde.') from None
            self.cache[key] = places
            if len(self.cache) > 128:
                self.cache.popitem(last=False)
            return places


def install_geography(app, authenticate):
    from fastapi import Depends, Query, Request
    places = Places()

    @app.get('/world/places', dependencies=[Depends(authenticate)])
    async def find_places(request: Request, q: str = Query(min_length=2, max_length=160)):
        if request.app.state.engine.settings.privacy_mode != 'online':
            raise HTTPException(403, 'Modo local: consulta mundial externa desativada.')
        return {'places': await places.search(q.strip())}
