"""Command and Factory Method patterns: bounded, read-only tools for the LLM agent."""
from abc import ABC, abstractmethod
from datetime import date, timedelta
from .models import parse_day, ValidationError


class ICommand(ABC):
    @abstractmethod
    def execute(self, controller, args):
        pass


class ListTasksCommand(ICommand):
    def execute(self, controller, args):
        tasks = controller.store.list_tasks()
        return '\n'.join(f'[{t.id}] {t.course_code} {t.title} | due {t.due_at or "unset"} | {t.remaining_minutes} min | {t.status}' for t in tasks) or 'No tasks.'


class RankTasksCommand(ICommand):
    def execute(self, controller, args):
        rows = controller.priority.rank_tasks(controller.store.list_tasks(False))
        return '\n'.join(f'{i}. [{t.id}] {t.title}: {score if score is not None else "date needs review"}'
                         for i, (t, score) in enumerate(rows, 1)) or 'No pending tasks.'


class PreviewPlanCommand(ICommand):
    def execute(self, controller, args):
        week = args.get('week_start') or (date.today() - timedelta(days=date.today().weekday())).isoformat()
        return controller.preview(week).summary()


class ListCoursesCommand(ICommand):
    def execute(self, controller, args):
        return '\n'.join(f'[{c.id}] {c.code} - {c.name}' for c in controller.store.list_courses()) or 'No courses.'


class ProgressSummaryCommand(ICommand):
    def execute(self, controller, args):
        ts = controller.store.list_tasks()
        completed = sum(t.status == 'done' for t in ts)
        total = len(ts)
        remaining = sum(t.remaining_minutes for t in ts)
        return f'{completed}/{total} completed; {remaining} study minutes remain.'


class HelpCommand(ICommand):
    def execute(self, controller, args):
        return ('The AI agent can list tasks/courses, rank priorities, preview a weekly plan, '
                'and summarize progress. For changes use the GUI forms or CLI commands; '
                'the agent cannot change data without review.')


# Factory Method - each subclass implements the object-construction decision.
class ToolFactory(ABC):
    @abstractmethod
    def create(self, tool):
        pass


class StudyToolFactory(ToolFactory):
    TYPES = {
        'list_tasks': ListTasksCommand,
        'rank_tasks': RankTasksCommand,
        'preview_plan': PreviewPlanCommand,
        'list_courses': ListCoursesCommand,
        'progress_summary': ProgressSummaryCommand,
        'help': HelpCommand,
    }

    def create(self, tool):
        return self.TYPES.get(tool, HelpCommand)()


class ToolManager:
    def __init__(self, factory=None):
        self.factory = factory or StudyToolFactory()

    def execute_tool(self, controller, intent):
        tool = str(intent.get('tool', 'help'))
        if tool not in StudyToolFactory.TYPES:
            tool = 'help'
        return self.factory.create(tool).execute(controller, intent)
