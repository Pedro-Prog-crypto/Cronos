"""Desktop panels: persisted preferences, measured resources and scoped local actions."""
import asyncio
import json
import os
import shutil
import sqlite3
import sys
import time
import zipfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4, UUID

import httpx
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from cronos import conversation_metrics
from cronos.integrations import ProviderSpec, checked_url, specs
from cronos.monitor import memory_pressure
from cronos.providers import ProviderError


class Preferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    context_messages: int = Field(default=40, ge=2, le=100)
    language: Literal['pt-BR', 'en-US', 'es-ES'] = 'pt-BR'
    response_style: Literal['natural', 'concise', 'detailed'] = 'natural'
    called_only: bool = False
    auto_index: bool = True
    save_diary: bool = True
    backup_daily: bool = False
    retention_days: Literal[7, 30, 90, 365] = 90
    web_enabled: bool = True
    apps_enabled: bool = True
    files_enabled: bool = True
    commands_enabled: bool = False
    confirm_tools: bool = False
    confirm_critical: Literal[True] = True
    lock_minimize: bool = False
    log_security: bool = True
    search_requested_only: bool = True
    trusted_sources: bool = True
    search_provider: Literal['auto', 'duckduckgo'] = 'auto'
    auto_refresh: bool = True
    refresh_seconds: Literal[5, 15, 30] = 5
    processing_mode: Literal['balanced', 'economy'] = 'balanced'
    priority: Literal['normal', 'low'] = 'normal'
    background_processing: bool = True
    voice_speed: float = Field(default=1, ge=.5, le=2)
    voice_pitch: float = Field(default=.5, ge=0, le=1)
    voice_volume: float = Field(default=.8, ge=0, le=1)
    voice_profile: Literal['configured'] = 'configured'
    input_label: str = Field(default='', max_length=300)
    output_label: str = Field(default='', max_length=300)
    device_auto_connect: bool = True
    microphone_sensitivity: int = Field(default=70,ge=0,le=100)
    microphone_gain: float = Field(default=2,ge=1,le=4)
    vision_threshold: int = Field(default=78, ge=0, le=100)
    vision_ocr: bool = True
    vision_realtime: bool = False


