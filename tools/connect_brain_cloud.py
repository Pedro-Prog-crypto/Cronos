"""Pair a persistent Cronos vault with a Brain Cloud device export."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv

from cronos.brain_cloud import BrainCloud
from cronos.config import Settings


async def verify(config: dict[str, str]) -> None:
    local = urlsplit(config['baseUrl']).hostname in {'localhost', '127.0.0.1'}
    async with httpx.AsyncClient(base_url=config['baseUrl'], follow_redirects=False,
                                 trust_env=not local, timeout=httpx.Timeout(10, connect=5)) as client:
        health = await client.get('/v1/health')
        if health.status_code != 200 or health.json().get('name') != 'CRONOS BRAIN CLOUD':
            raise ValueError('O endereço não respondeu como Cronos Brain Cloud.')
        session = await client.post('/v1/auth/sessions', json={'deviceId':config['deviceId'], 'credential':config['credential']})
        if session.status_code != 201 or not session.json().get('accessToken'):
            raise ValueError('O Brain Cloud recusou o dispositivo. Gere outra conexão no painel Integração.')


def import_pairing(source: Path, vault: Path) -> Path:
    config = BrainCloud.validate(json.loads(source.read_text(encoding='utf-8')))
    asyncio.run(verify(config))
    target = vault / '.cronos' / 'brain-cloud.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
    if os.name != 'nt': temporary.chmod(0o600)
    os.replace(temporary, target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?', type=Path)
    args = parser.parse_args()
    load_dotenv('.env', override=True)
    if args.file is None:
        from tkinter import Tk, filedialog
        root = Tk(); root.withdraw()
        selected = filedialog.askopenfilename(title='Escolha cronos-desktop.json do Brain Cloud',
                                               filetypes=[('Conexão JSON', '*.json')])
        root.destroy()
        if not selected: return
        source = Path(selected)
    else:
        source = args.file
    target = import_pairing(source, Settings.from_env().vault)
    print('Brain Cloud conectado. Pareamento guardado no vault do Cronos: ' + str(target))
    print('Reabra o Cronos. O Brain precisa estar em execução e ter um modelo de IA configurado para responder.')


if __name__ == '__main__': main()
