import io,os,sys,json,traceback,time,shutil,hashlib,tempfile,math,subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import TypeVar, Callable, ParamSpec
from gtts import gTTS
from pydub import AudioSegment
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
P = os.path
class C:
	fmt = 'wav'
	tar_lang = 'vi'
	tar_dir = 'speechs'
	pitch = 1.45
	atempo = 1.39
@dataclass
class Transcribe:
	start: float
	end: float
	text: str
	pitch: float = 1.0
	atempo: float = 1.25
class U:
	P = ParamSpec("P")
	R = TypeVar("R")
	@staticmethod
	def cal_time(fun: Callable[P, R], txt=None, tab=0, clear=0) -> Callable[P, R]:
		R_col, Y, B, C_col, W, GR, RS, K = '\033[31m', '\033[33m', '\033[34m', '\033[36m', '\033[37m', '\033[90m', '\033[0m', '\033[K'
		L = lambda x, k=W: print(f"{'\t'*tab}{k}{x}{RS}")
		p, m, cl, y = time.strftime, time.perf_counter, f'{B} : ', f'{GR}"{txt or fun.__name__}"'
		s, k = m(), f'{Y}{p("%H:%M:%S")}'
		L(f'{C_col}START{cl}{k}{cl}{y}', Y)
		e = fun()
		d = m()
		z, x = f'{Y}{p("%H:%M:%S")}', f' {W}({R_col}{d-s:.2f}{W})s'
		if clear > 0:
			sys.stdout.write(f"\r{K}\033[F"*clear)
			sys.stdout.flush()
			L(f'TIME{cl}{k} {W}~ {z}{x}{cl}{y}', C_col)
		else:
			L(f'END{cl}{z}{x}{cl}{y}', C_col)
		return e
	@staticmethod
	def pr(current=0, total=100, txt='Process', suffix=None, bar_color=None, tab=0, **bar):
		Y, C_col, W, GR, RS, CCL = '\x1b[33m', '\x1b[36m', '\x1b[37m', '\x1b[90m', '\x1b[0m', '\x1b[K'
		f, l, s = bar.get('fill', '█'), bar.get('line', '-'), bar.get('size', 25)
		total = total or 1
		percent = current / total
		pk = int(percent * s)
		sfx = suffix if suffix is not None else f"({percent*100:.2f})%"
		bar_str = f"{W}|{bar_color or W}{f*pk}{GR}{l*(s-pk)}{W}|"
		msg = f'{"    "*tab}{C_col}{txt} ({Y}{current}{C_col}/{Y}{total}{C_col}): {bar_str} : {GR}"{sfx}"{RS}'
		sys.stdout.write(f"\r{CCL}{msg}")
		sys.stdout.flush()
		if current >= total:
			print()
	@staticmethod
	def r_json(path: str) -> list | dict:
		if not os.path.exists(path):
			raise FileNotFoundError(path)
		with open(path, 'r', encoding='utf-8') as f:
			return json.load(f)
	@staticmethod
	def get_duration(path: str):
		try:
			cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path]
			result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').strip()
			return float(result)
		except (subprocess.CalledProcessError, ValueError):
			return .0
