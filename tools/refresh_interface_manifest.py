"""Hash the runtime files shipped by the local update and complete installers."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'tools/interface_update_manifest.json'

def refresh(revision: str) -> int:
    previous = json.loads(MANIFEST.read_text(encoding='utf-8'))['files']
    names = {name for name in previous if (ROOT / name).is_file() and not name.startswith('cronos/ui/assets/')}
    names |= {path.relative_to(ROOT).as_posix() for path in (ROOT / 'cronos/ui/assets').rglob('*') if path.is_file()}
    files = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(names)}
    MANIFEST.write_text(json.dumps({'revision': revision, 'files': files}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return len(files)

if __name__ == '__main__':
    print(refresh('cronos-interface-referencia-2026-11-15-r60'))
