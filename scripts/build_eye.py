"""Package original provider imports without npm installation on the user's PC."""
from pathlib import Path
import re,shutil
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'vendor/gods-eye'
TARGET=ROOT/'cronos/eye-server'
TARGET.mkdir(exist_ok=True)
seen=set()
def copy(path):
    path=path.resolve()
    if path in seen:return
    if path.is_relative_to(SOURCE.resolve()) and not path.is_file() and path.relative_to(SOURCE).parts[0]=='runtime' and (TARGET/path.relative_to(SOURCE)).is_file():return
    if not path.is_relative_to(SOURCE.resolve()) or not path.is_file():raise ValueError(f'Missing local dependency: {path}')
    seen.add(path);relative=path.relative_to(SOURCE);destination=TARGET/relative
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
    if path.suffix not in {'.js','.mjs'}:return
    text=re.sub(r'/\*.*?\*/|^\s*//[^\n]*','',path.read_text(),flags=re.S|re.M)
    for name in re.findall(r'(?:from\s*|import\s*\()\s*[\'\"](\.[^\'\"]+)',text):copy(path.parent/name)
copy(SOURCE/'cronos-service.mjs')
for name in ('runtime','config'):
    if (SOURCE/name).is_dir():shutil.copytree(SOURCE/name,TARGET/name,dirs_exist_ok=True)
    elif not (TARGET/name).is_dir():raise ValueError(f'Missing packaged {name}')
for name in ('package.json','LICENSE','DATA_SOURCES.md','THIRD_PARTY_NOTICES.md','PROVENANCE.md'):
    shutil.copy2(SOURCE/name,TARGET/name)
# vite-plugin-cesium duplicates the base directory in its copy destination.
misplaced=ROOT/'cronos/eye-ui/eye/cesium';correct=ROOT/'cronos/eye-ui/cesium'
if misplaced.exists():
    if correct.exists():shutil.rmtree(correct)
    shutil.move(str(misplaced),correct);misplaced.parent.rmdir()
print(f'Packaged {len(seen)} provider modules and original runtime/assets.')
