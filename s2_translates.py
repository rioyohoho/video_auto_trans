import sys
from pathlib import Path
from dataclasses import asdict,astuple
from src.enties import agr,Transcribe
from src.utils import txt,r_json,w_json,w_text,to_srt,handle_input,cal_time,filter_bad_words
from src.utils.text import str2bool
from src.modules.translate_G import translates,text_translation,ai_translation
from src.modules.translate_L import local_translation
from src.configuration import P_DIR,LANGS,TAR_LANG,PATH_BASE
from src.workspace import find_workspaces,Workspace,Model,TransModel

RE_WORDS:dict=cal_time(lambda:r_json(str(PATH_BASE/f'assets/replace_bad_words.{TAR_LANG}.json')),'Load bad_words',clear=1)

def find_existing_trans(ws:Workspace,lang:str,ext_name:str)->Path|None:
    candidates=[ws.work_dir/f"{ws.stem}_{m.value}.{lang}.{ext_name}"for m in Model if m.value]+[ws.work_dir/f"{ws.stem}.{lang}.{ext_name}"]
    for p in candidates:
        if p.exists()and p.stat().st_size>0:return p
    return None

def translate_workspace(ws:Workspace,lang:str,model_type:int=0,with_srt:bool=True):
    if not ws.origin_json.exists():return txt.yellow(f"[MISSING] Not found {ws.origin_json.name}")
    ex_json=find_existing_trans(ws,lang,'json')
    ex_srt=find_existing_trans(ws,lang,'srt')if with_srt else True
    if ex_json and ex_srt:
        txt.magenta(f'[PASS] "{str(ex_json)}"')
        if with_srt:txt.magenta(f'[PASS] "{str(ex_srt)}"')
        return
    out_json=ws.trans_file(lang,'json',model_type)
    out_srt=ws.trans_file(lang,'srt',model_type)
    data:list[Transcribe]=[Transcribe(**d)for d in r_json(str(ws.origin_json))]
    lines=[d.text for d in data]
    if model_type==TransModel.G_TRAN.value:texts=cal_time(lambda:text_translation(lines,tar_lang=lang),f'Google Translate to {lang}',tab=1,clear=1)
    elif model_type==TransModel.AI_TRAN.value:
        res=cal_time(lambda:ai_translation(lines,tar_lang=lang),f'Google AI Translate to {lang}',tab=1,clear=1)
        texts=res.split('\n')if res else cal_time(lambda:text_translation(lines,tar_lang=lang),f'Fallback Google Translate to {lang}',tab=1,clear=1)
    elif model_type==TransModel.L_TRAN.value:texts=cal_time(lambda:local_translation(lines,tar_lang=lang),f'Local Translate to {lang}',tab=1,clear=1)
    else:texts=cal_time(lambda:translates(texts=lines,tar_lang=lang),f'Translate to {lang}',tab=1,clear=1)
    texts=filter_bad_words(texts,RE_WORDS.get(lang))
    for d,tx in zip(data,texts):d.text=tx
    w_json(str(out_json),[asdict(d)for d in data])
    txt.green(f'[DONE]: "{str(out_json)}"')
    if with_srt:
        w_text(str(out_srt),to_srt([astuple(d)for d in data]))
        txt.green(f'[DONE]: "{str(out_srt)}"')

if __name__=='__main__':
    args=handle_input(
        agr(('-i','--input'),type=str,default=P_DIR),
        agr(('-l','--language'),type=str,default=','.join(LANGS)),
        agr(('-m','--model'),type=int,default=3),
        agr(('-s','--srt'),type=str2bool,default=True),
    )
    langs,workspaces=str(args.language).split(','),find_workspaces(args.input)
    if not workspaces:sys.exit(0)
    for ws in workspaces:
        txt.cyan(f"Translating: {ws.stem}")
        for l in langs:translate_workspace(ws,l.strip(),model_type=int(args.model),with_srt=bool(args.srt))