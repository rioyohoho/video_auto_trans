import os,sys,subprocess,platform
from pathlib import Path
from video_auto_trans.src.enties import agr,Canvas
from video_auto_trans.src.utils import handle_input,ext,txt
from video_auto_trans.src.configuration import TAR_LANG,LANGS,XTTS_TMP_VOICE,RENDER_CONFIG
from video_auto_trans.src.workspace import Model,TransModel

IS_NEW_CMD_WINDOWN = False
BASE_DIR=os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA={
    "s0_demucs.py":[("-m","voc")],
    "s1_transcribe.py":[("-l","auto"),("-c-bs",5),("-c-wt",True),("-c-copt",False),("-c-vf",True)],
    "s2_translates.py":[("-l",",".join(LANGS)),("-m",TransModel.L_TRAN.value),("-s",True)],
    "s3_Google_speech.py":[("-l",",".join(LANGS)),("-p",1.39),("-a",1.25),("-v",2.0)],
    "s3_AI_speech.py":[("-l",TAR_LANG),("-t",str(XTTS_TMP_VOICE))],
    "s4_srt.py":[("-l",",".join(LANGS)),("-w",5),("-k","#00aaff"),("-c-bs",5),("-c-wt",True),("-c-copt",False),("-c-vf",True)],
    "s5_ocr_delogo.py":[("-a",str(Canvas.Area.BOTTOM.value)),("-am",True),("-tm",True)],
    "s5.1_ocr_delogo_gui.py":[("-a",str(Canvas.Area.BOTTOM.value)),("-am",True),("-tm",False)],
    "s6_video_complex.py":[("-l",TAR_LANG),("-c",str(RENDER_CONFIG)),("-st",0.0),("-en",0.0)]
}

def str2bool(v):
    if isinstance(v,bool):return v
    if str(v).strip().lower()in('yes','true','t','y','1'):return True
    return False

def is_final_file(path_str:str)->bool:
    stem=Path(path_str).stem.lower()
    return stem.endswith(f"_{TAR_LANG.lower()}_final")or stem.endswith("_final")

def resolve_input_path(init_path:str=None)->str:
    if init_path and os.path.exists(init_path):return os.path.abspath(init_path)
    system,p=platform.system(),None
    if system=='Windows':
        cmd="Add-Type -AssemblyName System.Windows.Forms; $dlg = New-Object System.Windows.Forms.OpenFileDialog; $dlg.Filter = 'Video Files (*.mp4;*.avi;*.mkv)|*.mp4;*.avi;*.mkv|All Files (*.*)|*.*'; [void]$dlg.ShowDialog(); $dlg.FileName"
        p=subprocess.run(['powershell','-Command',cmd],capture_output=True,text=True).stdout.strip()
    elif system=='Darwin':p=subprocess.run(['osascript','-e','POSIX path of (choose file of type {"public.movie"} with prompt "Select video file:")'],capture_output=True,text=True).stdout.strip()
    elif system=='Linux':
        try:p=subprocess.run(['zenity','--file-selection'],capture_output=True,text=True).stdout.strip()
        except:pass
    return os.path.abspath(p)if p and os.path.exists(p)else''

def collect_video_paths(init_input)->list:
    video_exts=tuple(getattr(ext,'VIDEO',('.mp4','.mkv','.avi','.mov')))
    items=[]
    if isinstance(init_input,(list,tuple)):items=list(init_input)
    elif isinstance(init_input,str):
        if','in init_input:items=[x.strip()for x in init_input.split(',')if x.strip()]
        elif';'in init_input:items=[x.strip()for x in init_input.split(';')if x.strip()]
        else:items=[init_input.strip()]
    elif not init_input:
        single_path=resolve_input_path()
        if single_path:items=[single_path]
    valid_videos=[]
    for path_str in items:
        if not path_str:continue
        p=os.path.abspath(path_str.strip('"\''))
        if os.path.isdir(p):
            for root,_,files in os.walk(p):
                for f in files:
                    if f.lower().endswith(video_exts)and not is_final_file(f):
                        valid_videos.append(os.path.join(root,f))
        elif os.path.isfile(p):
            if p.lower().endswith(video_exts)and not is_final_file(p):
                valid_videos.append(p)
    return list(dict.fromkeys(valid_videos))

