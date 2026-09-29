import os, sys, subprocess, platform, pyperclip
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.widgets import Header, Footer, Label, Input, Checkbox, Button, RichLog, Select
from textual.events import Click
from rich.text import Text
from src.enties import agr, Canvas
from src.utils import handle_input
from src.configuration import TAR_LANG, LANGS, XTTS_TMP_VOICE, RENDER_CONFIG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AREA_OPTIONS = [
    ("BOTTOM (123)", str(Canvas.Area.BOTTOM.value)), ("TOP (789)", str(Canvas.Area.TOP.value)),
    ("CENTER (456)", str(Canvas.Area.CENTER.value)), ("BC (2)", str(Canvas.Area.BC.value)),
    ("TC (8)", str(Canvas.Area.TC.value)), ("BL (1)", str(Canvas.Area.BL.value)),
    ("BR (3)", str(Canvas.Area.BR.value)), ("TL (7)", str(Canvas.Area.TL.value)),
    ("TR (9)", str(Canvas.Area.TR.value)), ("CL (4)", str(Canvas.Area.CL.value)),
    ("CR (6)", str(Canvas.Area.CR.value)), ("CM (5)", str(Canvas.Area.CM.value)),
    ("DEFAULT (0)", str(Canvas.Area.DEFAULT.value))
]
DEFAULT_DATA = {
    "s0_demucs.py": ["Separation", [("-m", [("voc (Vocal)", "voc"), ("inst (Music)", "inst")])]],
    "s1_transcribe.py": ["Transcribe", [("-l", "auto"), ("-c-bs", 5), ("-c-wt", True), ("-c-copt", False), ("-c-vf", True)]],
    "s2_translates.py": ["Translate Subtitles", [("-l", ",".join(LANGS)), ("-m", [("0: Auto (G+AI)", "0"), ("1: Google Trans", "1"), ("2: Google AI", "2")]), ("-s", True)]],
    "s3_Google_speech.py": ["Google Speech", [("-l", ",".join(LANGS)), ("-p", 1.39), ("-a", 1.25), ("-v", 2.0)]],
    "s3_AI_speech.py": ["AI Speech - XTTS", [("-l", TAR_LANG), ("-t", str(XTTS_TMP_VOICE))]],
    "s4_srt.py": ["Word-Level SRT", [("-l", ",".join(LANGS)), ("-w", 5), ("-k", "#00aaff"), ("-c-bs", 5), ("-c-wt", True), ("-c-copt", False), ("-c-vf", True)]],
    "s5_ocr_delogo.py": ["OCR Delogo / Desub", [("-a", AREA_OPTIONS), ("-am", True), ("-tm", False)]],
    "s5.1_ocr_delogo_gui.py": ["GUI - Manual", [("-a", AREA_OPTIONS), ("-am", True), ("-tm", False)]],
    "s6_video_complex.py": ["Render Video Complex", [("-l", TAR_LANG), ("-c", str(RENDER_CONFIG)), ("-st", 0.0), ("-en", 0.0)]]
}

def resolve_input_path(init_path: str = None) -> str:
    if init_path and os.path.exists(init_path): return os.path.abspath(init_path)
    system = platform.system(); p = None
    if system == 'Windows':
        cmd = "Add-Type -AssemblyName System.Windows.Forms; $dlg = New-Object System.Windows.Forms.OpenFileDialog; $dlg.Filter = 'Video Files (*.mp4;*.avi;*.mkv)|*.mp4;*.avi;*.mkv|All Files (*.*)|*.*'; [void]$dlg.ShowDialog(); $dlg.FileName"
        p = subprocess.run(['powershell', '-Command', cmd], capture_output=True, text=True).stdout.strip()
    elif system == 'Darwin':
        p = subprocess.run(['osascript', '-e', 'POSIX path of (choose file of type {"public.movie"} with prompt "Chọn file video:")'], capture_output=True, text=True).stdout.strip()
    elif system == 'Linux':
        try: p = subprocess.run(['zenity', '--file-selection'], capture_output=True, text=True).stdout.strip()
        except: pass
    return os.path.abspath(p) if p and os.path.exists(p) else ''

