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
    assert second['network_download_bytes_per_second'] == (3097152 - 1000) / 2
    assert second['network_upload_bytes_per_second'] == 0
    assert second['cpu_percent'] == 28
    assert second['ram_percent'] == 46
    assert second['disk_percent'] == 72
    assert second['battery_percent'] == 78
    assert second['temperature_celsius'] is None


def test_optional_gpu_sensor_and_missing_values(monkeypatch):
    from cronos import system_metrics
    monkeypatch.setattr(system_metrics.shutil, 'which', lambda _: '/usr/bin/nvidia-smi')
    monkeypatch.setattr(system_metrics.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout='37, 1536, 4096, 58, Not Supported\n'))
    result = SystemMetrics._nvidia_gpu()
    assert result['gpu_percent'] == 37
    assert result['gpu_memory_used_bytes'] == 1536 * 1048576
    assert result['gpu_temperature_celsius'] == 58
    assert result['gpu_fan_percent'] is None
    monkeypatch.setattr(system_metrics.shutil, 'which', lambda _: None)
    assert all(value is None for value in SystemMetrics._nvidia_gpu().values())


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
