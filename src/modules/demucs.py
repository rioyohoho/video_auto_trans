import os,time,logging
from pathlib import Path
import numpy as np
from scipy.signal import correlate
from pydub import AudioSegment
from audio_separator.separator import Separator
from src.utils import extract_audio
from src.configuration import ext,UVR_MODEL,UVR_DIR_PATH
class C:
    fmt,model_dir,mn_audio_separate,log_level = 'mp3',UVR_DIR_PATH,UVR_MODEL,logging.WARNING
    audio_ext,video_ext,n_voice,n_instrumental = ext.AUDIO,ext.VIDEO,'vocal','music'
class Processor:
    def __init__(self):
        self.separator = Separator(model_file_dir=C.model_dir,output_format=C.fmt,log_level=C.log_level)
        self.separator.load_model(C.mn_audio_separate)
    def _clean(self,orig_p:Path,voc_p:Path,out_m:Path):
        try:
            o,v = AudioSegment.from_file(str(orig_p.resolve())),AudioSegment.from_file(str(voc_p.resolve()))
            v = v.set_frame_rate(o.frame_rate).set_channels(o.channels).set_sample_width(o.sample_width)
            os_,vs_ = np.array(o.get_array_of_samples(),dtype=np.float32),np.array(v.get_array_of_samples(),dtype=np.float32)
            if len(vs_)<len(os_): vs_ = np.pad(vs_,(0,len(os_)-len(vs_)),'constant')
            else: vs_ = vs_[:len(os_)]
            shift = np.argmax(correlate(os_,vs_,mode='full',method='fft'))-(len(vs_)-1)
            if shift>0: vs_ = np.pad(vs_[shift:],(0,shift),'constant')
            elif shift<0: vs_ = np.pad(vs_[:shift],(-shift,0),'constant')
            vn = np.linalg.norm(vs_)
            if vn>0:
                sc = np.dot(os_,vs_)/(vn**2)
                if 0.5<=sc<=1.5: vs_ *= sc
            cs = np.clip(os_-vs_,-32768,32767).astype(np.int16)
            c_seg = AudioSegment(cs.tobytes(),frame_rate=o.frame_rate,sample_width=o.sample_width,channels=o.channels)
            tmp = out_m.parent/f"temp_{out_m.name}"
            c_seg.export(str(tmp),format="mp3",bitrate="192k")
            if tmp.exists():
                if out_m.exists():
                    try: out_m.unlink()
                    except OSError: pass
                tmp.rename(out_m)
        except Exception: pass
    def separate(self,source:Path,output:Path|None=None,is_extract_audio=True,is_clean_music=True) -> tuple[Path,Path]:
        v_au = source if source.suffix.endswith(C.audio_ext) else (source.with_suffix('.m4a') if source.with_suffix('.m4a').exists() else (extract_audio(source) if is_extract_audio else source))
        source = v_au if is_extract_audio else source
        target_dir = output if output else source.parent
        target_dir.mkdir(parents=True,exist_ok=True)
        prefix = f"{source.stem}_" if source.stem else ""
        p_v,p_n = target_dir/f"{prefix}{C.n_voice}.mp3",target_dir/f"{prefix}{C.n_instrumental}.mp3"
        if p_v.resolve() == p_n.resolve(): p_n = target_dir/f"{prefix}music.mp3"
        if p_v.exists() and p_n.exists() and p_v.stat().st_size>0 and p_n.stat().st_size>0: return p_v,p_n
        out = None
        try:
            if not (source.suffix.lower() in C.audio_ext and source.stat().st_size<=10240): out = self.separator.separate(str(source))
        except Exception: out = None
        if not out or not isinstance(out,list) or len(out)<2:
            vid = source.with_suffix('.mp4')
            if not vid.exists():
                for e in C.video_ext:
                    if source.with_suffix(e).exists(): vid = source.with_suffix(e);break
            if vid.exists(): out = self.separator.separate(str(vid))
        if not out or not isinstance(out,list) or len(out)<2: raise RuntimeError(f"Failed: {source}")
        files = []
        for item in out[:2]:
            p = Path(item)
            if not p.exists():
                for d in [source.parent,Path.cwd(),Path(os.environ.get('TEMP',''))]:
                    if d and (d/p.name).exists(): p = d/p.name;break
            files.append(p)
        f1,f2 = files[0],files[1]
        n1,n2 = f1.name.lower(),f2.name.lower()
        v_s,m_s = (f1,f2) if (('vocal' in n1 and 'no' not in n1 and 'inst' not in n1) or 'inst' in n2 or 'no' in n2 or 'music' in n2) else (f2,f1)
        if not v_s.exists() or not m_s.exists(): raise RuntimeError(f"Stems not found: {source}")
        for _ in range(120):
            if v_s.stat().st_size>0 and m_s.stat().st_size>0:
                s1,s2 = v_s.stat().st_size,m_s.stat().st_size
                time.sleep(0.5)
                if v_s.stat().st_size==s1 and m_s.stat().st_size==s2: break
            time.sleep(0.5)
        for t,s in [(p_v,v_s),(p_n,m_s)]:
            temp_target = target_dir/f"temp_{t.name}"
            AudioSegment.from_file(str(s.resolve())).export(str(temp_target),format="mp3",bitrate="192k")
            if temp_target.exists():
                if t.exists():
                    try: t.unlink()
                    except OSError: pass
                temp_target.rename(t)
        if is_clean_music and v_au.exists() and p_v.exists() and p_n.exists(): self._clean(v_au,p_v,p_n)
        for s in [v_s,m_s]:
            if s.exists():
                try: s.unlink()
                except OSError: pass
        return p_v,p_n