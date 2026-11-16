"""Generate an evidence-aware Stage 2 report from the implementation in this package."""
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION_START

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'stage2-report.docx'
doc=Document()
sec=doc.sections[0]
sec.page_height, sec.page_width=Inches(11.7), Inches(8.3)
sec.top_margin=sec.bottom_margin=Inches(.72)
sec.left_margin=sec.right_margin=Inches(.72)
styles=doc.styles
styles['Normal'].font.name='Aptos'
styles['Normal'].font.size=Pt(9.2)
styles['Normal'].paragraph_format.space_after=Pt(6)
for h,size in [('Title',25),('Heading 1',15),('Heading 2',11.5)]:
 st=styles[h];st.font.name='Aptos Display';st.font.size=Pt(size);st.font.bold=True;st.font.color.rgb=RGBColor(33,63,103)

def para(text='',boldstart=None):
 p=doc.add_paragraph()
 if boldstart and text.startswith(boldstart):
  p.add_run(boldstart).bold=True;p.add_run(text[len(boldstart):])
 else:p.add_run(text)
 return p

def heading(text, level=1):doc.add_heading(text,level)

def bullet(text):doc.add_paragraph(text,style='List Bullet')

def table(headers, rows, sizes=None):
 t=doc.add_table(rows=1,cols=len(headers))
 t.style='Light Shading Accent 1';t.alignment=WD_TABLE_ALIGNMENT.CENTER
 for j,val in enumerate(headers):t.rows[0].cells[j].text=val
 for row in rows:
  cells=t.add_row().cells
  for j,val in enumerate(row): cells[j].text=str(val)
 for row in t.rows:
  for cell in row.cells:
   cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   for p in cell.paragraphs:
    for r in p.runs:r.font.size=Pt(8)
   if sizes:
    for c,w in zip(row.cells,sizes):c.width=Inches(w)
 return t

p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
p.add_run('EECS 3311  |  SOFTWARE DESIGN').bold=True
p=doc.add_paragraph(style='Title');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run('SmartStudy\nStage 2 Implementation Report')
p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run('AI Human Collaborative Implementation').italic=True
p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run('Prepared November 15, 2026  •  Local implementation evidence')
doc.add_paragraph('')
heading('Submission status and important qualification')
para('This report describes a working local application assembled from the submitted Stage 1 SmartStudy design. It is not evidence of historical student commits, student code review, a live external API request, or a public GitHub upload. Actual repository history, API cost records, and authentic demonstration links must be supplied by the student before claiming the course submission is complete.')
table(['Component','Verified status'],[
 ('Python source + SQLite','Implemented; deterministic tests passing'),
 ('Tkinter GUI and argparse CLI','Both launch; local walkthroughs captured'),
 ('LLM integration','Implemented as configurable OpenAI API adapter; real API request NOT verified'),
 ('Demonstration videos','GUI walkthrough (AI mocked) and real CLI run available locally; incomplete rubric coverage'),
 ('GitHub weekly activity','No user repository or commit history supplied; cannot certify'),
 ('API costs','Exact token counts and charges unavailable; must be recorded from real tools')], [2.1,5.2])

heading('1. Project overview and implementation status')
para('SmartStudy assists university students with course and task management, extraction of proposed deadlines, priority ranking, conflict-aware weekly scheduling, progress, replanning, deadline alerts, explanations, and CSV exports. The Stage 1 design calls for a Python application, SQLite storage, PDF text extraction, an LLM adapter, and a shared controller across GUI and CLI. The code in this package implements those components as a reproducible local project.')
para('System boundary: Tkinter GUI (smartstudy/gui.py) and argparse CLI (smartstudy/cli.py) call one AgentController facade (smartstudy/services.py). Persistence is implemented by SQLiteRepository (smartstudy/storage.py). PriorityEngine, SchedulePlanner, and ConflictChecker (smartstudy/planning.py) make deterministic decisions. The LLM interface in smartstudy/ai.py supports natural-language read-only tool routing, extraction candidates, and explanations.')
para('Meaningful agent behavior: natural-language intent is converted by IntentInterpreter into a permitted tool key; ToolManager obtains an ICommand using StudyToolFactory and executes it against live application data. AI-produced import candidates are validated and remain drafts until user confirmation. Actual scheduling and collision checks do not depend on LLM guesses.')
para('Runtime qualification: Features that depend on the AI provider require an actual personal OpenAI API key and internet access. Tests substitute a controlled FakeLLM; no live API usage or accuracy claims are made. The GUI uses a dated agenda list rather than a full drag-and-drop calendar; PDF input must contain selectable text. Reminders are in-app, not push/email.')

