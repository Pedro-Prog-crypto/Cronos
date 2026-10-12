import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


def topic_filename(topic: str) -> str:
    normalized = unicodedata.normalize("NFKC", topic).casefold().strip()
    safe = re.sub(r"[^\w -]", "-", normalized).strip(" .-")[:70] or "tema"
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:10]
    return f"{safe}-{digest}.md"


def quoted(value: str) -> str:
    # Impede que conteúdo de conversa injete cabeçalhos/metadados da nota.
    return "\n".join("> " + line for line in value.splitlines())


class Memory:
    def __init__(self, vault: Path):
        self.vault = vault
        for folder in ("Conversas", "Temas", ".cronos"):
            (vault / folder).mkdir(parents=True, exist_ok=True)

    def path(self, folder: str, name: str) -> Path:
        path = self.vault / folder / name
        if not path.resolve().is_relative_to(self.vault.resolve()) or path.is_symlink():
            raise ValueError("Caminho de memória inválido.")
        return path

    def history(self, session: UUID) -> list[dict]:
        path = self.path(".cronos", f"{session}.json")
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    def recall(self, message: str) -> str:
        words = set(re.findall(r"\w{4,}", message.casefold()))
        matches = []
        for path in sorted((self.vault / "Temas").glob("*.md")):
            path = self.path("Temas", path.name)
            title = path.read_text(encoding="utf-8").splitlines()[0]
            if words.intersection(re.findall(r"\w{4,}", title.casefold())):
                matches.append(path.read_text(encoding="utf-8")[-6000:])
                if len(matches) == 3:
                    break
        return "\n\n".join(matches)

    def record(self, session: UUID, message: str, reply: str, topics: list[dict]):
        stamp = datetime.now(timezone.utc).isoformat()
        history = self.history(session)
        history.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
        state = self.path(".cronos", f"{session}.json")
        temp = state.with_suffix(".tmp")
        temp.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
        temp.replace(state)
        entry = f"\n## {stamp}\n\n### Você\n{quoted(message)}\n\n### Cronos — resposta de IA, não verificada\n{quoted(reply)}\n"
        conversation = self.path("Conversas", f"{session}.md")
        if not conversation.exists():
            conversation.write_text(f"# Conversa {session}\n", encoding="utf-8")
        with conversation.open("a", encoding="utf-8") as file:
            file.write(entry)
        files = []
        for topic in topics:
            title = topic["title"]
            path = self.path("Temas", topic_filename(title))
            if not path.exists():
                path.write_text(f"# {title.replace(chr(10), ' ').replace(chr(13), ' ')}\n\nRegistros de conversa; não são fatos automaticamente verificados.\n", encoding="utf-8")
            with path.open("a", encoding="utf-8") as file:
                file.write(f"\n## {stamp}\n\nOrigem: [[Conversas/{session}]]\n\nResumo produzido por IA, não verificado:\n{quoted(topic['summary'])}\n")
            files.append(f"Temas/{path.name}")
        return files
