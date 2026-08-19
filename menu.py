import os
import sys
import subprocess
from src.utils import txt,ext,is_ext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
class cmd:
    def _run(call,*agrs):
        call = os.path.join(BASE_DIR,call)
        subprocess.run([sys.executable,call,*agrs], cwd=BASE_DIR)

from src.configuration import TAR_LANG,LANGS,XTTS_TMP_VOICE
MENU = [
    ["Exiting program", None],
    ["Separation", "s0_demucs.py"],
    ["Transcribe", "s1_transcribe.py",'-c-bs 5', '-c-wt True', '-c-copt False', '-c-vf True'],
    ["Translate Subtitles", "s2_translates.py", f'-l "{','.join(LANGS)}"', '-s True'],
    ["Text to Speech", "s3_audio.py", f'-l "{','.join(LANGS)}"', '-p 1.39', '-a 1.25', '-v 2.0'],
    ["Text to AI Speech - XTTS", "s3.1_AI_speechs.py", f'-l {TAR_LANG}', f'-t {XTTS_TMP_VOICE}', '-mi true'],
    ["Word-Level SRT Generation", "s3.2_srt.py", f'-l "{','.join(LANGS)}"', '-w 1', '-c-bs 5', '-c-wt True', '-c-copt False', '-c-vf True'],
]
_line = '='*95
MENU_TITLE=f"""{_line}
{'\t'*5}VIDEO AUTO TRANS PIPELINE
{_line}
{'\n'.join(f'[{i}] {name} {script}({ps})' for i, (name,script,*ps) in enumerate(MENU))}\n{_line}"""
def get_input_path(current_path):
    if current_path: return current_path
    while True:
        txt.yellow('Drag and drop your file/folder here, then press Enter: ');path = input().strip()
        if path.startswith('"') and path.endswith('"'): path = path[1:-1]
        if os.path.exists(path): return path
        else:txt.yellow(f"[ERROR] Path does not exist: {path}. Please try again.")
from typing import Callable
def exec(item:tuple[str,Callable|None], input_path:list[str]|str):
    if not item[1]: sys.exit(0)
    txt.magenta(f"{'\t'*3}{item[0]}")
    if isinstance(input_path,list):
        sz=len(input_path)
        for i,path in enumerate(input_path,1):txt.cyan(f'[{i}/{sz}]: {path}');cmd._run(*item[1:],'-i', path)
    else:cmd._run(*item[1:],'-i', input_path)

from tabulate import tabulate
def main():
    input_path = [src for src in sys.argv if is_ext(src,ext.MEDIA)]
    err = ''
    while True:
        if not input_path: input_path = get_input_path(input_path)
        subprocess.call("clear||cls", shell=True)
        txt.cyan(tabulate(
            headers=['index', 'name', 'execute', *[f'p_{i}' for i in range(1,10,1)]],
            tabular_data=[[*m[:2],'-i',input_path,*m[2:]] if m[1] else m for m in MENU],
            tablefmt='grid',showindex=True
        ))
        txt.gray(f'[Active Input] {input_path}')
        if err: txt.red(err)
        choice = input(f'Please enter your choice (0-{len(MENU)-1}): ').strip()
        try:
            item = MENU[int(choice)]
            if item: exec(item,input_path)
            else: txt.yellow(f"Invalid option. Select between 0 and {len(MENU)-1}.")
        except Exception as e:err=e;continue
        err='';input("\nPress Enter to return to the menu...")

if __name__ == "__main__":main()