heading('2. Feature-to-implementation mapping')
para('The Stage 1 project specified twelve feature IDs (F01-F12). All are represented in code; the table distinguishes implementation from external integration verification. Demo times are approximate in the included offline walkthroughs; they are not public links.')
features=[
('F01 Natural language','GUI Assistant / CLI ask','IntentInterpreter, ToolManager, StudyToolFactory, ICommand; interpret(), execute_tool(); Adapter, Command, Factory Method, Facade','AI dependent; offline fixture verified','gui_walkthrough.mp4 ~00:43-00:48'),
('F02 Course/tasks','GUI Dashboard / CLI course and task','AgentController, SQLiteRepository, Task; add_course(), add_task(), update_task(); Facade','Implemented, tests pass','GUI ~00:04-00:14; CLI ~00:02-00:13'),
('F03 PDF outline import','GUI Import / CLI import','DocumentProcessor, DeadlineExtractor, ILLMClient; import_pdf(), extract(), confirm_draft(); Adapter','Selectable-text extraction tested; live AI not verified','Not captured end-to-end; demo outstanding'),
('F04 Notes extraction','GUI Import / CLI notes','DeadlineExtractor, DraftTask, TaskValidator logic in confirm_draft(); extract(), confirm_draft(); Adapter','Mocked AI extraction and draft confirmation tested','GUI ~00:38-00:43 (mock AI)'),
('F05 Priority ranking','GUI Sort / CLI task rank','PriorityEngine, IPriorityStrategy, two strategies; rank_tasks(), score(); Strategy','Implemented, tests pass','GUI ~00:14-00:17; CLI ~00:13-00:19'),
('F06 Weekly planning','GUI Weekly Planner / CLI plan week','SchedulePlanner, Proposal, SQLiteRepository; generate(), approve(), save_sessions(); Strategy, Facade','Implemented, tests pass; partial plans flagged','GUI ~00:23-00:31; CLI ~00:23-00:30'),
('F07 Conflict detection','GUI commitment + preview / CLI block','ConflictChecker, StudySession, Commitment; validate(), overlaps()','Implemented, tests pass','GUI ~00:20-00:28; CLI ~00:19-00:30'),
('F08 Progress tracking','GUI Dashboard / CLI task progress','AgentController, SQLiteRepository, TaskEventPublisher; progress(), update_progress(); Observer','Implemented, tests pass','GUI ~00:17-00:20; CLI ~00:30-00:34'),
('F09 Replanning proposal','GUI Preview replan / CLI plan replan','SchedulePlanner, ConflictChecker, SQLiteRepository; preview(), approve(replan=True); Facade','Implemented, preserves saved schedule on incomplete proposal','GUI ~00:31-00:35'),
('F10 Deadline reminders','GUI Settings / CLI remind check','ReminderScheduler, SQLiteRepository, TaskEventPublisher; check_deadlines(), mark_reminder(); Observer','Implemented with suppression/retry; real due alert not video-captured','GUI controls ~00:48-00:53'),
('F11 Plan explanations','GUI Why this plan? / CLI plan explain','ExplanationService, ILLMClient; explain(), explain_plan(); Adapter','Template fallback works; live LLM not verified','GUI ~00:35-00:38 (mock AI)'),
('F12 Export + CLI','GUI CSV export / CLI export','ExportService behavior in AgentController.export_csv(); CLI; export_csv()','Implemented, automated CSV and CLI tests pass','GUI controls ~00:48-00:53; CLI export after ~00:35'),
]
for idtitle,interaction,implementation,status,demo in features:
 heading(idtitle,2)
 para(f'Interaction: {interaction}.')
 para(f'Classes/files and methods: {implementation}.')
 para(f'Status: {status}. Demonstration: {demo}.')

