"""Facade/controller + Observer event system + application services."""
import csv
from datetime import datetime, timedelta
from pathlib import Path
import os
from .models import ValidationError, parse_dt
from .storage import SQLiteRepository
from .planning import (PriorityEngine, DeadlinePriorityStrategy, BalancedPriorityStrategy,
                       ConflictChecker, SchedulePlanner)
from .ai import OpenAILLMAdapter, DeadlineExtractor, IntentInterpreter, ExplanationService, AIUnavailable
from .commands import ToolManager


class TaskEventPublisher:
    """Observer subject: listeners can react without TaskManager knowing their identities."""
    def __init__(self):
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    def notify(self, event, task_id):
        for listener in self.listeners:
            listener.on_task_change(event, task_id)


class CalendarRefreshListener:
    def __init__(self):
        self.change_counter = 0

    def on_task_change(self, event, task_id):
        self.change_counter += 1


class ReminderScheduler:
    def __init__(self, store):
        self.store = store
        self.should_check = False

    def on_task_change(self, event, task_id):
        self.should_check = True

    def check_deadlines(self, now=None, deliver=None):
        """Deliver in-app alerts, recording successful deliveries only.

        Optional deliver(message) is called before recording; a callback returning
        False or raising an exception leaves the reminder pending for retry.
        If no callback is supplied, returning the messages counts as in-app delivery.
        """
        now = now or datetime.now()
        lead = int(self.store.preference('reminder_lead_hours', '48'))
        if self.store.preference('reminders_enabled', '1') != '1':
            return []
        due_tasks = []
        for t in self.store.list_tasks(False):
            if not t.due_at:
                continue
            due = parse_dt(t.due_at)
            if now <= due <= now + timedelta(hours=lead) and not self.store.reminder_sent(t.id, t.due_at, lead):
                message = f'[{t.id}] {t.course_code} {t.title} is due {t.due_at}'
                try:
                    accepted = True if deliver is None else deliver(message)
                    if accepted is False:
                        continue
                except Exception:
                    continue  # Retry on the next notification check.
                due_tasks.append(message)
                self.store.mark_reminder(t.id, t.due_at, lead, now.strftime('%Y-%m-%d %H:%M'))
        self.should_check = False
        return due_tasks


class DocumentProcessor:
    def __init__(self, extractor):
        self.extractor = extractor

    def import_pdf(self, filename):
        try:
            import fitz
        except ImportError as exc:
            raise ValidationError('Install PyMuPDF: pip install -r requirements.txt') from exc
        path = Path(filename)
        if not path.is_file() or path.suffix.lower() != '.pdf':
            raise ValidationError('Select an existing .pdf file.')
        try:
            with fitz.open(path) as doc:
                if len(doc) > 80:
                    raise ValidationError('PDF exceeds the 80-page import limit.')
                text = '\n'.join(p.get_text() for p in doc)
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError('PDF could not be read.') from exc
        if len(text.strip()) < 30:
            raise ValidationError('PDF contains little selectable text. Scanned PDFs require manual entry.')
        return self.extractor.extract(text, origin=path.name)


