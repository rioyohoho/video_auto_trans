import io, time, hashlib, tempfile, math, subprocess, traceback
from gtts import gTTS
from pydub import AudioSegment
import pydub.effects as effects
from pathlib import Path
from src.utils import txt, line, progress
from src.enties import Clip_Audio, Source, Transcribe

class C:
    fmt = 'wav'
    atempo = 1.0

def mix_audio_files(audios: list[Clip_Audio], output_path: Path) -> tuple[Path, float]:
    output_path = Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    valid = [a for a in audios if a.source and Path(a.source.path).exists() and Path(a.source.path).stat().st_size > 0]
    if not valid: return output_path, .0
    cmd, flts = ['ffmpeg', '-y'], []
    for i, a in enumerate(valid):
        cmd.extend(['-i', str(Path(a.source.path).resolve())])
        vol, st = getattr(a, 'volume', 1.), int(getattr(a, 'start', .0) * 1000)
        f = f"volume={vol}" + (f",adelay={st}|{st}" if st > 0 else "")
        flts.append(f"[{i}:a]{f}[a{i}]")
    tags = ''.join([f"[a{i}]" for i in range(len(valid))])
    complex_filter = f"{';'.join(flts)};{tags}amix=inputs={len(valid)}:duration=longest:dropout_transition=0:normalize=0,alimiter=limit=0.95[out]"
    cmd.extend(['-filter_complex', complex_filter, '-map', '[out]', '-c:a', 'pcm_s16le' if output_path.suffix.lower() == '.wav' else 'libmp3lame', '-b:a', '192k', str(output_path.resolve()), '-loglevel', 'error'])
    subprocess.run(cmd, check=True)
    from src.utils.video import get_media_duration
    return output_path, get_media_duration(output_path)

def _build_atempo(t: float) -> list[str]:
    fl = []
    while t > 2.0: fl.append("atempo=2.0"); t /= 2.0
    while t < 0.5: fl.append("atempo=0.5"); t /= 0.5
    if abs(t - 1.0) > 0.005: fl.append(f"atempo={t:.4f}")
    return fl

def combine_audio_files(audios: list[Clip_Audio], output_path: Path, duration: float = .0, auto_speed=True) -> tuple[Path, float]:
    if not audios: return None, .0
    output_path = Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    audios = sorted(audios, key=lambda x: x.start)
    raw_segs, durs = [], []
    for a in audios:
        s = AudioSegment.from_file(Path(a.source.path))
        try: s = effects.strip_silence(s, silence_thresh=-50, chunk_size=10)
        except: pass
        raw_segs.append(s); durs.append(len(s) / 1000.0)

    n = len(audios)
    with tempfile.TemporaryDirectory() as tmp:
        processed_segs = []
        for i, (a, seg, dur) in enumerate(zip(audios, raw_segs, durs)):
            cur = seg
            lim = (audios[i+1].start - a.start) if i + 1 < n and audios[i+1].start > a.start else (a.end - a.start)
            if auto_speed and lim > 0.05 and dur > lim:
                item_atempo = min(dur / lim, 1.45)
                ti, to = Path(tmp) / f"i_{i}.wav", Path(tmp) / f"o_{i}.wav"
                seg.export(str(ti), format='wav')
                fl = _build_atempo(item_atempo)
                if fl:
                    subprocess.run(['ffmpeg', '-y', '-i', str(ti), '-filter:a', ','.join(fl), str(to), '-loglevel', 'error'], check=True)
                    cur = AudioSegment.from_file(to)
                    try: cur = effects.strip_silence(cur, silence_thresh=-50, chunk_size=10)
                    except: pass
            if getattr(a, 'volume', 1.0) != 1.0 and a.volume > 0:
                cur = cur + (20 * math.log10(a.volume))
            processed_segs.append(cur)

        max_track_end = max([a.start + (len(p) / 1000.0) for a, p in zip(audios, processed_segs)])
        total_len = max(duration, max_track_end)
        combined = AudioSegment.silent(duration=int(total_len * 1000) + 100, frame_rate=processed_segs[0].frame_rate)
        for a, p in zip(audios, processed_segs):
            combined = combined.overlay(p, position=int(a.start * 1000))

    combined.export(output_path, format=output_path.suffix.replace('.', ''), bitrate='192k')
    return output_path, combined.duration_seconds

def _gtts_speech(text: str, target_lang: str, trials=3, sleep=2):
    for attempt in range(1, trials + 1):
        try:
            mp3_fp = io.BytesIO()
            gTTS(str(text), lang=target_lang).write_to_fp(mp3_fp); mp3_fp.seek(0)
            return AudioSegment.from_file(mp3_fp, format='mp3')
        except:
            if attempt < trials: time.sleep(sleep)
            else: return None

def text_to_speech(txt_str: str, output: str = None, tempo=1., pitch=1., target=None, atempo=None) -> AudioSegment:
    if not txt_str or not str(txt_str).strip(): return None
    audio = _gtts_speech(txt_str, target)
    if not audio: return None
    cur_t, p = float(atempo if atempo is not None else (tempo or 1.)), float(pitch or 1.)
    if abs(cur_t - 1.) > 0.01 or abs(p - 1.) > 0.01:
        with tempfile.TemporaryDirectory() as tmp:
            t_in, t_out = Path(tmp) / f"in.{C.fmt}", Path(tmp) / f"out.{C.fmt}"
            audio.export(str(t_in), format=C.fmt)
            try:
                sr, act_t = audio.frame_rate, cur_t / p
                fl = [f"asetrate={int(sr * p)}"] + _build_atempo(act_t) + [f"aresample={sr}"]
                subprocess.run(['ffmpeg', '-y', '-i', str(t_in), '-filter:a', ','.join(fl), str(t_out), '-loglevel', 'error'], check=True)
                audio = AudioSegment.from_file(str(t_out), format=C.fmt)
            except: pass
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True); audio.export(output, format=C.fmt)
    return audio

def texts_to_speechs(segments: list[Transcribe], directory: Path, target_lang=None, pitch=1.0, tempo=1.0, volume=1.0) -> list[Clip_Audio]:
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    for i, s in enumerate(segments):
        txt_hash = hashlib.md5(str(s.text).encode('utf-8')).hexdigest()[:6]
        out_path = directory / f"{s.end:.3f}_{s.start:.3f}_{txt_hash}.{C.fmt}"
        if not out_path.exists():
            audio = text_to_speech(s.text, pitch=pitch, tempo=tempo, target=target_lang)
            if not audio: continue
            audio.export(out_path, format=C.fmt)
        else:
            audio = AudioSegment.from_file(out_path, format=C.fmt)
        actual_dur = len(audio) / 1000.0
        results.append(Clip_Audio(
            start=round(s.start, 3),
            end=round(s.end if s.end > s.start else s.start + actual_dur, 3),
            source=Source(start=0.0, end=actual_dur, path=str(out_path)),
            pitch=pitch, tempo=tempo, volume=volume
        ))
        progress(i + 1, len(segments), txt=f"{s.start:.2f}s -> {s.end:.2f}s")
    line()
    return results