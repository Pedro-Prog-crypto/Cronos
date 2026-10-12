"""Inicialização desktop: janela Windows com backend privado no loopback."""
import json
import os
import secrets
import socket
import sys
import threading
import time

from dotenv import load_dotenv


def main():
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
    server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level="warning"))
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
        window = webview.create_window("Cronos", f"http://127.0.0.1:{port}",
                                       width=1200, height=850, min_size=(700, 600))

        def connect():
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


if __name__ == "__main__":
    main()
