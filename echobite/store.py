import sqlite3
from contextlib import contextmanager
import unicodedata
from pathlib import Path


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    for mark in ('’', '‘', 'ʻ', 'ʼ', '`', '´'):
        text = text.replace(mark, "'")
    return ' '.join(text.split())


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('''CREATE TABLE IF NOT EXISTS audios (
                id INTEGER PRIMARY KEY, job TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL, search TEXT NOT NULL, file_id TEXT NOT NULL,
                duration REAL NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

            columns = {r['name'] for r in db.execute('PRAGMA table_info(audios)')}
            if 'kind' not in columns:
                db.execute("ALTER TABLE audios ADD COLUMN kind TEXT NOT NULL DEFAULT 'audio'")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, job, title, file_id, duration):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO audios(job,title,search,file_id,duration,kind) VALUES(?,?,?,?,?,'voice')",
                       (job, title, normalize(title), file_id, duration))

    def search(self, query, offset=0, limit=21, voices_only=False):
        words = normalize(query).split()[:12]
        clauses = ['instr(search, ?) > 0' for _ in words]
        if voices_only:
            clauses.append("kind='voice'")
        sql = 'SELECT * FROM audios'
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY id DESC LIMIT ? OFFSET ?'
        with self.connect() as db:
            return [dict(r) for r in db.execute(sql, (*words, limit, offset))]

    def get(self, audio_id):
        if not 0 < audio_id < 2**63:
            return None
        with self.connect() as db:
            row = db.execute('SELECT * FROM audios WHERE id=?', (audio_id,)).fetchone()
            return dict(row) if row else None

    def delete(self, audio_id, job):
        with self.connect() as db:
            return db.execute('DELETE FROM audios WHERE id=? AND job=?', (audio_id, job)).rowcount

    def clear_all(self):
        with self.connect() as db:
            return db.execute('DELETE FROM audios').rowcount

    def count(self):
        with self.connect() as db:
            return db.execute('SELECT count(*) FROM audios').fetchone()[0]

    def legacy(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM audios WHERE kind='audio'")]

    def set_voice(self, audio_id, file_id):
        with self.connect() as db:
            db.execute("UPDATE audios SET file_id=?,kind='voice' WHERE id=?", (file_id, audio_id))
