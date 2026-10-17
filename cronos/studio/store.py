import json
import sqlite3
import time
from contextlib import contextmanager
from uuid import UUID, uuid4

from cronos.security import safe_path


class Store:
    def __init__(self, vault):
        self.root = safe_path(vault, '.cronos/studio', private=True)
        self.root.mkdir(parents=True, exist_ok=True)
        self.dbpath = safe_path(self.root, 'projects.sqlite3', private=True)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,payload TEXT NOT NULL,updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS generation_drafts(project TEXT PRIMARY KEY,request_key TEXT NOT NULL,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS revisions(project TEXT,revision INTEGER,files TEXT NOT NULL,summary TEXT NOT NULL,report TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(project,revision));''')
        with self.connect() as db:
            if 'archived' not in {row[1] for row in db.execute('PRAGMA table_info(projects)')}:
                db.execute('ALTER TABLE projects ADD COLUMN archived INTEGER NOT NULL DEFAULT 0')
        # A server restart never pretends a paid request is still running or retries it.
        for project in self.list():
            if project['status'] in {'running', 'queued'}:
                value = self.get(project['id']); value['status'] = 'interrupted'; value['finished'] = time.time()
                self.event(value, 'interrupted', 'O Cronos foi reiniciado. Nenhuma chamada foi repetida; a última versão foi preservada.')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.dbpath, timeout=10)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            with db:
                yield db
        finally:
            db.close()

    def get(self, identifier):
        try:
            if str(UUID(identifier)) != identifier: raise ValueError()
        except (ValueError, TypeError): raise KeyError(identifier) from None
        with self.connect() as db:
            row = db.execute('SELECT payload FROM projects WHERE id=?', (identifier,)).fetchone()
        if not row: raise KeyError(identifier)
        return json.loads(row[0])

    def list(self, archived=False):
        with self.connect() as db:
            rows = db.execute('SELECT payload FROM projects WHERE archived=? ORDER BY updated DESC LIMIT 80', (int(archived),)).fetchall()
        return [{k: v for k, v in json.loads(row[0]).items() if k not in {'events', 'brief', 'reference', 'assets', 'screen_reviews'}} for row in rows]

    def save(self, project):
        project['updated'] = time.time()
        with self.connect() as db:
            db.execute('INSERT INTO projects(id,payload,updated,archived) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated,archived=excluded.archived',
                       (project['id'], json.dumps(project, ensure_ascii=False), project['updated'], int(project.get('archived', False))))

    def new(self, data):
        if len(self.list()) >= 80: raise ValueError('Limite de 80 projetos. Exporte e arquive projetos antes de criar outros.')
        project = {**data, 'id': str(uuid4()), 'revision': 0, 'status': 'draft', 'archived': False, 'events': [], 'assets': [], 'started': None, 'finished': None, 'created': time.time()}
        self.save(project)
        return project

    def event(self, project, phase, text):
        project['events'] = [*project['events'][-119:], {'at': time.time(), 'phase': phase, 'text': text[:2000]}]
        self.save(project)

    def revision(self, project, number=None):
        with self.connect() as db:
            row = db.execute('SELECT files,summary,report,created FROM revisions WHERE project=? AND revision=?',
                             (project['id'], number if number is not None else project['revision'])).fetchone()
        if not row: raise KeyError('revision')
        return {'files': json.loads(row[0]), 'summary': row[1], 'report': json.loads(row[2]), 'created': row[3]}

    def history(self, project):
        with self.connect() as db:
            return [{'revision': r[0], 'summary': r[1], 'created': r[2]} for r in db.execute('SELECT revision,summary,created FROM revisions WHERE project=? ORDER BY revision DESC', (project['id'],)).fetchall()]

    def commit(self, project, files, summary, report):
        # A revision and the pointer move together in one transaction. Failed edits never replace files.
        with self.connect() as db:
            latest = db.execute('SELECT MAX(revision) FROM revisions WHERE project=?', (project['id'],)).fetchone()[0]
            number = 0 if latest is None else latest + 1
            if number >= 40: raise ValueError('Este projeto já tem 40 versões. Duplique-o para continuar; o histórico foi preservado.')
            project['revision'] = number; project['updated'] = time.time()
            project['browser_reports'] = []
            db.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?)', (project['id'], number, json.dumps(files, ensure_ascii=False), summary,
                        json.dumps(report, ensure_ascii=False), project['updated']))
            db.execute('UPDATE projects SET payload=?,updated=? WHERE id=?', (json.dumps(project, ensure_ascii=False), project['updated'], project['id']))

    def directory(self, project):
        path = safe_path(self.root, project['id'], private=True)
        path.mkdir(exist_ok=True)
        return path

    def asset_path(self, project, name):
        return safe_path(self.directory(project), name, private=True)

    def generation_draft(self,project,key):
        with self.connect() as db:
            row=db.execute('SELECT payload FROM generation_drafts WHERE project=? AND request_key=?',(project['id'],key)).fetchone()
        return json.loads(row[0]) if row else None

    def save_generation_draft(self,project,key,raw,segments,request_payload=None):
        if len(raw)>700_000:raise ValueError('Entrega parcial acima do limite permitido.')
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO generation_drafts VALUES(?,?,?)',(project['id'],key,json.dumps({'raw':raw,'segments':segments,'request_payload':request_payload},ensure_ascii=True)))

    def clear_generation_draft(self,project):
        with self.connect() as db:db.execute('DELETE FROM generation_drafts WHERE project=?',(project['id'],))
