import io, time, hashlib, tempfile, math, subprocess, traceback
from gtts import gTTS
from pydub import AudioSegment
from pathlib import Path
from video_auto_trans.src.utils import txt, line, progress
from video_auto_trans.src.enties import Clip_Audio, Source, Transcribe

class C:
    fmt = 'wav'
    atempo = 1.0

def mix_audio_files(audios:list[Clip_Audio],output_path:Path)->tuple[Path,float]:
	output_path=Path(output_path);output_path.parent.mkdir(parents=True,exist_ok=True);valid_audios=[a for a in audios if a.source and Path(a.source.path).exists()and Path(a.source.path).stat().st_size>0]
	if not valid_audios:return output_path,.0
	cmd=['ffmpeg','-y'];filter_inputs=[]
	for(i,a)in enumerate(valid_audios):
		cmd.extend(['-i',str(Path(a.source.path).resolve())]);vol=getattr(a,'volume',1.);start_ms=int(getattr(a,'start',.0)*1000);flt=f"volume={vol}"
		if start_ms>0:flt+=f",adelay={start_ms}|{start_ms}"
		filter_inputs.append(f"[{i}:a]{flt}[a{i}]")
	n=len(valid_audios);mix_tags=''.join([f"[a{i}]"for i in range(n)]);complex_filter=f"{";".join(filter_inputs)};{mix_tags}amix=inputs={n}:duration=longest:dropout_transition=0:normalize=0,alimiter=limit=0.95[out]";cmd.extend(['-filter_complex',complex_filter,'-map','[out]','-c:a','pcm_s16le'if output_path.suffix.lower()=='.wav'else'libmp3lame','-b:a','192k',str(output_path.resolve()),'-loglevel','error']);subprocess.run(cmd,check=True);from video_auto_trans.src.utils.video import get_media_duration;actual_dur=get_media_duration(output_path);return output_path,actual_dur

def combine_audio_files(audios: list[Clip_Audio], output_path: Path, duration: float = .0, auto_speed=True) -> tuple[Path, float]:
    if not audios: 
        txt.yellow(f'WARNING(audios): {audios}')
        return (None, 0)
    audios = sorted(audios, key=lambda x: x.start)
    if duration <= 0:
        duration = max([a.end for a in audios])
    first_path = audios[0].source.path
    combined = AudioSegment.silent(duration=int(duration * 1e3), frame_rate=AudioSegment.from_file(first_path).frame_rate)
    n = len(audios); speeds = [1.0] * n; starts = [a.start for a in audios]; durs = []
    import pydub.effects as effects
    for a in audios:
        p = Path(a.source.path)
        s = AudioSegment.from_file(p)
        try:
            s = effects.strip_silence(s, silence_thresh=-50, chunk_size=10)
        except:
            pass
        durs.append(s.duration_seconds)
    if auto_speed and n > 0:
        for i in range(n):
            if i > 0 and starts[i-1] + (durs[i-1] / speeds[i-1]) > starts[i]:
                overlap = (starts[i-1] + durs[i-1]) - starts[i]
                if overlap > 0 and durs[i-1] / C.atempo < (starts[i] - starts[i-1]):
                    req = durs[i-1] / (starts[i] - starts[i-1]) if starts[i] > starts[i-1] else C.atempo
                    speeds[i-1] = min(max(speeds[i-1], req), C.atempo)
                else:
                    speeds[i-1] = C.atempo
            if i + 2 < n:
                sp = audios[i+2].start - starts[i]
                if sp > 0 and (durs[i] + durs[i+1]) > sp:
                    speeds[i] = min((durs[i] + durs[i+1]) / sp, C.atempo)
            lim = audios[i+1].start if i + 1 < n else duration
            if (lim - starts[i]) > 0 and durs[i] > (lim - starts[i]):
                speeds[i] = min(max(speeds[i], durs[i] / (lim - starts[i])), C.atempo)
        for i in range(n):
            if i > 0:
                prev_end = starts[i-1] + (durs[i-1] / speeds[i-1])
                if prev_end > starts[i]:
                    starts[i] = prev_end
    with tempfile.TemporaryDirectory() as tmp:
        for i, a in enumerate(audios):
            p = Path(a.source.path)
            seg = AudioSegment.from_file(p)
            try:
                seg = effects.strip_silence(seg, silence_thresh=-50, chunk_size=10)
            except:
                pass
            spd = speeds[i]
            if auto_speed and abs(spd - 1.0) > 0.01:
                sp = Path(tmp) / f"s_{i}{p.suffix}"
                subprocess.run(['ffmpeg', '-y', '-i', str(p), '-filter:a', f'atempo={spd}', str(sp), '-loglevel', 'quiet'], check=True)
                seg = AudioSegment.from_file(sp)
                try:
                    seg = effects.strip_silence(seg, silence_thresh=-50, chunk_size=10)
                except:
                    pass
            if a.volume != 1.0:
                db_gain = 20 * math.log10(a.volume) if a.volume > 0 else -100
                seg = seg + db_gain
            combined = combined.overlay(seg, position=int(starts[i] * 1e3))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(output_path, format=output_path.suffix.replace('.', ''), bitrate='192k')
    return output_path, combined.duration_seconds

