# Local feature demonstration evidence

The videos in this folder were captured from the runnable application, with synthetic data. They are **not** public GitHub/video URLs, and they are **not** a substitute for complete instructor-accessible recordings of all required features.

- `gui_walkthrough.mp4` (~58 seconds): actual Tkinter GUI interactions; offline `TestLLM` is used for AI examples, **NOT** a real provider. Feature segments: F02 ~00:04-00:14, F05 ~00:14-00:17, F08 ~00:17-00:20, F07 ~00:20-00:28, F06 ~00:23-00:31, F09 ~00:31-00:35, F11 ~00:35-00:38 simulated AI, F04 ~00:38-00:43 simulated AI, F01 ~00:43-00:48 simulated AI, F10/F12 settings ~00:48-00:53.
- `cli_walkthrough.mp4` (~36 seconds): real xterm executing the actual Python CLI against a temporary SQLite database. Demonstrates CLI creation, ranking, commitments, availability, planning, approval, task progress and status. Late commands including export may not be captured in the trimmed local recording.

**Still needed for a complete Stage 2 submission:** actual LLM API request with your local key (F01/F03/F04/F11); PDF import video (F03); due reminder alert (F10); complete export demonstration (F12); relevant alternative/error cases; exact accessible video links and timestamps in your public GitHub repository; any additional requirements from your instructor. Do not expose `.env` or tokens when filming.

The recording scripts (`record_gui_demo.py`, `record_cli_demo.py`, `terminal_walkthrough.sh`) are optional utilities for Linux with Xvfb/ffmpeg/Pillow/xterm; they are **not** required to run SmartStudy. Their use of an injected test double is disclosed in the GUI output itself.
