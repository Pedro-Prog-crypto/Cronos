@echo off
setlocal
set "CRONOS_RESCUE_SELF=%~f0"
set "CRONOS_RESCUE_FOLDER=%~dp0"
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; try { Add-Type -AssemblyName System.Windows.Forms; $root=$env:CRONOS_RESCUE_FOLDER; if (-not ((Test-Path -LiteralPath (Join-Path $root '.env')) -or (Test-Path -LiteralPath (Join-Path $root 'cronos')))) { $picker=New-Object System.Windows.Forms.FolderBrowserDialog; $picker.Description='Escolha a pasta ATUAL do Cronos com .env e cronos. Nao escolha um ZIP.'; if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }; $root=$picker.SelectedPath }; $question=[System.Windows.Forms.MessageBox]::Show('Feche o Cronos antes do backup. Continuar com a copia de seguranca da pasta selecionada? Nenhuma atualizacao sera instalada.','Salvar e abrir Cronos',[System.Windows.Forms.MessageBoxButtons]::OKCancel); if ($question -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }; $python=Join-Path $root '.venv\Scripts\python.exe'; $prefix=@(); if (-not (Test-Path -LiteralPath $python)) { if (Get-Command py.exe -ErrorAction SilentlyContinue) { $python='py.exe'; $prefix=@('-3') } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { $python='python.exe' } else { throw 'Python nao encontrado. O ambiente .venv pode ter sido apagado. Mantenha a pasta com seus dados.' } }; $raw=[IO.File]::ReadAllText($env:CRONOS_RESCUE_SELF); $parts=$raw -split '(?m)^# CRONOS_RESCUE_PYTHON\r?$'; if ($parts.Length -ne 2) { throw 'Arquivo incompleto; baixe novamente o BAT.' }; $temporary=Join-Path ([IO.Path]::GetTempPath()) ('cronos-rescue-'+[Guid]::NewGuid().ToString('N')+'.py'); [IO.File]::WriteAllText($temporary,$parts[1],(New-Object Text.UTF8Encoding($false))); try { & $python @prefix $temporary $root; $result=$LASTEXITCODE } finally { Remove-Item -LiteralPath $temporary -ErrorAction SilentlyContinue }; exit $result } catch { Write-Host ('Nao foi possivel iniciar: '+$_.Exception.Message); exit 1 }"
set "CRONOS_RESCUE_RESULT=%errorlevel%"
echo.
pause
exit /b %CRONOS_RESCUE_RESULT%
# CRONOS_RESCUE_PYTHON
"""Standalone rescue: snapshot the user's installation, then launch its OWN code.

Never overlays a release, imports Cronos, installs dependencies or edits settings.
This file is embedded into SALVAR-E-ABRIR-CRONOS.bat for one-file distribution.
"""
from datetime import datetime
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
from uuid import uuid4

