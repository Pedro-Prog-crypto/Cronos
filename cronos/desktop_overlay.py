"""Small native indicator/cards. Never opens the main Cronos interface itself."""
import queue


class Overlay:
    def __init__(self):
        self.messages=queue.Queue();self.actions=queue.Queue();self.window=None;self.card_window=None;self.closed=False
    def phase(self,text):self.messages.put(('phase',str(text)[:100]))
    def card(self,title,text):self.messages.put(('card',(str(title)[:80],str(text)[:50000])))
    def close(self):self.messages.put(('close',None))
    def run(self):
        import tkinter as tk
        from tkinter import ttk
        from tkinter import font as tkfont
        root=tk.Tk();root.withdraw();self.window=root
        family='Segoe UI' if 'Segoe UI' in tkfont.families(root) else 'DejaVu Sans'
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('Cronos.Vertical.TScrollbar',background='#16485f',troughcolor='#061724',bordercolor='#061724',arrowcolor='#91f1ff')
        dot=tk.Toplevel(root);dot.overrideredirect(True);dot.attributes('-topmost',True)
        width,height=root.winfo_screenwidth(),root.winfo_screenheight()
        dot.geometry(f'26x26+{width-40}+{height-80}')
        # Keep the listener's Tk event loop and optional cards, but do not
        # leave a floating status square over other applications.
        dot.withdraw()
        canvas=tk.Canvas(dot,width=26,height=26,bg='#06131e',highlightthickness=0);canvas.pack()
        circle=canvas.create_oval(6,6,20,20,fill='#f8bf6c',outline='#baf8ff')
        label=tk.StringVar(value='Cronos · iniciando microfone')
        menu=tk.Menu(dot,tearoff=False)
        menu.add_command(label='Abrir Cronos',command=lambda:self.actions.put('show'))
        menu.add_command(label='Enviar fala agora',command=lambda:self.actions.put('submit'))
        menu.add_command(label='Interromper resposta',command=lambda:self.actions.put('cancel'))
        menu.add_command(label='Tentar novamente',command=lambda:self.actions.put('retry'))
        menu.add_separator()
        menu.add_command(label='Pausar / retomar escuta',command=lambda:self.actions.put('pause'))
        menu.add_command(label='Ligar / desligar visão da tela',command=lambda:self.actions.put('screen'))
        menu.add_command(label='Encerrar assistente',command=lambda:self.actions.put('exit'))
        def popup(event):
            try:menu.tk_popup(event.x_root,event.y_root)
            finally:menu.grab_release()
        dot.bind('<Button-3>',popup);dot.bind('<Double-Button-1>',lambda event:self.actions.put('show'))
        tooltip=None
        def enter(event):
            nonlocal tooltip
            tooltip=tk.Toplevel(dot);tooltip.overrideredirect(True);tooltip.attributes('-topmost',True)
            tooltip.geometry(f'+{max(0,width-260)}+{height-110}')
            tk.Label(tooltip,textvariable=label,bg='#06131e',fg='#baf8ff',padx=10,pady=6).pack()
        def leave(event):
            nonlocal tooltip
            if tooltip:tooltip.destroy();tooltip=None
        dot.bind('<Enter>',enter);dot.bind('<Leave>',leave)
        def card(title,text):
            if not self.card_window or not self.card_window.winfo_exists():
                window=tk.Toplevel(root);self.card_window=window
                window.overrideredirect(True);window.attributes('-topmost',True)
                window.configure(bg='#061724',highlightthickness=1,highlightbackground='#28cce6')
                window.geometry(f'460x470+{max(8,width-490)}+70')
                header=tk.Frame(window,bg='#0a2639');header.pack(fill='x')
                heading=tk.Label(header,bg='#0a2639',fg='#91f1ff',font=(family,-15,'bold'),anchor='w',padx=12,pady=12)
                heading.pack(side='left',fill='x',expand=True)
                tk.Button(header,text='-',bg='#0a2639',fg='#91f1ff',bd=0,command=window.withdraw,font=(family,-18)).pack(side='left',padx=7)
                tk.Button(header,text='×',bg='#0a2639',fg='#91f1ff',bd=0,command=window.destroy).pack(side='right',padx=10)
                state={}
                def down(event):state.update(x=event.x_root-window.winfo_x(),y=event.y_root-window.winfo_y())
                def drag(event):
                    if 'x' in state:
                        x=max(0,min(width-window.winfo_width(),event.x_root-state['x']))
                        y=max(0,min(height-window.winfo_height(),event.y_root-state['y']))
                        window.geometry(f'+{x}+{y}')
                for widget in (header,heading):widget.bind('<Button-1>',down);widget.bind('<B1-Motion>',drag)
                body=tk.Frame(window,bg='#061724');body.pack(fill='both',expand=True,padx=10,pady=10)
                scrollbar=ttk.Scrollbar(body,style='Cronos.Vertical.TScrollbar');scrollbar.pack(side='right',fill='y')
                content=tk.Text(body,bg='#061724',fg='#e1f0f8',font=(family,-15),wrap='word',relief='flat',
                    padx=8,pady=8,yscrollcommand=scrollbar.set,selectbackground='#126c8c')
                content.pack(fill='both',expand=True);scrollbar.configure(command=content.yview)
                window.cronos_heading=heading;window.cronos_content=content
                window.bind('<Escape>',lambda event:window.withdraw())
            window=self.card_window;window.cronos_heading.configure(text=title)
            window.cronos_content.configure(state='normal');window.cronos_content.delete('1.0','end')
            window.cronos_content.insert('1.0',text);window.cronos_content.configure(state='disabled')
            window.deiconify();window.lift()
        menu.add_command(label='Restaurar último card',command=lambda:self.card_window.deiconify() if self.card_window and self.card_window.winfo_exists() else None)
        def tick():
            while True:
                try:kind,value=self.messages.get_nowait()
                except queue.Empty:break
                if kind=='phase':
                    label.set('Cronos · '+value)
                    color='#f8bf6c' if value not in ('Na escuta','Pausado') else '#41eaff' if value=='Na escuta' else '#7790a0'
                    canvas.itemconfigure(circle,fill=color)
                elif kind=='card':card(*value)
                elif kind=='close':self.closed=True;root.destroy();return
            root.after(80,tick)
        root.after(80,tick)
        try:root.mainloop()
        finally:self.closed=True;self.actions.put('exit')
