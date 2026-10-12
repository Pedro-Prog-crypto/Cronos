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

    @classmethod
    def from_env(cls):
        return cls(
            vault=Path(os.getenv("CRONOS_VAULT", "vault")).expanduser().resolve(),
            personality=Path(os.getenv("CRONOS_PERSONALITY", "modelos/personalidades/cronos.md")),
            token=os.getenv("CRONOS_API_TOKEN", ""),
            provider=os.getenv("CRONOS_PROVIDER", "gemini"),
            gemini_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            fish_key=os.getenv("FISH_API_KEY", ""),
            fish_reference=os.getenv("FISH_REFERENCE_ID", ""),
            fish_model=os.getenv("FISH_MODEL", "s2-pro"),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
            origins=tuple(x.strip() for x in os.getenv("CRONOS_CORS_ORIGINS", "").split(",") if x.strip()),
        )
