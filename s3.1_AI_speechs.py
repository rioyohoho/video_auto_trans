import os, sys
import torch
import torchaudio
from pathlib import Path
from tabulate import tabulate
from src.modules.speech_ai import XTTSProcessor
from src.enties import agr
from src.utils import ext, txt, file, r_json, listFilter, handle_input, txt_normalize, cal_time, str2bool, progress
from src.configuration import PATH_BASE, P_DIR, TAR_LANG, XTTS_TMP_VOICE

P = os.path
processor = cal_time(lambda: XTTSProcessor(), 'LOAD: XTTSProcessor', 1, 1)

def adjust_speed(wav: torch.Tensor, target_len: int, sr: int = 24000) -> torch.Tensor:
	"""Tự động tăng tốc độ đọc khớp với target_len (giữ nguyên tone giọng)"""
	cur_len = wav.shape[-1]
	if cur_len <= target_len or target_len <= 0:
		return wav
	speed_factor = cur_len / target_len
	try:
		n_fft = 512
		hop_length = n_fft // 4
		spec = torch.stft(wav, n_fft=n_fft, hop_length=hop_length, return_complex=True)
		stretched_spec = torchaudio.functional.phase_vocoder(spec, rate=speed_factor, hop_length=hop_length)
		return torch.istft(stretched_spec, n_fft=n_fft, hop_length=hop_length, length=target_len)
	except Exception:
		# Fallback nội suy tuyến tính nếu phase vocoder lỗi shape
		return torch.nn.functional.interpolate(wav.unsqueeze(0), size=target_len, mode='linear', align_corners=False).squeeze(0)

def run(text: str, output: Path, language: str = TAR_LANG, tmp_voice: str = str(XTTS_TMP_VOICE)):
	ts = processor.split_text_by_tokens(text, lang=language, mt=100)
	mini_text = lambda txt, sz=100: txt if len(txt) <= sz else txt[:sz//2] + ' ... ' + txt[-sz//2:]
	txt.cyan(tabulate(maxcolwidths=[None, None, None, 50], headers=['language', 'output', 'tmp_voice', 'texts'], tabular_data=[(language, str(output), str(tmp_voice), mini_text('\n'.join(ts), 50))], tablefmt="grid"))
	processor.save(output, processor.concat(processor.text_to_ai_speeches(ts, language=language, tmp_voice=tmp_voice)))

def run_timestamp(data: list, output: Path, language: str = TAR_LANG, tmp_voice: str = str(XTTS_TMP_VOICE), sr: int = 24000):
	valid_items = [x for x in data if isinstance(x, dict) and x.get('text', '').strip()]
	if not valid_items:
		txt.red("No valid subtitle items found in JSON!")
		return
	
	# Xác định tổng độ dài chính xác của audio theo timestamp cuối cùng
	max_end_time = max(float(x.get('end', 0.0)) for x in valid_items)
	total_samples = int(max_end_time * sr)
	canvas = torch.zeros((1, total_samples), dtype=torch.float32)

	mini_text = lambda txt, sz=100: txt if len(txt) <= sz else txt[:sz//2] + ' ... ' + txt[-sz//2:]
	preview_str = '\n'.join([f"[{x.get('start', 0.0)}s -> {x.get('end', 0.0)}s] {x.get('text')}" for x in valid_items])
	txt.cyan(tabulate(maxcolwidths=[None, None, None, 50], headers=['language', 'output', 'tmp_voice', f'Total: {max_end_time:.2f}s'], tabular_data=[(language, str(output), str(tmp_voice), mini_text(preview_str, 50))], tablefmt="grid"))

	total_items = len(valid_items)
	progress(0, total_items, txt="Generating TTS", suffix="Starting...")
	for i, item in enumerate(valid_items):
		start_sec = float(item.get('start', 0.0))
		end_sec = float(item.get('end', start_sec))
		
		if i + 1 < len(valid_items):
			next_start = float(valid_items[i + 1].get('start', end_sec))
			available_duration = max(end_sec - start_sec, next_start - start_sec)
		else:
			available_duration = end_sec - start_sec

		target_max_samples = int(available_duration * sr)
		start_sample = int(start_sec * sr)
		text_seg = item.get('text', '').strip()

		speeches = processor.text_to_ai_speeches([text_seg], language=language, tmp_voice=tmp_voice)
		if not speeches:
			continue

		seg_tensor = processor.concat(speeches)
		
		if seg_tensor.shape[-1] > target_max_samples and target_max_samples > 0:
			seg_tensor = adjust_speed(seg_tensor, target_max_samples, sr=sr)

		seg_len = seg_tensor.shape[-1]
		end_sample = min(start_sample + seg_len, total_samples)
		actual_len = end_sample - start_sample

		if actual_len > 0:
			canvas[:, start_sample:end_sample] = seg_tensor[:, :actual_len]
		short_txt = text_seg if len(text_seg) <= 20 else text_seg[:17] + '...'
		progress(i + 1, total_items, txt="Generating TTS", suffix=f"[{start_sec}s-{end_sec}s] {short_txt}")
	processor.save(output, canvas, sr=sr)

def _exec(p: Path, o: Path, l: str = TAR_LANG, t: Path = XTTS_TMP_VOICE, min_mode: bool = True):
	out_path = o or p.with_suffix(f'.{l}.wav')
	if p.suffix == '.json':
		raw_data = r_json(str(p))
		if not min_mode and isinstance(raw_data, list) and any('start' in x for x in raw_data if isinstance(x, dict)):
			run_timestamp(raw_data, out_path, l, str(t))
			return
		d = '\n'.join([x.get('text', '') for x in list[dict](raw_data) if x.get('text')])
	elif p.suffix == '.txt':
		d = file.r_text(str(p))
	else:
		txt.red(f'"{p}" is not a valid file!')
		return
	run(d, out_path, l, str(t))

def _exec_str(text: str, o: Path, l: str = TAR_LANG, t: Path = XTTS_TMP_VOICE):
	run(text, o or Path(f'./{txt_normalize(text, 39)}.{l}.wav'), l, str(t))

if __name__ == '__main__':
	args = handle_input(
		agr(('-i', '--input'), type=str, required=False, default=P_DIR),
		agr(('-o', '--output'), type=str, required=False, default=''),
		agr(('-t', '--temple'), type=str, required=False, default=XTTS_TMP_VOICE),
		agr(('-l', '--language'), type=str, required=False, default=TAR_LANG),
		agr(('-mi', '--min'), type=str2bool, required=False, default='true')
	)
	i, o, t, l, min_mode = str(args.input), str(args.output), Path(args.temple), str(args.language), bool(args.min)
	op = Path(o) if o else None
	if not t.is_absolute(): t = PATH_BASE / t
	try: p, is_d, is_f = Path(i), Path(i).is_dir(), Path(i).is_file()
	except OSError: p, is_d, is_f = Path('.'), False, False

	if is_d:
		if not p.exists(): sys.exit(0)
		for _, n in enumerate(listFilter(p, exts=ext.DOC), 1): _exec((p / n), op, l, t, min_mode=min_mode)
	elif is_f and str(p).endswith(ext.DOC):
		if not p.exists(): sys.exit(0)
		_exec(p, op, l, t, min_mode=min_mode)
	else:
		_exec_str(i, op, l, t)