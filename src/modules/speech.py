import io,time,hashlib,tempfile,math,subprocess,traceback
from gtts import gTTS
from pydub import AudioSegment
from pathlib import Path
from src.utils import txt,line,progress
from src.enties import Audio,TrackAudio

class C:
    fmt = 'wav'
    atempo = 1.0
def mix_audio_files(audios: list[TrackAudio], output_path: Path) -> tuple[Path, float]:
	audios = sorted(audios, key=lambda x: x.start)
	if not audios:
		output_path.parent.mkdir(parents=True, exist_ok=True)
		AudioSegment.silent(duration=0).export(output_path, format=output_path.suffix.replace('.', ''), bitrate='192k')
		return output_path, 0.0
	duration = max([a.end for a in audios])
	base_sample_rate = AudioSegment.from_file(audios[0].text).frame_rate
	combined = AudioSegment.silent(duration=int(duration * 1e3), frame_rate=base_sample_rate)
	import pydub.effects as effects
	with tempfile.TemporaryDirectory() as tmp:
		for i, a in enumerate(audios):
			p = Path(a.text)
			pitch = getattr(a, 'pitch', 1.0)
			atempo = getattr(a, 'atempo', 1.0)
			volume = getattr(a, 'volume', 1.0)
			sst = getattr(a, 'sst', 0.0)
			snd = getattr(a, 'snd', a.end)
			dur = max(0.0, snd - sst)
			sp = Path(tmp)/f"m_{i}{p.suffix}"
			filter_chains = []
			if abs(pitch - 1.0) > 0.01:
				new_rate = int(base_sample_rate * pitch)
				filter_chains.append(f"asetrate={new_rate}")
				filter_chains.append(f"atempo={1.0 / pitch}")
			if abs(atempo - 1.0) > 0.01:
				filter_chains.append(f"atempo={atempo}")
			if volume != 1.0:
				filter_chains.append(f"volume={volume}")
				filter_chains.append("alimiter=limit=0.95")
			cmd = ['ffmpeg', '-y', '-ss', str(sst), '-i', str(p)]
			if dur > 0:
				cmd.extend(['-t', str(dur)])
			if filter_chains:
				cmd.extend(['-filter:a', ','.join(filter_chains)])
			else:
				cmd.extend(['-c:a', 'copy'])
			cmd.extend([str(sp), '-loglevel', 'quiet'])
			subprocess.run(cmd, check=True)
			seg = AudioSegment.from_file(sp)
			try:
				seg = effects.strip_silence(seg, silence_thresh=-50, chunk_size=10)
			except:
				pass
			combined = combined.overlay(seg, position=int(a.start * 1e3))
	output_path.parent.mkdir(parents=True, exist_ok=True)
	combined.export(output_path, format=output_path.suffix.replace('.', ''), bitrate='192k')
	return output_path, combined.duration_seconds
def combine_audio_files(audios: list[Audio], output_path: Path, duration: float = .0, auto_speed=True) -> tuple[Path, float]:
    if not audios: txt.yellow(f'WARNING(audios): {audios}'); return (None,0)
    audios = sorted(audios, key=lambda x: x.start)
    if duration <= 0:duration = max([a.end for a in audios])
    combined = AudioSegment.silent(duration=int(duration * 1e3), frame_rate=AudioSegment.from_file(audios[0].text).frame_rate)
    n = len(audios); speeds = [1.0] * n; starts = [a.start for a in audios]; durs = []
    import pydub.effects as effects
    for a in audios:
        s = AudioSegment.from_file(a.text)
        try:s = effects.strip_silence(s, silence_thresh=-50, chunk_size=10)
        except:pass
        durs.append(s.duration_seconds)
    if auto_speed and n > 0:
        for i in range(n):
            if i > 0 and starts[i-1] + (durs[i-1]/speeds[i-1]) > starts[i]:
                overlap = (starts[i-1] + durs[i-1]) - starts[i]
                if overlap > 0 and durs[i-1]/C.atempo < (starts[i] - starts[i-1]):
                    req = durs[i-1]/(starts[i] - starts[i-1]) if starts[i] > starts[i-1] else C.atempo
                    speeds[i-1] = min(max(speeds[i-1], req), C.atempo)
                else:speeds[i-1] = C.atempo
            if i+2 < n:
                sp = audios[i+2].start - starts[i]
                if sp > 0 and (durs[i] + durs[i+1]) > sp:speeds[i] = min((durs[i] + durs[i+1])/sp, C.atempo)
            lim = audios[i+1].start if i+1 < n else duration
            if (lim - starts[i]) > 0 and durs[i] > (lim - starts[i]):speeds[i] = min(max(speeds[i], durs[i]/(lim - starts[i])), C.atempo)
        for i in range(n):
            if i > 0:
                prev_end = starts[i-1] + (durs[i-1]/speeds[i-1])
                if prev_end > starts[i]:starts[i] = prev_end
    with tempfile.TemporaryDirectory() as tmp:
        for i, a in enumerate(audios):
            p = Path(a.text); seg = AudioSegment.from_file(p)
            try:seg = effects.strip_silence(seg, silence_thresh=-50, chunk_size=10)
            except:pass
            spd = speeds[i]
            if auto_speed and abs(spd - 1.0) > 0.01:
                sp = Path(tmp)/f"s_{i}{p.suffix}"
                subprocess.run(['ffmpeg', '-y', '-i', str(p), '-filter:a', f'atempo={spd}', str(sp), '-loglevel', 'quiet'], check=True)
                seg = AudioSegment.from_file(sp)
                try:seg = effects.strip_silence(seg, silence_thresh=-50, chunk_size=10)
                except:pass
            if a.volume != 1.0:
                db_gain = 20 * math.log10(a.volume) if a.volume > 0 else -100
                seg = seg + db_gain
            combined = combined.overlay(seg, position=int(starts[i] * 1e3))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(output_path, format=output_path.suffix.replace('.', ''), bitrate='192k')
    return output_path, combined.duration_seconds
