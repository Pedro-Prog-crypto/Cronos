from types import SimpleNamespace
from dataclasses import replace

from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.config import Settings
from cronos.system_metrics import SystemMetrics


def test_metrics_are_measured_and_network_rate_is_delta(monkeypatch):
    from cronos import system_metrics
    clock = iter([10.0, 12.0])
    traffic = iter([1000, 3097152])
    monkeypatch.setattr(system_metrics, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(system_metrics.psutil, 'cpu_percent', lambda interval=None: 28.0)
    monkeypatch.setattr(system_metrics.psutil, 'virtual_memory', lambda: SimpleNamespace(percent=46.0, used=46, total=100))
    monkeypatch.setattr(system_metrics.psutil, 'disk_usage', lambda _: SimpleNamespace(percent=72.0, used=72, total=100))
    monkeypatch.setattr(system_metrics.psutil, 'sensors_battery', lambda: SimpleNamespace(percent=78.0, power_plugged=False))
    monkeypatch.setattr(system_metrics.psutil, 'sensors_temperatures', lambda: {})
    monkeypatch.setattr(system_metrics.psutil, 'net_io_counters', lambda: SimpleNamespace(bytes_recv=next(traffic), bytes_sent=0))
    sample = SystemMetrics()
    first = sample.snapshot()
    second = sample.snapshot()
    assert first['network_bytes_per_second'] is None
    assert second['network_bytes_per_second'] == (3097152 - 1000) / 2
    assert second['cpu_percent'] == 28
    assert second['ram_percent'] == 46
    assert second['disk_percent'] == 72
    assert second['battery_percent'] == 78
    assert second['temperature_celsius'] is None


def test_metrics_endpoint_requires_token(tmp_path):
    personality = tmp_path / 'personality.md'
    personality.write_text('Private personality')
    settings = replace(Settings.from_env(), token='a' * 32, vault=tmp_path / 'vault',
                       personality=personality, providers_file=tmp_path / 'providers.json')
    with TestClient(create_app(settings)) as client:
        assert client.get('/system/metrics').status_code == 401
        response = client.get('/system/metrics', headers={'Authorization': 'Bearer ' + 'a' * 32})
        assert response.status_code == 200
        assert 'cpu_percent' in response.json()
        assert 'gemini_key' not in response.json()
