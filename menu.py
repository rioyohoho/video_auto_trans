import os, sys, subprocess, shlex
from typing import Callable
from tabulate import tabulate
from src.utils import txt, ext, is_ext
from src.configuration import TAR_LANG, LANGS, XTTS_TMP_VOICE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class cmd:
    is_log = True
    def _run(call, *args):
        call = os.path.join(BASE_DIR, call)
        flat_args = [p.strip('"\'') for a in args for p in (shlex.split(a, posix=False) if isinstance(a, str) else [str(a)])]
        if cmd.is_log: txt.gray(f"[RUN] {call} {' '.join(flat_args)}")
        subprocess.run([sys.executable, call, *flat_args], cwd=BASE_DIR)

MENU = [
    ["Exiting program", None],
    ["Separation", "s0_demucs.py"],
    ["Transcribe", "s1_transcribe.py", f'-l "{TAR_LANG}"', '-c-bs 5', '-c-wt True', '-c-copt False', '-c-vf True'],
    ["Translate Subtitles", "s2_translates.py", f'-l "{','.join(LANGS)}"', '-s True'],
    ["Text to Speech", "s3_audio.py", f'-l "{','.join(LANGS)}"', '-p 1.39', '-a 1.25', '-v 2.0'],
    ["Text to AI Speech - XTTS", "s3.1_AI_speechs.py", f'-l "{TAR_LANG}"', f'-t {XTTS_TMP_VOICE}', '-mi true'],
    ["Word-Level SRT Generation", "s3.2_srt.py", f'-l "{','.join(LANGS)}"', '-w 1', '-c-bs 5', '-c-wt True', '-c-copt False', '-c-vf True'],
]
_line = '=' * 95
MENU_TITLE = f"{_line}\n{'\t'*5}VIDEO AUTO TRANS PIPELINE\n{_line}\n" + '\n'.join(f'[{i}] {name} {script}({ps})' for i, (name, script, *ps) in enumerate(MENU)) + f"\n{_line}"

def get_input_path(current_path):
    if current_path: return current_path
    while True:
        txt.yellow('Drag and drop your file/folder here, then press Enter: '); path = input().strip().strip('"')
        if os.path.exists(path): return path
        txt.yellow(f"[ERROR] Path does not exist: {path}. Please try again.")

def exec(item: tuple[str, Callable | None], input_path: list[str] | str):
    if not item[1]: sys.exit(0)
    txt.magenta(f"{'\t'*3}{item[0]}")
    if os.path.isdir(input_path):
        input_path = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]
    if isinstance(input_path, list):
        for i, path in enumerate(input_path, 1): txt.cyan(f'[{i}/{len(input_path)}]: {path}'); cmd._run(*item[1:], '-i', path)
    else: cmd._run(*item[1:], '-i', input_path)

def main():
    input_path = [src for src in sys.argv if is_ext(src, ext.MEDIA)]
    err = ''
    while True:
        if not input_path: input_path = get_input_path(input_path)
        subprocess.call("clear||cls", shell=True)
        txt.cyan(tabulate(
            headers=['index', 'name', 'execute', *[f'p_{i}' for i in range(1, 20)]],
            tabular_data=[[*m[:2], '-i', f'{input_path}\\*', *m[2:]] if m[1] else m for m in MENU],
            tablefmt='grid', showindex=True
        ))
        txt.gray(f'[Active Input] {input_path}')
        if err: txt.red(err)
        choice = input(f'Please enter your choice (0-{len(MENU)-1}): ').strip()
        try:
            item = MENU[int(choice)]
            if item: exec(item, input_path)
            else: txt.yellow(f"Invalid option. Select between 0 and {len(MENU)-1}.")
        except Exception as e: err = e; continue
        err = ''; input("\nPress Enter to return to the menu...")

if __name__ == "__main__":
    main()