heading('2.1 Typical collaboration and responsibility flow')
para('F02/F08 deterministic: GUI/CLI collects validated input -> AgentController -> SQLiteRepository commits a record -> TaskEventPublisher notifies ReminderScheduler and CalendarRefreshListener -> frontend refreshes its task display.')
para('F03/F04 hybrid: DocumentProcessor obtains selectable PDF text, or user supplies notes -> DeadlineExtractor calls ILLMClient.structured() -> invalid/ambiguous dates are flagged -> user edits/approves a candidate -> AgentController.confirm_draft() validates and saves via SQLiteRepository. No LLM text is written directly.')
para('F05/F06/F07/F09 deterministic planning with hybrid explanations: Controller collects pending tasks and commitments -> PriorityEngine applies a strategy -> SchedulePlanner allocates free intervals before deadlines -> ConflictChecker validates -> GUI/CLI previews -> explicit approval invokes SQLiteRepository.save_sessions() in a transaction. Replanning refuses incomplete replacements. F11 calls the model using verified schedule facts, with a deterministic fallback.')

heading('3. Implemented design patterns and updated UML')
patterns=[
 ('Strategy','IPriorityStrategy; DeadlinePriorityStrategy; BalancedPriorityStrategy; PriorityEngine','planning.py: score(), rank_tasks()','Swap ranking formulas without changing scheduling; matches Stage 1.'),
 ('Adapter','ILLMClient; OpenAILLMAdapter; IntentInterpreter; DeadlineExtractor','ai.py: structured(), interpret(), extract()','Isolate provider-specific JSON and HTTP handling from application services; matches Stage 1.'),
 ('Facade','AgentController with SmartStudyGUI and CLI clients','services.py: preview(), approve(), handle_request()','Single entry point for multiple cooperating services; matches Stage 1.'),
 ('Command','ICommand; ListTasksCommand; PreviewPlanCommand; ToolManager','commands.py: execute(), execute_tool()','Encapsulate an allowlisted application action independently of model prompts; matches Stage 1.'),
 ('Factory Method','ToolFactory; StudyToolFactory; command subclasses','commands.py: create()','Create concrete ICommand instances centrally based on intent; matches Stage 1.'),
 ('Observer','TaskEventPublisher; ReminderScheduler; CalendarRefreshListener','services.py: subscribe(), notify(), on_task_change()','React to task edits without hard-wiring every listener into persistence; Stage 1 extension now implemented.'),
]
for name, roles, files, explanation in patterns:
 heading(name,2)
 para(f'Participants and pattern roles: {roles}. Relevant files and methods: {files}.')
 para(explanation)
para('Note: the implementation uses Python ABCs and dependency composition for interfaces; the included diagram is regenerated from the implemented classes, not copied from Stage 1. Dashed arrows denote interface implementation.')
heading('3.1 Updated class structure',2)
doc.add_picture(str(ROOT/'diagrams/implemented_classes.png'),width=Inches(6.85))
para('Figure 1. Implemented classes and pattern participants. A full-resolution version is included at diagrams/implemented_classes.png.')
heading('3.2 Updated use-case model',2)
doc.add_picture(str(ROOT/'diagrams/use_cases_updated.png'),height=Inches(6.5))
para('Figure 2. Stage 2 update: only allowlisted read-only agent tools run autonomously; updates and scheduling require user approval. Full diagram: diagrams/use_cases_updated.png.')
heading('3.3 Updated sequence behavior',2)
para('SD05 (agent request) now includes allowlist enforcement: Student -> GUI/CLI -> AgentController.handle_request -> IntentInterpreter.structured -> ToolManager.execute_tool -> StudyToolFactory.create -> ICommand.execute -> repository/service -> result. Unsupported or modifying intents route to help, not direct writes.')
para('SD02 (planning) now reads configured daily study hours and commitments: Student -> GUI/CLI -> Controller.preview -> PriorityEngine.rank_tasks -> SchedulePlanner.generate -> ConflictChecker.validate -> preview -> Student approval -> Controller.approve -> SQLiteRepository.save_sessions. In a replan, unresolved effort blocks replacement and preserves the previously saved sessions.')
para('SD01 (import) remains extraction -> draft validation -> student confirmation -> persistence. Ambiguous dates remain unsaved. SD04 reminder now passes through an observer and records delivery only after its UI callback succeeds; failed deliveries remain eligible for retry.')

