"""Escuta local opcional para ativar, pausar e retomar o Cronos por voz."""
import argparse
import hashlib
import importlib.util
import json
import os
import queue
import subprocess
import sys
import tempfile
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx

from cronos.security import safe_path
from cronos.windows_agent import safe_extract

MODEL_NAME = "vosk-model-small-pt-0.3"
MODEL_URL = "https://alphacephei.com/vosk/models/" + MODEL_NAME + ".zip"
DEFAULT_SETTINGS = {
    "activation_phrase": "cronos",
    "pause_phrase": "pausar cronos",
    "resume_phrase": "retomar cronos",
    "start_with_windows": False,
}
PHRASES = {"abrir cronos", "abrir kronos", "cronos abrir", "kronos abrir"}  # compatibilidade antiga
MODEL_LAYOUTS = (("am/final.mdl", "conf/model.conf"),
                 ("final.mdl", "mfcc.conf", "HCLr.fst", "Gr.fst"))


def normalize_phrase(value):
    if not isinstance(value, str):
        return ""
    value = "".join(character for character in unicodedata.normalize("NFKD", value.casefold())
                    if not unicodedata.combining(character))
    return " ".join("".join(ch if ch.isalnum() else " " for ch in value).split())


def validate_settings(data):
    if not isinstance(data, dict):
        raise ValueError("As configurações do ouvinte precisam ser um objeto.")
    result = {}
    for key in ("activation_phrase", "pause_phrase", "resume_phrase"):
        value = data.get(key)
        normalized = normalize_phrase(value)
        if not normalized or len(normalized) > 80 or len(normalized.split()) > 10:
            raise ValueError("Cada frase precisa ter entre 1 e 10 palavras e até 80 caracteres.")
        result[key] = " ".join(str(value).strip().split())
    if len({normalize_phrase(result[key]) for key in result}) != 3:
        raise ValueError("Ativação, pausa e retomada precisam usar frases diferentes.")
    result["start_with_windows"] = bool(data.get("start_with_windows", False))
    return result


def settings():
    path = root() / "settings.json"
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        return validate_settings({**DEFAULT_SETTINGS, **stored})
    except FileNotFoundError:
        return dict(DEFAULT_SETTINGS)
    except (OSError, ValueError, TypeError):
        # Um arquivo inválido nunca deve impedir a inicialização; status expõe o padrão.
        return dict(DEFAULT_SETTINGS)


def save_settings(data):
    current = settings()
    current.update(data if isinstance(data, dict) else {})
    clean = validate_settings(current)
    folder = root()
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "settings.tmp"
    temporary.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(folder / "settings.json")
    return clean


def paused():
    try:
        return bool(json.loads((root() / "mode.json").read_text(encoding="utf-8")).get("paused"))
    except (OSError, ValueError, TypeError):
        return False


def set_paused(value):
    folder = root()
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "mode.tmp"
    temporary.write_text(json.dumps({"paused": bool(value)}, ensure_ascii=False), encoding="utf-8")
    temporary.replace(folder / "mode.json")


def model_present(folder):
    return any(all((folder / name).is_file() for name in layout) for layout in MODEL_LAYOUTS)


def root():
    base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / ".local/share"))
    return base / "Cronos" / "wake"


