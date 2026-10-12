"""Auditoria e ações nomeadas do Windows; nunca aceita PowerShell do modelo."""
import asyncio
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class WindowsError(ValueError):
    pass


# Somente código do projeto. Nada de prompts, caminhos ou comandos gerados por IA.
SCRIPTS = {
    "audit": r'''
$defender = $null; $profiles = @(); $updates = $null; $encryption = $null; $secureBoot = $null
try { $d = Get-MpComputerStatus -ErrorAction Stop; $defender = @{
    antivirus_enabled=$d.AntivirusEnabled; realtime_enabled=$d.RealTimeProtectionEnabled;
    signatures_age_days=$d.AntivirusSignatureAge; quick_scan_age_days=$d.QuickScanAge;
    tamper_protected=$d.IsTamperProtected } } catch {}
try { $profiles = @(Get-NetFirewallProfile -ErrorAction Stop | ForEach-Object { @{name=$_.Name; enabled=[bool]$_.Enabled} }) } catch {}
try { $u = Get-HotFix -ErrorAction Stop | Sort-Object InstalledOn -Descending | Select-Object -First 1;
    if ($u.InstalledOn) { $updates = $u.InstalledOn.ToUniversalTime().ToString('o') } } catch {}
try { $b = Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop; $encryption = [string]$b.ProtectionStatus } catch {}
try { $secureBoot = Confirm-SecureBootUEFI -ErrorAction Stop } catch {}
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$v = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction Stop
$legacy = @(Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -in @('JARVIS Dashboard Port 8000','JARVIS Dashboard Port 8001','JARVIS Dashboard Python') } | ForEach-Object { @{name=$_.DisplayName; enabled=[string]$_.Enabled; action=[string]$_.Action} })
@{windows=@{build=[int]$v.CurrentBuildNumber; edition=[string]$v.EditionID; release=[string]$v.DisplayVersion};
    running_as_admin=$admin; defender=$defender; firewall=$profiles; last_hotfix_utc=$updates;
    encryption=$encryption; secure_boot=$secureBoot; legacy_rules=$legacy} | ConvertTo-Json -Depth 6 -Compress
''',
    "devices": r'''
$cpu = Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1
$ram = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
$gpu = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | ForEach-Object { [string]$_.Name })
$audio = @(Get-CimInstance Win32_SoundDevice -ErrorAction SilentlyContinue | ForEach-Object { @{name=[string]$_.Name; status=[string]$_.Status} })
@{cpu=[string]$cpu.Name; logical_processors=$cpu.NumberOfLogicalProcessors; ram_gib=[math]::Round($ram.TotalPhysicalMemory/1GB,1);
    gpu=$gpu; audio=$audio} | ConvertTo-Json -Depth 4 -Compress
''',
    "update_signatures": "Update-MpSignature -ErrorAction Stop; @{completed=$true; action='update_signatures'} | ConvertTo-Json -Compress",
    "quick_scan": "Start-MpScan -ScanType QuickScan -ErrorAction Stop; @{completed=$true; action='quick_scan'} | ConvertTo-Json -Compress",
    "enable_firewall": "Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True -ErrorAction Stop; @{completed=$true; action='enable_firewall'} | ConvertTo-Json -Compress",
    "remove_legacy_rules": r"Get-NetFirewallRule -ErrorAction Stop | Where-Object { $_.DisplayName -in @('JARVIS Dashboard Port 8000','JARVIS Dashboard Port 8001','JARVIS Dashboard Python') } | Remove-NetFirewallRule -ErrorAction Stop; @{completed=$true; action='remove_legacy_rules'} | ConvertTo-Json -Compress",
}