SKIP = {'.venv', 'venv', 'node_modules', '.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}
# Backups and dependency caches are not the user's live data.
SKIP_LOCAL = {'manual-updates', 'backups', 'cache'}
# This mutex is held by the updater during the snapshot. Reading its locked
# byte on Windows raises WinError 33. It is recreated at startup, not user data.
PROCESS_FILES = {'.cronos-local/updater/supervisor.lock'}
PATH_KEYS = {'CRONOS_VAULT', 'CRONOS_PERSONALITY', 'CRONOS_PROVIDERS_FILE'}


def regular(path):
    info = path.lstat()
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 1024


def env_paths(root):
    """Read ONLY three path settings, never evaluate shell syntax or expose keys."""
    filename = root / '.env'
    if not filename.is_file(): return []
    content = filename.read_text(encoding='utf-8-sig', errors='replace')
    values = {}
    for line in content.splitlines():
        match = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
        if not match or match[1] not in PATH_KEYS: continue
        raw = match[2]
        if raw.startswith(('"', "'")):
            quote = raw[0]
            end = raw.find(quote, 1)
            if end < 0: raise ValueError('Uma configuracao de caminho no .env esta incompleta. Nenhum arquivo foi alterado.')
            raw = raw[1:end]
        else: raw = re.split(r'\s+#', raw, maxsplit=1)[0].strip()
        if not raw: continue
        def substitute(m):
            name = m[1]
            if name not in os.environ:
                raise ValueError('Um caminho do .env usa variavel nao disponivel: ' + name + '. Confira antes de abrir.')
            return os.environ[name]
        raw = re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', substitute, raw)
        raw = os.path.expandvars(os.path.expanduser(raw))
        path = Path(raw)
        if not path.is_absolute(): path = root / path
        values[match[1]] = path.absolute()
    # Environment-only overrides also matter, without dumping their values.
    for key in PATH_KEYS:
        if key in os.environ and os.environ[key].strip() and key not in values:
            raw = os.path.expandvars(os.path.expanduser(os.environ[key]))
            path = Path(raw)
            values[key] = path.absolute() if path.is_absolute() else (root / path).absolute()
    return list(values.items())


def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''): checksum.update(block)
    return checksum.hexdigest()


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    is_sqlite = False
    if source.suffix.lower() in {'.sqlite', '.sqlite3', '.db'}:
        with source.open('rb') as src: is_sqlite = src.read(16) == b'SQLite format 3\0'
    if is_sqlite:
        # A consistent online backup also includes committed WAL transactions.
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=5)) as src:
            with closing(sqlite3.connect(target)) as dst:
                deadline = time.monotonic() + 20
                def progress(*_):
                    if time.monotonic() > deadline: raise TimeoutError('Feche o Cronos e tente novamente; a copia do banco esta ocupada.')
                src.backup(dst, pages=256, progress=progress, sleep=.1)
                if dst.execute('PRAGMA quick_check').fetchone()[0] != 'ok': raise ValueError('A copia do banco nao passou na verificacao.')
    else:
        before = source.stat()
        shutil.copy2(source, target)
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Um arquivo mudou durante o backup. Feche o Cronos e tente novamente.')
        if digest(source) != digest(target): raise ValueError('Uma copia nao corresponde ao arquivo de origem.')
    return {'bytes': target.stat().st_size, 'sha256': digest(target), 'sqlite_snapshot': is_sqlite}


