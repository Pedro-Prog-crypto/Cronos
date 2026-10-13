import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    vault: Path
    personality: Path
    token: str
    provider: str
    gemini_key: str
    gemini_model: str
    fish_key: str
    fish_reference: str
    fish_model: str
    ollama_url: str
    ollama_model: str
    origins: tuple[str, ...] = ()
    providers_file: Path = Path("config/providers.json")
    context_messages: int = 40
    context_chars: int = 48000
    memory_chars: int = 16000
    memory_results: int = 8
    tool_rounds: int = 6
    files_root: Path = Path.home() / "Downloads"
    fish_speed: float = 1.0
    fish_latency: str = "balanced"
    enable_plugins: bool = False
    output_tokens: int | None = None
    provider_timeout: float = 180
    privacy_mode: str = "online"
    allow_executables: bool = False
    fish_format: str = "mp3"
    transcription_provider: str = "fish"
    gemini_transport: str = "live"
    gemini_live_model: str = "models/gemini-3.1-flash-live-preview"

    def __post_init__(self):
        if self.gemini_transport not in {'live','rest'}:
            raise ValueError('GEMINI_TRANSPORT deve ser live ou rest.')
        if self.transcription_provider not in {"fish", "vosk"}:
            raise ValueError("CRONOS_TRANSCRIPTION_PROVIDER deve ser fish ou vosk.")
        if self.fish_format not in {"mp3", "wav"}:
            raise ValueError("FISH_FORMAT deve ser mp3 ou wav.")
        if self.privacy_mode not in {"online", "local"}:
            raise ValueError("CRONOS_PRIVACY_MODE deve ser online ou local.")

    @classmethod
    def from_env(cls):
        return cls(
            vault=Path(os.getenv("CRONOS_VAULT", "vault")).expanduser().resolve(),
            personality=Path(os.getenv("CRONOS_PERSONALITY", "modelos/personalidades/cronos.md")),
            token=os.getenv("CRONOS_API_TOKEN", ""),
            provider=os.getenv("CRONOS_PROVIDER", "gemini"),
            gemini_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            gemini_transport=os.getenv('GEMINI_TRANSPORT','live').strip().lower(),
            gemini_live_model=os.getenv('GEMINI_LIVE_MODEL','models/gemini-3.1-flash-live-preview').strip(),
            fish_key=os.getenv("FISH_API_KEY", ""),
            fish_reference=os.getenv("FISH_REFERENCE_ID", ""),
            fish_model=os.getenv("FISH_MODEL", "").strip().lower(),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
            origins=tuple(x.strip() for x in os.getenv("CRONOS_CORS_ORIGINS", "").split(",") if x.strip()),
            providers_file=Path(os.getenv("CRONOS_PROVIDERS_FILE", "config/providers.json")),
            context_messages=max(2, int(os.getenv("CRONOS_CONTEXT_MESSAGES", "40"))),
            context_chars=max(2000, int(os.getenv("CRONOS_CONTEXT_CHARS", "48000"))),
            memory_chars=max(0, int(os.getenv("CRONOS_MEMORY_CHARS", "16000"))),
            memory_results=max(1, int(os.getenv("CRONOS_MEMORY_RESULTS", "8"))),
            tool_rounds=max(1, int(os.getenv("CRONOS_TOOL_ROUNDS", "6"))),
            files_root=Path(os.getenv("CRONOS_FILES_ROOT") or str(Path.home() / "Downloads")).expanduser().resolve(),
            fish_speed=float(os.getenv("FISH_SPEED", "1.0")),
            transcription_provider=os.getenv("CRONOS_TRANSCRIPTION_PROVIDER", "fish").strip().lower(),
            fish_format=os.getenv("FISH_FORMAT", "mp3").strip().lower(),
            fish_latency=os.getenv("FISH_LATENCY", "balanced"),
            enable_plugins=os.getenv("CRONOS_ENABLE_PLUGINS", "0").casefold() in {"1", "true", "yes"},
            output_tokens=int(os.getenv("CRONOS_OUTPUT_TOKENS")) if os.getenv("CRONOS_OUTPUT_TOKENS") else None,
            provider_timeout=max(1, float(os.getenv("CRONOS_PROVIDER_TIMEOUT", "180"))),
            privacy_mode=os.getenv("CRONOS_PRIVACY_MODE", "online"),
            allow_executables=os.getenv("CRONOS_ALLOW_EXECUTABLES", "0").casefold() in {"1", "true", "yes"},
        )
