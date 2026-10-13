"""Importa só a configuração de voz original; não executa código do ZIP."""
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile
from cronos.migrate import apply_env


def read_voice(source):
    source=Path(source)
    if source.suffix.lower()=='.zip':
        with ZipFile(source) as archive:
            files=[name for name in archive.namelist() if name.replace('\\','/').endswith('config/fish_audio.json')]
            if len(files)!=1:raise ValueError('O ZIP precisa conter uma única configuração config/fish_audio.json.')
            if archive.getinfo(files[0]).file_size>65536:raise ValueError('Configuração de voz muito grande.')
            data=json.loads(archive.read(files[0]))
    else:
        if source.stat().st_size>65536:raise ValueError('Configuração de voz muito grande.')
        data=json.loads(source.read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict):raise ValueError('Configuração inválida.')
    url=urlsplit(data.get('api_url') or 'https://api.fish.audio/v1/tts')
    if url.scheme!='https' or url.hostname!='api.fish.audio' or url.path!='/v1/tts' or url.username or url.query or url.fragment or url.port not in (None,443):
        raise ValueError('A configuração não usa o endpoint HTTPS oficial esperado.')
    key=str(data.get('api_key') or '').strip().removeprefix('Bearer ').strip()
    reference=str(data.get('reference_id') or '').strip()
    if not key or not re.fullmatch('[0-9a-fA-F]{32}',reference):raise ValueError('Chave ou ID de voz ausente/inválido.')
    model=str(data.get('model') or '').strip().lower()
    if not re.fullmatch('[a-z0-9._-]{1,64}',model):raise ValueError('Modelo inválido.')
    fmt=data.get('format','wav')
    if fmt not in {'wav','mp3'}:raise ValueError('Formato de áudio não suportado.')
    speed=float(data.get('speed',1))
    if not .5<=speed<=2:raise ValueError('Velocidade inválida.')
    latency=data.get('latency','balanced')
    if latency not in {'balanced','normal'}:raise ValueError('Latência inválida.')
    return {'CRONOS_TRANSCRIPTION_PROVIDER':'vosk','FISH_API_KEY':key,'FISH_REFERENCE_ID':reference,'FISH_MODEL':model,
            'FISH_FORMAT':fmt,'FISH_SPEED':str(speed),'FISH_LATENCY':latency}


def read_original_gemini(source):
    source=Path(source)
    if source.suffix.lower()=='.zip':
        with ZipFile(source) as archive:
            matches=[name for name in archive.namelist() if name.replace('\\','/').endswith('config/api_keys.json')]
            if not matches:return {}
            if len(matches)!=1 or archive.getinfo(matches[0]).file_size>65536:raise ValueError('Configuração de conexão inválida.')
            data=json.loads(archive.read(matches[0]))
    else:
        file=source.parent/'api_keys.json'
        if not file.is_file():return {}
        if file.stat().st_size>65536:raise ValueError('Configuração de conexão inválida.')
        data=json.loads(file.read_text(encoding='utf-8-sig'))
    key=data.get('gemini_api_key') if isinstance(data,dict) else None
    if not key:return {}
    if not isinstance(key,str) or len(key)>512 or '\n' in key or '\r' in key:raise ValueError('Chave original inválida.')
    return {'GEMINI_API_KEY':key.strip()}


def import_voice(source,destination):
    values=read_voice(source);destination=Path(destination)
    from dotenv import dotenv_values
    current=dotenv_values(destination) if destination.exists() else {}
    if not (current.get('GEMINI_API_KEY') or '').strip():values.update(read_original_gemini(source))
    if destination.exists():
        folder=destination.parent/'.cronos-local';folder.mkdir(exist_ok=True)
        backup=folder/('env-before-voice-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.bak')
        shutil.copy2(destination,backup)
        try:backup.chmod(0o600)
        except OSError:pass
    apply_env(destination,values,overrides=set(values))
    try:destination.chmod(0o600)
    except OSError:pass


def main():
    import tkinter as tk
    from tkinter import filedialog,messagebox
    root=tk.Tk();root.withdraw()
    source=filedialog.askopenfilename(title='Selecione o ZIP original ou fish_audio.json',filetypes=[('Configuração original','*.zip *.json')])
    if source:
        try:
            import_voice(source,Path.cwd()/'.env')
            messagebox.showinfo('Kronos','Voz original importada. A chave Gemini já configurada foi preservada; só é recuperada do original quando ausente. Chaves e IDs não foram exibidos. Modelo Gemini, memória e personalidade foram preservados. Feche e reabra o Kronos.')
        except Exception:
            messagebox.showerror('Kronos','Não foi possível importar. Verifique se o arquivo contém config/fish_audio.json válido. Credenciais não serão exibidas.')
    root.destroy()


if __name__=='__main__':main()
