import sys
from types import SimpleNamespace

import httpx
import pytest

from cronos import desktop


def test_desktop_starts_private_server_and_connects_window(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CRONOS_API_TOKEN", "")
    monkeypatch.setenv("CRONOS_VAULT", str(tmp_path / "vault"))
    monkeypatch.setattr(desktop, "load_dotenv", lambda *args: None)
    monkeypatch.setattr(desktop, "sys", SimpleNamespace(platform="win32"))
    state = {}

    class Loaded:
        def __init__(self): self.callbacks = []
        def __iadd__(self, callback):
            self.callbacks.append(callback)
            return self

    class Window:
        events = SimpleNamespace(loaded=Loaded())
        def get_current_url(self): return state["url"]
        def evaluate_js(self, script):
            state["script"] = script

    def create_window(title, url, **kwargs):
        assert title == "Cronos"
        assert url.startswith("http://127.0.0.1:")
        state["url"] = url
        state["window"] = Window()
        return state["window"]

    def start(**kwargs):
        assert kwargs == {"gui": "edgechromium", "debug": False}
        assert httpx.get(state["url"]).status_code == 200
        for callback in state["window"].events.loaded.callbacks:
            callback()
        from os import environ
        token = environ["CRONOS_API_TOKEN"]
        assert len(token) >= 32
        response = httpx.get(state["url"] + "/status", headers={"Authorization": "Bearer " + token})
        assert response.status_code == 200
        assert "requestSubmit" in state["script"]

    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(create_window=create_window, start=start))
    desktop.main()
    # Fechar a janela deve encerrar o servidor e liberar a porta.
    with pytest.raises(httpx.ConnectError):
        httpx.get(state["url"], timeout=1)


def test_desktop_explains_missing_dependency(monkeypatch):
    monkeypatch.setattr(desktop, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setitem(sys.modules, "webview", None)
    with pytest.raises(SystemExit, match="Instale o modo desktop"):
        desktop.main()
