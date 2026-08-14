import os,time,logging
from pathlib import Path
from pydub import AudioSegment
from audio_separator.separator import Separator
from src.utils import extract_audio
from src.configuration import ext,UVR_MODEL,UVR_DIR_PATH

class C:
    fmt = 'mp3'
    model_dir = UVR_DIR_PATH #onnxruntime-gpu
    mn_audio_separate = UVR_MODEL
    log_level = logging.WARNING
    audio_ext = ext.AUDIO
    video_ext = ext.VIDEO
    n_voice = 'vocal'
    n_instrumental = 'music'

class Processor:
    def __init__(self):
        self.separator = Separator(model_file_dir=C.model_dir, output_format=C.fmt, log_level=C.log_level)
        self.separator.load_model(C.mn_audio_separate)
    def separate(self, source: Path, output:Path|None=None, is_extract_audio=True) -> tuple[Path, Path]:
        if source.suffix.endswith(C.audio_ext): v_au = source
        elif is_extract_audio:
            v_au = source.with_suffix('.m4a')
            source = v_au if v_au.exists() else extract_audio(source)
        target_dir = output# if output else source.with_name(subname)
        target_dir.mkdir(parents=True, exist_ok=True)
        prefix = f"{source.stem}_" if source.stem else ""
        p_v = target_dir / f"{prefix}{C.n_voice}.mp3"
        p_n = target_dir / f"{prefix}{C.n_instrumental}.mp3"
        if p_v.resolve() == p_n.resolve():
            p_n = target_dir / f"{prefix}music.mp3"
        if p_v.exists() and p_n.exists() and p_v.stat().st_size > 0 and p_n.stat().st_size > 0:
            return p_v, p_n
        out = None
        try:
            if not (source.suffix.lower() in C.audio_ext and source.stat().st_size <= 10240):
                out = self.separator.separate(str(source))
        except Exception:
            out = None
        if not out or not isinstance(out, list) or len(out) < 2:
            vid = source.with_suffix('.mp4')
            if not vid.exists():
                for ext in C.video_ext:
                    if source.with_suffix(ext).exists():
                        vid = source.with_suffix(ext)
                        break
            if vid.exists():
                out = self.separator.separate(str(vid))
        if not out or not isinstance(out, list) or len(out) < 2:
            raise RuntimeError(f"Failed: {source}")
        files = []
        for item in out[:2]:
            p = Path(item)
            if not p.exists():
                for d in [source.parent, Path.cwd(), Path(os.environ.get('TEMP', ''))]:
                    if d and (d / p.name).exists():
                        p = d / p.name
                        break
            files.append(p)
        f1, f2 = files[0], files[1]
        n1, n2 = f1.name.lower(), f2.name.lower()
        if ('vocal' in n1 and 'no' not in n1 and 'inst' not in n1) or 'inst' in n2 or 'no' in n2 or 'music' in n2:
            v_s, m_s = f1, f2
        else:
            v_s, m_s = f2, f1
        if not v_s.exists() or not m_s.exists():
            raise RuntimeError(f"Stems not found: {source}")
        for _ in range(120):
            if v_s.stat().st_size > 0 and m_s.stat().st_size > 0:
                s1, s2 = v_s.stat().st_size, m_s.stat().st_size
                time.sleep(0.5)
                if v_s.stat().st_size == s1 and m_s.stat().st_size == s2:
                    break
            time.sleep(0.5)
        for t, s in [(p_v, v_s), (p_n, m_s)]:
            temp_target = target_dir / f"temp_{t.name}"
            AudioSegment.from_file(str(s.resolve())).export(str(temp_target), format="mp3", bitrate="192k")
            if temp_target.exists():
                if t.exists():
                    try: t.unlink()
                    except OSError: pass
                temp_target.rename(t)
        for s in [v_s, m_s]:
            if s.exists():
                try: s.unlink()
                except OSError: pass
        return p_v, p_n

