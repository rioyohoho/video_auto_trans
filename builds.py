import os
import json
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Footer, Header, Label, RichLog


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "apps"
BUILD_DIR = BASE_DIR / "build" / "pyinstaller"
TARGETS = [
    ("exec_soft_render.py", "Soft Render Pipeline"),
    ("exec.py", "Full Pipeline"),
    ("menu.py", "Menu"),
    ("s0_demucs.py", "s0 - Demucs"),
    ("s1_transcribe.py", "s1 - Transcribe"),
    ("s2_translates.py", "s2 - Translate"),
    ("s3_Google_speech.py", "s3 - Google Speech"),
    ("s3_AI_speech.py", "s3.1 - AI Speech"),
    ("s4_srt.py", "s4 - SRT"),
    ("s5_ocr_delogo.py", "s5 - OCR Delogo"),
    ("s5.1_ocr_delogo_gui.py", "s5.1 - Delogo GUI"),
    ("s6_video_complex.py", "s6 - Render Video"),
]
RUNTIME_ENV_KEYS = {
    "PATH_DIR", "RENDER_CONFIG", "FFMPEG_CONFIG", "SOFT_RENDER", "OCR_READER",
    "LANGS", "TAR_LANG", "UVR_MODEL", "UVR_DIR_PATH", "XTTS_TMP_VOICE",
    "XTTS_REPO_ID", "XTTS_DIR_PATH", "GEMINI_MODEL", "KEY_STATUS_PATH",
    "AUD_SPEECHS", "AUD_VOCAL", "AUD_MUSIC",
}


class BuildApp(App):
    TITLE = "Build Pipeline EXE"
    CSS = """
    Screen { background: #10151b; }
    #body { padding: 1 2; height: 1fr; }
    #title { color: #43d9a3; text-style: bold; margin-bottom: 1; }
    #target_list { height: 1fr; border: solid #34434c; padding: 0 1; }
    Checkbox { height: 1; margin: 0; }
    #actions { height: 3; align: left middle; }
    Button { margin-right: 1; }
    #build_button { background: #147d64; }
    #log { height: 1fr; border: solid #34434c; }
    #status { height: 1; color: #43d9a3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.target_checks: dict[str, Checkbox] = {}
        self.is_building = False
        self.build_button: Button | None = None
        self.log_widget: RichLog | None = None
        self.status_widget: Label | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="body"):
            yield Label("Chọn chương trình cần đóng gói", id="title")
            with Horizontal(id="actions"):
                yield Checkbox("Chọn tất cả", id="select_all")
                self.build_button = Button("Build đã chọn", id="build_button", variant="success")
                yield self.build_button
                yield Button("Xóa log", id="clear_button")
                yield Button("Thoát", id="exit_button", variant="error")
            with VerticalScroll(id="target_list"):
                for script, title in TARGETS:
                    widget_id = Path(script).stem.replace(".", "_")
                    checkbox = Checkbox(f"{title}  [{Path(script).stem}.exe]", value=False, id=f"target_{widget_id}")
                    self.target_checks[script] = checkbox
                    yield checkbox
            self.log_widget = RichLog(id="log", wrap=True, markup=False)
            yield self.log_widget
            self.status_widget = Label("Sẵn sàng", id="status")
            yield self.status_widget
        yield Footer()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "select_all":
            for checkbox in self.target_checks.values():
                checkbox.value = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "exit_button":
            self.exit()
        elif button_id == "clear_button":
            self.query_one("#log", RichLog).clear()
        elif button_id == "build_button" and not self.is_building:
            selected = [script for script, checkbox in self.target_checks.items() if checkbox.value]
            if not selected:
                self.notify("Hãy chọn ít nhất một chương trình.", severity="warning")
                return
            self.build_targets(selected)

    def build_command(self, script: str) -> list[str]:
        name = Path(script).stem
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            name,
            "--distpath",
            str(OUTPUT_DIR),
            "--workpath",
            str(BUILD_DIR / "work" / name),
            "--specpath",
            str(BUILD_DIR / "spec"),
            "--paths",
            str(BASE_DIR),
        ]
        for data_file in sorted((BASE_DIR / "assets").glob("*.json")):
            command.extend(["--add-data", f"{data_file}{os.pathsep}assets"])
        env_values = {
            key: value
            for key, value in dotenv_values(BASE_DIR / ".env").items()
            if key in RUNTIME_ENV_KEYS and value is not None
        }
        if env_values:
            env_file = BUILD_DIR / "runtime" / ".env"
            env_file.parent.mkdir(parents=True, exist_ok=True)
            env_file.write_text(
                "\n".join(f"{key}={json.dumps(value)}" for key, value in env_values.items()),
                encoding="utf-8",
            )
            command.extend(["--add-data", f"{env_file}{os.pathsep}."])
        if script == "exec_soft_render.py":
            command.extend(["--add-data", f"{BASE_DIR / 'exec.py'}{os.pathsep}."])
        command.append(str(BASE_DIR / script))
        return command

    @work(thread=True, exclusive=True)
    def build_targets(self, scripts: list[str]) -> None:
        self.is_building = True
        self.app.call_from_thread(setattr, self.build_button, "disabled", True)
        self.app.call_from_thread(self.log_widget.clear)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        success_count = 0

        for index, script in enumerate(scripts, start=1):
            command = self.build_command(script)
            self.app.call_from_thread(
                self.status_widget.update,
                f"Đang build {index}/{len(scripts)}: {Path(script).stem}.exe",
            )
            self.app.call_from_thread(self.log_widget.write, f"\n>>> {' '.join(command)}")
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "utf-8"
            try:
                process = subprocess.Popen(
                    command,
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=environment,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    self.app.call_from_thread(self.log_widget.write, line.rstrip())
                return_code = process.wait()
            except OSError as error:
                return_code = 1
                self.app.call_from_thread(self.log_widget.write, f"Không chạy được PyInstaller: {error}")

            if return_code == 0:
                success_count += 1
                self.app.call_from_thread(self.log_widget.write, f"OK: {OUTPUT_DIR / (Path(script).stem + '.exe')}")
            else:
                self.app.call_from_thread(self.log_widget.write, f"LỖI: build {script} thất bại (exit code {return_code}).")

        self.is_building = False
        self.app.call_from_thread(setattr, self.build_button, "disabled", False)
        self.app.call_from_thread(
            self.status_widget.update,
            f"Hoàn tất: {success_count}/{len(scripts)} build thành công. Thư mục đầu ra: {OUTPUT_DIR}",
        )


if __name__ == "__main__":
    BuildApp().run()