"""Find an existing Cronos data folder and migrate it into a new installation.

Only paths are inspected during discovery. Credentials and vault contents stay
on the user's computer and are copied by migrate_local_data, never uploaded.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

try:
    from .migrate_local_data import _data_root, migrate
except ImportError:  # Direct execution from the extracted Windows installation.
    from migrate_local_data import _data_root, migrate


def documents_folder(home: Path) -> Path:
    if os.name == 'nt':
        try:
            import ctypes

            result = ctypes.create_unicode_buffer(32768)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, result) == 0 and result.value:
                return Path(result.value)
        except (AttributeError, OSError, ValueError):
            pass
    return home / 'Documents'


def roots(home: Path) -> list[Path]:
    result = [home, documents_folder(home), home / 'Downloads', home / 'Desktop']
    if one_drive := os.environ.get('OneDrive'):
        result.extend(Path(one_drive) / name for name in ('Documents', 'Desktop'))
    return list(dict.fromkeys(result))


def has_data(folder: Path) -> bool:
    try:
        if not folder.is_dir() or folder.is_symlink():
            return False
        data = _data_root(folder)
        return (data / '.env').is_file() and (data / 'vault').is_dir() or (
            (folder / '.env').is_file() and (folder / 'vault').is_dir()
        )
    except (OSError, ValueError):
        return False


def find_sources(target: Path, home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    target = target.resolve()
    found: dict[str, Path] = {}
    for root in roots(home):
        if not root.is_dir():
            continue
        # The data launcher stores the authoritative shared vault here.
        candidates = [root, root / 'Cronos-Dados']
        try:
            candidates.extend(child for child in root.iterdir() if child.is_dir() and (
                child.name.lower().startswith('cronos') or child.name.lower() == 'downloads'
            ))
        except OSError:
            pass
        for candidate in candidates[:500]:
            try:
                resolved = candidate.resolve()
                if resolved != target and has_data(resolved):
                    found[os.path.normcase(str(resolved))] = resolved
            except (OSError, ValueError):
                continue
    return sorted(found.values(), key=lambda path: str(path).casefold())


def default_configuration(folder: Path) -> bool:
    """A fresh R39/R40 copy is not evidence of the user's old credentials."""
    env, example = folder / '.env', folder / '.env.example'
    try:
        return env.is_file() and example.is_file() and env.read_bytes() == example.read_bytes()
    except OSError:
        return False


def automatic_source(candidates: list[Path], home: Path) -> Path | None:
    preferred = documents_folder(home) / 'Cronos-Dados'
    if preferred in candidates:
        return preferred
    if len(candidates) == 1 and not default_configuration(candidates[0]):
        return candidates[0]
    return None


def select_source(candidates: list[Path], target: Path, home: Path | None = None) -> Path | None:
    home = home or Path.home()
    if automatic := automatic_source(candidates, home):
        return automatic

    import tkinter as tk
    from tkinter import filedialog, messagebox

    window = tk.Tk()
    window.title('Importar meus dados para o Cronos')
    window.geometry('730x360')
    window.attributes('-topmost', True)
    tk.Label(window, text='Escolha a pasta antiga com suas memórias e integrações.',
             font=('Segoe UI', 12), wraplength=680).pack(padx=18, pady=14)
    selection = tk.Listbox(window, width=100, height=10)
    selection.pack(padx=18, fill='both', expand=True)
    for candidate in candidates:
        suffix = ' (configuração padrão; confira se tem memórias)' if default_configuration(candidate) else ''
        selection.insert('end', str(candidate) + suffix)
    if candidates:
        selection.selection_set(0)
    selected: list[Path] = []

    def accept() -> None:
        indexes = selection.curselection()
        if indexes:
            selected.append(candidates[indexes[0]])
            window.destroy()
        else:
            messagebox.showinfo('Cronos', 'Selecione uma pasta ou clique em Outra pasta.', parent=window)

    def browse() -> None:
        choice = filedialog.askdirectory(parent=window, title='Pasta antiga do Cronos, com .env e vault')
        if choice:
            selected.append(Path(choice))
            window.destroy()

    buttons = tk.Frame(window)
    buttons.pack(pady=12)
    tk.Button(buttons, text='Usar esta pasta', command=accept).pack(side='left', padx=8)
    tk.Button(buttons, text='Outra pasta...', command=browse).pack(side='left', padx=8)
    window.mainloop()
    return selected[0] if selected else None


def restore(target: Path, home: Path | None = None, source: Path | None = None) -> Path | None:
    target = target.resolve(strict=True)
    if (target / '.env').is_file():
        return None  # Never overwrite a configured installation on a later run.
    candidates = find_sources(target, home)
    source = source or select_source(candidates, target, home)
    if source is None:
        raise ValueError('Nenhuma pasta antiga foi escolhida. O programa foi instalado, mas seus dados não foram importados.')
    if not has_data(source):
        raise ValueError('Essa pasta não contém .env e vault. Escolha a instalação antiga que já tem seus dados.')
    migrate(source, target)
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    try:
        source = restore(args.target, source=args.source)
        if source:
            print('Dados antigos importados de ' + str(source))
        else:
            print('Dados já presentes nesta instalação; nenhuma importação foi feita.')
        return 0
    except Exception as exc:
        print('Importação não concluída: ' + str(exc))
        print('A pasta antiga foi preservada. Execute este instalador novamente e escolha a pasta correta.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
