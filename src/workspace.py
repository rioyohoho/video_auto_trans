import sys
from enum import IntEnum
from pathlib import Path
from src.utils import is_ext
from src.configuration import ext,aud,P_DIR
from enum import StrEnum

class Model(StrEnum):
    DEFAULT=''
    G='G'
    AI='AI'
    L='L'

class TransModel(IntEnum):
    DEFAULT=0
    G_TRAN=1
    AI_TRAN=2
    L_TRAN=3

class Workspace:
    def __init__(self,media_path:Path):
        self.media_path=media_path.resolve()
        self.stem=self.media_path.stem
        self.root_dir=self.media_path.parent
        self.work_dir=self.root_dir/self.stem
        self.work_dir.mkdir(parents=True,exist_ok=True)
    def vocal_path(self,e:str='.mp3')->Path:return self.work_dir/f"{self.stem}_vocal{e}"
    def music_path(self,e:str='.mp3')->Path:return self.work_dir/f"{self.stem}_music{e}"
    def find_vocal(self)->Path|None:
        for e in ext.AUDIO:
            p=self.work_dir/f"{self.stem}_vocal{e}"
            if p.exists()and p.stat().st_size>0:return p
        return None
    def find_music(self)->Path|None:
        for e in ext.AUDIO:
            p=self.work_dir/f"{self.stem}_music{e}"
            if p.exists()and p.stat().st_size>0:return p
        return None
    def find_transcribe_audio(self)->Path:
        v=self.find_vocal()
        if v:return v
        for e in ext.AUDIO:
            p=self.work_dir/f"{self.stem}{e}"
            if p.exists()and p.stat().st_size>0:return p
        return self.media_path
    @property
    def origin_json(self)->Path:return self.work_dir/f"{self.stem}.json"
    def trans_file(self,lang:str,ext_name:str='json',model_type:int|str|TransModel|Model=0)->Path:
        val=model_type.value if isinstance(model_type,(TransModel,Model))else model_type
        m=str(val).upper()
        tag=""if m in(0,'0','','DEFAULT')else(f"_{Model.G.value}"if m in(1,'1','G','G_TRAN','GOOGLE')else(f"_{Model.AI.value}"if m in(2,'2','AI','AI_TRAN')else f"_{Model.L.value}"))
        return self.work_dir/f"{self.stem}{tag}.{lang}.{ext_name}"
    def find_speech_doc(self,lang:str,mode:str|Model=Model.G)->Path|None:
        m=mode.value if isinstance(mode,Model)else str(mode)
        tags=[f"_{m}",f"_{Model.L.value}",f"_{Model.AI.value}",f"_{Model.G.value}"]
        for tag in dict.fromkeys(tags):
            for e in('.json','.srt','.txt'):
                p=self.work_dir/f"{self.stem}{tag}.{lang}{e}"
                if p.exists()and p.stat().st_size>0:return p
        for e in('.json','.srt','.txt'):
            p=self.work_dir/f"{self.stem}.{lang}{e}"
            if p.exists()and p.stat().st_size>0:return p
        return None
    def tts_dir(self,lang:str,mode:str|Model=Model.G)->Path:
        m=mode.value if isinstance(mode,Model)else str(mode)
        return self.work_dir/f"{self.stem}_{m}.{lang}"
    def tts_audio(self,lang:str,fmt:str='mp3',mode:str|Model=Model.G)->Path:
        m=mode.value if isinstance(mode,Model)else str(mode)
        return self.work_dir/f"{self.stem}_{m}.{lang}.{fmt}"
    def mixed_audio(self,lang:str,fmt:str='mp3',mode:str|Model=Model.G)->Path:
        m=mode.value if isinstance(mode,Model)else str(mode)
        return self.work_dir/f"{self.stem}_{m}.{lang}_mixed.{fmt}"
    def find_media_srt(self,lang:str)->Path:
        for tag in(f"_{Model.G.value}",f"_{Model.AI.value}",f"_{Model.L.value}"):
            for e in ext.MEDIA:
                p=self.work_dir/f"{self.stem}{tag}.{lang}{e}"
                if p.exists()and p.stat().st_size>0:return p
        for e in ext.MEDIA:
            p=self.work_dir/f"{self.stem}.{lang}{e}"
            if p.exists()and p.stat().st_size>0:return p
        v=self.find_vocal()
        return v if v else self.media_path
    def word_json(self,lang:str,words:int=1,mode:str='S')->Path:return self.work_dir/f"{self.stem}_{mode}.{lang}.json"
    def word_srt(self,lang:str,words:int=1,mode:str='S')->Path:return self.work_dir/f"{self.stem}_{mode}.{lang}.srt"
    def final_video(self,lang:str)->Path:return self.root_dir/f"{self.stem}_{lang}_final.mp4"
    def get_mix_volumes(self):return{'speech':aud.speechs.value if aud.speechs.value>0 else 1.0,'music':aud.music.value or 0,'vocal':aud.vocal.value or 0}

def find_workspaces(input_target:str|Path=None)->list[Workspace]:
    target=input_target or P_DIR
    p=Path(target).resolve()
    if not p.exists():return[]
    if p.is_file():
        if is_ext(str(p),ext.MEDIA):return[Workspace(p)]
        if p.suffix.lower()in('.json','.srt','.txt'):
            raw=p.stem.split('.')[0]
            for tag in('_vocal','_music',f"_{Model.G.value}",f"_{Model.AI.value}",f"_{Model.L.value}",'_mixed','_S'):
                if raw.endswith(tag):raw=raw[:-len(tag)]
            for v_ext in ext.VIDEO+ext.AUDIO:
                for cand in(p.parent.parent/f"{raw}{v_ext}",p.parent/f"{raw}{v_ext}"):
                    if cand.exists():return[Workspace(cand)]
            return[Workspace(p.with_name(f"{raw}.mp4"))]
    if p.is_dir():
        for e in ext.VIDEO:
            c=p.parent/f"{p.name}{e}"
            if c.exists():return[Workspace(c)]
        media_files={}
        for f in p.iterdir():
            if f.is_file()and is_ext(str(f),ext.VIDEO)and f.stem not in media_files:media_files[f.stem]=f
        for f in p.iterdir():
            if f.is_file()and is_ext(str(f),ext.AUDIO)and f.stem not in media_files:
                if not any(f.stem.endswith(t)for t in('_vocal','_music','_mixed')):media_files[f.stem]=f
        if not media_files:
            for sub in p.iterdir():
                if sub.is_dir():
                    for e in ext.VIDEO:
                        c=p/f"{sub.name}{e}"
                        if c.exists()and sub.name not in media_files:media_files[sub.name]=c
                    for f in sub.iterdir():
                        if f.is_file()and is_ext(str(f),ext.VIDEO)and f.stem not in media_files:media_files[f.stem]=f
                    for f in sub.iterdir():
                        if f.is_file()and is_ext(str(f),ext.AUDIO)and f.stem not in media_files:
                            if not any(f.stem.endswith(t)for t in('_vocal','_music','_mixed')):media_files[f.stem]=f
        return[Workspace(f)for f in media_files.values()]
    return[]