class AgentController:
    """Facade shared by CLI and GUI; no business logic is duplicated across frontends."""
    def __init__(self, store, llm=None):
        self.store = store
        self.llm = llm or OpenAILLMAdapter()
        self.priority = PriorityEngine(DeadlinePriorityStrategy())
        self.checker = ConflictChecker()
        self.planner = SchedulePlanner(self.checker, self.priority)
        self.extractor = DeadlineExtractor(self.llm)
        self.documents = DocumentProcessor(self.extractor)
        self.intents = IntentInterpreter(self.llm)
        self.explanations = ExplanationService(self.llm)
        self.tools = ToolManager()
        self.events = TaskEventPublisher()
        self.refresh = CalendarRefreshListener()
        self.reminders = ReminderScheduler(store)
        self.events.subscribe(self.refresh)
        self.events.subscribe(self.reminders)

    def add_course(self, code, name):
        return self.store.add_course(code, name)

    def add_task(self, course_id, title, due_at, effort=60, importance=3):
        task_id = self.store.add_task(int(course_id), title, due_at, int(effort), int(importance))
        self.events.notify('created', task_id)
        return task_id

    def edit_task(self, task_id, *, title=None, due_at='__unchanged__', importance=None):
        self.store.update_task(int(task_id), title=title, due_at=due_at, importance=importance)
        self.events.notify('updated', int(task_id))

    def progress(self, task_id, remaining=None, complete=False):
        self.store.update_progress(int(task_id), remaining_minutes=remaining, complete=complete)
        self.events.notify('progress', int(task_id))

    def add_commitment(self, title, starts_at, ends_at):
        return self.store.add_commitment(title, starts_at, ends_at)

    def set_strategy(self, mode):
        if mode == 'deadline':
            self.priority.strategy = DeadlinePriorityStrategy()
        elif mode == 'balanced':
            self.priority.strategy = BalancedPriorityStrategy()
        else:
            raise ValidationError('Strategy must be deadline or balanced.')
        self.store.set_preference('priority_strategy', mode)

    def ranked_tasks(self):
        return self.priority.rank_tasks(self.store.list_tasks(False))

    def preview(self, week_start):
        start = int(self.store.preference('study_start_hour', '9'))
        end = int(self.store.preference('study_end_hour', '21'))
        return self.planner.generate(week_start, self.store.list_tasks(False),
                                     self.store.list_commitments(), day_start=start, day_end=end)

    def set_availability(self, start_hour, end_hour):
        start_hour, end_hour = int(start_hour), int(end_hour)
        if not (0 <= start_hour < end_hour <= 24):
            raise ValidationError('Availability must satisfy 0 <= start hour < end hour <= 24.')
        self.store.set_preference('study_start_hour', start_hour)
        self.store.set_preference('study_end_hour', end_hour)

    def approve(self, proposal, replan=False):
        if proposal.conflicts:
            raise ValidationError('Cannot approve a proposal containing conflicts.')
        if replan and proposal.unscheduled:
            raise ValidationError('Replan cannot fit all outstanding effort. Original plan preserved.')
        # Revalidate with fresh committed work and current state before saving.
        tasks = {t.id: t for t in self.store.list_tasks(False)}
        for task_id, title, start, end in proposal.sessions:
            if task_id not in tasks:
                raise ValidationError('Task changed since proposal was created; preview again.')
            if tasks[task_id].due_at and parse_dt(end) > parse_dt(tasks[task_id].due_at):
                raise ValidationError('A due date changed; preview again.')
        conflicts = self.checker.validate(proposal.sessions, self.store.list_commitments(),
                                          {t.id: t.due_at for t in tasks.values() if t.due_at})
        if conflicts:
            raise ValidationError('Conflicts appeared after preview. Please preview again.')
        self.store.save_sessions([(tid, s, e) for tid, _, s, e in proposal.sessions], proposal.week_start)
        return len(proposal.sessions)

    def extract_notes(self, text):
        return self.extractor.extract(text, 'pasted announcement')

    def import_outline(self, filename):
        return self.documents.import_pdf(filename)

    def confirm_draft(self, course_id, draft, corrected_due=None):
        due = corrected_due if corrected_due is not None else draft.due_at
        if not due:
            raise ValidationError('Confirm a complete, unambiguous date before saving the imported task.')
        return self.add_task(course_id, draft.title, due, draft.effort_minutes, draft.importance)

    def explain_plan(self, proposal):
        return self.explanations.explain(proposal)

    def handle_request(self, request):
        if not request.strip():
            raise ValidationError('Enter a question or request.')
        intent = self.intents.interpret(request)
        return f'Agent selected tool: {intent["tool"]}\n' + self.tools.execute_tool(self, intent)

    def export_csv(self, file_path, sessions=None):
        if sessions is None:
            rows = [(s.task_id, s.title, s.starts_at, s.ends_at) for s in self.store.list_sessions()]
        else:
            rows = sessions
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['task_id', 'title', 'starts_at', 'ends_at'])
            writer.writerows(rows)
        return str(file_path)

    def settings(self, *, reminders_enabled=None, lead_hours=None):
        if reminders_enabled is not None:
            self.store.set_preference('reminders_enabled', '1' if reminders_enabled else '0')
        if lead_hours is not None:
            lead_hours = int(lead_hours)
            if not 1 <= lead_hours <= 720:
                raise ValidationError('Lead hours must be between 1 and 720.')
            self.store.set_preference('reminder_lead_hours', str(lead_hours))


def load_local_env(filename='.env'):
    """Load a local file without overriding existing environment values."""
    path = Path(filename)
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        key = key.strip()
        if key in ('OPENAI_API_KEY', 'OPENAI_MODEL', 'OPENAI_ENDPOINT'):
            os.environ.setdefault(key, value.strip().strip('"\''))


def create_app(db_path=None, llm=None):
    root = Path(__file__).resolve().parent.parent
    load_local_env(root / '.env')
    path = db_path or os.getenv('SMARTSTUDY_DB', str(root / 'smartstudy.db'))
    app = AgentController(SQLiteRepository(path), llm=llm)
    strategy = app.store.preference('priority_strategy', 'deadline')
    app.set_strategy(strategy if strategy in ('deadline', 'balanced') else 'deadline')
    return app
