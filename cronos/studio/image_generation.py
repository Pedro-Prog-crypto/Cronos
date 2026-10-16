"""Optional image generation using an existing official OpenAI integration.

No provider is registered and no key is copied or persisted by this module.
"""
import base64
import os

import httpx

from cronos.integrations import specs
from cronos.providers import ProviderError

MODELS = ('gpt-image-1',)
SIZES = {'horizontal': '1536x1024', 'vertical': '1024x1536'}


def image_providers(settings):
    if settings.privacy_mode != 'online': return []
    return [{'id': spec.id, 'models': list(MODELS)} for spec in specs(settings)
            if spec.kind == 'openai' and spec.base_url.rstrip('/') == 'https://api.openai.com/v1'
            and spec.key_env and os.getenv(spec.key_env, '').strip()]


async def generate_image(settings, provider_id, prompt, orientation, model='gpt-image-1'):
    if model not in MODELS or orientation not in SIZES:
        raise ValueError('Escolha um modelo e um formato de imagem disponíveis.')
    if provider_id not in {p['id'] for p in image_providers(settings)}:
        raise ValueError('Adicione uma integração oficial OpenAI com chave válida para gerar imagens. A assinatura ChatGPT não inclui créditos desta API.')
    spec = next(s for s in specs(settings) if s.id == provider_id)
    # Deliberately fixed: a compatible text API is not evidence of image support.
    endpoint = 'https://api.openai.com/v1/images/generations'
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(endpoint, headers={'Authorization': 'Bearer ' + os.getenv(spec.key_env).strip()}, json={
                'model': model, 'prompt': prompt, 'size': SIZES[orientation], 'quality': 'medium', 'n': 1,
                'output_format': 'jpeg'})
            response.raise_for_status()
            value = response.json()['data'][0]['b64_json']
            if not isinstance(value, str) or len(value) > 11_200_000: raise ValueError()
            raw = base64.b64decode(value, validate=True)
            if len(raw) > 8 * 1024 * 1024: raise ValueError()
            return raw
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        reason = {401: 'chave rejeitada', 403: 'acesso ao modelo de imagem não liberado para este projeto',
                  429: 'cota ou limite da API de imagens atingido', 400: 'pedido ou modelo de imagem recusado'}.get(status, 'serviço de imagens indisponível')
        raise ProviderError(f'OpenAI imagens: {reason} (HTTP {status}). Nenhuma tentativa foi repetida automaticamente.', status) from None
    except httpx.RequestError:
        raise ProviderError('A API de imagens não respondeu. Confira seu painel de uso antes de tentar novamente; não houve repetição automática.') from None
    except (ValueError, KeyError, IndexError, TypeError):
        raise ValueError('A API não entregou uma imagem válida. A proposta anterior foi preservada.') from None