def _gtts_speech(text:str,target_lang:str,trials=3,sleep=3):
	for attempt in range(1,trials+1):
		try:mp3_fp=io.BytesIO();gTTS(str(text),lang=target_lang).write_to_fp(mp3_fp);mp3_fp.seek(0);return AudioSegment.from_file(mp3_fp,format='mp3')
		except Exception as e:
			txt.yellow(f'❌ Google-TTS({trials}) "{text[:30]}"')
			if attempt<trials:time.sleep(sleep)
			else:txt.red(f'❌ Error(BREAK): try {e}');return
def text_to_speech(txt:str,output:str=None,atempo=1.,pitch=1.,target=None)->AudioSegment:
    if not txt or not str(txt).strip():return
    cur_t,p=float(atempo or 1.),float(pitch or 1.);audio=_gtts_speech(txt,target)
    if not audio:return
    if abs(cur_t-1.)>0 or abs(p-1.)>0:
        with tempfile.TemporaryDirectory()as tmp:
            t_in,t_out=Path(tmp)/f"in.{C.fmt}",Path(tmp)/f"out.{C.fmt}";audio.export(str(t_in),format=C.fmt)
            try:
                sr=audio.frame_rate;act_t,fl=cur_t/p,[f"asetrate={int(sr*p)}"]
                if act_t>2.:n=math.ceil(math.log2(act_t));fl.extend([f"atempo={act_t**(1/n):.4f}"]*n)
                elif act_t<.5:n=math.ceil(math.log(act_t,.5));fl.extend([f"atempo={act_t**(1/n):.4f}"]*n)
                elif abs(act_t-1.)>.005:fl.append(f"atempo={act_t:.4f}")
                fl.append(f"aresample={sr}");subprocess.run(['ffmpeg','-y','-i',str(t_in),'-filter:a',','.join(fl),str(t_out)],check=True,capture_output=True,text=True);audio=AudioSegment.from_file(str(t_out),format=C.fmt)
            except subprocess.CalledProcessError as e:traceback.print_exception(e)
            except Exception as e:traceback.print_exception(e)
    if output:Path(output).parent.mkdir(parents=True,exist_ok=True);audio.export(output,format=C.fmt)
    return audio
def texts_to_speechs(segments:list[Audio],directory:Path,target_lang=None)->list[Audio]:
    directory.mkdir(parents=True,exist_ok=True);total=len(segments);results:list[Audio]=[]
    for(i,s)in enumerate(segments,0):
        txt_hash=hashlib.md5(str(s.text).encode('utf-8')).hexdigest()[:6];name=f"{s.end:.3f}_{s.start:.3f}_{txt_hash}.{C.fmt}";out_path=directory/name
        if out_path.exists():
            audio=AudioSegment.from_file(out_path,format=C.fmt);actual_dur=len(audio)/1e3;ns,ne=round(s.start,3),round(s.start+actual_dur,3)
            if ns<0:ne=round(ne+abs(ns),3);ns=.0
            results.append(Audio(start=ns,end=ne,text=out_path,pitch=s.pitch,atempo=s.atempo));progress(i,total,f'Skip({ns}:{ne}) "{name}"');continue
        audio=text_to_speech(s.text,pitch=s.pitch,atempo=s.atempo,target=target_lang)
        if not audio:continue
        actual_dur=len(audio)/1e3;ns=round(s.start,3);ne=round(s.start+actual_dur,3)
        if ns<0:ne=round(ne+abs(ns),3);ns=.0
        audio.export(out_path,format=C.fmt);results.append(Audio(start=ns,end=ne,text=out_path,pitch=s.pitch,atempo=s.atempo));progress(i,total,txt=f"To speech: {ns}s -> {ne}s",tab=1)
    progress(total,total,txt='All segments synchronized',bar_color='\x1b[90m',tab=1);line();return results
