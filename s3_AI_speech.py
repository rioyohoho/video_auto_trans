import hashlib,re
from pathlib import Path
from src.modules.speech_AI import XTTSProcessor
from src.modules import speech_G as mdl
from src.enties import Clip_Audio,Source,Transcribe,agr
from src.utils import txt,r_json,r_text,handle_input,get_media_duration,cal_time,str2bool
from src.configuration import PATH_BASE,P_DIR,TAR_LANG,XTTS_TMP_VOICE
from src.workspace import find_workspaces,Workspace

processor=cal_time(lambda:XTTSProcessor(),'LOAD: XTTSProcessor',1,1)

def parse_segments(p:Path)->list[Transcribe]:
    if not p.exists():return []
    if p.suffix=='.json':return[Transcribe.parse(x)for x in r_json(str(p))if isinstance(x,dict)and str(x.get('text','')).strip()]
    return[Transcribe(start=0.0,end=0.0,text=s.strip())for s in re.split(r'[,.;\n]',r_text(str(p)))if s.strip()]

def run_tts(ws:Workspace,lang:str,tmp_voice:Path):
    out_m=ws.mixed_audio(lang,fmt='wav',mode='AI')
    if out_m.exists()and out_m.stat().st_size>0:return txt.magenta(f'[PASS] "{str(out_m)}"')
    doc=ws.find_speech_doc(lang,mode='AI')
    if not doc:return txt.yellow(f"[MISSING] No DOC found for {ws.stem} (Lang: {lang})")
    out_wav,seg_dir=ws.tts_audio(lang,fmt='wav',mode='AI'),ws.tts_dir(lang,mode='AI')
    segments=parse_segments(doc)
    if not segments:return
    seg_dir.mkdir(parents=True,exist_ok=True)
    peechs:list[Clip_Audio]=[]
    for s in segments:
        text_to_read=s.text.strip()
        if not text_to_read.endswith(('.',',','!','?')):text_to_read+='.'
        txt_hash=hashlib.md5(text_to_read.encode('utf-8')).hexdigest()[:6]
        seg_path=seg_dir/f"{s.end:.3f}_{s.start:.3f}_{txt_hash}.wav"
        if not seg_path.exists()or seg_path.stat().st_size==0:
            speeches=processor.text_to_ai_speeches([text_to_read],language=lang,tmp_voice=str(tmp_voice))
            if not speeches:continue
            tensor=processor.concat(speeches)
            processor.save(seg_path,tensor)
            actual_dur=tensor.shape[-1]/24000.0
        else:actual_dur=get_media_duration(seg_path)
        ns,ne=round(s.start,3),round(s.start+actual_dur,3)
        peechs.append(Clip_Audio(start=ns,end=ne,source=Source(start=0.0,end=actual_dur,path=str(seg_path))))
    if not peechs:return
    combined_path,_=mdl.combine_audio_files(peechs,out_wav,auto_speed=any(s.end>0 for s in segments))
    mus,voc=ws.find_music(),ws.find_vocal()
    if combined_path and mus:
        mixes=[Clip_Audio(source=Source(path=str(mus),end=get_media_duration(str(mus))),volume=.5),Clip_Audio(source=Source(path=str(combined_path),end=get_media_duration(str(combined_path))),volume=2.0)]
        if voc:mixes.insert(1,Clip_Audio(source=Source(path=str(voc),end=get_media_duration(str(voc))),volume=.25))
        try:
            mdl.mix_audio_files(mixes,out_m)
            txt.green(f'[DONE]: "{str(out_m)}"')
        except Exception as e:txt.yellow(f"Mix error: {e}")

if __name__=='__main__':
    args=handle_input(
        agr(('-i','--input'),type=str,default=P_DIR),
        agr(('-o','--output'),type=str,default=''),
        agr(('-t','--temple'),type=str,default=XTTS_TMP_VOICE),
        agr(('-l','--language'),type=str,default=TAR_LANG),
        agr(('-mi','--min'),type=str2bool,default='true'),
        agr(('-bs','--by_segment'),type=str2bool,default='true')
    )
    t=Path(args.temple)
    if not t.is_absolute():t=PATH_BASE/t
    for ws in find_workspaces(args.input):run_tts(ws,args.language,t)