def powershell(name, timeout=15, cancel=None):
    if sys.platform != "win32":
        raise WindowsError("Execute esta função no Cronos instalado no seu Windows.")
    if name not in SCRIPTS:
        raise WindowsError("Ação do Windows não permitida.")
    directory = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetWindowsDirectoryW(directory, len(directory)):
        raise WindowsError("Não foi possível localizar o diretório do Windows.")
    executable = Path(directory.value) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); $ErrorActionPreference='Stop'; " + SCRIPTS[name]
    try:
        process = subprocess.Popen([str(executable), "-NoProfile", "-NonInteractive", "-Command", script],
                                   shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + timeout
        try:
            while True:
                if cancel is not None and cancel.is_set():
                    raise WindowsError("O acompanhamento foi encerrado. Uma ação já iniciada pelo Windows pode continuar.")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(process.args, timeout)
                try:
                    output, _ = process.communicate(timeout=min(1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
        if process.returncode:
            raise WindowsError("O Windows não concluiu a operação. Pode exigir permissão administrativa, ter proteção contra alterações ou serviço indisponível. Abra a Segurança do Windows para conferir.")
        if len(output) > 128 * 1024:
            raise WindowsError("Relatório do Windows acima do limite.")
        return json.loads(output.lstrip("\ufeff"))
    except subprocess.TimeoutExpired as exc:
        raise WindowsError("Tempo de espera esgotado. Uma operação já iniciada pelo Windows pode continuar; confira sua Segurança do Windows antes de repetir.") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WindowsError("Não foi possível ler o resultado da operação do Windows.") from exc


def findings(report):
    warnings = []
    defender = report.get("defender")
    if defender is None:
        warnings.append({"code": "defender_unknown", "severity": "unknown", "message": "Estado do Defender indisponível; outro antivírus ou falta de permissão pode explicar isso."})
    else:
        if not defender.get("antivirus_enabled") or not defender.get("realtime_enabled"):
            warnings.append({"code": "defender_disabled", "severity": "warning", "message": "Defender ou proteção em tempo real desativado. Confira se outro antivírus oferece proteção antes de mudar configurações."})
        age = defender.get("signatures_age_days")
        if isinstance(age, (int, float)) and age > 3:
            warnings.append({"code": "signatures_old", "severity": "warning", "message": "Definições do Defender têm mais de três dias; tente atualizá-las."})
    if not report.get("firewall"):
        warnings.append({"code": "firewall_unknown", "severity": "unknown", "message": "Estado do firewall não pôde ser consultado."})
    elif any(not profile.get("enabled") for profile in report["firewall"]):
        warnings.append({"code": "firewall_disabled", "severity": "warning", "message": "Há um perfil de firewall desativado; habilitá-lo pode bloquear conexões de aplicativos."})
    if report.get("running_as_admin"):
        warnings.append({"code": "admin", "severity": "warning", "message": "O Cronos está rodando com privilégios administrativos. Prefira uma conta comum."})
    build = report.get("windows", {}).get("build")
    if isinstance(build, int) and 10240 <= build < 22000:
        warnings.append({"code": "windows10_support", "severity": "warning", "message": "O suporte regular ao Windows 10 terminou em 14/10/2025. Confira elegibilidade e inscrição no ESU; este relatório não verifica a inscrição."})
    if report.get("legacy_rules"):
        warnings.append({"code": "legacy_rules", "severity": "warning", "message": "Foram encontradas regras do dashboard antigo. Revise se ainda são necessárias antes de removê-las."})
    if report.get("encryption") == "Off":
        warnings.append({"code": "encryption", "severity": "warning", "message": "A proteção BitLocker consultada está desligada; notas e chaves podem ficar expostas se alguém acessar o disco."})
    return warnings


class WindowsSystem:
    def __init__(self, runner=None, monitor=None, platform=None, privacy_mode="online"):
        self.runner = runner or powershell
        self.platform = platform or sys.platform
        self.monitor = monitor
        self.jobs = {}
        self.tasks = set()
        self.last_audit = None
        self.privacy_mode = privacy_mode
        self.cancel = threading.Event()

    def _run(self, name, timeout):
        if self.runner is powershell:
            return powershell(name, timeout, self.cancel)
        return self.runner(name, timeout)

    def require_windows(self):
        if self.platform != "win32":
            raise WindowsError("Disponível apenas no computador Windows local; a nuvem não controla seu notebook.")

    async def audit(self):
        self.require_windows()
        report = await asyncio.to_thread(self._run, "audit", 20)
        result = {"checked_at": datetime.now(timezone.utc).isoformat(), "report": report,
                  "findings": findings(report), "scope": "Leitura do Windows local. Não certifica ausência de malware, atualizações pendentes ou invasões."}
        self.last_audit = result
        if self.monitor:
            risky = any(item["severity"] == "warning" for item in result["findings"])
            unknown = any(item["severity"] == "unknown" for item in result["findings"])
            self.monitor.update("windows_audit", risky, "warning", "A auditoria do Windows encontrou configurações que merecem revisão.",
                                "Abra o módulo Segurança para ver o relatório. Nenhuma configuração foi alterada pela auditoria.")
            self.monitor.update("windows_audit_partial", unknown, "warning", "Parte do estado de segurança do Windows não pôde ser consultada.",
                                "Confira Defender/firewall no módulo Segurança. Informação indisponível não comprova proteção nem invasão.")
        return result

    async def devices(self):
        self.require_windows()
        return await asyncio.to_thread(self._run, "devices", 20)

    async def action(self, name):
        self.require_windows()
        from cronos import wake
        voice_actions = {"prepare_voice": wake.prepare_model, "start_voice": wake.start, "stop_voice": wake.stop,
                         "enable_voice_startup": lambda: wake.startup(True), "disable_voice_startup": lambda: wake.startup(False)}
        if name in voice_actions and name != "prepare_voice":
            return await asyncio.to_thread(voice_actions[name])
        if name == "prepare_voice" and self.privacy_mode != "online":
            raise WindowsError("Modo local: prepare o modelo antes de ativar esse modo; download externo está bloqueado.")
        if name in {"open_security", "open_updates"}:
            os.startfile({"open_security": "windowsdefender:", "open_updates": "ms-settings:windowsupdate"}[name])
            return {"opened": name, "note": "Tela aberta; isso não comprova correção nem instalação de atualizações."}
        if name not in {"update_signatures", "quick_scan", "enable_firewall", "remove_legacy_rules", "prepare_voice"}:
            raise WindowsError("Ação não permitida.")
        if self.tasks:
            raise WindowsError("Já há uma operação do Windows em andamento. Aguarde antes de iniciar outra.")
        identifier = str(uuid4())
        job = {"id": identifier, "action": name, "status": "running", "started": datetime.now(timezone.utc).isoformat()}
        self.jobs[identifier] = job
        if len(self.jobs) > 30:
            del self.jobs[next(iter(self.jobs))]
        async def run():
            try:
                result = (await asyncio.to_thread(wake.prepare_model, self.cancel) if name == "prepare_voice" else
                          await asyncio.to_thread(self._run, name, 600 if name == "quick_scan" else 120))
                if result.get("completed") is not True and result.get("installed") is not True:
                    raise WindowsError("O Windows não confirmou a conclusão da operação.")
                job.update(status="completed", result=result)
                if name != "prepare_voice":
                    await self.audit()
                    if self.monitor:
                        self.monitor.update("windows_action", False)
            except asyncio.CancelledError:
                job.update(status="interrupted", error="Acompanhamento encerrado. Uma ação do Windows já iniciada pode continuar.")
                raise
            except Exception:
                error = ("Preparação do modelo de voz falhou. Confira conexão com alphacephei.com, espaço livre e arquivos existentes; o modelo não foi ativado." if name == "prepare_voice" else
                         "A operação ou sua verificação não foi concluída. Confira permissões e Segurança do Windows; uma ação iniciada pode continuar mesmo após timeout.")
                job.update(status="failed", error=error)
                if self.monitor:
                    self.monitor.update("windows_action", True, "warning", "Uma operação local falhou ou não pôde ser verificada.", "Confira o resultado em Consultar operações antes de repetir.")
            finally:
                job["finished"] = datetime.now(timezone.utc).isoformat()
        task = asyncio.create_task(run())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return dict(job)

    async def watch(self):
        if self.platform != "win32":
            return
        while True:
            try:
                await self.audit()
                if self.monitor:
                    self.monitor.update("windows_audit_unavailable", False)
            except Exception:
                if self.monitor:
                    self.monitor.update("windows_audit_unavailable", True, "warning", "A consulta de segurança do Windows não pôde ser concluída.", "Abra Segurança para verificar permissões e disponibilidade. O estado do Windows não foi confirmado.")
            await asyncio.sleep(120)

    async def close(self):
        self.cancel.set()
        for task in list(self.tasks):
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