class mdl:
	@staticmethod
	def combine_audio_files(audios: list[Transcribe], output_path: Path, duration: float = .0, auto_speed=True) -> tuple[Path, float]:
		audios = sorted(audios, key=lambda x: x.start)
		if duration <= 0:
			duration = max([a.end for a in audios])
		combined = AudioSegment.silent(duration=int(duration * 1e3), frame_rate=AudioSegment.from_file(audios[0].text).frame_rate)
		n = len(audios)
		speeds = [1.0] * n
		starts = [a.start for a in audios]
		durs = []
		import pydub.effects as effects
		for a in audios:
			s = AudioSegment.from_file(a.text)
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
				lim = audios[i+1].start if i+1 < n else duration
				if (lim - starts[i]) > 0 and durs[i] > (lim - starts[i]):
					speeds[i] = min(max(speeds[i], durs[i] / (lim - starts[i])), C.atempo)
			for i in range(n):
				if i > 0:
					prev_end = starts[i-1] + (durs[i-1] / speeds[i-1])
					if prev_end > starts[i]:
						starts[i] = prev_end
		with tempfile.TemporaryDirectory() as tmp:
			for i, a in enumerate(audios):
				p = Path(a.text)
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
				combined = combined.overlay(seg, position=int(starts[i] * 1e3))
		output_path.parent.mkdir(parents=True, exist_ok=True)
		combined.export(output_path, format=output_path.suffix.replace('.', ''), bitrate='192k')
		return output_path, combined.duration_seconds
	@staticmethod
	def _gtts_speech(text, target_lang) -> AudioSegment:
		try:
			mp3_fp = io.BytesIO()
			gTTS(str(text), lang=target_lang).write_to_fp(mp3_fp)
			mp3_fp.seek(0)
			return AudioSegment.from_file(mp3_fp, format='mp3')
		except Exception as e:
			print(f"❌ Google-TTS Error: {e}")
			return None
	@staticmethod
	def text_to_speech(txt: str, output: str = None, atempo=1., pitch=1., target=C.tar_lang) -> AudioSegment:
		if not txt or not str(txt).strip():
			return None
		cur_t, p = float(atempo or 1.), float(pitch or 1.)
		audio = mdl._gtts_speech(txt, target)
		if not audio:
			return None
		if abs(cur_t - 1.) > 0 or abs(p - 1.) > 0:
			with tempfile.TemporaryDirectory() as tmp:
				t_in, t_out = Path(tmp) / f"in.{C.fmt}", Path(tmp) / f"out.{C.fmt}"
				audio.export(str(t_in), format=C.fmt)
				try:
					sr = audio.frame_rate
					act_t, fl = cur_t / p, [f"asetrate={int(sr*p)}"]
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
	@staticmethod
	def texts_to_speechs(segments: list[Transcribe], directory: Path) -> list[Transcribe]:
		directory.mkdir(parents=True, exist_ok=True)
		total = len(segments)
		results: list[Transcribe] = []
		for i, s in enumerate(segments, 0):
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
				results.append(Transcribe(start=ns, end=ne, text=out_path, pitch=s.pitch, atempo=s.atempo))
				U.pr(i, total, f'Skip({ns}:{ne}) "{name}"')
				continue
			audio = mdl.text_to_speech(s.text, pitch=s.pitch, atempo=s.atempo)
			if not audio:
				continue
			actual_dur = len(audio) / 1e3
			ns = round(s.start, 3)
			ne = round(s.start + actual_dur, 3)
			if ns < 0:
				ne = round(ne + abs(ns), 3)
				ns = .0
			audio.export(out_path, format=C.fmt)
			results.append(Transcribe(start=ns, end=ne, text=out_path, pitch=s.pitch, atempo=s.atempo))
			U.pr(i, total, txt=f"To speech: {ns}s -> {ne}s", tab=1)
		U.pr(total, total, txt='All segments synchronized', bar_color='\x1b[90m', tab=1)
		return results
class SpeakerRowWidget(QWidget):
	def __init__(self, text, on_delete):
		super().__init__()
		from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton
		layout = QHBoxLayout()
		layout.setContentsMargins(2, 2, 2, 2)
		layout.setSpacing(5)
		self.lbl = QLabel(text)
		self.btn = QPushButton("❌")
		self.btn.setFixedWidth(25)
		self.btn.clicked.connect(on_delete)
		layout.addWidget(self.lbl, 1)
		layout.addWidget(self.btn)
		self.setLayout(layout)
