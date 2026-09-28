import re, hashlib
from pathlib import Path
from video_auto_trans.src.modules import speech_G as mdl
from video_auto_trans.src.enties import Clip_Audio,Source,Transcribe,agr
from video_auto_trans.src.utils import txt,r_json,r_text,handle_input,get_media_duration
from video_auto_trans.src.configuration import P_DIR,LANGS
from video_auto_trans.src.workspace import find_workspaces,Workspace

def parse_segments(p:Path)->list[Transcribe]:
    if not p.exists():return []
    if p.suffix=='.json':return[Transcribe.parse(x)for x in r_json(str(p))if isinstance(x,dict)and str(x.get('text','')).strip()]
    return[Transcribe(start=0.0,end=0.0,text=s.strip())for s in re.split(r'[,.;\n]',r_text(str(p)))if s.strip()]

def run_tts(ws:Workspace,lang:str,pitch:float=1.39,tempo:float=1.25,volume:float=2.0,mode:str='G',tmp_voice:Path=None,processor=None):
    fmt='wav'if mode=='AI'else'mp3'
    out_mixed=ws.mixed_audio(lang,fmt=fmt,mode=mode)
    if out_mixed.exists()and out_mixed.stat().st_size>0:return txt.magenta(f'[PASS] "{str(out_mixed)}"')
    doc=ws.find_speech_doc(lang,mode=mode)
    if not doc:return txt.yellow(f"[MISSING] No DOC found for {ws.stem} (Lang: {lang})")
    segments=parse_segments(doc)
    if not segments:return
    out_audio,seg_dir=ws.tts_audio(lang,fmt=fmt,mode=mode),ws.tts_dir(lang,mode=mode)
    seg_dir.mkdir(parents=True,exist_ok=True)
    if mode=='AI':
        peechs=[]
        for s in segments:
            tx=s.text.strip()+('.'if not s.text.strip().endswith(('.',',','!','?'))else'')
            h=hashlib.md5(tx.encode('utf-8')).hexdigest()[:6]
            sp=seg_dir/f"{s.end:.3f}_{s.start:.3f}_{h}.wav"
            if not sp.exists()or sp.stat().st_size==0:
                spchs=processor.text_to_ai_speeches([tx],language=lang,tmp_voice=str(tmp_voice))
                if not spchs:continue
                ts=processor.concat(spchs);processor.save(sp,ts);dur=ts.shape[-1]/24000.0
            else:dur=get_media_duration(sp)
            peechs.append(Clip_Audio(start=round(s.start,3),end=round(s.start+dur,3),source=Source(start=0.0,end=dur,path=str(sp))))
    else:peechs=mdl.texts_to_speechs(segments,seg_dir,target_lang=lang,pitch=pitch,tempo=tempo,volume=volume)
    if not peechs:return
    combined_path,_=mdl.combine_audio_files(peechs,out_audio,auto_speed=any(s.end>0 for s in segments))
    mus,voc=ws.find_music(),ws.find_vocal()
    if combined_path and mus:
        vols=ws.get_mix_volumes()
        m_dur,s_dur=get_media_duration(str(mus)),get_media_duration(str(combined_path))
        mixes=[
            Clip_Audio(start=0.0,end=m_dur,source=Source(path=str(mus),start=0.0,end=m_dur),volume=0.5 if mode=='AI'else vols['music']),
            Clip_Audio(start=0.0,end=s_dur,source=Source(path=str(combined_path),start=0.0,end=s_dur),volume=2.0 if mode=='AI'else vols['speech'])
        ]
        if voc and(mode=='AI'or vols['vocal']>0):
            v_dur=get_media_duration(str(voc))
            mixes.insert(1,Clip_Audio(start=0.0,end=v_dur,source=Source(path=str(voc),start=0.0,end=v_dur),volume=0.25 if mode=='AI'else vols['vocal']))
        try:
            mdl.mix_audio_files(mixes,out_mixed)
            txt.green(f'[DONE]: "{str(out_mixed)}"')
        except Exception as e:txt.yellow(f"Mix error: {e}")

if __name__=='__main__':
    args=handle_input(
        agr(('-i','--input'),type=str,default=P_DIR),
        agr(('-l','--language'),type=str,default=','.join(LANGS)),
        agr(('-p','--pitch'),type=float,default=1.39),
        agr(('-a','--tempo'),type=float,default=1.25),
        agr(('-v','--volume'),type=float,default=2.0)
    )
    for ws in find_workspaces(args.input):
        for l in str(args.language).split(','):run_tts(ws,l.strip(),float(args.pitch),float(args.tempo),float(args.volume))