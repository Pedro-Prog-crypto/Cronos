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
    if sys.platform != "win32":
        raise SystemExit("A janela desktop do Cronos deve ser iniciada no Windows.")
    try:
        import webview
    except ImportError:
        raise SystemExit('Instale o modo desktop: python -m pip install -e ".[desktop]"')

    # Carregar configurações antes de importar a aplicação.
    load_dotenv(".env")
    if not os.getenv("CRONOS_API_TOKEN", "").strip():
        os.environ["CRONOS_API_TOKEN"] = secrets.token_urlsafe(32)
    from cronos.app import create_app
    from cronos.config import Settings
    import uvicorn

    settings = Settings.from_env()
    server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level="warning", access_log=False))
    # Reservar a porta evita colisões com o servidor usado nos testes anteriores.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise SystemExit("O backend não iniciou. Confira o arquivo .env e a pasta de memória.")
            time.sleep(.05)
        address = f"http://127.0.0.1:{port}"
        window = webview.create_window("Cronos", address,
                                       width=1200, height=850, min_size=(700, 600))

        def connect():
            if (window.get_current_url() or "").rstrip("/") != address:
                return
            # Token local, não gravado em HTML, logs ou armazenamento do navegador.
            window.evaluate_js(
                "document.getElementById('token').value = " + json.dumps(settings.token) + ";"
                "document.getElementById('connect-form').requestSubmit();"
            )

        window.events.loaded += connect
        webview.start(gui="edgechromium", debug=False)
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()


def main():
    from cronos.wake import single_instance
    with single_instance("CronosDesktop") as acquired:
        if acquired:
            _run()
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
