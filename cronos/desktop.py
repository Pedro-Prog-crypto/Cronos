"""Inicialização desktop: janela Windows com backend privado no loopback."""
import json
import os
import secrets
import socket
import sys
import threading
import time

from dotenv import load_dotenv


def _run():
    from pathlib import Path
    from cronos.persistent_data import activate
    from cronos.resident import ensure, folder
    project = Path(__file__).resolve().parents[1]
    activate(project)
    if sys.platform != "win32":
        raise SystemExit("A janela desktop do Cronos deve ser iniciada no Windows.")
    flag='--autoplay-policy=no-user-gesture-required'
    arguments=os.getenv('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS','')
    if flag not in arguments:os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS']=(arguments+' '+flag).strip()
    try:
        import webview
    except ImportError:
        raise SystemExit('Instale o modo desktop: python -m pip install -e ".[desktop]"')
    load_dotenv('.env', override=True)
    connection = ensure(project)
    address = connection.data['url']
    token = connection.data['token']
    profile = folder(project).parent / 'webview-profile'
    profile.mkdir(parents=True,exist_ok=True)
    from cronos.wake import set_ui_open
    set_ui_open(True)
    def start_listener():
        from cronos.wake import settings,status,start
        try:
            current=status()
            if settings()['background_enabled'] and current['model_installed'] and current['dependencies_installed']:
                start()
        except (OSError,ValueError):pass
    threading.Thread(target=start_listener,daemon=True,name='cronos-enable-background').start()
    class DesktopBridge:
        def trusted(self):return (window.get_current_url() or '').rstrip('/') == address
        def connection(self):
            if not self.trusted():return None
            from cronos.resident import discover
            current=discover(project)
            if current:
                try:
                    if current.data['url']!=address:return None
                    return {'token':current.data['token']}
                finally:current.close()
            return {'token':token}
        def choose_vault(self):
            if not self.trusted():return None
            chosen=window.create_file_dialog(webview.FileDialog.FOLDER)
            if not self.trusted():return None
            return chosen[0] if chosen else None
        def show_main(self):
            if not self.trusted():return None
            window.restore();window.show();return {'requested':True}
        def close_main(self):
            if not self.trusted():return None
            window.destroy();return {'requested':True}
    bridge=DesktopBridge()
    window = webview.create_window('Cronos',address,js_api=bridge,width=1200,height=850,min_size=(700,600))
    def connect():
        if (window.get_current_url() or '').rstrip('/') != address:return
        credentials=bridge.connection()
        if not credentials:return
        active_token=credentials['token']
        window.evaluate_js('(function connectCronos(attempt) {'
            'if (window.cronosConnect) { window.cronosConnect('+json.dumps(active_token)+'); }'
            'else if (document.getElementById("token")) { document.getElementById("token").value='+json.dumps(active_token)+';document.getElementById("connect-form").requestSubmit(); }'
            'else if(attempt<100){window.setTimeout(()=>connectCronos(attempt+1),50);}})(0);')
    window.events.loaded += connect
    try:
        # The same profile and loopback origin survive reopening the app. Never
        # auto-grant permissions or erase a denied permission.
        webview.start(gui='edgechromium',debug=False,private_mode=False,storage_path=str(profile))
    finally:
        from cronos.wake import set_ui_listening
        set_ui_listening(False)
        set_ui_open(False)
        connection.close()
        # Closing the UI releases its microphone; the resident backend and
        # explicitly started native listener continue without reopening it.


def main():
    from cronos.wake import single_instance
    with single_instance("CronosDesktop") as acquired:
        if acquired:
            try:
                _run()
            except BaseException as exc:
                if sys.platform == "win32" and (getattr(sys, "stderr", False) is None or getattr(sys, "stdout", False) is None):
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(None, "Não foi possível iniciar o Cronos. Confira a instalação, .env e WebView2.\n" + str(exc)[:350], "Cronos", 0x10)
                    raise SystemExit(1) from exc
                else:
                    raise
        elif sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            user.FindWindowW.restype = wintypes.HWND
            user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            user.SetForegroundWindow.argtypes = [wintypes.HWND]
            window = user.FindWindowW(None, "Cronos")
            if window:
                user.ShowWindow(window, 9)
                user.SetForegroundWindow(window)


if __name__ == "__main__":
    main()
