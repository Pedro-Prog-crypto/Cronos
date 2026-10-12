"""Migração explícita de configurações locais; nunca imprime credenciais."""
import argparse
import json
import os
import tempfile
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from dotenv import dotenv_values, set_key

from cronos.memory import Memory


def read_json(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Configuração antiga precisa ser um objeto JSON.")
    return data


def prepare(source):
    api = read_json(source / "config/api_keys.json")
    fish = read_json(source / "config/fish_audio.json")
    storage = read_json(source / "config/storage.json")
    council = read_json(source / "config/ai_council.json")
    values = {
        "GEMINI_API_KEY": api.get("gemini_api_key", ""),
        "FISH_API_KEY": fish.get("api_key", ""),
        "FISH_REFERENCE_ID": fish.get("reference_id", ""),
        "FISH_MODEL": fish.get("model", ""),
        "FISH_SPEED": fish.get("speed", ""),
        "FISH_LATENCY": fish.get("latency", ""),
        "CRONOS_VAULT": storage.get("obsidian_vault", api.get("obsidian_vault", "")),
    }
    keys = council.get("keys") or {}
    if not isinstance(keys, dict):
        raise ValueError("O campo keys da configuração antiga precisa ser um objeto.")
    for provider, variable in {"openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY", "cerebras": "CEREBRAS_API_KEY",
                               "openrouter": "OPENROUTER_API_KEY", "mistral": "MISTRAL_API_KEY", "nvidia": "NVIDIA_API_KEY"}.items():
        values[variable] = keys.get(provider, "")
    values = {key: str(value).strip() for key, value in values.items() if value is not None and str(value).strip()}
    for key in ("GEMINI_API_KEY", "FISH_API_KEY"):
        if key in values:
            values[key] = values[key].removeprefix("Bearer ").strip()
    if values.get("CRONOS_VAULT"):
        path = Path(values["CRONOS_VAULT"]).expanduser()
        values["CRONOS_VAULT"] = str(path.resolve() if path.is_absolute() else (source / path).resolve())
    raw = storage.get("realtime_memory_path")
    facts = Path(raw).expanduser() if raw else source / "memory/long_term.json"
    if raw and not facts.is_absolute():
        facts = source / facts
    return values, facts


def apply_env(destination, values, overrides=()):
    current = dotenv_values(destination) if destination.exists() else {}
    additions = {name: value for name, value in values.items() if name in overrides or (not current.get(name) and not os.getenv(name))}
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="cronos-env-", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        temporary.write_bytes(destination.read_bytes() if destination.exists() else b"")
        for name, value in additions.items():
            set_key(temporary, name, value)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return list(additions)


def import_facts(memory, source):
    facts = read_json(source)
    content = []
    for category, entries in facts.items():
        if isinstance(entries, dict):
            for name, entry in entries.items():
                value = entry.get("value") if isinstance(entry, dict) else entry
                if value is not None:
                    content.append(f"{category}/{name}: {value}")
    if not content:
        return 0
    digest = __import__("hashlib").sha256(source.read_bytes()).hexdigest()
    session = uuid5(NAMESPACE_URL, "cronos-import:" + str(source.resolve()) + ":" + digest)
    if memory.history(session):
        return 0
    text = "\n".join(content)
    memory.record(session, "Importação de relatos armazenados no Cronos anterior; preservar como relatos, não como fatos verificados.",
                  text, [{"title": "Memória importada do Cronos anterior", "summary": text}])
    return len(content)


def main():
    parser = argparse.ArgumentParser(description="Importar dados do Cronos anterior sem executar código antigo")
    parser.add_argument("source", type=Path, help="Pasta extraída do Cronos anterior")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--apply", action="store_true", help="Aplicar a migração; sem este argumento apenas diagnostica")
    args = parser.parse_args()
    try:
        source = args.source.resolve()
        if not source.is_dir():
            raise ValueError("Pasta antiga não encontrada.")
        values, facts = prepare(source)
        print("Configurações encontradas (nomes somente):", ", ".join(sorted(values)) or "nenhuma")
        print("Arquivo de memória antigo:", "presente" if facts.exists() else "ausente")
        if not args.apply:
            print("Prévia concluída. Nada foi alterado. Use --apply para importar; --vault escolhe o vault de destino.")
            return
        if args.vault:
            values["CRONOS_VAULT"] = str(args.vault.resolve())
        added = apply_env(args.env, values, {"CRONOS_VAULT"} if args.vault else ())
        current = dotenv_values(args.env)
        vault = args.vault or Path(current.get("CRONOS_VAULT") or values.get("CRONOS_VAULT") or "vault")
        count = import_facts(Memory(vault.resolve()), facts) if facts.exists() else 0
        print("Variáveis importadas (credenciais existentes preservadas):", ", ".join(added) or "nenhuma")
        print("Relatos importados:", count)
        print("Originais preservados. A interface e os prompts antigos não foram importados.")
    except (ValueError, OSError, TypeError) as exc:
        print("Migração interrompida; verifique caminhos e formatos dos arquivos. Credenciais não serão exibidas.")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