class ListRowWidget(QWidget):
	def __init__(self, text, full_text, on_delete, on_check, checked=True):
		super().__init__()
		from PyQt6.QtWidgets import QHBoxLayout, QCheckBox, QLabel, QPushButton
		layout = QHBoxLayout()
		layout.setContentsMargins(2, 2, 2, 2)
		layout.setSpacing(5)
		self.cb = QCheckBox()
		self.cb.setChecked(checked)
		if on_check: self.cb.stateChanged.connect(on_check)
		self.lbl = QLabel(text)
		self.full_text = full_text
		self.btn = QPushButton("❌")
		self.btn.setFixedWidth(25)
		self.btn.clicked.connect(on_delete)
		layout.addWidget(self.cb)
		layout.addWidget(self.lbl, 1)
		layout.addWidget(self.btn)
		self.setLayout(layout)
class SpeakerTesterApp(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("PyQt6 Speaker Voice Tester")
		self.resize(1100, 600)
		self.current_file_path = None
		self.diarization_data = {"speakers": [], "timestamps": []}
		self.temp_test_dir = tempfile.mkdtemp()
		self.media_player = QMediaPlayer()
		self.audio_output = QAudioOutput()
		self.media_player.setAudioOutput(self.audio_output)
		self.imported_raw_content = None
		self.imported_data = None
		self.imported_type = None
		self.generated_voices = []
		self.init_ui()
	def init_ui(self):
		from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QWidget
		main_widget = QWidget()
		self.setCentralWidget(main_widget)
		h_layout = QHBoxLayout()
		main_widget.setLayout(h_layout)
		left_panel = QVBoxLayout()
		left_panel.addWidget(QLabel("Diarization"))
		row1 = QHBoxLayout()
		self.btn_load = QPushButton("[Import diarization.json]")
		self.btn_load.clicked.connect(self.load_json_file)
		self.btn_save = QPushButton("[Save]")
		self.btn_save.clicked.connect(self.save_json_file)
		self.btn_clear = QPushButton("[Clear]")
		self.btn_clear.clicked.connect(self.clear_data)
		row1.addWidget(self.btn_load)
		row1.addWidget(self.btn_save)
		row1.addWidget(self.btn_clear)
		left_panel.addLayout(row1)
		batch_layout = QHBoxLayout()
		batch_layout.addWidget(QLabel("pitch"))
		self.cb_p_sign = QComboBox()
		self.cb_p_sign.addItems(["+", "-"])
		batch_layout.addWidget(self.cb_p_sign)
		self.txt_p_off = QLineEdit("0.25")
		self.txt_p_off.setFixedWidth(50)
		batch_layout.addWidget(self.txt_p_off)
		batch_layout.addWidget(QLabel("atempo"))
		self.cb_a_sign = QComboBox()
		self.cb_a_sign.addItems(["+", "-"])
		batch_layout.addWidget(self.cb_a_sign)
		self.txt_a_off = QLineEdit("0.25")
		self.txt_a_off.setFixedWidth(50)
		batch_layout.addWidget(self.txt_a_off)
		self.btn_batch = QPushButton("[Set]")
		self.btn_batch.clicked.connect(self.apply_batch_offset)
		batch_layout.addWidget(self.btn_batch)
		left_panel.addLayout(batch_layout)
		add_speaker_layout = QHBoxLayout()
		add_speaker_layout.addWidget(QLabel("pitch"))
		self.txt_add_p = QLineEdit("1.0")
		self.txt_add_p.setFixedWidth(40)
		add_speaker_layout.addWidget(self.txt_add_p)
		add_speaker_layout.addWidget(QLabel("atempo"))
		self.txt_add_a = QLineEdit("1.0")
		self.txt_add_a.setFixedWidth(40)
		add_speaker_layout.addWidget(self.txt_add_a)
		self.btn_add_diar = QPushButton("[Add diarization]")
		self.btn_add_diar.clicked.connect(self.add_diarization)
		add_speaker_layout.addWidget(self.btn_add_diar)
		left_panel.addLayout(add_speaker_layout)
		self.list_speakers = QListWidget()
		self.list_speakers.currentRowChanged.connect(self.on_speaker_selected)
		left_panel.addWidget(self.list_speakers)
		self.lbl_selected_speaker = QLabel("[ No Speaker Selected ]:")
		left_panel.addWidget(self.lbl_selected_speaker)
		settings_layout = QHBoxLayout()
		settings_layout.addWidget(QLabel("pitch"))
		self.txt_pitch = QLineEdit("1.0")
		self.txt_pitch.textChanged.connect(self.on_settings_edited)
		settings_layout.addWidget(self.txt_pitch)
		settings_layout.addWidget(QLabel("atempo"))
		self.txt_atempo = QLineEdit("1.0")
		self.txt_atempo.textChanged.connect(self.on_settings_edited)
		settings_layout.addWidget(self.txt_atempo)
		left_panel.addLayout(settings_layout)
		self.lbl_speaker_status = QLabel("Speakers(count): 0       No speaker selected")
		left_panel.addWidget(self.lbl_speaker_status)
		h_layout.addLayout(left_panel, 1)
		mid_panel = QVBoxLayout()
		row5_header = QHBoxLayout()
		row5_header.addWidget(QLabel("Text to test"))
		self.btn_clear_checked_phrases = QPushButton("[Clear (0)]")
		self.btn_clear_checked_phrases.clicked.connect(self.clear_checked_phrases)
		row5_header.addWidget(self.btn_clear_checked_phrases)
		self.cb_lang = QComboBox()
		self.cb_lang.addItems(["vi", "en", "zh-cn", "ja", "ko"])
		self.cb_lang.setCurrentText(C.tar_lang)
		row5_header.addWidget(self.cb_lang)
		mid_panel.addLayout(row5_header)
		self.list_test_phrases = QListWidget()
		mid_panel.addWidget(self.list_test_phrases)
		test_input_layout = QHBoxLayout()
		self.txt_new_test = QLineEdit("Xin chào, đây là giọng thử nghiệm của tôi.")
		self.btn_add_test = QPushButton("[Add test]")
		self.btn_add_test.clicked.connect(self.add_test_phrase)
		test_input_layout.addWidget(self.txt_new_test, 1)
		test_input_layout.addWidget(self.btn_add_test)
		mid_panel.addLayout(test_input_layout)
		import_layout = QHBoxLayout()
		self.btn_import_text = QPushButton("[Import data text]")
		self.btn_import_text.clicked.connect(self.import_text_data)
		self.cb_key_select = QComboBox()
		self.cb_key_select.setEditable(True)
		self.cb_key_select.addItems(["None", "text", C.tar_lang])
		self.cb_key_select.currentTextChanged.connect(self.update_imported_text)
		self.btn_clear_import = QPushButton("[clear]")
		self.btn_clear_import.clicked.connect(self.clear_imported_text)
		import_layout.addWidget(self.btn_import_text)
		import_layout.addWidget(self.cb_key_select)
		import_layout.addWidget(self.btn_clear_import)
		mid_panel.addLayout(import_layout)
		self.lbl_import_count = QLabel("Import 0 objects")
		mid_panel.addWidget(self.lbl_import_count)
		self.btn_test = QPushButton("[          START          ]")
		self.btn_test.clicked.connect(self.run_voice_test)
		mid_panel.addWidget(self.btn_test)
		h_layout.addLayout(mid_panel, 1)
		right_panel = QVBoxLayout()
		row_voice_header = QHBoxLayout()
		row_voice_header.addWidget(QLabel("Voice"))
		self.btn_remove_checked_voices = QPushButton("[remove (0) audio]")
		self.btn_remove_checked_voices.clicked.connect(self.remove_checked_voices)
		row_voice_header.addWidget(self.btn_remove_checked_voices)
		right_panel.addLayout(row_voice_header)
		self.list_voices = QListWidget()
		self.list_voices.itemClicked.connect(self.play_voice_item)
		right_panel.addWidget(self.list_voices)
		self.btn_export = QPushButton("[Export (0) files]")
		self.btn_export.clicked.connect(self.export_voice_files)
		right_panel.addWidget(self.btn_export)
		h_layout.addLayout(right_panel, 1)
		for text in ["Xin chào, đây là giọng thử nghiệm của tôi.", "Tôi muốn kiểm tra độ cao và tốc độ nói.", "Mỗi dòng điện thoại thông minh đều có ưu điểm riêng biệt."]:
			self.add_phrase_to_list(text)
	def add_phrase_to_list(self, text):
		from PyQt6.QtWidgets import QListWidgetItem
		text = text.strip()
		if not text: return
		for i in range(self.list_test_phrases.count()):
			item = self.list_test_phrases.item(i)
			w = self.list_test_phrases.itemWidget(item)
			if w and w.full_text == text: return
		item = QListWidgetItem()
		self.list_test_phrases.addItem(item)
		disp_text = text[:30] + "..." if len(text) > 30 else text
		row_widget = ListRowWidget(disp_text, text, lambda: self.delete_phrase(item), self.update_phrase_counts)
		item.setSizeHint(row_widget.sizeHint())
		self.list_test_phrases.setItemWidget(item, row_widget)
		self.update_phrase_counts()
	def delete_phrase(self, item):
		row = self.list_test_phrases.row(item)
		if row >= 0:
			self.list_test_phrases.takeItem(row)
		self.update_phrase_counts()
	def clear_checked_phrases(self):
		for i in range(self.list_test_phrases.count() - 1, -1, -1):
			item = self.list_test_phrases.item(i)
			w = self.list_test_phrases.itemWidget(item)
			if w and w.cb.isChecked():
				self.list_test_phrases.takeItem(i)
		self.update_phrase_counts()
	def update_phrase_counts(self, state=None):
		total = self.list_test_phrases.count()
		checked = 0
		for i in range(total):
			item = self.list_test_phrases.item(i)
			w = self.list_test_phrases.itemWidget(item)
			if w and w.cb.isChecked():
				checked += 1
		self.lbl_import_count.setText(f"Import {total} objects")
		self.btn_clear_checked_phrases.setText(f"[Clear ({checked})]")
	def add_voice_to_list(self, v_info):
		from PyQt6.QtWidgets import QListWidgetItem
		idx = len(self.generated_voices)
		trunc_txt = v_info['text'][:30] + "..." if len(v_info['text']) > 30 else v_info['text']
		display_text = f"{idx} {trunc_txt} ({v_info['duration']:.2f}:{v_info['pitch']})"
		item = QListWidgetItem()
		self.list_voices.addItem(item)
		row_widget = ListRowWidget(display_text, v_info['text'], lambda: self.delete_voice(item), self.update_export_btn_text)
		item.setSizeHint(row_widget.sizeHint())
		self.list_voices.setItemWidget(item, row_widget)
		self.update_export_btn_text()
	def delete_voice(self, item):
		row = self.list_voices.row(item)
		if row >= 0:
			self.list_voices.takeItem(row)
			if row < len(self.generated_voices):
				self.generated_voices.pop(row)
		self.update_export_btn_text()
	def remove_checked_voices(self):
		for i in range(self.list_voices.count() - 1, -1, -1):
			item = self.list_voices.item(i)
			w = self.list_voices.itemWidget(item)
			if w and w.cb.isChecked():
				self.list_voices.takeItem(i)
				if i < len(self.generated_voices):
					self.generated_voices.pop(i)
		self.update_export_btn_text()
	def play_voice_item(self, item):
		from PyQt6.QtCore import QUrl
		row = self.list_voices.row(item)
		if row >= 0 and row < len(self.generated_voices):
			v = self.generated_voices[row]
			self.media_player.stop()
			self.media_player.setSource(QUrl.fromLocalFile(v["path"]))
			self.media_player.play()
	def update_export_btn_text(self, state=None):
		checked = 0
		for i in range(self.list_voices.count()):
			item = self.list_voices.item(i)
			w = self.list_voices.itemWidget(item)
			if w and w.cb.isChecked():
				checked += 1
		self.btn_remove_checked_voices.setText(f"[remove ({checked}) audio]")
		self.btn_export.setText(f"[Export ({checked}) files]")
	def export_voice_files(self):
		from PyQt6.QtWidgets import QFileDialog, QMessageBox
		import re
		checked_indices = []
		for i in range(self.list_voices.count()):
			item = self.list_voices.item(i)
			w = self.list_voices.itemWidget(item)
			if w and w.cb.isChecked():
				checked_indices.append(i)
		if not checked_indices:
			QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một file để export!")
			return
		export_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file")
		if not export_dir: return
		try:
			for idx in checked_indices:
				if idx < len(self.generated_voices):
					v = self.generated_voices[idx]
					clean_txt = re.sub(r'[\\/*?:"<>|]', "", v["text"]).replace(" ", "_")
					fn = f"{idx + 1}_{clean_txt}_{v['duration']:.2f}_{v['pitch']}.wav"
					dest = Path(export_dir) / fn
					shutil.copy(v["path"], dest)
			QMessageBox.information(self, "Thành công", f"Đã export thành công {len(checked_indices)} files!")
		except Exception as e:
			QMessageBox.critical(self, "Lỗi", f"Lỗi khi export:\n{e}")
	def import_text_data(self):
		file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file", "", "Supported Files (*.txt *.json);;All Files (*)")
		if not file_path: return
		try:
			with open(file_path, 'r', encoding='utf-8') as f:
				content = f.read()
			self.imported_raw_content = content
			try:
				self.imported_data = json.loads(content)
				self.imported_type = "json"
			except:
				self.imported_data = [line.strip() for line in content.split('\n') if line.strip()]
				self.imported_type = "text"
			self.update_imported_text()
		except Exception as e:
			QMessageBox.critical(self, "Lỗi", f"Không thể import file:\n{e}")
	def update_imported_text(self):
		if self.imported_raw_content is None: return
		key = self.cb_key_select.currentText().strip()
		items = []
		if self.imported_type == "json":
			if key == "None" or not key:
				items = [line.strip() for line in self.imported_raw_content.split('\n') if line.strip()]
			else:
				if isinstance(self.imported_data, list):
					items = [str(d.get(key)) for d in self.imported_data if isinstance(d, dict) and d.get(key) is not None]
				elif isinstance(self.imported_data, dict):
					items = [str(self.imported_data.get(key))] if self.imported_data.get(key) is not None else []
		else:
			items = self.imported_data
		self.list_test_phrases.clear()
		if items:
			for item_txt in items:
				self.add_phrase_to_list(item_txt)
		self.update_phrase_counts()
	def clear_imported_text(self):
		self.imported_raw_content = None
		self.imported_data = None
		self.imported_type = None
		self.list_test_phrases.clear()
		for text in ["Xin chào, đây là giọng thử nghiệm của tôi.", "Tôi muốn kiểm tra độ cao và tốc độ nói.", "Mỗi dòng điện thoại thông minh đều có ưu điểm riêng biệt."]:
			self.add_phrase_to_list(text)
		self.update_phrase_counts()
	def load_json_file(self):
		file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file diarization.json", "", "JSON Files (*.json)")
		if not file_path: return
		try:
			data = U.r_json(file_path)
			if not isinstance(data, dict) or "speakers" not in data:
				raise ValueError("Cấu trúc file JSON không hợp lệ (thiếu khoá 'speakers').")
			self.current_file_path = file_path
			self.diarization_data = data
			self.refresh_speaker_list()
			self.btn_load.setText(f"File: {Path(file_path).name}")
		except Exception as e:
			QMessageBox.critical(self, "Lỗi", f"Không thể đọc file JSON:\n{e}")
	def clear_data(self):
		self.current_file_path = None
		self.diarization_data["speakers"] = []
		self.list_speakers.clear()
		self.update_speaker_status()
		self.lbl_selected_speaker.setText("[ No Speaker Selected ]:")
		self.txt_pitch.setText("1.0")
		self.txt_atempo.setText("1.0")
		self.btn_load.setText("[Import diarization.json]")
	def refresh_speaker_list(self):
		from PyQt6.QtWidgets import QListWidgetItem
		self.list_speakers.blockSignals(True)
		self.list_speakers.clear()
		speakers = self.diarization_data.get("speakers", [])
		for sp in speakers:
			name = sp.get('name', 'UNKNOWN')
			trunc_name = name[:30] + "..." if len(name) > 30 else name
			display_text = f"{trunc_name} : id: {sp.get('id')} : pitch: {sp.get('pitch', 1.0)} : atempo: {sp.get('atempo', 1.0)}"
			item = QListWidgetItem()
			self.list_speakers.addItem(item)
			row_widget = SpeakerRowWidget(display_text, lambda s_item=item: self.delete_speaker(s_item))
			item.setSizeHint(row_widget.sizeHint())
			self.list_speakers.setItemWidget(item, row_widget)
		self.list_speakers.blockSignals(False)
		self.update_speaker_status()
	def delete_speaker(self, item):
		row = self.list_speakers.row(item)
		if row >= 0:
			self.list_speakers.takeItem(row)
			speakers = self.diarization_data.get("speakers", [])
			if row < len(speakers):
				speakers.pop(row)
		self.update_speaker_status()
	def add_diarization(self):
		try:
			p = float(self.txt_add_p.text() or 1.0)
			a = float(self.txt_add_a.text() or 1.0)
		except ValueError: return
		speakers = self.diarization_data.setdefault("speakers", [])
		new_id = max([s.get("id", 0) for s in speakers], default=0) + 1
		new_sp = {"id": new_id, "name": f"SPEAKER_{new_id:02d}", "pitch": p, "atempo": a}
		speakers.append(new_sp)
		self.refresh_speaker_list()
	def update_speaker_status(self):
		cnt = len(self.diarization_data.get("speakers", []))
		row = self.list_speakers.currentRow()
		if row >= 0 and row < cnt:
			name = self.diarization_data["speakers"][row].get("name", "UNKNOWN")
			self.lbl_speaker_status.setText(f"Speakers(count): {cnt}       Selected: {name}")
		else:
			self.lbl_speaker_status.setText(f"Speakers(count): {cnt}       No speaker selected")
	def on_speaker_selected(self, index):
		self.update_speaker_status()
		if index < 0 or index >= len(self.diarization_data.get("speakers", [])): return
		sp = self.diarization_data["speakers"][index]
		self.lbl_selected_speaker.setText(f"[ {sp.get('name')} ]:")
		self.txt_pitch.blockSignals(True)
		self.txt_atempo.blockSignals(True)
		self.txt_pitch.setText(str(sp.get("pitch", 1.0)))
		self.txt_atempo.setText(str(sp.get("atempo", 1.0)))
		self.txt_pitch.blockSignals(False)
		self.txt_atempo.blockSignals(False)
	def on_settings_edited(self):
		index = self.list_speakers.currentRow()
		if index < 0 or index >= len(self.diarization_data.get("speakers", [])): return
		try:
			new_pitch = float(self.txt_pitch.text() or 1.0)
			new_atempo = float(self.txt_atempo.text() or 1.0)
		except ValueError: return
		sp = self.diarization_data["speakers"][index]
		sp["pitch"] = new_pitch
		sp["atempo"] = new_atempo
		self.refresh_speaker_list()
	def apply_batch_offset(self):
		try:
			p_val = float(self.txt_p_off.text() or 0.0)
			a_val = float(self.txt_a_off.text() or 0.0)
		except ValueError:
			QMessageBox.warning(self, "Cảnh báo", "Giá trị sai!")
			return
		p_sign = 1.0 if self.cb_p_sign.currentText() == "+" else -1.0
		a_sign = 1.0 if self.cb_a_sign.currentText() == "+" else -1.0
		for sp in self.diarization_data.get("speakers", []):
			cur_p = sp.get("pitch", 1.0)
			cur_a = sp.get("atempo", 1.0)
			new_p = max(0.1, round(cur_p + (p_sign * p_val), 3))
			new_a = max(0.1, round(cur_a + (a_sign * a_val), 3))
			sp["pitch"] = new_p
			sp["atempo"] = new_a
		self.refresh_speaker_list()
		curr_row = self.list_speakers.currentRow()
		if curr_row >= 0:
			self.on_speaker_selected(curr_row)
	def save_json_file(self):
		if self.current_file_path:
			save_path = self.current_file_path
		else:
			save_path, _ = QFileDialog.getSaveFileName(self, "Lưu file Diarization", "Test_diarization.json", "JSON Files (*.json)")
			if not save_path: return
		try:
			with open(save_path, 'w', encoding='utf-8') as f:
				json.dump(self.diarization_data, f, indent=4, ensure_ascii=False)
			self.current_file_path = save_path
			self.btn_load.setText(f"File: {Path(save_path).name}")
			QMessageBox.information(self, "Thành công", f"Đã lưu thành công tại:\n{save_path}")
		except Exception as e:
			QMessageBox.critical(self, "Lỗi", f"Không thể lưu file JSON:\n{e}")
	def run_voice_test(self):
		from PyQt6.QtCore import QUrl
		from PyQt6.QtWidgets import QMessageBox
		checked_texts = []
		for i in range(self.list_test_phrases.count()):
			item = self.list_test_phrases.item(i)
			w = self.list_test_phrases.itemWidget(item)
			if w and w.cb.isChecked():
				checked_texts.append(w.full_text)
		if not checked_texts:
			QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một văn bản để test!")
			return
		try:
			pitch = float(self.txt_pitch.text() or 1.0)
			atempo = float(self.txt_atempo.text() or 1.0)
		except ValueError:
			QMessageBox.warning(self, "Cảnh báo", "Giá trị pitch hoặc atempo không hợp lệ!")
			return
		lang = self.cb_lang.currentText().strip()
		self.btn_test.setEnabled(False)
		self.btn_test.setText("TTS...")
		QApplication.processEvents()
		try:
			for text in checked_texts:
				existing = None
				for g in self.generated_voices:
					if g["text"] == text and abs(g["pitch"] - pitch) < 1e-4 and abs(g["atempo"] - atempo) < 1e-4 and g["lang"] == lang:
						existing = g
						break
				if existing:
					self.media_player.stop()
					self.media_player.setSource(QUrl.fromLocalFile(existing["path"]))
					self.media_player.play()
					time.sleep(0.1)
					continue
				temp_wav_path = os.path.join(self.temp_test_dir, f"test_speaker_{int(time.time())}_{len(self.generated_voices)}.wav")
				audio = mdl.text_to_speech(text, output=temp_wav_path, atempo=atempo, pitch=pitch, target=lang)
				if audio is None: raise ValueError("Không tạo được audio.")
				dur = len(audio) / 1000.0
				v_info = {"text": text, "pitch": pitch, "atempo": atempo, "lang": lang, "path": temp_wav_path, "duration": dur}
				self.generated_voices.append(v_info)
				self.add_voice_to_list(v_info)
				self.media_player.stop()
				self.media_player.setSource(QUrl.fromLocalFile(temp_wav_path))
				self.media_player.play()
		except Exception as e:
			QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra:\n{e}")
		finally:
			self.btn_test.setEnabled(True)
			self.btn_test.setText("[          START          ]")
	def add_test_phrase(self):
		text = self.txt_new_test.text().strip()
		if text:
			self.add_phrase_to_list(text)
	def closeEvent(self, event):
		if os.path.exists(self.temp_test_dir):
			shutil.rmtree(self.temp_test_dir, ignore_errors=True)
		super().closeEvent(event)
if __name__ == "__main__":
	app = QApplication(sys.argv)
	tester = SpeakerTesterApp()
	tester.show()
	sys.exit(app.exec())

	