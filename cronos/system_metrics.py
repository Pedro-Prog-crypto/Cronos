"""Small, read-only system sample for the home dashboard."""
import os
import shutil
from pathlib import Path
from threading import Lock
from time import monotonic

try:
    import psutil
except ImportError:  # Existing installations can run before dependencies are refreshed.
    psutil = None


class SystemMetrics:
    def __init__(self):
        self._lock = Lock()
        self._previous_network = None
        self._previous_time = None

    def snapshot(self):
        # None means unavailable. In particular, many Windows laptops do not expose
        # CPU temperature through the OS; never display an invented value.
        with self._lock:
            if psutil is None:
                from cronos.monitor import memory_pressure
                disk = shutil.disk_usage(Path.home().anchor or os.path.abspath(os.sep))
                return {'cpu_percent': None, 'ram_percent': memory_pressure(),
                        'ram_used_bytes': None, 'ram_total_bytes': None,
                        'disk_percent': round(100 * disk.used / disk.total, 1) if disk.total else None,
                        'disk_used_bytes': disk.used, 'disk_total_bytes': disk.total,
                        'network_bytes_per_second': None, 'temperature_celsius': None,
                        'battery_percent': None, 'battery_plugged': None}
            cpu = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            drive = Path.home().anchor or os.path.abspath(os.sep)
            disk = psutil.disk_usage(drive)
            battery_reader = getattr(psutil, 'sensors_battery', None)
            temperature_reader = getattr(psutil, 'sensors_temperatures', None)
            try:
                battery = battery_reader() if battery_reader else None
            except (OSError, RuntimeError):
                battery = None
            try:
                temperatures = temperature_reader() if temperature_reader else {}
            except (OSError, RuntimeError):
                temperatures = {}
            temperature = next((reading.current for group in temperatures.values() for reading in group
                                if reading.current is not None), None)
            now = monotonic()
            network = psutil.net_io_counters()
            rate = None
            if self._previous_network is not None and self._previous_time is not None and now > self._previous_time:
                delta = (network.bytes_recv + network.bytes_sent) - self._previous_network
                rate = round(max(0, delta) / (now - self._previous_time), 1)
            self._previous_network = network.bytes_recv + network.bytes_sent
            self._previous_time = now
            return {
                'cpu_percent': round(cpu, 1),
                'ram_percent': round(memory.percent, 1),
                'ram_used_bytes': memory.used,
                'ram_total_bytes': memory.total,
                'disk_percent': round(disk.percent, 1),
                'disk_used_bytes': disk.used,
                'disk_total_bytes': disk.total,
                'network_bytes_per_second': rate,
                'temperature_celsius': round(temperature, 1) if temperature is not None else None,
                'battery_percent': round(battery.percent, 1) if battery else None,
                'battery_plugged': battery.power_plugged if battery else None,
            }
