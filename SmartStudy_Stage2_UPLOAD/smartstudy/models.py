"""Domain objects, validation and timestamps for SmartStudy."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

DATE_FMT = '%Y-%m-%d'
DT_FMT = '%Y-%m-%d %H:%M'


class ValidationError(ValueError):
    pass


def parse_dt(value: str) -> datetime:
    try:
        return datetime.strptime(value, DT_FMT)
    except (ValueError, TypeError) as exc:
        raise ValidationError('Date/time must be YYYY-MM-DD HH:MM (24-hour clock).') from exc


def parse_day(value: str):
    try:
        return datetime.strptime(value, DATE_FMT).date()
    except (ValueError, TypeError) as exc:
        raise ValidationError('Date must be YYYY-MM-DD.') from exc


def checked_dt(value: str) -> str:
    parse_dt(value)
    return value


def clean_title(value: str) -> str:
    value = (value or '').strip()
    if not value or len(value) > 180:
        raise ValidationError('Title must contain 1 to 180 characters.')
    return value


@dataclass(frozen=True)
class Course:
    id: int
    code: str
    name: str


@dataclass(frozen=True)
class Task:
    id: int
    course_id: int
    course_code: str
    title: str
    due_at: Optional[str]
    effort_minutes: int
    remaining_minutes: int
    importance: int
    status: str = 'pending'


@dataclass(frozen=True)
class StudySession:
    id: int
    task_id: int
    title: str
    starts_at: str
    ends_at: str


@dataclass(frozen=True)
class Commitment:
    id: int
    title: str
    starts_at: str
    ends_at: str


@dataclass(frozen=True)
class DraftTask:
    title: str
    due_at: Optional[str]
    effort_minutes: int = 60
    importance: int = 3
    source: str = ''
    warning: str = ''


def validate_interval(start: str, end: str):
    a, b = parse_dt(start), parse_dt(end)
    if a >= b:
        raise ValidationError('End time must be after start time.')
    return a, b


def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def overlaps_minutes(a_start, a_end, b_start, b_end) -> int:
    if not overlaps(a_start, a_end, b_start, b_end):
        return 0
    return int((min(a_end, b_end) - max(a_start, b_start)).total_seconds() // 60)