def build_cmd(script:str,input_path:str)->list:
    args=[sys.executable,"-u",os.path.join(BASE_DIR,script),"-i",input_path]
    for flag,val in DEFAULT_DATA.get(script,[]):args.extend([flag,str(val)])
    return args

def find_first_existing(wdir:Path,candidates:list[str])->Path|None:
    for name in candidates:
        p=wdir/name
        if p.exists()and p.stat().st_size>0:return p
    return None

def get_expected_outputs(script:str,video_path:str)->list[Path]:
    p=Path(video_path).resolve();stem=p.stem;wdir=p.parent/stem
    cfg_dict=dict(DEFAULT_DATA.get(script,[]))
    langs=[l.strip()for l in cfg_dict.get('-l',TAR_LANG).split(',')if l.strip()]
    if script=="s0_demucs.py":return[wdir/f"{stem}_vocal.mp3",wdir/f"{stem}_music.mp3"]
    if script=="s1_transcribe.py":return[wdir/f"{stem}.json"]
    if script=="s2_translates.py":
        outs=[]
        for l in langs:
            j_cand=[f"{stem}_{m.value}.{l}.json"for m in Model if m.value]+[f"{stem}.{l}.json"]
            s_cand=[f"{stem}_{m.value}.{l}.srt"for m in Model if m.value]+[f"{stem}.{l}.srt"]
            outs.append(find_first_existing(wdir,j_cand)or(wdir/f"{stem}.{l}.json"))
            outs.append(find_first_existing(wdir,s_cand)or(wdir/f"{stem}.{l}.srt"))
        return outs
    if script=="s3_Google_speech.py":return[wdir/f"{stem}_G.{l}_mixed.mp3"for l in langs]
    if script=="s3_AI_speech.py":return[wdir/f"{stem}_AI.{l}_mixed.wav"for l in langs]
    if script=="s4_srt.py":
        outs=[]
        for l in langs:outs.extend([wdir/f"{stem}_S.{l}.json",wdir/f"{stem}_S.{l}.srt"])
        return outs
    if script in("s5_ocr_delogo.py","s5.1_ocr_delogo_gui.py"):return[wdir/"blurs.json"]
    if script=="s6_video_complex.py":return[p.parent/f"{stem}_{l}_final.mp4"for l in langs]
    return[]

def check_outputs_exist(paths:list[Path])->bool:
    if not paths:return False
    return all(p.exists()and p.stat().st_size>0 for p in paths)

def run_cmd(cmd_args:list,script_name:str,new_window:bool=False)->int:
    system=platform.system()
    txt.cyan(f"\n=======================================================")
    txt.cyan(f"⏳ RUNNING: {script_name}")
    txt.gray(f"{' '.join(cmd_args)}")
    txt.cyan(f"=======================================================")
    if not new_window:
        return subprocess.run(cmd_args).returncode
    if system=='Windows':
        cli=f'title [Running] {script_name} && '+subprocess.list2cmdline(cmd_args)
        return subprocess.run(['cmd.exe','/c',cli],creationflags=subprocess.CREATE_NEW_CONSOLE).returncode
    elif system=='Darwin':
        temp_cmd=" ".join([f'"{c}"'if" "in c else c for c in cmd_args])
        apple_script=f'''tell application "Terminal"
set newTab to do script "{temp_cmd}; exit"
repeat
delay 1
if not (exists newTab) then exit repeat
set isBusy to busy of newTab
if not isBusy then
close (first window whose tabs contains newTab) saving no
exit repeat
end if
end repeat
end tell'''
        return subprocess.run(['osascript','-e',apple_script]).returncode
    else:
        try:return subprocess.run(['xterm','-title',script_name,'-e']+cmd_args).returncode
        except FileNotFoundError:return subprocess.run(cmd_args).returncode

