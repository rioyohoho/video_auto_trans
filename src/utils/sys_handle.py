import os,sys,time,subprocess
from pathlib import Path
from typing import Callable, Any, Iterable
from src.configuration import ext

def execute_after_countdown(exec_in=3,exec_sys:str|Callable=lambda:0):
	B=exec_sys;A=exec_in;print(f"Execute command: '{B}' in {A} senconds.")
	try:
		for C in range(A,0,-1):sys.stdout.write(f"\rTimeout: {C}s ... ");sys.stdout.flush();time.sleep(1)
		print('\nExecuting...')
		if isinstance(exec_sys,str):subprocess.run(exec_sys, shell=True)
		elif callable(exec_sys):exec_sys()
	except KeyboardInterrupt:print('\nCancel by user.')
exec_in = execute_after_countdown

import argparse
from dataclasses import dataclass, asdict
@dataclass
class agr:
    name_or_flags: list[str] | str
    action: str | type[argparse.Action] | None = None
    nargs: int | str | None = None
    const: Any = None
    default: Any = None
    type: Callable[[str], Any] | None = None
    choices: Iterable[Any] | None = None
    required: bool | None = None
    help: str | None = None
    metavar: str | tuple[str, ...] | None = None
    dest: str | None = None

def handle_input(*args: agr):
    parser = argparse.ArgumentParser(description=__file__)
    for a in args:
        config = asdict(a)
        name_or_flags = config.pop('name_or_flags')
        if isinstance(name_or_flags, str):flags = [name_or_flags]
        else:flags = name_or_flags
        clean_config = {k: v for k, v in config.items() if v is not None}
        parser.add_argument(*flags, **clean_config)
    parsed_args:argparse.Namespace = parser.parse_args()
    return parsed_args

def is_ext(path:str,exts:list[str]=ext.AUDIO+ext.VIDEO):return path.lower().endswith(exts)
def listFilter(source:Path,exts:tuple=ext.AUDIO+ext.VIDEO)->list[str]:
	if not source.exists():return[]
	all_files=[f for f in os.listdir(source) if is_ext(f,exts)];AUDIO_EXT=ext.AUDIO;file_dict={}
	for f in all_files:
		path_obj=Path(f);stem=path_obj.stem.lower();ext_name=path_obj.suffix.lower()
		if stem not in file_dict:file_dict[stem]=f
		else:
			current_ext=Path(file_dict[stem]).suffix.lower()
			if ext_name in AUDIO_EXT and current_ext not in AUDIO_EXT:file_dict[stem]=f
	return list(file_dict.values())