def status():
    folder = root()
    installed = model_present(folder / MODEL_NAME) and (folder / "model-hashes.json").is_file()
    config = settings()
    result = {"model_installed": installed,
              "dependencies_installed": all(importlib.util.find_spec(name) is not None for name in ("vosk", "sounddevice")),
              "state": "stopped", "local_only": True,
              "phrases": [config["activation_phrase"]], "settings": config,
              "paused": paused()}
    try:
        data = json.loads((folder / "status.json").read_text())
        age = time.time() - float(data["heartbeat"])
        if 0 <= age < 20 or data.get("state") == "error":
            result.update({key: data[key] for key in ("state", "last_opened") if key in data})
            reasons = {"dependency_missing", "microphone_unavailable", "model_or_platform_unavailable", "audio_library_or_device_unavailable", "unknown"}
            if data.get("reason") in reasons:
                result["reason"] = data["reason"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    startup = Path(os.getenv("APPDATA") or folder) / "Microsoft/Windows/Start Menu/Programs/Startup/Cronos Voice.lnk"
    result["start_with_windows"] = startup.exists()
    return result


def _write_status(state, last_opened=None, reason=None):
    folder = root(); folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "status.tmp"
    data = {"state": state, "heartbeat": time.time(), "last_opened": last_opened}
    if reason:
        data["reason"] = reason
    temporary.write_text(json.dumps(data))
    temporary.replace(folder / "status.json")


def prepare_model(cancel=None):
    folder = root(); folder.mkdir(parents=True, exist_ok=True)
    if (folder / MODEL_NAME).exists():
        verify_model()
        return {"installed": True, "downloaded": False}
    with tempfile.TemporaryDirectory(prefix="cronos-wake-") as temporary:
        archive = Path(temporary) / "model.zip"
        size = 0
        # URL fixa oficial. TLS permanece verificado; não segue redirects.
        with httpx.Client(timeout=httpx.Timeout(15, read=10), follow_redirects=False) as client:
            with client.stream("GET", MODEL_URL) as response:
                response.raise_for_status()
                with archive.open("wb") as file:
                    for chunk in response.iter_bytes():
                        if cancel is not None and cancel.is_set():
                            raise ValueError("Preparação interrompida; nenhum modelo foi ativado.")
                        size += len(chunk)
                        if size > 100 * 1024**2:
                            raise ValueError("Modelo excedeu o limite de download.")
                        file.write(chunk)
        extracted = Path(temporary) / "extracted"
        safe_extract(archive, extracted)
        model = extracted / MODEL_NAME
        if not model_present(model):
            raise ValueError("Pacote não contém o modelo de português esperado.")
        hashes = {}
        for file in model.rglob("*"):
            if file.is_file():
                if file.suffix.lower() in {".exe", ".dll", ".py", ".ps1", ".bat", ".cmd"}:
                    raise ValueError("O pacote contém arquivos executáveis inesperados.")
                hashes[file.relative_to(model).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
        import shutil
        # Destino dentro da pasta do usuário, nunca dentro do projeto/vault.
        shutil.move(str(model), str(folder / MODEL_NAME))
        (folder / "model-hashes.json").write_text(json.dumps(hashes))
        return {"installed": True, "downloaded": True, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "note": "Hashes detectam mudanças posteriores. Não são uma assinatura independente do fornecedor."}


def verify_model():
    folder = root()
    model = safe_path(folder, MODEL_NAME, private=True)
    try:
        hashes = json.loads((folder / "model-hashes.json").read_text())
        if not isinstance(hashes, dict) or not 1 <= len(hashes) <= 1000:
            raise ValueError()
        if not any(all(name in hashes for name in layout) for layout in MODEL_LAYOUTS):
            raise ValueError()
        actual = {file.relative_to(model).as_posix() for file in model.rglob("*") if file.is_file()}
        if actual != set(hashes):
            raise ValueError()
        for name, digest in hashes.items():
            file = safe_path(model, name, private=True)
            if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                raise ValueError()
    except (OSError, ValueError, TypeError):
        raise ValueError("Modelo ausente ou alterado. Revise os arquivos do iniciador antes de ativá-lo.") from None
    return model


class Trigger:
    def __init__(self, config=None):
        self.last_activation = float("-inf")
        self.last_transition = float("-inf")
        self.config = validate_settings(config or settings())

    def action(self, result, now=None):
        now = time.monotonic() if now is None else now
        text = normalize_phrase(result.get("text", ""))
        words = result.get("result", [])
        confidence = sum(word.get("conf", 0) for word in words) / len(words) if words else 0
        action = ("paused" if text == normalize_phrase(self.config["pause_phrase"]) else
                  "resumed" if text == normalize_phrase(self.config["resume_phrase"]) else
                  "activate" if text == normalize_phrase(self.config["activation_phrase"]) else None)
        cooldown = 20 if action == "activate" else 2
        last_action = self.last_activation if action == "activate" else self.last_transition
        if confidence < .75 or action is None or now - last_action < cooldown:
            return None
        if action == "paused":
            self.last_transition = now
            set_paused(True)
            return "paused"
        if action == "resumed":
            self.last_transition = now
            set_paused(False)
            return "resumed"
        if paused():
            return None
        self.last_activation = now
        return "activate"

    def accept(self, result, now=None):
        """Compatibilidade com integrações antigas que só verificam ativação."""
        return self.action(result, now) == "activate"


@contextmanager
def single_instance(name):
    if sys.platform != "win32":
        yield True
        return
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    ctypes.set_last_error(0)
    handle = kernel.CreateMutexW(None, False, "Local\\" + name)
    if not handle:
        raise ValueError("Não foi possível reservar a instância local.")
    acquired = ctypes.get_last_error() != 183
    try:
        yield acquired
    finally:
        kernel.CloseHandle(handle)


def python_windowless():
    candidate = Path(sys.executable).with_name("pythonw.exe")
    return candidate if candidate.exists() else Path(sys.executable)


def start():
    if sys.platform != "win32":
        raise ValueError("O iniciador deve executar no Windows do usuário.")
    verify_model()
    if not status()["dependencies_installed"]:
        raise ValueError('Instale o extra wake: python -m pip install -e ".[wake]".')
    project = Path(__file__).resolve().parent.parent
    subprocess.Popen([str(python_windowless()), "-m", "cronos.wake"], cwd=project, shell=False,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"requested": True, "note": "Confira o estado do microfone após alguns segundos. Iniciar processo não comprova reconhecimento de voz."}


def stop():
    folder = root(); folder.mkdir(parents=True, exist_ok=True)
    (folder / "stop.request").write_text("stop")
    return {"requested": True}


def startup(enabled):
    if sys.platform != "win32":
        raise ValueError("Inicialização automática disponível somente no Windows.")
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise ValueError("Pasta de inicialização do usuário indisponível.")
    destination = Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup/Cronos Voice.lnk"
    if not enabled:
        destination.unlink(missing_ok=True)
        save_settings({"start_with_windows": False})
        return {"start_with_windows": False, "note": "Não encerra o ouvinte atual; use Parar microfone."}
    verify_model()
    if not status()["dependencies_installed"]:
        raise ValueError("Instale as dependências do iniciador antes de ativar o início automático.")
    if destination.exists():
        raise ValueError("O atalho já existe. Desative a opção antes de recriar.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    def literal(value):
        return "'" + str(value).replace("'", "''") + "'"
    script = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(" + literal(destination) + ");"
    script += "$s.TargetPath=" + literal(python_windowless()) + ";$s.Arguments='-m cronos.wake';"
    script += "$s.WorkingDirectory=" + literal(Path(__file__).resolve().parent.parent) + ";$s.Description='Cronos: comando de voz local';$s.Save()"
    import ctypes
    directory = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetWindowsDirectoryW(directory, len(directory)):
        raise ValueError("Diretório do Windows indisponível.")
    executable = Path(directory.value) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    process = subprocess.run([str(executable), "-NoProfile", "-NonInteractive", "-Command", script],
                             shell=False, capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    if process.returncode or not destination.exists():
        raise ValueError("O Windows não confirmou a criação do atalho.")
    save_settings({"start_with_windows": True})
    return {"start_with_windows": True}


def listen():
    if sys.platform != "win32":
        raise ValueError("Execute no seu Windows.")
    with single_instance("CronosVoiceLauncher") as acquired:
        if not acquired:
            return
        model = verify_model()
        import sounddevice
        from vosk import KaldiRecognizer, Model, SetLogLevel
        SetLogLevel(-1)
        config = settings()
        phrases = [config["activation_phrase"], config["pause_phrase"], config["resume_phrase"]]
        acoustic_model = Model(str(model))
        grammar = json.dumps([*phrases, "[unk]"], ensure_ascii=False)
        recognizer = KaldiRecognizer(acoustic_model, 16000, grammar)
        recognizer.SetWords(True)
        frames = queue.Queue(maxsize=16)
        def audio(data, count, timing, status):
            try:
                frames.put_nowait(bytes(data))
            except queue.Full:
                pass
        folder = root(); (folder / "stop.request").unlink(missing_ok=True)
        trigger, opened, heartbeat = Trigger(config), None, 0
        settings_stamp = (root() / "settings.json").stat().st_mtime if (root() / "settings.json").exists() else None
        try:
            with sounddevice.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=audio):
                while not (folder / "stop.request").exists():
                    settings_path = root() / "settings.json"
                    try:
                        next_stamp = settings_path.stat().st_mtime
                    except OSError:
                        next_stamp = None
                    if next_stamp != settings_stamp:
                        config = settings()
                        phrases = [config["activation_phrase"], config["pause_phrase"], config["resume_phrase"]]
                        recognizer = KaldiRecognizer(acoustic_model, 16000,
                                                     json.dumps([*phrases, "[unk]"], ensure_ascii=False))
                        recognizer.SetWords(True)
                        trigger = Trigger(config)
                        settings_stamp = next_stamp
                    if time.monotonic() - heartbeat > 5:
                        _write_status("paused" if paused() else "listening", opened); heartbeat = time.monotonic()
                    try:
                        frame = frames.get(timeout=.5)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(frame):
                        action = trigger.action(json.loads(recognizer.Result()))
                        if action == "activate":
                            subprocess.Popen([str(python_windowless()), "-m", "cronos.browser"],
                                             cwd=Path(__file__).resolve().parent.parent, shell=False,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                            opened = datetime.now(timezone.utc).isoformat()
                        if action in {"activate", "paused", "resumed"}:
                            _write_status("paused" if paused() else "listening", opened)
        finally:
            _write_status("stopped", opened)


def main():
    parser = argparse.ArgumentParser(description="Abrir Cronos por voz, localmente")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    try:
        if args.stop:
            stop()
        else:
            listen()
    except KeyboardInterrupt:
        _write_status("stopped")
    except Exception as exc:
        reason = ("dependency_missing" if isinstance(exc, ImportError) else
                  "microphone_unavailable" if exc.__class__.__name__ == "PortAudioError" else
                  "model_or_platform_unavailable" if isinstance(exc, ValueError) else
                  "audio_library_or_device_unavailable" if isinstance(exc, OSError) else "unknown")
        _write_status("error", reason=reason)
        print("O iniciador não pôde ativar o microfone/modelo. Consulte Dispositivos no Cronos.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
