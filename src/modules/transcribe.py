import os
from typing import Optional, List
from faster_whisper import WhisperModel
from pathlib import Path
from dataclasses import asdict
from src.utils import extract_audio, cal_time, w_json
from torch import cuda
from src.enties import Transcribe

class C: #configuration
	MODEL = 'medium' # WhisperModel : name or path
	HF_TOKEN = os.getenv('HF_TOKEN')
	_IS_CUDA = cuda.is_available()
	DEVICE = "cuda" if _IS_CUDA else "cpu"
	TYPE = "float16" if _IS_CUDA else "int8"
	language=None
	smin=.15
	smax=3.0
	beam_size=5
	word_timestamps=True,
	condition_on_previous_text=True,
	vad_filter=False

class mdl: # Models
	ndigits=3
	whisper:WhisperModel = cal_time(lambda: WhisperModel(C.MODEL, device=C.DEVICE, compute_type=C.TYPE), 'Load WhisperModel', clear=1)
	def transcribe(audio_path:str,language:Optional[str]=C.language)->List[Transcribe]:
		def r(nf,dg=mdl.ndigits):return round(nf,dg)
		res,_= mdl.whisper.transcribe(
			audio_path,
			beam_size=C.beam_size,
			word_timestamps=C.word_timestamps,
			condition_on_previous_text=C.condition_on_previous_text,
			vad_filter=C.vad_filter,
			language=language
		)
		segments:List[Transcribe]=[]
		for s in res:
			txt=s.text.strip()
			if txt:segments.append(Transcribe(r(s.start),r(s.end),txt))
		return segments
	def transcribe_length(audio_path:str,language:Optional[str]=C.language,max_words:int=10)->List[Transcribe]:
		def r(nf,dg=mdl.ndigits):return round(nf,dg)
		res,_=mdl.whisper.transcribe(
			audio_path,
			beam_size=C.beam_size,
			word_timestamps=C.word_timestamps,
			condition_on_previous_text=C.condition_on_previous_text,
			vad_filter=C.vad_filter,
			language=language
		);segments=[]
		for s in res:
			txt=s.text.strip()
			if not txt:continue
			if max_words<1 or not s.words:segments.append(Transcribe(r(s.start),r(s.end),txt))
			else:
				words=s.words;total_words=len(words)
				if total_words<=max_words:segments.append(Transcribe(r(s.start),r(s.end),txt))
				else:
					for i in range(0,total_words,max_words):
						chunk=words[i:i+max_words];chunk_start=chunk[0].start;chunk_end=chunk[-1].end;chunk_text=' '.join([w.word.strip()for w in chunk])
						if chunk_text:segments.append(Transcribe(r(chunk_start),r(chunk_end),chunk_text))
		return segments
	def transcribe_range(audio_path:str,language:Optional[str]=C.language, min=C.smin, max=C.smax)->List[Transcribe]:
		def r(nf,dg=mdl.ndigits):return round(nf,dg)
		res,_= mdl.whisper.transcribe(
			audio_path,
			beam_size=C.beam_size,
			word_timestamps=C.word_timestamps,
			condition_on_previous_text=C.condition_on_previous_text,
			vad_filter=C.vad_filter,
			language=language
		)
		segments:List[Transcribe]=[]
		for s in res:
			if s.avg_logprob < -1.0: continue
			txt=s.text.strip()
			if not txt:continue
			if not s.words:
				if s.end-s.start>=min:segments.append(Transcribe(r(s.start),r(s.end),txt))
				continue
			curr_txt=''
			curr_st=s.start
			for(i,w)in enumerate(s.words):
				word_txt=w.word.strip()
				if not word_txt:continue
				curr_txt+=word_txt
				current_duration=w.end-curr_st
				gap_to_next=0
				if i+1<len(s.words):gap_to_next=s.words[i+1].start-w.end
				is_punctuation=any(p in word_txt for p in'，。！？,!?')
				should_split=is_punctuation or gap_to_next>=.35 or current_duration>=max
				if should_split and current_duration>=min:
					if curr_txt.strip():segments.append(Transcribe(r(curr_st),r(w.end),curr_txt.strip()))
					curr_txt=''
					if i+1<len(s.words):curr_st=s.words[i+1].start
			if curr_txt.strip():
				if s.end-curr_st>=min:segments.append(Transcribe(r(curr_st),r(s.end),curr_txt.strip()))
		return segments

# execute
def initialization(p_audio:Path, target:Path, language:str=None):
	p_json = (target/target.stem).with_suffix('.json')
	if p_json.exists(): return
	p_json.parent.mkdir(parents=True, exist_ok=True)
	step_1 = lambda: mdl.transcribe(p_audio, language=language)
	data:list[Transcribe] = cal_time(step_1, f'Transcribe: {p_audio}', clear=1,tab=1)
	w_json(p_json, [asdict(d) for d in data])

