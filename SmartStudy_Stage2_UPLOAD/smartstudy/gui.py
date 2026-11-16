"""Tkinter GUI for SmartStudy - all features invoke shared application services."""
from datetime import date, timedelta
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from .models import ValidationError
from .ai import AIUnavailable
from .services import create_app


class SmartStudyGUI:
    def __init__(self, root, controller=None):
        self.root = root
        self.app = controller or create_app()
        self.root.title('SmartStudy  |  Academic Planning Agent')
        self.root.geometry('1120x780')
        self.root.minsize(900, 650)
        self.root.configure(bg='#eef2f7')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TNotebook', background='#eef2f7', borderwidth=0)
        style.configure('TNotebook.Tab', padding=(20, 11), font=('Arial', 10, 'bold'))
        style.configure('Treeview', rowheight=25)
        style.configure('TButton', padding=(10, 6))
        style.configure('Header.TLabel', font=('Arial', 16, 'bold'), foreground='#233d65')
        tk.Label(root, text='SmartStudy', bg='#233d65', fg='white', anchor='w',
                 font=('Arial', 23, 'bold'), padx=24, pady=12).pack(fill='x')
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill='both', expand=True, padx=16, pady=14)
        self.dash = self._tab('Courses & Tasks')
        self.calendar = self._tab('Weekly Planner')
        self.importer = self._tab('Deadline Import')
        self.assistant = self._tab('AI Assistant')
        self.settings_tab = self._tab('Reminders & Export')
        self.last_proposal = None
        self.drafts = []
        self.build_dashboard()
        self.build_calendar()
        self.build_import()
        self.build_assistant()
        self.build_settings()
        self.refresh()
        self.root.after(1000, self.check_reminders)

    def _tab(self, title):
        tab = ttk.Frame(self.tabs, padding=15)
        self.tabs.add(tab, text=title)
        return tab

    def guard(self, work):
        try:
            return work()
        except (ValidationError, AIUnavailable, ValueError, OSError) as exc:
            messagebox.showerror('SmartStudy', str(exc), parent=self.root)
            return None

    def entry(self, parent, label, row, col, default='', width=24):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky='w', padx=4, pady=4)
        widget = ttk.Entry(parent, width=width)
        widget.insert(0, default)
        widget.grid(row=row+1, column=col, sticky='ew', padx=4, pady=4)
        return widget

    def build_dashboard(self):
        f = self.dash
        ttk.Label(f, text='Manage your courses and assignments', style='Header.TLabel').pack(anchor='w', pady=(0, 12))
        course_frame = ttk.LabelFrame(f, text='Add course', padding=8); course_frame.pack(fill='x', pady=4)
        self.course_code = self.entry(course_frame, 'Course code', 0, 0, 'EECS3311')
        self.course_name = self.entry(course_frame, 'Course name', 0, 1, 'Software Design')
        ttk.Button(course_frame, text='Add course', command=self.add_course).grid(row=1, column=2, padx=8)
        task_frame = ttk.LabelFrame(f, text='Add task', padding=8); task_frame.pack(fill='x', pady=4)
        self.task_course = self.entry(task_frame, 'Course ID', 0, 0, width=10)
        self.task_title = self.entry(task_frame, 'Assignment / exam', 0, 1, width=30)
        self.task_due = self.entry(task_frame, 'Due (YYYY-MM-DD HH:MM)', 0, 2, width=22)
        self.task_minutes = self.entry(task_frame, 'Minutes', 0, 3, '120', 8)
        self.task_importance = self.entry(task_frame, 'Importance 1-5', 0, 4, '3', 8)
        ttk.Button(task_frame, text='Add task', command=self.add_task).grid(row=1, column=5, padx=8)
        ttk.Label(f, text='Saved courses and tasks (select a task to update progress)').pack(anchor='w', pady=(12, 2))
        self.courses_text = ttk.Label(f, text=''); self.courses_text.pack(anchor='w', pady=3)
        columns = ('id', 'course', 'title', 'due', 'remaining', 'importance', 'status')
        self.tasks_tree = ttk.Treeview(f, columns=columns, show='headings', height=11)
        widths = (55, 105, 270, 170, 100, 95, 80)
        for col, width in zip(columns, widths):
            self.tasks_tree.heading(col, text=col.title()); self.tasks_tree.column(col, width=width, stretch=(col=='title'))
        self.tasks_tree.pack(fill='both', expand=True)
        actions = ttk.Frame(f); actions.pack(fill='x', pady=8)
        self.remaining = self.entry(actions, 'Remaining minutes', 0, 0, '0', 14)
        ttk.Button(actions, text='Update progress', command=self.update_progress).grid(row=1, column=1, padx=5)
        ttk.Button(actions, text='Mark complete', command=self.complete_task).grid(row=1, column=2, padx=5)
        ttk.Button(actions, text='Sort by priority', command=self.rank_tasks).grid(row=1, column=3, padx=5)
        ttk.Button(actions, text='Refresh', command=self.refresh).grid(row=1, column=4, padx=5)

    def selected_task(self):
        selected = self.tasks_tree.selection()
        if not selected:
            raise ValidationError('Select a task in the table first.')
        return int(self.tasks_tree.item(selected[0], 'values')[0])

    def add_course(self):
        def action():
            self.app.add_course(self.course_code.get(), self.course_name.get()); self.refresh()
        self.guard(action)

    def add_task(self):
        def action():
            self.app.add_task(int(self.task_course.get()), self.task_title.get(), self.task_due.get().strip() or None,
                              int(self.task_minutes.get()), int(self.task_importance.get()))
            self.refresh()
        self.guard(action)

    def update_progress(self):
        self.guard(lambda: (self.app.progress(self.selected_task(), remaining=int(self.remaining.get())), self.refresh()))

    def complete_task(self):
        self.guard(lambda: (self.app.progress(self.selected_task(), complete=True), self.refresh()))

    def rank_tasks(self):
        def action():
            ranked = self.app.ranked_tasks()
            order = {t.id: i for i, (t, _) in enumerate(ranked)}
            for node in self.tasks_tree.get_children():
                values = self.tasks_tree.item(node, 'values')
                self.tasks_tree.move(node, '', order.get(int(values[0]), len(order)))
            msg = '\n'.join(f'{i}. {t.title} ({score or "needs due date"})' for i,(t,score) in enumerate(ranked,1))
            messagebox.showinfo('Priority ranking', msg or 'No pending tasks.', parent=self.root)
        self.guard(action)

    def build_calendar(self):
        f = self.calendar
        ttk.Label(f, text='Create a conflict-free weekly study plan', style='Header.TLabel').pack(anchor='w')
        block = ttk.LabelFrame(f, text='Add fixed commitment (classes, shifts, etc.)', padding=9); block.pack(fill='x', pady=9)
        self.block_title = self.entry(block, 'Title', 0, 0, 'Class')
        self.block_start = self.entry(block, 'Start (YYYY-MM-DD HH:MM)', 0, 1, width=23)
        self.block_end = self.entry(block, 'End (YYYY-MM-DD HH:MM)', 0, 2, width=23)
        ttk.Button(block, text='Add commitment', command=self.add_block).grid(row=1, column=3, padx=8)
        controls = ttk.Frame(f); controls.pack(fill='x', pady=8)
        monday = date.today() - timedelta(days=date.today().weekday())
        self.week = self.entry(controls, 'Monday of week', 0, 0, monday.isoformat())
        ttk.Button(controls, text='Preview plan', command=lambda:self.preview_plan(False)).grid(row=1, column=1, padx=5)
        ttk.Button(controls, text='Preview replan', command=lambda:self.preview_plan(True)).grid(row=1, column=2, padx=5)
        ttk.Button(controls, text='Approve proposal', command=self.approve_plan).grid(row=1, column=3, padx=5)
        ttk.Button(controls, text='Why this plan?', command=self.explain).grid(row=1, column=4, padx=5)
        self.plan_output = tk.Text(f, height=20, wrap='word', font=('Courier New', 10), relief='flat', bg='white')
        self.plan_output.pack(fill='both', expand=True, pady=10)
        self.is_replan = False

    def add_block(self):
        def action():
            self.app.add_commitment(self.block_title.get(), self.block_start.get(), self.block_end.get())
            messagebox.showinfo('Saved', 'Commitment added.', parent=self.root)
        self.guard(action)

    def preview_plan(self, replan):
        def action():
            self.last_proposal = self.app.preview(self.week.get())
            self.is_replan = replan
            self._text(self.plan_output, self.last_proposal.summary() + '\n\nPREVIEW ONLY: approval is required to save.')
        self.guard(action)

    def approve_plan(self):
        def action():
            if not self.last_proposal:
                raise ValidationError('Generate a preview before approving.')
            if not messagebox.askyesno('Confirm', 'Replace saved sessions in this week with the proposal?', parent=self.root):
                return
            count = self.app.approve(self.last_proposal, replan=self.is_replan)
            messagebox.showinfo('Saved', f'{count} study sessions saved.', parent=self.root)
        self.guard(action)

    def explain(self):
        def action():
            if not self.last_proposal: raise ValidationError('Generate a plan preview first.')
            self._text(self.plan_output, self.last_proposal.summary() + '\n\nWHY THIS PLAN\n' + self.app.explain_plan(self.last_proposal))
        self.guard(action)

    def build_import(self):
        f = self.importer
        ttk.Label(f, text='Import a course outline or paste an announcement', style='Header.TLabel').pack(anchor='w')
        controls = ttk.Frame(f); controls.pack(fill='x', pady=12)
        ttk.Button(controls, text='Select PDF and extract drafts', command=self.import_pdf).pack(side='left', padx=5)
        ttk.Button(controls, text='Extract from pasted notes', command=self.import_notes).pack(side='left', padx=5)
        ttk.Label(f, text='Paste announcement text (AI requires your local API key):').pack(anchor='w')
        self.notes_text = tk.Text(f, height=7, wrap='word'); self.notes_text.pack(fill='x', pady=6)
        ttk.Label(f, text='AI drafts: review every date before saving').pack(anchor='w', pady=(9, 3))
        self.draft_tree = ttk.Treeview(f, columns=('number','title','date','minutes','warning'), show='headings', height=7)
        for col, w in [('number',55),('title',310),('date',160),('minutes',90),('warning',320)]:
            self.draft_tree.heading(col,text=col.title()); self.draft_tree.column(col,width=w)
        self.draft_tree.pack(fill='both', expand=True)
        save = ttk.Frame(f); save.pack(fill='x', pady=9)
        self.import_course = self.entry(save, 'Confirm course ID', 0, 0, width=12)
        self.import_due = self.entry(save, 'Correct selected date (YYYY-MM-DD HH:MM)', 0, 1, width=24)
        ttk.Button(save, text='Save selected draft', command=self.save_draft).grid(row=1, column=2, padx=10)
        ttk.Label(f, text='No drafts are saved automatically. Select one and supply/correct its date before saving.').pack(anchor='w')

    def _display_drafts(self):
        for item in self.draft_tree.get_children(): self.draft_tree.delete(item)
        for i,d in enumerate(self.drafts):
            self.draft_tree.insert('', 'end', values=(i+1,d.title,d.due_at or 'REVIEW REQUIRED',d.effort_minutes,d.warning))

    def import_pdf(self):
        filename = filedialog.askopenfilename(filetypes=[('PDF files','*.pdf')], parent=self.root)
        if filename:
            self.guard(lambda: self._set_drafts(self.app.import_outline(filename)))

    def import_notes(self):
        self.guard(lambda: self._set_drafts(self.app.extract_notes(self.notes_text.get('1.0','end').strip())))

    def _set_drafts(self, drafts):
        self.drafts = drafts
        self._display_drafts()
        if not drafts: messagebox.showinfo('Result', 'No clear deadlines identified.', parent=self.root)

    def save_draft(self):
        def action():
            selected = self.draft_tree.selection()
            if not selected: raise ValidationError('Select an imported draft.')
            i = int(self.draft_tree.item(selected[0], 'values')[0])-1
            draft = self.drafts[i]
            date_text = self.import_due.get().strip() or draft.due_at
            if not messagebox.askyesno('Confirm extracted deadline', f'Save "{draft.title}" due {date_text}?', parent=self.root):
                return
            self.app.confirm_draft(int(self.import_course.get()), draft, corrected_due=date_text)
            self.drafts.pop(i); self._display_drafts(); self.refresh()
            messagebox.showinfo('Saved', 'Confirmed deadline saved.', parent=self.root)
        self.guard(action)

    def build_assistant(self):
        f = self.assistant
        ttk.Label(f, text='Ask the AI agent (read-only tool selection)', style='Header.TLabel').pack(anchor='w')
        ttk.Label(f, text='Try: "Show my urgent tasks" or "Preview my weekly study plan". Modifications require GUI confirmation.').pack(anchor='w', pady=10)
        self.chat_input = tk.Text(f, height=5, wrap='word'); self.chat_input.pack(fill='x', pady=7)
        ttk.Button(f, text='Ask SmartStudy', command=self.ask_ai).pack(anchor='w', pady=6)
        self.chat_result = tk.Text(f, height=19, bg='white', wrap='word'); self.chat_result.pack(fill='both', expand=True)

    def ask_ai(self):
        def action():
            request = self.chat_input.get('1.0','end').strip()
            self._text(self.chat_result, self.app.handle_request(request))
        self.guard(action)

    def build_settings(self):
        f = self.settings_tab
        ttk.Label(f, text='Reminders, priorities and CSV export', style='Header.TLabel').pack(anchor='w')
        control = ttk.Frame(f); control.pack(fill='x', pady=15)
        self.reminder_enabled = tk.BooleanVar(value=self.app.store.preference('reminders_enabled','1') == '1')
        ttk.Checkbutton(control, text='Enable in-app deadline reminders', variable=self.reminder_enabled).grid(row=0,column=0,sticky='w')
        self.lead_hours = self.entry(control, 'Remind this many hours before due time', 1, 0,
                                     self.app.store.preference('reminder_lead_hours','48'))
        ttk.Button(control, text='Save reminders', command=self.save_settings).grid(row=2,column=1,padx=8)
        ttk.Button(control, text='Check reminders now', command=self.check_reminders).grid(row=3,column=0,pady=12,sticky='w')
        self.priority_mode = tk.StringVar(value=self.app.store.preference('priority_strategy','deadline'))
        availability = ttk.Frame(f); availability.pack(fill='x', pady=10)
        self.start_hour = self.entry(availability, 'Daily study start hour (0-23)', 0, 0,
                                     self.app.store.preference('study_start_hour','9'), 12)
        self.end_hour = self.entry(availability, 'Daily study end hour (1-24)', 0, 1,
                                   self.app.store.preference('study_end_hour','21'), 12)
        ttk.Button(availability, text='Save availability', command=self.save_availability).grid(row=1,column=2,padx=10)
        ttk.Label(f, text='Priority strategy (Strategy design pattern)').pack(anchor='w', pady=6)
        mode = ttk.Combobox(f, values=['deadline','balanced'], textvariable=self.priority_mode, state='readonly', width=16)
        mode.pack(anchor='w')
        ttk.Button(f, text='Apply priority strategy', command=self.apply_strategy).pack(anchor='w', pady=8)
        ttk.Button(f, text='Export saved study sessions to CSV', command=self.export).pack(anchor='w', pady=18)
        ttk.Label(f, text='AI requires a separately configured local .env file; keys are never displayed here.').pack(anchor='w')

    def save_settings(self):
        def action():
            self.app.settings(reminders_enabled=self.reminder_enabled.get(), lead_hours=int(self.lead_hours.get()))
            messagebox.showinfo('Saved', 'Reminder preferences saved.', parent=self.root)
        self.guard(action)

    def save_availability(self):
        def action():
            self.app.set_availability(int(self.start_hour.get()), int(self.end_hour.get()))
            messagebox.showinfo('Saved', 'Daily study hours saved.', parent=self.root)
        self.guard(action)

    def apply_strategy(self):
        self.guard(lambda: self.app.set_strategy(self.priority_mode.get()))

    def export(self):
        file = filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')], parent=self.root)
        if file:
            self.guard(lambda: messagebox.showinfo('Export', self.app.export_csv(file), parent=self.root))

    def check_reminders(self):
        def action():
            self.app.reminders.check_deadlines(
                deliver=lambda item: messagebox.showinfo('Upcoming deadline', item, parent=self.root) is None)
        self.guard(action)
        # Rechecks are local and periodic; already delivered reminders are suppressed.
        self.root.after(60000, self.check_reminders)

    def refresh(self):
        courses = self.app.store.list_courses()
        self.courses_text.configure(text='Courses: ' + (', '.join(f'{c.id}={c.code}' for c in courses) or '(none)'))
        for item in self.tasks_tree.get_children(): self.tasks_tree.delete(item)
        for t in self.app.store.list_tasks():
            self.tasks_tree.insert('', 'end', values=(t.id,t.course_code,t.title,t.due_at or 'needs date',
                                                     t.remaining_minutes,t.importance,t.status))

    @staticmethod
    def _text(widget, content):
        widget.delete('1.0', 'end'); widget.insert('1.0', content)


def main():
    root = tk.Tk()
    SmartStudyGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
