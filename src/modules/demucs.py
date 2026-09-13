import os,time,logging
from pathlib import Path
import numpy as np
import librosa
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
            y_orig, sr = librosa.load(str(orig_p.resolve()), sr=None, mono=False)
            y_voc, _ = librosa.load(str(voc_p.resolve()), sr=sr, mono=False)
            if y_orig.ndim == 1:
                y_orig = np.expand_dims(y_orig, axis=0)
            if y_voc.ndim == 1:
                y_voc = np.expand_dims(y_voc, axis=0)
            min_len = min(y_orig.shape[1], y_voc.shape[1])
            y_orig = y_orig[:, :min_len]
            y_voc = y_voc[:, :min_len]
            channels = y_orig.shape[0]
            inst_channels = []
            for ch in range(channels):
                oc, vc = y_orig[ch], y_voc[ch]
                corr = np.correlate(oc, vc, mode='full')
                lag = np.argmax(corr) - (len(vc) - 1)
                if abs(lag) < sr * 0.1:
                    if lag > 0:
                        vc_aligned = np.pad(vc[lag:], (0, lag), mode='constant')
                    elif lag < 0:
                        vc_aligned = np.pad(vc[:lag], (-lag, 0), mode='constant')
                    else:
                        vc_aligned = vc
                else:
                    vc_aligned = vc
                S_o = librosa.stft(oc, n_fft=2048, hop_length=512)
                S_v = librosa.stft(vc_aligned, n_fft=2048, hop_length=512)
                mag_o, phase_o = np.abs(S_o), np.angle(S_o)
                mag_v = np.abs(S_v)
                spec_env = np.maximum(mag_o - mag_v, 0.02 * mag_o)
                S_inst = spec_env * np.exp(1j * phase_o)
                ic = librosa.istft(S_inst, hop_length=512, length=len(oc))
                inst_channels.append(ic)
            inst_arr = np.stack(inst_channels, axis=-1) if channels >  1 else np.expand_dims(inst_channels[0], axis=-1)
            inst_int16 = np.clip(inst_arr * 32767.0, -32768, 32767).astype(np.int16)
            c_seg = AudioSegment(inst_int16.tobytes(), frame_rate=sr, sample_width=2, channels=channels)
            tmp = out_m.parent/f"temp_{out_m.name}"
            c_seg.export(str(tmp), format="mp3", bitrate="192k")
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