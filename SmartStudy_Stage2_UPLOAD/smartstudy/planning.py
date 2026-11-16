"""Strategy-pattern priority scoring and a deterministic, conflict-checked scheduler."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from .models import parse_dt, parse_day, overlaps, ValidationError, DT_FMT


class IPriorityStrategy(ABC):
    @abstractmethod
    def score(self, task, now):
        """Higher is more urgent; unspecified deadlines get no fabricated urgency."""


class DeadlinePriorityStrategy(IPriorityStrategy):
    def score(self, task, now):
        if not task.due_at:
            return None
        days = max(0.0, (parse_dt(task.due_at) - now).total_seconds() / 86400)
        return round(100 / (1 + days) + task.importance * 8 + min(task.remaining_minutes / 60, 10), 2)


class BalancedPriorityStrategy(IPriorityStrategy):
    def score(self, task, now):
        if not task.due_at:
            return None
        days = max(0.0, (parse_dt(task.due_at) - now).total_seconds() / 86400)
        return round(55 / (1 + days) + task.importance * 14 + min(task.remaining_minutes / 60, 10) * 2, 2)


class PriorityEngine:
    def __init__(self, strategy=None):
        self.strategy = strategy or DeadlinePriorityStrategy()

    def rank_tasks(self, tasks, now=None):
        now = now or datetime.now()
        rows = [(task, self.strategy.score(task, now)) for task in tasks if task.status == 'pending' and task.remaining_minutes > 0]
        return sorted(rows, key=lambda pair: (pair[1] is None, -(pair[1] or 0), pair[0].due_at or '9999', pair[0].id))


@dataclass
class Proposal:
    week_start: str
    sessions: list = field(default_factory=list)  # tuples (task_id, title, start text, end text)
    unscheduled: list = field(default_factory=list)  # tuples (task_id, title, remaining minutes, reason)
    conflicts: list = field(default_factory=list)

    @property
    def scheduled_minutes(self):
        return sum(int((parse_dt(e) - parse_dt(s)).total_seconds() / 60) for _, _, s, e in self.sessions)

    def summary(self):
        header = f'Week {self.week_start}: {len(self.sessions)} session(s), {self.scheduled_minutes} min planned.'
        lines = [header]
        for task_id, title, start, end in self.sessions:
            lines.append(f'  [{task_id}] {start} - {end[-5:]}  {title}')
        for task_id, title, minutes, reason in self.unscheduled:
            lines.append(f'  UNSCHEDULED [{task_id}] {title}: {minutes} min ({reason})')
        for item in self.conflicts:
            lines.append(f'  CONFLICT: {item}')
        return '\n'.join(lines)


class ConflictChecker:
    def validate(self, sessions, commitments, deadlines=None):
        """Check overlap among sessions and existing commitments, plus task deadlines."""
        problems = []
        dates = []
        for task_id, title, start, end in sessions:
            a, b = parse_dt(start), parse_dt(end)
            if a >= b:
                problems.append(f'{title}: invalid interval')
            if deadlines and deadlines.get(task_id) and b > parse_dt(deadlines[task_id]):
                problems.append(f'{title}: ends after deadline')
            dates.append((title, a, b))
        for i, (title, a, b) in enumerate(dates):
            for other, c, d in dates[i + 1:]:
                if overlaps(a, b, c, d):
                    problems.append(f'{title} overlaps session {other}')
            for block in commitments:
                if overlaps(a, b, parse_dt(block.starts_at), parse_dt(block.ends_at)):
                    problems.append(f'{title} overlaps commitment {block.title}')
        return problems


class SchedulePlanner:
    """Assigns real free intervals, with a priority strategy and explicit confirmation."""
    def __init__(self, checker, priority):
        self.checker = checker
        self.priority = priority

    def generate(self, week_start, tasks, commitments, day_start=9, day_end=21, now=None):
        first = parse_day(week_start)
        if first.weekday() != 0:
            raise ValidationError('Please choose a Monday for the start of your study week.')
        if not (0 <= day_start < day_end <= 24):
            raise ValidationError('Study hours must satisfy 0 <= start < end <= 24.')
        now = now or datetime.now()
        ranked = self.priority.rank_tasks(tasks, now=now)
        proposal = Proposal(week_start)
        occupied = [(parse_dt(c.starts_at), parse_dt(c.ends_at)) for c in commitments]
        # Proposed sessions must not overlap existing commitments, each other, or the present.
        for task, _score in ranked:
            remaining = task.remaining_minutes
            deadline = parse_dt(task.due_at) if task.due_at else None
            if not deadline:
                proposal.unscheduled.append((task.id, task.title, remaining, 'missing due date - review required'))
                continue
            for offset in range(7):
                if remaining <= 0:
                    break
                day = first + timedelta(days=offset)
                start = datetime.combine(day, time.min) + timedelta(hours=day_start)
                stop = datetime.combine(day, time.min) + timedelta(hours=day_end)
                if now > start:
                    # round up to next 30-minute point to avoid scheduling in the past
                    minutes = now.hour * 60 + now.minute
                    ceil30 = ((minutes + 29) // 30) * 30
                    start = max(start, datetime.combine(now.date(), time.min) + timedelta(minutes=ceil30)) if day == now.date() else start
                    if day < now.date():
                        continue
                stop = min(stop, deadline)
                t = start
                while remaining > 0 and t + timedelta(minutes=30) <= stop:
                    size = 60 if remaining >= 60 and t + timedelta(minutes=60) <= stop else 30
                    # Do not schedule extra time beyond remaining effort (30-minute resolution).
                    if remaining < 30:
                        size = remaining
                    end = t + timedelta(minutes=size)
                    if end > stop:
                        break
                    if any(overlaps(t, end, a, b) for a, b in occupied):
                        t += timedelta(minutes=30)
                        continue
                    s_text, e_text = t.strftime(DT_FMT), end.strftime(DT_FMT)
                    proposal.sessions.append((task.id, task.title, s_text, e_text))
                    occupied.append((t, end))
                    remaining -= size
                    t = end + timedelta(minutes=15)
            if remaining > 0:
                proposal.unscheduled.append((task.id, task.title, remaining, 'insufficient free time before deadline'))
        proposal.sessions.sort(key=lambda row: row[2])
        deadline_map = {task.id: task.due_at for task, _ in ranked if task.due_at}
        proposal.conflicts = self.checker.validate(proposal.sessions, commitments, deadline_map)
        return proposal