def _gtts_speech(text: str, target_lang: str, trials=3, sleep=3):
    for attempt in range(1, trials + 1):
        try:
            mp3_fp = io.BytesIO()
            gTTS(str(text), lang=target_lang).write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            return AudioSegment.from_file(mp3_fp, format='mp3')
        except Exception as e:
            txt.yellow(f'❌ Google-TTS({trials}) "{text[:30]}"')
            if attempt < trials:
                time.sleep(sleep)
            else:
                txt.red(f'❌ Error(BREAK): try {e}')
                return

def text_to_speech(txt: str, output: str = None, tempo=1., pitch=1., target=None, atempo=None) -> AudioSegment:
    if not txt or not str(txt).strip(): return
    cur_t = float(atempo if atempo is not None else (tempo or 1.))
    p = float(pitch or 1.)
    audio = _gtts_speech(txt, target)
    if not audio: return
    if abs(cur_t - 1.) > 0 or abs(p - 1.) > 0:
        with tempfile.TemporaryDirectory() as tmp:
            t_in, t_out = Path(tmp) / f"in.{C.fmt}", Path(tmp) / f"out.{C.fmt}"
            audio.export(str(t_in), format=C.fmt)
            try:
                sr = audio.frame_rate
                act_t, fl = cur_t / p, [f"asetrate={int(sr * p)}"]
                if act_t > 2.:
                    n = math.ceil(math.log2(act_t))
                    fl.extend([f"atempo={act_t**(1/n):.4f}"] * n)
                elif act_t < .5:
                    n = math.ceil(math.log(act_t, .5))
                    fl.extend([f"atempo={act_t**(1/n):.4f}"] * n)
                elif abs(act_t - 1.) > .005:
                    fl.append(f"atempo={act_t:.4f}")
                fl.append(f"aresample={sr}")
                subprocess.run(['ffmpeg', '-y', '-i', str(t_in), '-filter:a', ','.join(fl), str(t_out)], check=True, capture_output=True, text=True)
                audio = AudioSegment.from_file(str(t_out), format=C.fmt)
            except subprocess.CalledProcessError as e:
                traceback.print_exception(e)
            except Exception as e:
                traceback.print_exception(e)
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        audio.export(output, format=C.fmt)
    return audio

def texts_to_speechs(segments: list[Transcribe], directory: Path, target_lang=None, pitch=1.0, tempo=1.0, volume=1.0) -> list[Clip_Audio]:
    directory.mkdir(parents=True, exist_ok=True)
    total = len(segments)
    results: list[Clip_Audio] = []
    for (i, s) in enumerate(segments, 0):
        txt_hash = hashlib.md5(str(s.text).encode('utf-8')).hexdigest()[:6]
        name = f"{s.end:.3f}_{s.start:.3f}_{txt_hash}.{C.fmt}"
        out_path = directory / name
        
        if out_path.exists():
            audio = AudioSegment.from_file(out_path, format=C.fmt)
            actual_dur = len(audio) / 1e3
            ns, ne = round(s.start, 3), round(s.start + actual_dur, 3)
            if ns < 0:
                ne = round(ne + abs(ns), 3)
                ns = .0
            results.append(
                Clip_Audio(
                    start=ns,
                    end=ne,
                    source=Source(start=0.0, end=actual_dur, path=str(out_path)),
                    pitch=pitch,
                    tempo=tempo,
                    volume=volume
                )
            )
            progress(i, total, f'Skip({ns}:{ne}) "{name}"')
            continue

        audio = text_to_speech(s.text, pitch=pitch, tempo=tempo, target=target_lang)
        if not audio:
            continue
        actual_dur = len(audio) / 1e3
        ns = round(s.start, 3)
        ne = round(s.start + actual_dur, 3)
        if ns < 0:
            ne = round(ne + abs(ns), 3)
            ns = .0
        audio.export(out_path, format=C.fmt)
        results.append(
            Clip_Audio(
                start=ns,
                end=ne,
                source=Source(start=0.0, end=actual_dur, path=str(out_path)),
                pitch=pitch,
                tempo=tempo,
                volume=volume
            )
        )
        progress(i, total, txt=f"To speech: {ns}s -> {ne}s", tab=1)
    progress(total, total, txt='All segments synchronized', bar_color='\x1b[90m', tab=1)
    line()
    return results