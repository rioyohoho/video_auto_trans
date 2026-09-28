import sys,traceback
from dataclasses import asdict
from video_auto_trans.src.enties import agr,Transcribe
from video_auto_trans.src.utils import txt,handle_input,cal_time,w_json
from video_auto_trans.src.utils.text import str2bool
from video_auto_trans.src.modules import transcribe
from video_auto_trans.src.configuration import P_DIR
from video_auto_trans.src.workspace import find_workspaces,Workspace

def run(ws:Workspace,language:str=None):
    if ws.origin_json.exists()and ws.origin_json.stat().st_size>0:return txt.magenta(f'[PASS] "{str(ws.origin_json)}"')
    source_audio=ws.find_transcribe_audio()
    target_lang=None if not language or language.lower()in('auto','none','')else language
    try:
        c=transcribe.mdl
        c1=getattr(transcribe.C,'_call')
        if not c1 or c1==0 or c1=='transcribe':call=c.transcribe
        elif c1==1 or c1=='transcribe_length':call=c.transcribe_length
        elif c1==2 or c1=='transcribe_range':call=c.transcribe_range
        else:call=c.transcribe
        txt.cyan(f'[Callable]({c1}) {call}')
        data:list[Transcribe]=cal_time(lambda:call(str(source_audio),language=target_lang),f'Transcribing {ws.stem} using {source_audio.name}',tab=1)
        w_json(ws.origin_json,[asdict(d)for d in data])
        txt.green(f'[DONE]: "{str(ws.origin_json)}"')
    except Exception as e:traceback.print_exception(e)

if __name__=='__main__':
    args=handle_input(
        agr(('-i','--input'),default=P_DIR),
        agr(('-l','--language'),type=str,default='auto'),
        agr(('-c','--_call'),default='transcribe'),
        agr(('-c-bs','--beam_size'),type=int),
        agr(('-c-wt','--word_timestamps'),type=str2bool),
        agr(('-c-copt','--condition_on_previous_text'),type=str2bool),
        agr(('-c-vf','--vad_filter'),type=str2bool),
    )
    for k,v in list(vars(args).items())[2:]:
        if v is not None:setattr(transcribe.C,k,v)
    workspaces=find_workspaces(args.input)
    if not workspaces:sys.exit(0)
    for ws in workspaces:
        txt.cyan(f"Transcribe: {ws.stem}")
        run(ws,language=args.language)