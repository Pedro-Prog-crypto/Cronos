"""One-screen local launcher: find existing data, apply code, open that installation."""
import argparse
from collections import deque
import os
from pathlib import Path
import queue
import stat
import subprocess
import threading

from apply_interface_update import apply,regular

SKIP={'.git','.venv','venv','node_modules','__pycache__','vault','cronos','frontend','vendor','.cronos-local'}


def installation(path):
    path=Path(path)
    try:
        regular(path)
        return all((path/name).is_file() for name in ('.env','cronos/app.py','.venv/Scripts/python.exe','.venv/Scripts/pythonw.exe'))
    except (OSError,ValueError):return False


def search_roots(source):
    home=Path.home()
    roots=[Path(source).parent,home/'Downloads',home/'Desktop',home/'Documents']
    if os.getenv('OneDrive'):roots.extend([Path(os.environ['OneDrive'])/'Desktop',Path(os.environ['OneDrive'])/'Documents'])
    return roots


def discover(source,roots=None,limit=500):
    source=Path(source).absolute()
    if installation(source):return [source]
    pending=deque((Path(p),0) for p in (roots if roots is not None else search_roots(source)))
    visited=set();found=set()
    while pending and len(visited)<limit:
        path,depth=pending.popleft();path=path.absolute()
        key=os.path.normcase(str(path))
        if key in visited:continue
        visited.add(key)
        try:
            regular(path)
            if path!=source and installation(path):found.add(path);continue
            if depth>=2:continue
            with os.scandir(path) as children:
                for child in children:
                    if child.name.startswith('.') or child.name.lower() in SKIP:continue
                    if child.is_dir(follow_symlinks=False) and not getattr(child.stat(follow_symlinks=False),'st_file_attributes',0)&1024:
                        pending.append((Path(child.path),depth+1))
        except (OSError,ValueError):continue
    return sorted(found,key=lambda p:str(p).casefold())


def update_and_launch(source,target,launch=subprocess.Popen):
    source,target=Path(source).absolute(),Path(target).absolute()
    if not installation(target):raise ValueError('Esta pasta nao e a instalacao configurada. Escolha onde voce ja abria o Cronos.')
    backup=None
    if source!=target:backup=apply(source,target)
    python=target/'.venv/Scripts/pythonw.exe'
    runner=target/'.cronos-local/updater/runner.py'
    command=[str(python),str(runner),'--run',str(target)] if runner.is_file() else [str(python),'-m','cronos.supervisor']
    # No shell, no prompt kept in background, no edits to the user's launchers.
    launch(command,cwd=str(target),creationflags=0x08000000 if os.name=='nt' else 0)
    return backup


def main(source,target=None):
    import tkinter as tk
    from tkinter import filedialog,messagebox,ttk
    app=tk.Tk();app.title('Abrir Cronos');app.geometry('630x260');app.configure(bg='#06131e')
    app.minsize(570,240)
    label=tk.Label(app,text='Preparando seu Cronos…',bg='#06131e',fg='#9ceaff',font=('Segoe UI',16),wraplength=580);label.pack(pady=(28,12))
    detail=tk.Label(app,text='Suas APIs, integracoes e memorias continuam na instalacao atual.',bg='#06131e',fg='#b3c8d4',font=('Segoe UI',10),wraplength=580);detail.pack(padx=20)
    progress=ttk.Progressbar(app,mode='indeterminate',length=490);progress.pack(pady=24);progress.start()
    messages=queue.Queue();started=False
    def task(function):
        def run():
            try:messages.put(('result',function()))
            except Exception as error:messages.put(('error',str(error)))
        threading.Thread(target=run,daemon=True).start()
    def begin(path):
        nonlocal started
        started=True;label.configure(text='Atualizando e abrindo o Cronos…');detail.configure(text='Configuracoes preservadas. Aguarde a verificacao e o backup do codigo.')
        task(lambda:update_and_launch(source,path))
    def choose(candidates):
        progress.stop();progress.pack_forget()
        label.configure(text='Encontrei mais de uma instalacao')
        detail.configure(text='Escolha a que voce usa. Nao sera preciso configurar as APIs novamente.')
        box=ttk.Combobox(app,values=[str(p) for p in candidates],state='readonly',width=76);box.current(0);box.pack(padx=20,pady=12)
        def selected():
            choice=box.get();box.destroy();button.destroy();progress.pack(pady=18);progress.start();begin(Path(choice))
        button=ttk.Button(app,text='Abrir esta instalacao',command=selected);button.pack()
    def poll():
        try:kind,value=messages.get_nowait()
        except queue.Empty:app.after(100,poll);return
        if kind=='error':
            progress.stop();messagebox.showerror('Cronos',value,parent=app);app.destroy();return
        if started:
            label.configure(text='Cronos atualizado. Abrindo…');detail.configure(text='A janela do navegador vai abrir com suas configuracoes atuais.');app.after(1200,app.destroy);return
        if len(value)==1:begin(value[0])
        elif len(value)>1:choose(value)
        else:
            chosen=filedialog.askdirectory(parent=app,title='Escolha a pasta do Cronos que voce ja usa (com .env e .venv)')
            if not chosen:app.destroy();return
            if not installation(chosen):messagebox.showerror('Pasta incorreta','Escolha a pasta antiga onde o Cronos funcionava, que contem .env, .venv e a pasta cronos.',parent=app);app.destroy();return
            begin(Path(chosen))
        app.after(100,poll)
    def closing():
        if started:detail.configure(text='Aguarde o fim da verificacao para fechar esta janela.')
        else:app.destroy()
    app.protocol('WM_DELETE_WINDOW',closing)
    task(lambda:[Path(target)] if target else discover(source))
    app.after(100,poll);app.mainloop()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--target');args=parser.parse_args()
    try:main(Path(__file__).resolve().parents[1],args.target)
    except Exception as error:
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,'Nao foi possivel iniciar o Cronos: '+str(error),'Cronos',16)
        else:raise