heading('4. Changes and rationale (Stage 1 -> Stage 2)')
changes=[
 ('F01','Agent intended to select permitted tools, potentially including writes','Read-only command allowlist; mutations through explicit GUI/CLI','Prevent accidental LLM changes','IntentInterpreter; ToolManager; Command/Factory Method; UC01/SD05'),
 ('F06','Availability and commitments conceptually modeled','One global daily availability window plus specific fixed commitments','Implement bounded simple deterministic allocator','SchedulePlanner; Settings GUI/CLI; UC04/SD02'),
 ('F10','NotificationService abstracted, with retries','In-app Tk/CLI callback with successful-delivery deduplication','No external notification provider or credentials required','ReminderScheduler, storage reminders table; Observer; UC06/SD04'),
 ('F12','Separate ExportService class planned','CSV writer in AgentController.export_csv()','Reduce unnecessary service boilerplate','Facade; UC08/SD06'),
 ('F03/F04','LLM-suggested candidates reviewed and confirmed','Explicit DraftTask validation and confirmation dialog/CLI --confirm','Prevent ambiguous due dates from being committed','DeadlineExtractor, DocumentProcessor, AgentController; Adapter; UC03/SD01'),
 ('F11','LLM based plan explanation','Explicit deterministic fallback when model is unavailable','Keep the feature useful offline','ExplanationService; Adapter; UC07/SD06'),
]
for feature,original,change,reason,impact in changes:
 heading(feature,2);para(f'Original design: {original}. Implemented change: {change}.')
 para(f'Reason: {reason}. Impact on features/classes/patterns/use cases: {impact}.')
para('No original Stage 1 feature ID has been silently dropped. Features requiring real external AI calls are implemented as integration points but cannot be marked live-service verified without a user key.')

heading('5. AI tool and collaboration log')
table(['Tool/model','Usage','Tokens / money'],[
 ('ChatGPT / GPT-6','Generated application structure, modules, pytest cases, documentation, diagrams and this report. User review remains required.','Token count: unavailable here; money cost: unavailable here. Do not estimate as fact.'),
 ('OpenAI chat completions / gpt-4o-mini (default configured model)','Runtime LLM adapter for intents, extraction and explanations. This delivered environment did not access a live account.','No live requests verified in this environment; account-wide token and charge totals unknown.'),
 ('Offline FakeLLM (non-LLM test double)','Deterministic AI-interface unit tests and labeled GUI demonstration only.','0 LLM tokens in these fixtures; not proof of live integration.')
], [2.1,3.1,2.1])
para('Representative model-assisted development tasks: produce a SQLite repository with parameterized queries and transaction safety; map Stage 1 F01-F12 to source methods; design a deterministic conflict-checking planner; write tests for incomplete replanning and draft confirmation; explain the six design pattern roles. Resulting files are present in the repository. The student should document their own substantial AI prompts, edits, code review and accurate provider usage from their tooling.')