class PanelState:
    def __init__(self, app):
        self.app = app
        state = app.state
        with state.memory.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS panel_preferences (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
            row = db.execute('SELECT payload FROM panel_preferences WHERE id=1').fetchone()
        self.preferences = Preferences(context_messages=state.engine.settings.context_messages,
                                       voice_speed=state.engine.settings.fish_speed,
                                       commands_enabled=state.engine.settings.allow_executables)
        if row:
            self.preferences = Preferences.model_validate_json(row[0])
        self.initial_settings = state.engine.settings
        self.requests = 0
        self.active = 0
        self.cpu_previous = None
        self.last_network = None
        self.backup_info = None
        self.apply()
        if self.preferences.priority == 'low':
            try:set_priority('low')
            except ValueError:
                state.monitor.update('priority_failed', True, message='O Windows não aplicou a prioridade baixa configurada.')

    def apply(self):
        state, prefs = self.app.state, self.preferences
        state.engine.settings = replace(state.engine.settings, context_messages=prefs.context_messages)
        state.engine.panel_preferences = prefs
        state.memory.save_diary = prefs.save_diary
        state.monitor.record_events = prefs.log_security
        state.registry.permission_policy = self.policy

    def policy(self, name):
        p = self.preferences
        group = 'web_enabled' if name in {'web_search', 'web_news', 'browser_open', 'browser_search'} else 'apps_enabled' if name == 'desktop_open_app' else 'commands_enabled' if name == 'desktop_run_executable' else 'files_enabled' if name.startswith('files_') or name == 'desktop_open_folder' else None
        return (not group or getattr(p, group)), p.confirm_tools or (p.confirm_critical and name == 'desktop_run_executable')

    def save(self, changes):
        data = self.preferences.model_dump()
        data.update(changes)
        candidate = Preferences.model_validate(data)
        if candidate.priority != self.preferences.priority:
            set_priority(candidate.priority)
        with self.app.state.memory.connect() as db:
            db.execute('INSERT OR REPLACE INTO panel_preferences VALUES(1,?)', (candidate.model_dump_json(),))
        self.preferences = candidate
        self.apply()
        if 'retention_days' in changes:self.archive_old_backups()
        return candidate.model_dump()

    def cpu(self):
        try:
            if sys.platform == 'win32':
                import ctypes
                from ctypes import wintypes
                idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
                if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                    return None
                number = lambda f: (f.dwHighDateTime << 32) | f.dwLowDateTime
                current = number(idle), number(kernel) + number(user)
            else:
                values = [int(n) for n in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
                current = values[3] + values[4], sum(values)
            previous, self.cpu_previous = self.cpu_previous, current
            if not previous or current[1] <= previous[1]:
                return None
            return round(max(0, min(100, 100 * (1 - (current[0]-previous[0])/(current[1]-previous[1])))), 1)
        except (OSError, ValueError, IndexError):
            return None

    def snapshot(self):
        state = self.app.state
        stats = state.memory.stats()
        with state.memory.connect() as db:
            searches = [dict(row) for row in db.execute("SELECT payload,created FROM tool_events ORDER BY id DESC LIMIT 200")]
        searches = [{'time':r['created'], **json.loads(r['payload'])} for r in searches if json.loads(r['payload']).get('name') in {'web_search','web_news'}][:30]
        disk = shutil.disk_usage(state.memory.vault)
        return {'preferences':self.preferences.model_dump(), 'memory':{**stats, 'vault':str(state.memory.vault),
                'database_bytes':state.memory.database.stat().st_size, 'disk_used_bytes':disk.used,
                'disk_total_bytes':disk.total, 'folders':[p.name for p in state.memory.vault.iterdir() if p.is_dir() and not p.name.startswith('.') and not p.is_symlink()]},
                'backup':self.backup_info or self.last_backup(), 'archived_backups':len(list((self.backup_root/'archive').glob('memory-*.zip'))) if (self.backup_root/'archive').exists() else 0, 'cpu_percent':self.cpu(), 'ram_percent':memory_pressure(),
                'timings_ms':conversation_metrics.read(), 'live_timings_ms':conversation_metrics.read_live(), 'client_latency':conversation_metrics.read_client(), 'processing_phase':getattr(state.engine,'phase','idle'), 'active_requests':self.active, 'completed_requests':self.requests,
                'network':self.last_network, 'searches':searches, 'monitor':state.monitor.snapshot(),
                'modules':state.features.catalog(), 'windows_audit':state.windows.last_audit,
                'windows_available':state.windows.platform == 'win32', 'encrypted_storage':False,
                'keys_hidden':True, 'files_root':str(state.engine.settings.files_root),
                'executables_available':state.engine.settings.allow_executables,
                'last_tool':state.memory.tool_history_any()}

    @property
    def backup_root(self):
        return self.app.state.memory.path('.cronos', 'backups')

    def last_backup(self):
        if not self.backup_root.exists():
            return None
        entries = sorted(self.backup_root.glob('memory-*.zip'))
        return {'name':entries[-1].name, 'created':datetime.fromtimestamp(entries[-1].stat().st_mtime, timezone.utc).isoformat()} if entries else None

    def backup(self):
        memory = self.app.state.memory
        root = self.backup_root
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink() or not root.resolve().is_relative_to(memory.vault):
            raise ValueError('Destino de backup inválido.')
        name = f'memory-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}-{uuid4().hex[:8]}.zip'
        temporary = root / (name + '.tmp')
        snapshot = root / (name + '.sqlite3')
        try:
            with memory.connect() as source, sqlite3.connect(snapshot) as destination:
                source.backup(destination)
            with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
                archive.write(snapshot, '.cronos/memory.sqlite3')
                count, size = 0, 0
                for directory, folders, files in os.walk(memory.vault, followlinks=False):
                    folders[:] = [f for f in folders if not f.startswith('.') and not (Path(directory)/f).is_symlink()]
                    for file in files:
                        path = Path(directory)/file
                        if path.suffix.lower() != '.md' or path.is_symlink():
                            continue
                        count += 1; size += path.stat().st_size
                        if count > 100000 or size > 512*1024*1024:
                            raise ValueError('Backup excede 100 mil notas ou 512 MB de Markdown.')
                        memory.path('', path.relative_to(memory.vault).as_posix())
                        archive.write(path, path.relative_to(memory.vault))
            temporary.replace(root/name)
            self.archive_old_backups()
            self.backup_info = {'name':name, 'created':datetime.now(timezone.utc).isoformat(), 'notes':count}
            return self.backup_info
        finally:
            snapshot.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)

    def archive_old_backups(self):
        if not self.backup_root.exists():return
        limit=time.time()-self.preferences.retention_days*86400
        for path in self.backup_root.glob('memory-*.zip'):
            if path.is_symlink() or path.stat().st_mtime>=limit:continue
            archive=self.app.state.memory.path('.cronos', 'backups/archive')
            archive.mkdir(exist_ok=True)
            target=archive/path.name
            if not target.exists():path.rename(target)

    async def maintain(self):
        while True:
            await asyncio.sleep(60)
            if self.preferences.backup_daily:
                last = self.last_backup()
                if not last or (datetime.now(timezone.utc)-datetime.fromisoformat(last['created'])).total_seconds() >= 86400:
                    async with self.app.state.lock:
                        try:
                            await asyncio.to_thread(self.backup)
                        except (OSError, ValueError):
                            self.app.state.monitor.update('backup_failed', True, message='O backup local não foi concluído.')
            # Expired backups are archived, never deleted automatically.


def set_priority(value):
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        kernel.SetPriorityClass.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000 if value == 'low' else 0x20):
            raise ValueError('O Windows recusou a mudança de prioridade.')
    # On the development host this desktop-only setting is persisted but not applied.


class Adapter(BaseModel):
    model_config = ConfigDict(extra='forbid')
    spec: ProviderSpec


