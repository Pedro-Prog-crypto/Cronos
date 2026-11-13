"""Small, read-only system sample for the home dashboard."""
import os
import shutil
import subprocess
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

    @staticmethod
    def _nvidia_gpu():
        """Read optional NVIDIA sensors without requiring a driver or new package."""
        empty = {'gpu_percent': None, 'gpu_memory_used_bytes': None,
                 'gpu_memory_total_bytes': None, 'gpu_temperature_celsius': None,
                 'gpu_fan_percent': None}
        executable = shutil.which('nvidia-smi')
        if not executable:
            return empty
        try:
            result = subprocess.run(
                [executable, '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,fan.speed',
                 '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=1.5, check=False)
            if result.returncode:
                return empty
            fields = [field.strip() for field in result.stdout.splitlines()[0].split(',')]
            if len(fields) != 5:
                return empty
            def number(value):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
            utilization, used, total, temperature, fan = map(number, fields)
            return {'gpu_percent': utilization,
                    'gpu_memory_used_bytes': round(used * 1048576) if used is not None else None,
                    'gpu_memory_total_bytes': round(total * 1048576) if total is not None else None,
                    'gpu_temperature_celsius': temperature, 'gpu_fan_percent': fan}
        except (OSError, subprocess.SubprocessError, IndexError):
            return empty

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
                        'network_download_bytes_per_second': None, 'network_upload_bytes_per_second': None,
                        'cpu_frequency_ghz': None, 'cpu_frequency_max_ghz': None,
                        'cpu_temperature_celsius': None,
                        'fan_rpm': None, 'battery_percent': None, 'battery_plugged': None,
                        **self._nvidia_gpu()}
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
            cpu_temperature = next((reading.current for name, group in temperatures.items()
                                    if any(word in name.lower() for word in ('cpu', 'coretemp', 'k10temp', 'thermal'))
                                    for reading in group if reading.current is not None), None)
            try:
                frequency = psutil.cpu_freq()
            except (OSError, RuntimeError, AttributeError):
                frequency = None
            try:
                fans = psutil.sensors_fans() if hasattr(psutil, 'sensors_fans') else {}
            except (OSError, RuntimeError):
                fans = {}
            fan_rpm = next((reading.current for group in fans.values() for reading in group
                            if reading.current is not None), None)
            now = monotonic()
            network = psutil.net_io_counters()
            rate = download = upload = None
            if self._previous_network is not None and self._previous_time is not None and now > self._previous_time:
                elapsed = now - self._previous_time
                download = round(max(0, network.bytes_recv - self._previous_network[0]) / elapsed, 1)
                upload = round(max(0, network.bytes_sent - self._previous_network[1]) / elapsed, 1)
                rate = download + upload
            self._previous_network = (network.bytes_recv, network.bytes_sent)
            self._previous_time = now
            return {
                'cpu_percent': round(cpu, 1),
                'cpu_frequency_ghz': round(frequency.current / 1000, 2) if frequency and frequency.current else None,
                'cpu_frequency_max_ghz': round(frequency.max / 1000, 2) if frequency and frequency.max else None,
                'cpu_temperature_celsius': round(cpu_temperature, 1) if cpu_temperature is not None else None,
                'ram_percent': round(memory.percent, 1),
                'ram_used_bytes': memory.used,
                'ram_total_bytes': memory.total,
                'disk_percent': round(disk.percent, 1),
                'disk_used_bytes': disk.used,
                'disk_total_bytes': disk.total,
                'network_bytes_per_second': rate,
                'network_download_bytes_per_second': download,
                'network_upload_bytes_per_second': upload,
                'temperature_celsius': round(temperature, 1) if temperature is not None else None,
                'fan_rpm': round(fan_rpm) if fan_rpm is not None else None,
                'battery_percent': round(battery.percent, 1) if battery else None,
                'battery_plugged': battery.power_plugged if battery else None,
                **self._nvidia_gpu(),
            }
