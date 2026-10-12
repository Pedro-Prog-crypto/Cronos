"""Diagnóstico local limitado e eventos sem prompts, chaves ou caminhos privados."""
import asyncio
import hashlib
import os
import shutil
import sqlite3
import threading
import time
from collections import deque
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def memory_pressure():
    """Percentual de RAM ocupada; None quando a plataforma não fornece o dado."""
    if os.name == "nt":
        import ctypes
        class Status(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in (
                    "total", "available", "page_total", "page_available", "virtual_total",
                    "virtual_available", "extended_available")]
        status = Status()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.load
        return None
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            name, value = line.split(":", 1)
            if name in {"MemTotal", "MemAvailable"}:
                values[name] = int(value.split()[0])
        return round(100 * (1 - values["MemAvailable"] / values["MemTotal"]), 1)
    except (OSError, ValueError, KeyError, ZeroDivisionError):
        return None


class Monitor:
    interval = 15

    def __init__(self, settings, memory):
        self.settings, self.memory = settings, memory
        self.lock = threading.RLock()
        self.alerts = {}
        self.events = deque(maxlen=200)
        self.denials = deque(maxlen=100)
        self.sequence = 0
        self.checked_at = None
        self.resources = {}
        self.baseline = None
        self.component_status = {}

    def update(self, code, active, severity="warning", message="", suggestion=""):
        with self.lock:
            previous = self.alerts.get(code)
            if not active:
                if previous:
                    del self.alerts[code]
                    self._event(code, "resolved", "info", "Condição encerrada: " + previous["message"], "")
                return
            if previous and (previous["severity"], previous["message"]) == (severity, message):
                return
            event = self._event(code, "active", severity, message, suggestion)
            self.alerts[code] = {**event, "acknowledged": False}

    def _event(self, code, status, severity, message, suggestion):
        self.sequence += 1
        event = {"id": self.sequence, "code": code, "status": status, "severity": severity,
                 "message": message, "suggestion": suggestion,
                 "time": datetime.now(timezone.utc).isoformat()}
        self.events.append(event)
        return event

    def denied(self):
        with self.lock:
            self.denials.append(time.monotonic())
            self._denial_state()

    def _denial_state(self):
        now = time.monotonic()
        while self.denials and self.denials[0] < now - 60:
            self.denials.popleft()
        self.update("access_denied", len(self.denials) >= 5, "warning",
                    "Várias tentativas de acesso foram bloqueadas no último minuto.",
                    "Confira o token e as interfaces abertas. Isso também pode ser erro de configuração; não comprova invasão.")

    def response(self, path, status):
        component = {"/chat": "conversation", "/voice/speech": "voice", "/voice/stream": "voice",
                     "/voice/transcribe": "voice", "/memory/sync": "memory",
                     "/vision/analyze": "vision", "/missions": "planning"}.get(path)
        if not component or (status < 500 and not 200 <= status < 300):
            return
        labels = {"conversation": "conversa com a IA", "voice": "voz", "memory": "sincronização da memória",
                  "vision": "análise de imagem", "planning": "planejamento"}
        with self.lock:
            self.component_status[component] = "failed" if status >= 500 else "last_request_ok"
            self.update("service_" + component, status >= 500, "warning",
                        "A última solicitação de " + labels[component] + " falhou.",
                        "Consulte o erro da operação. Uma nova operação bem-sucedida encerra este alerta.")

    def collect(self):
        # Não chama modelos, Fish, buscadores nem executa comandos do Windows.
        with self.lock:
            self._denial_state()
        self.update("token", len(self.settings.token) < 24, "warning",
                    "O token local está ausente ou é curto.",
                    "Use um token aleatório longo. No modo desktop, um token é gerado quando não há configuração.")
        self.update("executables", self.settings.allow_executables, "warning",
                    "A execução de programas está habilitada.", "Confirme apenas programas confiáveis; execução não é isolada do Windows.")
        self.update("plugins", self.settings.enable_plugins, "warning",
                    "Plugins externos estão habilitados.", "Plugins usam seus privilégios. Instale apenas código revisado e confiável.")
        try:
            # Leitura limitada, sem armazenar nem expor conteúdo.
            with self.settings.personality.open("rb") as file:
                data = file.read(256 * 1024 + 1)
            if not data.strip() or len(data) > 256 * 1024:
                raise ValueError()
            digest = hashlib.sha256(data).digest()
            if self.baseline is None:
                self.baseline = digest
            self.update("personality_unavailable", False)
            self.update("personality_changed", digest != self.baseline, "warning",
                        "O arquivo de personalidade mudou desde o início do monitor.",
                        "Confira se a edição foi sua. Alteração detectada não significa invasão; reinicie após validar a edição.")
        except (OSError, ValueError):
            self.update("personality_unavailable", True, "critical",
                        "O arquivo de personalidade está ausente, vazio ou não pode ser lido dentro do limite do monitor.",
                        "Restaure o arquivo configurado antes de continuar a conversa.")
        try:
            free = shutil.disk_usage(self.settings.vault).free
            with self.lock:
                self.resources["disk_free_mib"] = round(free / 1024**2)
            self.update("disk", free < 250 * 1024**2, "critical",
                        "O disco da memória tem menos de 250 MiB livres.",
                        "Libere espaço para evitar falhas ao salvar conversas; não apague seu vault sem backup.")
            with closing(sqlite3.connect(self.memory.database.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
                pending = db.execute("SELECT EXISTS(SELECT 1 FROM exports WHERE done=0)").fetchone()[0]
            self.update("memory_check", False)
            self.update("exports", bool(pending), "warning",
                        "Há notas aguardando exportação para o Obsidian.",
                        "Confira permissões e espaço da pasta e tente sincronizar a memória.")
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            self.update("memory_check", True, "critical", "O diagnóstico não conseguiu consultar a memória ou seu disco.",
                        "Confira o vault e as permissões. O monitor não altera nem repara arquivos automaticamente.")
        pressure = memory_pressure()
        with self.lock:
            self.resources["ram_used_percent"] = pressure
        self.update("ram", pressure is not None and pressure >= 90, "warning",
                    "O computador está usando pelo menos 90% da RAM.",
                    "Feche programas pesados e prefira modelos externos neste notebook de 4 GB.")
        with self.lock:
            self.checked_at = datetime.now(timezone.utc).isoformat()

    async def run(self):
        while True:
            await asyncio.sleep(self.interval)
            try:
                await asyncio.to_thread(self.collect)
                self.update("monitor_check", False)
            except Exception:
                self.update("monitor_check", True, "warning", "Uma verificação do monitor falhou.",
                            "A cobertura do diagnóstico está reduzida; consulte o diagnóstico do aplicativo.")

    def snapshot(self, after=0):
        with self.lock:
            return {"state": "attention" if self.alerts else "monitoring", "checked_at": self.checked_at,
                    "interval_seconds": self.interval, "cursor": self.sequence,
                    "alerts": [dict(value) for value in self.alerts.values()],
                    "events": [dict(value) for value in self.events if value["id"] > after],
                    "resources": dict(self.resources), "components": dict(self.component_status),
                    "scope": "Processo Cronos, tentativas bloqueadas, personalidade, memória, disco e pressão de RAM. Não é antivírus nem detector geral de invasões."}

    def acknowledge(self, alert_id):
        with self.lock:
            for alert in self.alerts.values():
                if alert["id"] == alert_id:
                    alert["acknowledged"] = True
                    return True
            return False