class ClientLatency(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)
    turn_id: UUID
    source: Literal['text','voice']
    chat_ms: float = Field(ge=0,le=1_800_000)
    recognition_ms: float | None = Field(default=None,ge=0,le=1_800_000)
    endpoint_ms: float | None = Field(default=None,ge=0,le=60000)
    speech_request_ms: float | None = Field(default=None,ge=0,le=1_800_000)
    playback_ms: float | None = Field(default=None,ge=0,le=1_800_000)
    first_audio_ms: float | None = Field(default=None,ge=0,le=1_800_000)


class VaultSelection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    path: str = Field(min_length=1,max_length=2000)


class NativeAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['audio', 'bluetooth', 'lock', 'vault', 'providers']


def install_panels(app, authenticate):
    auth = [Depends(authenticate)]

    @app.post('/panels/latency', dependencies=auth)
    async def latency(body: ClientLatency):
        await asyncio.to_thread(conversation_metrics.save_client, body.model_dump(mode='json'))
        return {'recorded':True}

    @app.get('/panels', dependencies=auth)
    async def snapshot(request: Request):
        return await asyncio.to_thread(request.app.state.panels.snapshot)

    @app.patch('/panels/preferences', dependencies=auth)
    async def preferences(request: Request):
        changes = await request.json()
        if not isinstance(changes, dict):
            raise HTTPException(422, 'Preferências inválidas.')
        async with request.app.state.lock:
            try:
                result = await asyncio.to_thread(request.app.state.panels.save, changes)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
        return {'preferences':result}

    @app.post('/panels/backup', dependencies=auth)
    async def backup(request: Request):
        async with request.app.state.lock:
            try:
                return await asyncio.to_thread(request.app.state.panels.backup)
            except (OSError, ValueError) as exc:
                raise HTTPException(409, str(exc)) from None

    @app.post('/panels/network', dependencies=auth)
    async def network(request: Request):
        if request.app.state.engine.settings.privacy_mode != 'online':
            raise HTTPException(409, 'O teste de internet está desativado no modo local.')
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                response = await client.get('https://www.gstatic.com/generate_204')
                response.raise_for_status()
            result = {'connected':response.status_code==204, 'latency_ms':round((time.perf_counter()-started)*1000), 'checked_at':datetime.now(timezone.utc).isoformat()}
        except httpx.HTTPError:
            result = {'connected':False, 'latency_ms':None, 'checked_at':datetime.now(timezone.utc).isoformat()}
        request.app.state.panels.last_network = result
        return result

    @app.post('/panels/adapters', dependencies=auth)
    async def adapter(body: Adapter, request: Request):
        state = request.app.state
        async with state.lock:
            settings = state.engine.settings
            try:
                if body.spec.id in {'gemini', 'ollama'}:
                    raise ValueError('Use um ID distinto dos provedores principais.')
                if body.spec.base_url:
                    checked_url(body.spec.base_url)
                entries = specs(settings)
                if any(e.id == body.spec.id for e in entries):
                    raise ValueError('ID de integração já registrado.')
                path = settings.providers_file
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix('.tmp')
                temporary.write_text(json.dumps({'providers':[e.model_dump() for e in entries] + [body.spec.model_dump()]}, ensure_ascii=False, indent=2), encoding='utf-8')
                temporary.replace(path)
            except (ValueError, ProviderError, OSError) as exc:
                raise HTTPException(422, str(exc)) from None
        return {'registered':body.spec.id}

    @app.post('/panels/vault', dependencies=auth)
    async def vault(body: VaultSelection, request: Request):
        if request.app.state.windows.platform != 'win32':
            raise HTTPException(409, 'A seleção do cofre requer o Cronos instalado no Windows.')
        path=Path(body.path).expanduser()
        if not path.is_absolute() or not path.is_dir() or path.is_symlink():
            raise HTTPException(422, 'Escolha uma pasta existente e sem links simbólicos.')
        from dotenv import set_key
        async with request.app.state.lock:
            try:await asyncio.to_thread(set_key, '.env', 'CRONOS_VAULT', str(path.resolve()))
            except OSError:raise HTTPException(409, 'Não foi possível salvar a escolha do cofre no arquivo .env.') from None
        return {'next_vault':str(path.resolve()), 'restart_required':True}

    @app.post('/panels/native', dependencies=auth)
    async def native(body: NativeAction, request: Request):
        state = request.app.state
        if state.windows.platform != 'win32':
            raise HTTPException(409, 'Esta ação requer o Cronos instalado no Windows.')
        if body.action == 'lock':
            import ctypes
            if not ctypes.windll.user32.LockWorkStation():
                raise HTTPException(409, 'Não foi possível bloquear a sessão do Windows.')
        else:
            target = {'audio':'ms-settings:sound', 'bluetooth':'ms-settings:bluetooth',
                      'vault':str(state.memory.vault), 'providers':str(state.engine.settings.providers_file.resolve())}[body.action]
            try:
                os.startfile(target)
            except OSError:
                raise HTTPException(409, 'O Windows não conseguiu abrir esse destino.') from None
        return {'opened':body.action}
