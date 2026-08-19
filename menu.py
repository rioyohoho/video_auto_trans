import os
import sys
import subprocess
from src.utils import txt,ext,is_ext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
class cmd:
    def _run(call,*agrs):
        call = os.path.join(BASE_DIR,call)
        subprocess.run([sys.executable,call,*agrs], cwd=BASE_DIR)
    def s0_demucs(p:str):
        cmd._run("s0_demucs.py", '-i', p)
    def s1_transcribe(p:str):
        cmd._run("s1_transcribe.py", '-i', p)
    def s2_translates(p:str):
        cmd._run("s2_translates.py", '-i', p)
    def s3_audio(p:str):
        cmd._run("s3_audio.py", '-i', p)
    def s3_1_AI_speechs(p:str):
        cmd._run("s3.1_AI_speechs.py", '-i', p)
    def s3_2_srt(p:str):
        cmd._run("s3.2_srt.py", '-i', p)
        


MENU = [
    ("Exiting program", None),
    ("Separation", cmd.s0_demucs),
    ("Transcribe", cmd.s1_transcribe),
    ("Translate Subtitles", cmd.s2_translates),
    ("Text to Speech", cmd.s3_audio),
    ("Text to AI Speech - XTTS", cmd.s3_1_AI_speechs),
    ("Word-Level SRT Generation", cmd.s3_2_srt),
]
_line = '='*95
MENU_TITLE=f"""{_line}
{'\t'*5}VIDEO AUTO TRANS PIPELINE
{_line}
{'\n'.join(f'[{i}] {name} ({script})' for i, (name,script) in enumerate(MENU))}\n{_line}"""
def get_input_path(current_path):
    if current_path: return current_path
    while True:
        txt.yellow('Drag and drop your file/folder here, then press Enter: ');path = input().strip()
        if path.startswith('"') and path.endswith('"'): path = path[1:-1]
        if os.path.exists(path): return path
        else:txt.yellow(f"[ERROR] Path does not exist: {path}. Please try again.")
from typing import Callable
def exec(item:tuple[str,Callable|None], input_path:list[str]|str):
    name,func=item
    if not func: sys.exit(0)
    txt.magenta(f"{'\t'*3}{name}")
    if isinstance(input_path,list):
        sz=len(input_path)
        for i,path in enumerate(input_path,1):txt.cyan(f'[{i}/{sz}]: {path}');func(path)
    else:func(input_path)

def main():
    input_path = [src for src in sys.argv if is_ext(src,ext.MEDIA)]
    err = ''
    while True:
        if not input_path: input_path = get_input_path(input_path)
        subprocess.call("clear||cls", shell=True)
        txt.cyan(MENU_TITLE)
        txt.gray(f'[Active Input] {input_path}')
        if err: txt.red(err)
        choice = input(f'Please enter your choice (0-{len(MENU)}): ').strip()
        try:
            item = MENU[int(choice)]
            if item: exec(item,input_path)
            else: txt.yellow(f"Invalid option. Select between 0 and {len(MENU)}.")
        except Exception as e:err=e;continue
        err='';input("\nPress Enter to return to the menu...")

if __name__ == "__main__":main()