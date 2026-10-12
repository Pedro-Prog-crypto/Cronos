import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def local_http_client_defaults(monkeypatch):
    original = TestClient.__init__
    def initialize(self, *args, **kwargs):
        kwargs.setdefault('base_url', 'http://127.0.0.1')
        kwargs.setdefault('client', ('127.0.0.1', 50000))
        original(self, *args, **kwargs)
    monkeypatch.setattr(TestClient, '__init__', initialize)