heading('6. Development and verification summary')
para('Local verification: 15 pytest tests passed with python -m pytest -q; python -m compileall -q smartstudy completed; a Tkinter GUI startup smoke check under a virtual X display succeeded; CLI subprocess tests exercised an actual fresh SQLite database. Screen-captured GUI and terminal demonstrations were produced from a runnable application. The test suite itself contains a clearly identified fake model for offline checks.')
table(['Checked behavior','Result'],[
 ('Course creation, persistence, task status, invalid input','Automated passing tests'),
 ('Two priority strategies, switch persistence','Automated passing test'),
 ('Conflict-free planning, deadlines, approval-only saving','Automated passing test'),
 ('Insufficient free time and preservation of old plan on failed replan','Automated passing tests'),
 ('Reminder deduplication, observer event, CSV export','Automated passing tests'),
 ('PDF selectable text import, AI extraction/intent/fallback under mock','Automated passing tests'),
 ('Real OpenAI API call, real external billing/cost, real student review','Not verified; action needed'),
 ('Real GitHub commit URLs, public link access, authentic complete feature videos','Not verified; action needed')
],[4.0,3.3])
heading('6.1 Weekly GitHub commit evidence',2)
para('The course requires at least FIVE meaningful source/test code commits in each period, with links. Dates use Toronto local time. No repository history was supplied, so none can be claimed or recreated.')
table(['Required period','Verified commits','Evidence'],[
 ('Oct 20-26, 2026','Not verifiable','No repository / URLs supplied'),
 ('Oct 27-Nov 2, 2026','Not verifiable','No repository / URLs supplied'),
 ('Nov 3-9, 2026','Not verifiable','No repository / URLs supplied')],[2.1,1.4,3.8])
para('Stage 2 instructions specify a single five-point deduction total if any required period lacks five meaningful code commits. This report does not assert that the student has or has not fulfilled the condition; the required evidence is simply unavailable.')

heading('7. Feature demonstration index')
para('The included local media files are demos/gui_walkthrough.mp4 (approx. 58 seconds; automated GUI interaction, AI TEST DOUBLE) and demos/cli_walkthrough.mp4 (a real terminal session of deterministic CLI commands; approximately 36 seconds). All paths must be converted to accessible GitHub/video URLs once actually uploaded. Demonstrations of a *real* provider call, PDF import, actual reminder display, and all relevant error cases still need user recordings.')
for a,b,c,d,e in features:
 para(f'{a}: {e}. Status: {d}.')
heading('7.1 Recording safety and authenticity',2)
bullet('The GUI capture was generated from the actual Tk application and wired services, but uses a fake AI implementation for reproducible offline illustration. This is NOT evidence of API requests.')
bullet('The CLI capture executes the real Python CLI against a temporary SQLite database using synthetic dates. It demonstrates deterministic flows only.')
bullet('Before grading: record every feature invoked with real inputs, outcomes and relevant error behavior; capture both GUI and CLI; include direct accessible URLs with exact timestamps; ensure secrets never appear.')

heading('8. Submission and reviewer traceability checklist')
for t in [
 'Complete source for GUI, CLI, agent, model adapter, SQL storage, scheduler and tests - included.',
 'README with setup, dependencies, local .env, launch instructions, and example usage - included.',
 'requirements.txt, .gitignore and .env.example - included; no actual API key present.',
 'stage2-report.docx and stage2-report.pdf - generated from the implementation.',
 'Feature demo videos - partial labeled local evidence, not a substitute for complete authentic instructor-accessible demos.',
 'Public GitHub URL and commit links - not supplied; add real evidence before submission.',
 'Inspect every reported class/method, run GUI+CLI, review the code yourself, and record honest AI-tool costs.'
]:bullet(t)
para('Traceability: Stage 1 Fxx -> Section 2 mapping -> source files/methods -> Section 3 pattern -> Section 7 demo index. Project due date in the supplied instructions was November 10, 2026; this local artifact was prepared afterward. No retroactive compliance is asserted.')

def footers():
 for s in doc.sections:
  f=s.footer.paragraphs[0]
  f.alignment=WD_ALIGN_PARAGRAPH.CENTER
  f.add_run('SmartStudy  |  EECS3311 Stage 2  |  Implementation evidence (not complete submission)').font.size=Pt(7.5)
footers()
doc.save(OUT)
print(OUT)