def main():
    args=handle_input(
        agr(default=None,name_or_flags=('-i','--input')),
        agr(default=1,name_or_flags=('-s0','--s0_demucs'),type=str2bool),
        agr(default=1,name_or_flags=('-s1','--s1_transcribe'),type=str2bool),
        agr(default=1,name_or_flags=('-s2','--s2_translates'),type=str2bool),
        agr(default=1,name_or_flags=('-s3','--s3_Google_speech'),type=str2bool),
        agr(default=0,name_or_flags=('-s3.1','--s3_AI_speech'),type=str2bool),
        agr(default=1,name_or_flags=('-s4','--s4_srt'),type=str2bool),
        agr(default=1,name_or_flags=('-s5','--s5_ocr_delogo'),type=str2bool),
        agr(default=0,name_or_flags=('-s5.1','--s5.1_ocr_delogo_gui'),type=str2bool),
        agr(default=1,name_or_flags=('-s6','--s6_video_complex'),type=str2bool),
        agr(default=IS_NEW_CMD_WINDOWN,name_or_flags=('-nw','--new_window'),type=str2bool)
    )
    video_list=collect_video_paths(args.input)
    if not video_list:
        txt.red("❌ Error: No valid video files selected or found.")
        sys.exit(1)
    pipeline_map=[
        (getattr(args,'s0_demucs',None),"s0_demucs.py"),
        (getattr(args,'s1_transcribe',None),"s1_transcribe.py"),
        (getattr(args,'s2_translates',None),"s2_translates.py"),
        (getattr(args,'s3_Google_speech',None),"s3_Google_speech.py"),
        (getattr(args,'s3_AI_speech',None),"s3_AI_speech.py"),
        (getattr(args,'s4_srt',None),"s4_srt.py"),
        (getattr(args,'s5_ocr_delogo',None),"s5_ocr_delogo.py"),
        (getattr(args,'s5.1_ocr_delogo_gui',None),"s5.1_ocr_delogo_gui.py"),
        (getattr(args,'s6_video_complex',None),"s6_video_complex.py"),
    ]
    selected_tasks=[script for is_enabled,script in pipeline_map if is_enabled]
    if"s3_Google_speech.py"in selected_tasks and"s3_AI_speech.py"in selected_tasks:selected_tasks.remove("s3_AI_speech.py")
    if not selected_tasks:
        txt.yellow("⚠️ Warning: No tasks enabled to execute.")
        return
    size,total_tasks=len(video_list),len(selected_tasks)
    for i,video_path in enumerate(video_list,1):
        txt.yellow(f'[{i}/{size}] "{video_path}"')
        for idx,script in enumerate(selected_tasks,1):
            expected_outs=get_expected_outputs(script,video_path)
            if check_outputs_exist(expected_outs):
                for p_out in expected_outs:txt.magenta(f'[PASS] "{str(p_out)}"')
                continue
            cmd_args=build_cmd(script,video_path)
            txt.white(f"🚀 [{idx}/{total_tasks}] Launching: {script}")
            exit_code=run_cmd(cmd_args,script,new_window=bool(args.new_window))
            if exit_code!=0:txt.red(f"❌ Process {script} failed (Exit code: {exit_code})")
            else:
                for p_out in get_expected_outputs(script,video_path):
                    if p_out.exists()and p_out.stat().st_size>0:txt.green(f'[DONE]: "{str(p_out)}"')
                txt.green(f"✅ Completed successfully: {script}")
    txt.cyan("\n🎉 ALL PIPELINE TASKS COMPLETED FOR ALL VIDEOS!")

if __name__=='__main__':main()