import re
from dataclasses import astuple,asdict
from src.enties import Transcribe,agr
from src.utils.text import str2bool
from src.modules.transcribe import mdl,C as trC
from src.utils import txt,w_json,w_text,to_srt,handle_input
from src.configuration import P_DIR,LANGS
from src.workspace import find_workspaces,Workspace

PUNCT=re.compile(r'[.,;:?!…]["\'”’)]?$')

def fmt_active(words:list[str],a:int,pri:str,sec:str="#FFFFFF")->str:
    f,l=a==0,a==len(words)-1
    pre,act,post=""if f else" ".join(words[:a]),(""if f else" ")+words[a]+(""if l else" "),""if l else" ".join(words[a+1:])
    return f'{f"""<font color="{sec}">{pre}</font>""" if pre else ""}<font color="{pri}">{act}</font>{f"""<font color="{sec}">{post}</font>""" if post else ""}'

def split_sentence_words(words:list[Transcribe],pause_th:float=0.45)->list[list[Transcribe]]:
    res,cur=[],[]
    for i,w in enumerate(words):
        cur.append(w)
        if(i==len(words)-1)or bool(PUNCT.search(w.text.strip()))or(words[i+1].start-w.end>=pause_th):
            res.append(cur);cur=[]
    return res

def run_word_srt(ws:Workspace,lang:str,words:int=1,primary_color:str=None,sec_color:str="#FFFFFF"):
    out_json,out_srt=ws.work_dir/f"{ws.stem}_S.{lang}.json",ws.work_dir/f"{ws.stem}_S.{lang}.srt"
    if out_json.exists()and out_json.stat().st_size>0 and out_srt.exists()and out_srt.stat().st_size>0:
        txt.magenta(f'[PASS] "{str(out_json)}"')
        txt.magenta(f'[PASS] "{str(out_srt)}"')
        return
    audio_target=ws.find_media_srt(lang)
    if primary_color:
        raw_words:list[Transcribe]=mdl.transcribe_length(str(audio_target),lang,1)
        for d in raw_words:d.text=re.sub(r'[,.!@?]','',d.text).strip()
        groups,n,data=split_sentence_words([w for w in raw_words if w.text]),max(1,words),[]
        for gw in groups:
            for i in range(0,len(gw),n):
                chunk=gw[i:i+n];text_list=[w.text for w in chunk]
                for k in range(len(chunk)):data.append(Transcribe(start=chunk[k].start,end=chunk[k].end,text=fmt_active(text_list,k,primary_color.upper(),sec_color.upper())))
    else:
        data:list[Transcribe]=mdl.transcribe_length(str(audio_target),lang,words)if words>0 else mdl.transcribe(str(audio_target),lang)
        if words==1:
            for d in data:d.text=re.sub(r'[,.!@?]','',d.text).strip()
    w_json(str(out_json),[asdict(d)for d in data])
    w_text(str(out_srt),to_srt([astuple(d)for d in data]))
    txt.green(f'[DONE]: "{str(out_json)}"')
    txt.green(f'[DONE]: "{str(out_srt)}"')

if __name__=='__main__':
    args=handle_input(
        agr(('-i','--input'),default=P_DIR),
        agr(('-l','--language'),default=','.join(LANGS)),
        agr(('-w','--words'),type=int,default=1),
        agr(('-k','--primary-color'),default=None),
        agr(('-c-bs','--beam_size'),type=int),
        agr(('-c-wt','--word_timestamps'),type=str2bool),
        agr(('-c-copt','--condition_on_previous_text'),type=str2bool),
        agr(('-c-vf','--vad_filter'),type=str2bool),
    )
    for k,v in list(vars(args).items())[4:]:
        if v is not None:setattr(trC,k,v)
    for ws in find_workspaces(args.input):
        for l in str(args.language).split(','):run_word_srt(ws,l.strip(),int(args.words),args.primary_color)