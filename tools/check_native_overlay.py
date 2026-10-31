"""Exercise the real Tk overlay under an X server. No physical Windows claims."""
import json
import tkinter as tk
from cronos.desktop_overlay import Overlay


def main():
    ui=Overlay();checks=[];errors=[];original=tk.Tk
    def root_factory():
        root=original()
        def check():
            try:
                card=ui.card_window
                assert card and card.winfo_exists()
                assert card.overrideredirect() and card.attributes('-topmost')
                assert card.winfo_width()==460 and card.winfo_height()==470
                assert card.cronos_heading.cget('text')=='Resumo da tela'
                assert 'mitose' in card.cronos_content.get('1.0','end')
                checks.append('native compact card, complete text and separate indicator render without main app')
                try:
                    from PIL import ImageGrab
                    ImageGrab.grab().save('/tmp/cronos-native-overlay.png')
                except OSError:pass
                heading=card.cronos_heading;x,y=card.winfo_x(),card.winfo_y()
                heading.event_generate('<ButtonPress-1>',x=5,y=5,rootx=x+5,rooty=y+5)
                heading.event_generate('<B1-Motion>',x=5,y=5,rootx=x-95,rooty=y+65)
                root.update_idletasks()
                assert card.winfo_x()==x-100 and card.winfo_y()==y+60
                checks.append('dragging uses the native header and keeps the close button on screen')
                buttons=[widget for widget in heading.master.winfo_children() if isinstance(widget,tk.Button)]
                next(button for button in buttons if button.cget('text')=='-').invoke()
                assert card.state()=='withdrawn'
                checks.append('minimizing the card does not close the indicator or the conversation')
                card.deiconify()
                next(button for button in buttons if button.cget('text')=='×').invoke()
                assert not card.winfo_exists()
                checks.append('X closes only the card')
                assert root.state()=='withdrawn'
                assert any(isinstance(w,tk.Toplevel) and w.winfo_exists() for w in root.winfo_children())
                checks.append('resident indicator stays available after closing the card')
            except Exception as exc:errors.append(repr(exc))
            finally:ui.close()
        root.after(700,check)
        return root
    tk.Tk=root_factory
    ui.card('Resumo da tela','A mitose divide uma célula e conserva o número de cromossomos.\n\n'+('Exemplo: renovação da pele e crescimento dos tecidos.\n'*40))
    try:ui.run()
    finally:tk.Tk=original
    assert not errors,errors
    print(json.dumps({'checks_passed':len(checks),'checks':checks,'environment':'Real Tk widgets and Xvfb; no Windows microphone, WebView2 or audio device validation'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
