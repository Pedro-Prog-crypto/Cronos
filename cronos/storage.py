"""Memória durável + projeções Markdown idempotentes para Obsidian."""
import hashlib
import json
import os
import re
import sqlite3
import threading
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
from cronos.security import safe_path
from cronos.memory_policy import knowledge_topics,graph_note,substantive_question


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text)).casefold()
                   if not unicodedata.combining(c))


def topic_filename(topic):
    normalized = unicodedata.normalize("NFKC", topic).casefold().strip()
    safe = re.sub(r"[^\w -]", "-", normalized).strip(" .-")[:70] or "tema"
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:10]
    return f"{safe}-{digest}.md"


def quoted(value):
    return "\n".join("> " + line for line in value.splitlines())


STOP_WORDS = set("a as o os de da das do dos e em na nas no nos um uma eu voce ele ela que quem qual como para por sobre foi era ser minha meu me se isso quero saber diga fale explique".split())


class Memory:
    def __init__(self, vault: Path):
        self.vault = vault.resolve()
        self.warnings = []
        self._index_lock = threading.RLock()
        self._export_lock = threading.RLock()
        for folder in ("Conversas", "Temas", "Memorias", ".cronos"):
            self.path(folder, "").mkdir(parents=True, exist_ok=True)
        self.database = self.path(".cronos", "memory.sqlite3")
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY, session TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, created TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS turns_session ON turns(session,id);
                CREATE TABLE IF NOT EXISTS topics (id INTEGER PRIMARY KEY, title TEXT NOT NULL, path TEXT UNIQUE NOT NULL);
                CREATE TABLE IF NOT EXISTS aliases (name TEXT PRIMARY KEY, topic INTEGER NOT NULL REFERENCES topics(id));
                CREATE TABLE IF NOT EXISTS exports (id INTEGER PRIMARY KEY, path TEXT NOT NULL, marker TEXT NOT NULL UNIQUE,
                    header TEXT NOT NULL, body TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS imports (path TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS tool_events (id INTEGER PRIMARY KEY, session TEXT NOT NULL,
                    payload TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS notes (path TEXT PRIMARY KEY, title TEXT NOT NULL, fingerprint TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS note_links (source TEXT NOT NULL, target TEXT NOT NULL, PRIMARY KEY(source,target));
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(path UNINDEXED,title,body, tokenize='unicode61 remove_diacritics 2');
            ''')
        self._import_json_sessions()
        self.flush_exports()
        try:
            self.sync_notes()
        except (OSError, ValueError):
            self.warnings.append("Indexação pendente: verifique arquivos, permissões e links no vault.")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def path(self, folder, name):
        relative = (Path(folder) / name).as_posix()
        return safe_path(self.vault, relative, private=True)

    def _import_json_sessions(self):
        # Compatibilidade com a primeira base, sem apagar os arquivos originais.
        for file in (self.vault / ".cronos").glob("*.json"):
            try:
                session = str(UUID(file.stem))
            except ValueError:
                continue
            with self.connect() as db:
                if db.execute("SELECT 1 FROM imports WHERE path=?", (file.name,)).fetchone():
                    continue
                data = json.loads(self.path(".cronos", file.name).read_text(encoding="utf-8-sig"))
                if not isinstance(data, list) or any(not isinstance(m, dict) or m.get("role") not in {"user", "assistant"}
                                                   or not isinstance(m.get("content"), str) for m in data):
                    raise ValueError("Histórico antigo inválido; arquivo original preservado.")
                stamp = datetime.now(timezone.utc).isoformat()
                db.executemany("INSERT INTO turns(session,role,content,created) VALUES(?,?,?,?)",
                               [(session, m["role"], m["content"], stamp) for m in data])
                db.execute("INSERT INTO imports(path) VALUES(?)", (file.name,))

    def history(self, session: UUID, limit=None):
        with self.connect() as db:
            if limit is None:
                rows = db.execute("SELECT role,content FROM turns WHERE session=? ORDER BY id", (str(session),)).fetchall()
            else:
                rows = list(reversed(db.execute("SELECT role,content FROM turns WHERE session=? ORDER BY id DESC LIMIT ?",
                                                (str(session), max(0, limit))).fetchall()))
        return [dict(row) for row in rows]

    def _markdown_files(self):
        for directory, folders, filenames in os.walk(self.vault, followlinks=False):
            folders[:] = [f for f in folders if not f.startswith(".") and not (Path(directory)==self.vault and f=='Conversas')]
            for folder in folders:
                candidate = Path(directory) / folder
                if candidate.is_symlink():
                    raise ValueError("Link simbólico no vault; revisão necessária antes de indexar.")
            for name in filenames:
                if name.lower().endswith(".md"):
                    path = Path(directory) / name
                    self.path("", path.relative_to(self.vault).as_posix())
                    yield path

    def sync_notes(self):
        # Indexing is independent of the conversation queue. Commit each note
        # separately so a large vault does not hold a database write lock.
        with self._index_lock:
            self._sync_notes()

    def _sync_notes(self):
        found = set()
        with self.connect() as db:
            for path in self._markdown_files():
                relative = path.relative_to(self.vault).as_posix()
                found.add(relative)
                stat = path.stat()
                fingerprint = f"chunks3:{stat.st_mtime_ns}:{stat.st_size}"
                previous = db.execute("SELECT fingerprint FROM notes WHERE path=?", (relative,)).fetchone()
                if previous and previous[0] == fingerprint:
                    continue
                content = path.read_text(encoding="utf-8-sig")
                title = next((line.lstrip("# ").strip() for line in content.splitlines() if line.startswith("# ")), path.stem)
                aliases = [row[0] for row in db.execute("SELECT a.name FROM aliases a JOIN topics t ON a.topic=t.id WHERE t.path=?", (relative,))]
                indexed = re.sub(r"<!--.*?-->", "", content, flags=re.S)
                indexed = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", indexed, count=1, flags=re.S)
                db.execute("DELETE FROM note_links WHERE source=?", (relative,))
                db.executemany("INSERT OR IGNORE INTO note_links(source,target) VALUES(?,?)", [(relative, link.split("|",1)[0].split("#",1)[0].strip()) for link in re.findall(r"\[\[([^\]]+)\]\]", content) if link.split("|",1)[0].split("#",1)[0].strip()])
                db.execute("DELETE FROM notes_fts WHERE path=?", (relative,))
                chunks = []
                sections = re.split(r"(?m)(?=^## )", indexed)
                preface = sections.pop(0) if len(sections) > 1 and not sections[0].startswith("## ") else ""
                for section in sections:
                    heading = section.splitlines()[0] if section.startswith("## ") else ""
                    for start in range(0, len(section), 3700):
                        chunk = section[start:start + 4000]
                        chunks.append((relative, title, preface + (heading + "\n" if start else "") + chunk + "\n" + " ".join(aliases)))
                db.executemany("INSERT INTO notes_fts(path,title,body) VALUES(?,?,?)", chunks or [(relative, title, indexed)])
                db.execute("INSERT OR REPLACE INTO notes(path,title,fingerprint) VALUES(?,?,?)", (relative, title, fingerprint))
                if path.parent == self.vault / "Temas" or path.parent.relative_to(self.vault).as_posix().casefold() == "cronos/temas":
                    db.execute("INSERT OR IGNORE INTO topics(title,path) VALUES(?,?)", (title, relative))
                    topic = db.execute("SELECT id FROM topics WHERE path=?", (relative,)).fetchone()[0]
                    db.execute("INSERT OR IGNORE INTO aliases(name,topic) VALUES(?,?)", (fold(title.strip()), topic))
                db.commit()
            for row in db.execute("SELECT path FROM notes").fetchall():
                if row[0] not in found:
                    db.execute("DELETE FROM notes WHERE path=?", (row[0],))
                    db.execute("DELETE FROM notes_fts WHERE path=?", (row[0],))

    def graph(self, offset=0, limit=600):
        with self.connect() as db:
            all_notes = db.execute("SELECT path,title FROM notes ORDER BY path").fetchall()
            all_notes = [row for row in all_notes if graph_note(row['path'],row['title'])]
            rows = all_notes[offset:offset+limit]
            lookup = {}
            for note in all_notes:
                for alias in (note['path'], note['path'][:-3], Path(note['path']).stem, note['title']):
                    lookup.setdefault(fold(alias), []).append(note['path'])
            visible = {row["path"] for row in rows}
            valid = {row["path"] for row in all_notes}
            edges = set()
            for link in db.execute("SELECT source,target FROM note_links"):
                matches = list(dict.fromkeys(lookup.get(fold(link['target']), [])))
                if link['source'] in valid and len(matches) == 1 and matches[0] != link['source']:
                    edges.add(tuple(sorted((link['source'], matches[0]))))
            return {"nodes": [dict(row) for row in rows],
                    "edges": [{"source": a, "target": b} for a,b in sorted(edges) if a in visible or b in visible],
                    "total": len(all_notes), "next_offset": offset + len(rows) if offset + len(rows) < len(all_notes) else None}

    def search(self, query, limit=8, *, refresh=True):
        if refresh:
            self.sync_notes()
        terms = list(dict.fromkeys(w for w in re.findall(r"\w+", fold(query)) if len(w) > 1 and w not in STOP_WORDS))
        if not terms:
            return []
        expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        with self.connect() as db:
            rows = db.execute("""SELECT rowid AS chunk_id,path,title,body AS excerpt
                FROM notes_fts WHERE notes_fts MATCH ? ORDER BY bm25(notes_fts,0,4,1),rowid DESC LIMIT ?""",
                              (expression, max(1, min(limit, 100)) * 20)).fetchall()
        results = {}
        for row in rows:
            if row['path'] not in results:
                if len(results) == limit:
                    continue
                results[row['path']] = []
            results[row['path']].append(dict(row))
        output = []
        for path, matches in results.items():
            recent = sorted(matches, key=lambda row: row['chunk_id'], reverse=True)[:2]
            if matches[0]['chunk_id'] not in {row['chunk_id'] for row in recent}:
                recent.append(matches[0])
            output.append({'path': path, 'title': matches[0]['title'],
                           'excerpt': '\n\n'.join(row['excerpt'] for row in recent)})
        return output

    def recall(self, message, limit=8, budget=16000, *, refresh=True):
        parts, remaining = [], max(0, budget)
        for note in self.search(message, limit, refresh=refresh):
            excerpt = f"[{note['path']}] {note['title']}\n{note['excerpt']}"
            if remaining <= 0:
                break
            parts.append(excerpt[:remaining])
            remaining -= len(parts[-1])
        return "\n\n".join(parts)

    def read_note(self, relative):
        if not relative.lower().endswith(".md") or any(part.startswith(".") for part in Path(relative).parts):
            raise ValueError("Informe o caminho relativo de uma nota Markdown pública do vault.")
        return safe_path(self.vault, relative).read_text(encoding="utf-8-sig")

    def _topic(self, db, title, aliases):
        title = " ".join(title.split())
        names = list(dict.fromkeys(fold(n.strip()) for n in [title, *aliases] if n.strip()))
        matches = {r[0] for name in names for r in db.execute("SELECT topic FROM aliases WHERE name=?", (name,))}
        if len(matches) > 1:
            # Um alias ambíguo não autoriza fundir/apagar duas notas existentes.
            row = db.execute("SELECT topic FROM aliases WHERE name=?", (names[0],)).fetchone()
            matches = {row[0]} if row else set()
        if matches:
            topic = matches.pop()
        else:
            path = "Temas/" + topic_filename(title)
            db.execute("INSERT OR IGNORE INTO topics(title,path) VALUES(?,?)", (title, path))
            topic = db.execute("SELECT id FROM topics WHERE path=?", (path,)).fetchone()[0]
        for name in names:
            db.execute("INSERT OR IGNORE INTO aliases(name,topic) VALUES(?,?)", (name, topic))
        return db.execute("SELECT title,path FROM topics WHERE id=?", (topic,)).fetchone()

    def record(self, session, message, reply, topics):
        topics=knowledge_topics(message,topics)
        stamp = datetime.now(timezone.utc).isoformat()
        event = str(uuid4())
        conversation = f"Conversas/{session}.md"
        files = []
        with self.connect() as db:
            db.executemany("INSERT INTO turns(session,role,content,created) VALUES(?,?,?,?)",
                           [(str(session), "user", message, stamp), (str(session), "assistant", reply, stamp)])
            body = f"\n## {stamp}\n\n### Você\n{quoted(message)}\n\n### Cronos — resposta de IA, não verificada\n{quoted(reply)}\n"
            if getattr(self, 'save_diary', True):
                db.execute("INSERT INTO exports(path,marker,header,body) VALUES(?,?,?,?)",
                           (conversation, event, f"# Conversa {session}\n", body))
            seen = set()
            for topic in topics:
                target = self._topic(db, topic["title"], topic.get("aliases", []))
                if target["path"] in seen:
                    continue
                seen.add(target["path"])
                files.append(target["path"])
                related = [f"[[{self._topic(db,t['title'],t.get('aliases',[]))['path'][:-3]}]]" for t in topics if t is not topic]
                body = f"\n## {stamp}\n\nOrigem: [[Conversas/{session}]]\n\nResumo produzido por IA, não verificado:\n{quoted(topic['summary'])}\n"
                if related:
                    body += "\nRelacionadas: " + " · ".join(dict.fromkeys(related)) + "\n"
                aliases = json.dumps(topic.get('aliases',[]),ensure_ascii=False)
                header = f"---\ntype: cronos-topic\ntitle: {json.dumps(target['title'],ensure_ascii=False)}\naliases: {aliases}\n---\n\n# {target['title']}\n\nRegistros de conversa; não são fatos automaticamente verificados.\n"
                db.execute("INSERT INTO exports(path,marker,header,body) VALUES(?,?,?,?)",
                           (target["path"], event + ":" + target["path"], header, body))
                index_body = f"- [[{target['path'][:-3]}|{target['title'].replace(']', '').replace('|', '-')}]]\n"
                db.execute("INSERT OR IGNORE INTO exports(path,marker,header,body) VALUES(?,?,?,?)",
                           ("Mapa de Conhecimento.md", "index:" + target["path"], "# Mapa de Conhecimento\n\n", index_body))
            if topics or substantive_question(message):
                knowledge = f"Memorias/{event}.md"
                links = " · ".join(f"[[{path[:-3]}]]" for path in files)
                db.execute("INSERT INTO exports(path,marker,header,body) VALUES(?,?,?,?)",
                           (knowledge, event + ':memory', f"# {message[:100].replace(chr(10), ' ')}\n",
                            f"\nCriada: {stamp}\n\nOrigem: [[Conversas/{session}]]\n\nTemas: {links}\n\n### Você\n{quoted(message)}\n\n### Resposta de IA, não verificada\n{quoted(reply)}\n"))
                if not topics:files.append(knowledge)
        self.flush_exports()
        try:
            if topics or substantive_question(message):
                self.sync_notes()
        except (OSError, ValueError):
            self.warnings.append("Conversa salva; indexação pendente. Verifique arquivos, permissões e links no vault.")
        return files

    def flush_exports(self):
        with self._export_lock:
            self._flush_exports()

    def _flush_exports(self):
        self.warnings = []
        with self.connect() as db:
            rows = db.execute("SELECT * FROM exports WHERE done=0 ORDER BY id").fetchall()
            for row in rows:
                try:
                    path = self.path("", row["path"])
                    existing = path.read_text(encoding="utf-8") if path.exists() else row["header"]
                    marker = f"<!-- cronos:{row['marker']} -->"
                    if marker not in existing:
                        temporary = self.path("", row["path"] + ".cronos-tmp")
                        temporary.write_text(existing + "\n" + marker + "\n" + row["body"], encoding="utf-8")
                        os.replace(temporary, path)
                    db.execute("UPDATE exports SET done=1 WHERE id=?", (row["id"],))
                except (OSError, ValueError):
                    self.warnings.append(f"Conversa salva; exportação pendente para {row['path']}. Tente sincronizar novamente.")

    def stats(self):
        with self.connect() as db:
            return {"messages": db.execute("SELECT count(*) FROM turns").fetchone()[0],
                    "indexed_notes": db.execute("SELECT count(*) FROM notes").fetchone()[0],
                    "pending_exports": db.execute("SELECT count(*) FROM exports WHERE done=0").fetchone()[0]}

    def log_tool(self, session, result):
        with self.connect() as db:
            db.execute("INSERT INTO tool_events(session,payload,created) VALUES(?,?,?)",
                       (str(session), json.dumps(result, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))

    def tool_history(self, session, limit=30):
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM tool_events WHERE session=? ORDER BY id DESC LIMIT ?",
                              (str(session), limit)).fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def tool_history_any(self):
        with self.connect() as db:
            row = db.execute('SELECT payload,created FROM tool_events ORDER BY id DESC LIMIT 1').fetchone()
        return {**json.loads(row['payload']), 'time':row['created']} if row else None