def snapshot(root, backup_parent=None):
    root = Path(root).absolute()
    if not root.is_dir() or not regular(root): raise ValueError('Escolha uma pasta real do Cronos, sem atalhos ou junctions.')
    if not (root / '.env').is_file() and not (root / 'cronos').is_dir():
        raise ValueError('Esta pasta nao parece uma instalacao do Cronos. Escolha a pasta com .env e cronos.')
    parent = Path(backup_parent) if backup_parent else Path.home() / 'Documents' / 'CRONOS-Backups'
    parent = parent.absolute()
    if parent == root or parent.is_relative_to(root):
        raise ValueError('A pasta de backup precisa ficar fora da instalacao, para nao copiar um backup dentro dele mesmo.')
    parent.mkdir(parents=True, exist_ok=True)
    for part in (parent, *parent.parents):
        if not regular(part): raise ValueError('A pasta de backup nao pode usar links ou junctions.')
    backup = parent / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:6])
    backup.mkdir()
    entries = {}; skipped = []; missing = []
    (backup / 'INCOMPLETO.txt').write_text('Backup em andamento. Somente RELATORIO.json com complete=true confirma a conclusao.\n', encoding='utf-8')
    def copy_tree(source, target, live_root):
        if source.relative_to(live_root).as_posix().casefold() in PROCESS_FILES:
            skipped.append(str(source)); return
        if not source.exists(): missing.append(str(source)); return
        if not regular(source):
            raise ValueError('Ha um link/junction na pasta selecionada. Copie o destino real separadamente; backup interrompido sem alterar a origem.')
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            for child in sorted(source.iterdir(), key=lambda p:p.name.casefold()):
                if child.name.casefold() in SKIP or (source.name == '.cronos-local' and child.name.casefold() in SKIP_LOCAL):
                    skipped.append(str(child)); continue
                # SQLite copies contain their own committed journal state.
                if child.name.endswith(('-wal', '-shm', '-journal')):
                    main = child.with_name(child.name.rsplit('-', 1)[0])
                    if main.is_file(): skipped.append(str(child)); continue
                copy_tree(child, target / child.name, live_root)
        elif source.is_file():
            try:
                entry = copy_file(source, target)
            except OSError as exc:
                if getattr(exc, 'winerror', None) in {32, 33}:
                    raise ValueError('Um arquivo de dados ainda esta em uso: ' + str(source.relative_to(live_root)) + '. Feche o Cronos e tente novamente. O backup nao foi concluido e o codigo nao foi atualizado.') from None
                raise
            entries[str(target.relative_to(backup))] = entry
            if len(entries) % 200 == 0: print('Arquivos copiados e conferidos:', len(entries), flush=True)
    try:
        copy_tree(root, backup / 'instalacao', root)
        for key, path in env_paths(root):
            if not path.is_relative_to(root): copy_tree(path, backup / 'dados-externos' / key, path)
        report = {'complete': True, 'installation': str(root), 'files': entries, 'excluded': skipped, 'missing_paths': missing,
                  'notice': 'Contem chaves e dados privados. Nao compartilhe esta pasta. Ambientes Python e dependencias podem precisar de reinstalacao.'}
        (backup / 'RELATORIO.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (backup / 'INCOMPLETO.txt').unlink()
        return backup, report
    except Exception:
        (backup / 'INCOMPLETO.txt').write_text('Backup interrompido. A origem nao foi alterada. Nao considere esta copia completa.\n', encoding='utf-8')
        raise


def diagnose(root):
    problems = []
    for relative in ('cronos/app.py', 'cronos/supervisor.py', '.venv/Scripts/python.exe', '.venv/Scripts/pythonw.exe'):
        if not (root / relative).is_file(): problems.append('Arquivo ausente: ' + relative)
    for source in (root / 'cronos').rglob('*.py'):
        if '__pycache__' in source.parts: continue
        try: compile(source.read_bytes(), str(source), 'exec')
        except (SyntaxError, ValueError, OSError) as exc:
            # Never include source lines, which may contain hard-coded secrets.
            problems.append('Codigo invalido: ' + str(source.relative_to(root)) + ', linha ' + str(getattr(exc, 'lineno', '?')))
    return problems


def launch(root, log, popen=subprocess.Popen):
    # Run the selected installation itself. Never overlay the user's Mistral edits.
    python = root / '.venv/Scripts/pythonw.exe'
    with log.open('ab') as output:
        process = popen([str(python), '-m', 'cronos.supervisor'], cwd=str(root), stdout=output, stderr=output,
                        creationflags=0x08000000 if os.name == 'nt' else 0)
    return process


def main():
    if len(sys.argv) != 2: raise ValueError('Selecione a pasta da instalacao atual.')
    root = Path(sys.argv[1]).absolute()
    print('SALVAR E ABRIR CRONOS\nNao instala atualizacoes nem substitui codigo.\nFeche o Cronos antes desta copia.\n', flush=True)
    print('Criando copia de seguranca. Aguarde; memorias grandes podem levar alguns minutos.', flush=True)
    backup, report = snapshot(root)
    print('\nBACKUP CONCLUIDO:', backup, flush=True)
    print('Nao compartilhe esta pasta: ela contem suas chaves e memorias.', flush=True)
    problems = diagnose(root)
    if report['missing_paths']: problems.append('Um caminho configurado nao foi encontrado; confira missing_paths no RELATORIO.json.')
    (backup / 'DIAGNOSTICO.txt').write_text('\n'.join(problems) if problems else 'Arquivos de inicio e sintaxe Python conferidos. Isto nao comprova funcionamento do programa nem do 3D.', encoding='utf-8')
    if problems:
        print('\nNao vou iniciar uma instalacao incompleta. Confira DIAGNOSTICO.txt no backup.', flush=True)
        for problem in problems[:12]: print(problem, flush=True)
        return 2
    print('\nAbrindo a sua instalacao, com o codigo e as configuracoes que ja estao nela.', flush=True)
    process = launch(root, backup / 'ABERTURA.log')
    for _ in range(8):
        time.sleep(.5)
        result = process.poll()
        if result is not None:
            if result:
                print('O iniciador falhou. Confira ABERTURA.log no backup. Nenhum codigo foi substituido.', flush=True)
                return 3
            break
    print('Inicio solicitado. Se a pagina nao abrir, confira ABERTURA.log e mantenha a pasta antiga.', flush=True)
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as error:
        print('Nao foi possivel concluir:', str(error), flush=True)
        print('Nenhum arquivo da instalacao foi apagado ou substituido.', flush=True)
        sys.exit(1)