class MenuApp(App):
    BINDINGS = [("q", "quit", "Quit"), ("escape", "quit", "Exit"), ("enter", "back_to_menu", "Back to Menu")]
    CSS = """
    Screen { background: #0f1117; }
    Header { background: #161922; color: #a1a1aa; height: 1; }
    Footer { background: #161922; height: 1; }
    #menu_view { height: 1fr; background: #161922; border: solid #27272a; padding: 1; }
    .top-bar { height: 3; padding: 0 1; background: #161922; border: solid #27272a; align: left middle; }
    .top-lbl { color: #00e5ff; text-style: bold; margin-right: 1; background: transparent; }
    #scroll_container { height: 1fr; background: transparent; }
    .task-row { height: 3; background: #161922; border: solid #27272a; align-vertical: middle; }
    .task-row:hover { background: #1e2332; border: solid #ffffff; }
    .task-cb { margin-right: 1; }
    .task-title { color: #00e5ff; text-style: bold; width: 22; background: transparent; height: 1; content-align: left middle; }
    .task-title:hover { color: #ffffff; text-style: bold underline; }
    .params-container { width: 1fr; height: 1; align: left middle; background: transparent; }
    .param-box { width: auto; height: 1; align: left middle; margin-right: 2; background: transparent; }
    .param-lbl { color: #71717a; margin-right: 1; background: transparent; height: 1; content-align: left middle; }
    .param-lbl:hover { color: #00e5ff; }
    Input { height: 1; min-height: 1; border: none; background: #222634; color: #ffffff; }
    Input:focus { background: #2d3345; color: #00e5ff; }
    Checkbox { height: 1; min-height: 1; border: none; background: transparent; padding: 0; min-width: 4; color: #52525b; }
    Checkbox.-on { color: #ff9800; text-style: bold; }
    Checkbox > .toggle--button { color: #52525b; background: transparent; }
    Checkbox.-on > .toggle--button { color: #ff9800; background: transparent; }
    Select { height: 1; min-height: 1; border: none; background: #222634; color: #ffffff; padding: 0; width: 20; }
    SelectCurrent { height: 1; min-height: 1; border: none; }
    .btn-run { min-width: 8; height: 1; min-height: 1; border: none; background: #22c55e; color: #000000; text-style: bold; margin-left: 1; }
    .btn-run:hover { background: #16a34a; }
    .btn-copy { min-width: 6; height: 1; min-height: 1; border: none; background: #eab308; color: #000000; text-style: bold; margin-left: 1; }
    .btn-copy:hover { background: #ca8a04; }
    .bottom-row { height: 1; background: transparent; }
    .bottom-left { width: 1fr; height: 1; align: left middle; background: transparent; }
    .btn-run-all { min-width: 10; height: 1; min-height: 1; border: none; background: #3b82f6; color: #ffffff; text-style: bold; margin-left: 2; }
    .btn-run-all:hover { background: #2563eb; }
    .btn-exit { min-width: 8; height: 1; min-height: 1; border: none; background: #ef4444; color: #000000; text-style: bold; }
    .btn-exit:hover { background: #dc2626; }
    #log_view { height: 1fr; background: #161922; border: solid #27272a; padding: 1; display: none; }
    RichLog { background: #0f1117; color: #d4d4d8; height: 1fr; }
    #log_bar { height: 1; align: center middle; background: #222634; color: #22c55e; text-style: bold; }
    """

    def __init__(self, input_path: str):
        super().__init__()
        self.input_path, self.controls, self.task_checks, self.label_targets, self.task_running = input_path, {}, {}, {}, False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="menu_view"):
            with Horizontal(classes="top-bar"):
                top_lbl = Label("Dropdown -l (LANGS):", classes="top-lbl")
                lang_opts = [(l, l) for l in LANGS]
                sel_top = Select(options=lang_opts, value=TAR_LANG if TAR_LANG in LANGS else (LANGS[0] if LANGS else "auto"), allow_blank=False, id="global_lang")
                self.label_targets[top_lbl] = sel_top
                yield top_lbl
                yield sel_top
            with VerticalScroll(id="scroll_container"):
                for script, (title, params) in DEFAULT_DATA.items():
                    self.controls[script] = []
                    with Horizontal(classes="task-row"):
                        cb_task = Checkbox(value=False, classes="task-cb")
                        self.task_checks[script] = cb_task
                        yield cb_task
                        t_lbl = Label(title, classes="task-title")
                        self.label_targets[t_lbl] = cb_task
                        yield t_lbl
                        with Horizontal(classes="params-container"):
                            for flag, val in params:
                                with Horizontal(classes="param-box"):
                                    p_lbl = Label(flag, classes="param-lbl")
                                    yield p_lbl
                                    if isinstance(val, bool):
                                        cb = Checkbox(value=val)
                                        self.controls[script].append((flag, cb, "bool"))
                                        self.label_targets[p_lbl] = cb
                                        yield cb
                                    elif isinstance(val, list):
                                        opts = [(str(k), str(v)) for k, v in val]
                                        sel = Select(options=opts, value=opts[0][1], allow_blank=False)
                                        self.controls[script].append((flag, sel, "select"))
                                        self.label_targets[p_lbl] = sel
                                        yield sel
                                    else:
                                        s_val = str(val)
                                        inp = Input(value=s_val)
                                        inp.styles.width = max(8, len(s_val) + 3)
                                        self.controls[script].append((flag, inp, "val"))
                                        self.label_targets[p_lbl] = inp
                                        yield inp
                        s_key = script.replace('.', '_')
                        yield Button("Run", id=f"btn_{s_key}", classes="btn-run")
                        yield Button("Copy", id=f"cp_{s_key}", classes="btn-copy")
            with Horizontal(classes="bottom-row"):
                with Horizontal(classes="bottom-left"):
                    yield Checkbox("All", id="cb_toggle_all", value=False)
                    yield Button("Run All", id="btn_run_all", classes="btn-run-all")
                yield Button("Exit", id="btn_exit", classes="btn-exit")
        with Vertical(id="log_view"):
            yield RichLog(id="console_log", wrap=True, highlight=False, markup=False)
            yield Label("⏳ Đang chạy... Vui lòng đợi.", id="log_bar")
        yield Footer()

    def build_cmd(self, script: str) -> list:
        args = [sys.executable, "-u", os.path.join(BASE_DIR, script), "-i", f'"{self.input_path}"' if ' ' in self.input_path else self.input_path]
        for flag, ctrl, ctype in self.controls.get(script, []):
            args.append(flag)
            val = str(ctrl.value) if ctype in ("bool", "select") else ctrl.value.strip('"\'')
            args.append(f'"{val}"' if ' ' in val else val)
        return args

    def on_click(self, event: Click) -> None:
        target = self.label_targets.get(event.widget)
        if target:
            if isinstance(target, Checkbox): target.value = not target.value
            else: target.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        event.input.styles.width = max(8, len(event.value) + 3)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "global_lang" and event.value != Select.BLANK:
            val = str(event.value)
            for script, params in self.controls.items():
                if script == "s1_transcribe.py": continue
                for flag, ctrl, ctype in params:
                    if flag == "-l":
                        if ctype == "val": ctrl.value = val
                        elif ctype == "select" and val in [opt[1] for opt in ctrl._options]: ctrl.value = val

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        cid = event.checkbox.id or ""
        if cid == "cb_toggle_all":
            for script, cb in self.task_checks.items():
                cb.value = (event.value and script not in ("s3_AI_speech.py", "s5.1_ocr_delogo_gui.py")) if event.value else False
        elif event.checkbox == self.task_checks.get("s3_Google_speech.py") and event.value:
            if "s3_AI_speech.py" in self.task_checks: self.task_checks["s3_AI_speech.py"].value = False
        elif event.checkbox == self.task_checks.get("s3_AI_speech.py") and event.value:
            if self.task_checks.get("s3_Google_speech.py", None) and self.task_checks["s3_Google_speech.py"].value:
                event.checkbox.value = False

    def action_back_to_menu(self) -> None:
        if not self.task_running and self.query_one("#log_view").display:
            self.query_one("#log_view").display = False
            self.query_one("#menu_view").display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn_exit": return self.exit()
        if btn_id == "btn_run_all":
            targets = [s for s, cb in self.task_checks.items() if cb.value]
            if "s3_Google_speech.py" in targets and "s3_AI_speech.py" in targets: targets.remove("s3_AI_speech.py")
            if targets: self.run_pipeline(targets)
            return
        for script in DEFAULT_DATA.keys():
            s_key = script.replace('.', '_')
            if btn_id == f"btn_{s_key}":
                self.run_pipeline([script])
                break
            elif btn_id == f"cp_{s_key}":
                cmd = " ".join(self.build_cmd(script))
                try: pyperclip.copy(cmd)
                except: subprocess.run("clip", input=cmd, text=True, shell=True)
                event.button.label = "✓"
                self.set_timer(1.2, lambda b=event.button: setattr(b, "label", "Copy"))
                break

    @work(thread=True)
    def run_pipeline(self, scripts: list) -> None:
        self.task_running = True
        log, bar = self.query_one(RichLog), self.query_one("#log_bar", Label)
        self.app.call_from_thread(log.clear)
        self.app.call_from_thread(setattr, self.query_one("#menu_view"), "display", False)
        self.app.call_from_thread(setattr, self.query_one("#log_view"), "display", True)
        total = len(scripts)
        for idx, script in enumerate(scripts, 1):
            self.app.call_from_thread(bar.update, f"⏳ [{idx}/{total}] Đang chạy {script}...")
            cmd_args = [sys.executable, "-u", os.path.join(BASE_DIR, script), "-i", self.input_path]
            for flag, ctrl, ctype in self.controls.get(script, []):
                cmd_args.append(flag)
                if ctype in ("bool", "select"): cmd_args.append(str(ctrl.value))
                else: cmd_args.append(ctrl.value.strip('"\''))
            sub_env = os.environ.copy()
            sub_env["PYTHONIOENCODING"], sub_env["PYTHONUTF8"] = "utf-8", "1"
            log.write(Text.from_ansi(f"\033[36m[START {idx}/{total}]\033[0m {' '.join(cmd_args)}\n"))
            proc = subprocess.Popen(cmd_args, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1, env=sub_env)
            for line in iter(proc.stdout.readline, ''):
                if not line: continue
                raw = line.rstrip('\r\n')
                if '\r' in line or '%"' in line or 'RENDERING' in line: self.app.call_from_thread(bar.update, Text.from_ansi(raw.strip()))
                else: log.write(Text.from_ansi(raw))
            proc.stdout.close(); proc.wait()
            color = "\033[32m" if proc.returncode == 0 else "\033[31m"
            log.write(Text.from_ansi(f"\n{color}[XONG {script}] Exit code: {proc.returncode}\033[0m\n\n"))
        self.task_running = False
        self.app.call_from_thread(bar.update, "✅ Đã xong toàn bộ! Nhấn ENTER để quay lại Menu")

if __name__ == '__main__':
    args = handle_input(agr(('-i', '--input'), default=None))
    target_path = resolve_input_path(args.input)
    MenuApp(input_path=target_path).run()