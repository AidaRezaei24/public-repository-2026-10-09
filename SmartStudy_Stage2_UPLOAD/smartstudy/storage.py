"""SQLite-backed persistence and repositories. All statements are parameterized."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .models import (Course, Task, StudySession, Commitment, ValidationError,
                     clean_title, checked_dt, validate_interval)

SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE COLLATE NOCASE, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES courses(id),
  title TEXT NOT NULL, due_at TEXT, effort_minutes INTEGER NOT NULL,
  remaining_minutes INTEGER NOT NULL, importance INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS commitments (
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, starts_at TEXT NOT NULL, ends_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  starts_at TEXT NOT NULL, ends_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reminders (
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  due_at TEXT NOT NULL, lead_hours INTEGER NOT NULL, sent_at TEXT NOT NULL,
  PRIMARY KEY(task_id, due_at, lead_hours));
CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL);
'''


class SQLiteRepository:
    def __init__(self, path='smartstudy.db'):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def add_course(self, code, name):
        code, name = clean_title(code).upper(), clean_title(name)
        with self.connect() as db:
            try:
                return db.execute('INSERT INTO courses(code,name) VALUES(?,?)', (code, name)).lastrowid
            except sqlite3.IntegrityError as exc:
                raise ValidationError(f'Course {code} already exists.') from exc

    def list_courses(self):
        with self.connect() as db:
            return [Course(**dict(row)) for row in db.execute('SELECT * FROM courses ORDER BY code')]

    def _ensure_course(self, db, course_id):
        if not db.execute('SELECT 1 FROM courses WHERE id=?', (course_id,)).fetchone():
            raise ValidationError(f'Unknown course ID: {course_id}')

    def add_task(self, course_id, title, due_at, effort_minutes=60, importance=3):
        title = clean_title(title)
        if due_at:
            checked_dt(due_at)
        if not isinstance(effort_minutes, int) or effort_minutes < 1 or effort_minutes > 30000:
            raise ValidationError('Effort must be between 1 and 30000 minutes.')
        if not isinstance(importance, int) or not 1 <= importance <= 5:
            raise ValidationError('Importance must be between 1 and 5.')
        with self.connect() as db:
            self._ensure_course(db, course_id)
            return db.execute('''INSERT INTO tasks(course_id,title,due_at,effort_minutes,
             remaining_minutes,importance) VALUES(?,?,?,?,?,?)''',
             (course_id, title, due_at, effort_minutes, effort_minutes, importance)).lastrowid

    def list_tasks(self, include_done=True):
        sql = '''SELECT t.*, c.code course_code FROM tasks t JOIN courses c ON c.id=t.course_id'''
        if not include_done:
            sql += " WHERE t.status='pending' AND t.remaining_minutes>0"
        sql += ' ORDER BY CASE WHEN t.due_at IS NULL THEN 1 ELSE 0 END, t.due_at, t.id'
        with self.connect() as db:
            return [Task(**dict(row)) for row in db.execute(sql)]

    def get_task(self, task_id):
        with self.connect() as db:
            row = db.execute('''SELECT t.*, c.code course_code FROM tasks t
               JOIN courses c ON c.id=t.course_id WHERE t.id=?''', (task_id,)).fetchone()
            if not row:
                raise ValidationError(f'Unknown task ID: {task_id}')
            return Task(**dict(row))

    def update_task(self, task_id, *, title=None, due_at='__unchanged__', importance=None):
        old = self.get_task(task_id)
        new_title = clean_title(title) if title is not None else old.title
        due = old.due_at if due_at == '__unchanged__' else (checked_dt(due_at) if due_at else None)
        rank = old.importance if importance is None else importance
        if not isinstance(rank, int) or not 1 <= rank <= 5:
            raise ValidationError('Importance must be between 1 and 5.')
        with self.connect() as db:
            db.execute('UPDATE tasks SET title=?, due_at=?, importance=? WHERE id=?',
                       (new_title, due, rank, task_id))

    def update_progress(self, task_id, remaining_minutes=None, complete=False):
        old = self.get_task(task_id)
        if complete:
            remaining_minutes = 0
        if remaining_minutes is None or not isinstance(remaining_minutes, int) or not 0 <= remaining_minutes <= old.effort_minutes:
            raise ValidationError(f'Remaining effort must be 0 through {old.effort_minutes}.')
        with self.connect() as db:
            db.execute('UPDATE tasks SET remaining_minutes=?, status=? WHERE id=?',
                       (remaining_minutes, 'done' if remaining_minutes == 0 else 'pending', task_id))

    def add_commitment(self, title, starts_at, ends_at):
        title = clean_title(title)
        validate_interval(starts_at, ends_at)
        with self.connect() as db:
            return db.execute('INSERT INTO commitments(title,starts_at,ends_at) VALUES(?,?,?)',
                              (title, starts_at, ends_at)).lastrowid

    def list_commitments(self):
        with self.connect() as db:
            return [Commitment(**dict(row)) for row in db.execute('SELECT * FROM commitments ORDER BY starts_at')]

    def list_sessions(self):
        with self.connect() as db:
            return [StudySession(**dict(row)) for row in db.execute('''SELECT s.*,t.title FROM sessions s
                         JOIN tasks t ON s.task_id=t.id ORDER BY s.starts_at, s.id''')]

    def save_sessions(self, session_specs, week_start=None):
        # Replace one week's sessions atomically; only invoked after explicit approval.
        with self.connect() as db:
            if week_start is not None:
                from datetime import timedelta
                from .models import parse_day
                first = parse_day(week_start).isoformat()
                last = (parse_day(week_start) + timedelta(days=7)).isoformat()
                db.execute('DELETE FROM sessions WHERE starts_at>=? AND starts_at<?', (first, last))
            for task_id, start, end in session_specs:
                validate_interval(start, end)
                db.execute('INSERT INTO sessions(task_id,starts_at,ends_at) VALUES(?,?,?)',
                           (task_id, start, end))

    def reminder_sent(self, task_id, due_at, lead_hours):
        with self.connect() as db:
            return bool(db.execute('''SELECT 1 FROM reminders WHERE task_id=? AND due_at=? AND lead_hours=?''',
                        (task_id, due_at, lead_hours)).fetchone())

    def mark_reminder(self, task_id, due_at, lead_hours, sent_at):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO reminders VALUES(?,?,?,?)',
                       (task_id, due_at, lead_hours, sent_at))

    def preference(self, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM preferences WHERE key=?', (key,)).fetchone()
            return row['value'] if row else default

    def set_preference(self, key, value):
        with self.connect() as db:
            db.execute('INSERT INTO preferences(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                       (key, str(value)))
