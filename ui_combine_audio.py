import json, os, subprocess, sys, tempfile
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QPointF, QUrl
from PyQt6.QtGui import QColor, QFont, QPen, QBrush, QPainter
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import *
def get_dur(p):
	try:
		r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", p], capture_output=True, text=True, encoding="utf-8")
		d = json.loads(r.stdout)
		if "format" in d and "duration" in d["format"]: return float(d["format"]["duration"])
		for s in d.get("streams", []):
			if "duration" in s: return float(s["duration"])
	except: pass
	try:
		r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprintwrappers=1:nokey=1", p], capture_output=True, text=True)
		return float(r.stdout.strip())
	except: pass
	return 180.0
@dataclass
class AudioClip:
	file_path: str; name: str; start_time: float = 0.0; duration: float = 0.0; clip_start: float = 0.0; clip_end: float = 0.0; speed: float = 1.0; pitch: float = 0.0; volume: float = 1.0; track: int = 0
class ClipGraphicsItem(QGraphicsRectItem):
	def __init__(A, c, mw):
		super().__init__(); A.clip, A.mw = c, mw
		A.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
		A.setAcceptHoverEvents(True); A.setBrush(QBrush(QColor(0, 180, 216, 180))); A.setPen(QPen(QColor(255, 255, 255), 1.5)); A.drag_mode = None; A.update_rect()
	def update_rect(A):
		d = (A.clip.clip_end - A.clip.clip_start) / max(0.1, A.clip.speed)
		A.setRect(0, 0, max(10.0, d * A.mw.zoom_factor), 50); A.setPos(A.clip.start_time * A.mw.zoom_factor, 40 + A.clip.track * 60)
	def paint(A, p, o, w):
		super().paint(p, o, w); p.setPen(QColor(255, 255, 255)); p.setFont(QFont("consolas", 8, QFont.Weight.Bold))
		p.drawText(A.rect().adjusted(5, 5, -5, -5), f"{A.clip.name} [{A.clip.speed}x|{A.clip.pitch:+}st]")
	def hoverMoveEvent(A, e):
		p = e.pos().x(); A.setCursor(Qt.CursorShape.SizeHorCursor if p < 8 or p > A.rect().width() - 8 else Qt.CursorShape.ArrowCursor); super().hoverMoveEvent(e)
	def mousePressEvent(A, e):
		A.mw.select_clip(A.clip); p = e.pos().x(); A.drag_mode = "left" if p < 8 else ("right" if p > A.rect().width() - 8 else "move")
		A.press_x = e.scenePos().x(); A.orig_st, A.orig_cs, A.orig_ce = A.clip.start_time, A.clip.clip_start, A.clip.clip_end; super().mousePressEvent(e)
	def mouseMoveEvent(A, e):
		if A.drag_mode in ("left", "right"):
			dx = (e.scenePos().x() - A.press_x) / A.mw.zoom_factor
			if A.drag_mode == "left":
				ns = A.orig_cs + dx * A.clip.speed
				if 0 <= ns < A.orig_ce - 0.1: A.clip.clip_start = ns; A.clip.start_time = A.orig_st + (ns - A.orig_cs) / A.clip.speed
			elif A.drag_mode == "right":
				ne = A.orig_ce + dx * A.clip.speed
				if A.orig_cs + 0.1 < ne <= A.clip.duration: A.clip.clip_end = ne
			A.update_rect(); A.mw.sync_clip_controls()
		else: super().mouseMoveEvent(e)
	def mouseReleaseEvent(A, e): A.drag_mode = None; super().mouseReleaseEvent(e)
	def itemChange(A, c, v):
		if c == QGraphicsItem.GraphicsItemChange.ItemPositionChange and A.scene() and A.drag_mode == "move":
			nx, nt = max(0.0, v.x()), max(0, int((v.y() - 40) / 60)); A.clip.start_time, A.clip.track = nx / A.mw.zoom_factor, nt; A.mw.sync_clip_controls()
			return QPointF(nx, 40 + nt * 60)
		return super().itemChange(c, v)
class AudioTimelineView(QGraphicsView):
	def __init__(A, mw): super().__init__(); A.mw = mw; A.setAcceptDrops(True); A.setRenderHint(QPainter.RenderHint.Antialiasing)
	def dragEnterEvent(A, e): (e.acceptProposedAction() if e.mimeData().hasUrls() else None)
	def dragMoveEvent(A, e): (e.acceptProposedAction() if e.mimeData().hasUrls() else None)
	def dropEvent(A, e):
		if e.mimeData().hasUrls():
			for u in e.mimeData().urls():
				p = u.toLocalFile()
				if p.lower().endswith((".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg")): A.mw.add_audio_file(p)
		e.acceptProposedAction()
	def wheelEvent(A, e):
		if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
			A.mw.zoom_factor = max(5.0, min(300.0, A.mw.zoom_factor * (1.15 if e.angleDelta().y() > 0 else 0.85))); A.mw.redraw_scene(); e.accept()
		else: super().wheelEvent(e)
	def mousePressEvent(A, e):
		if e.button() == Qt.MouseButton.LeftButton:
			sp = A.mapToScene(e.pos())
			if sp.y() < 30: A.mw.set_playhead(max(0.0, sp.x() / A.mw.zoom_factor))
		super().mousePressEvent(e)
class AudioMixerApp(QMainWindow):
	def __init__(A):
		super().__init__(); A.setWindowTitle("FFmpeg Audio Editor & Mixer"); A.resize(1200, 700); A.setStyleSheet("background-color: #181818; color: #ffffff; font-family: consolas;")
		A.clips, A.selected_clip, A.zoom_factor, A.current_time = [], None, 30.0, 0.0; A.playhead_line = None; A.temp_file = os.path.join(tempfile.gettempdir(), "preview_mix.wav")
		A.player, A.audio_output = QMediaPlayer(), QAudioOutput(); A.player.setAudioOutput(A.audio_output); A.player.positionChanged.connect(A.on_player_position); A.init_ui()
	def init_ui(A):
		s = QSplitter(Qt.Orientation.Horizontal); lw, rw = QWidget(), QWidget(); ll, rl = QVBoxLayout(lw), QVBoxLayout(rw); ll.setContentsMargins(4, 4, 4, 4); rl.setContentsMargins(8, 8, 8, 8); rl.setSpacing(10)
		A.scene, A.view = QGraphicsScene(), AudioTimelineView(A); A.view.setScene(A.scene); ll.addWidget(A.view, stretch=1); cb = QHBoxLayout()
		A.btn_play = QPushButton("Play (Space)"); A.btn_play.setFocusPolicy(Qt.FocusPolicy.NoFocus); A.btn_play.clicked.connect(A.toggle_play)
		A.btn_stop = QPushButton("Stop"); A.btn_stop.setFocusPolicy(Qt.FocusPolicy.NoFocus); A.btn_stop.clicked.connect(A.stop_play)
		A.btn_cut = QPushButton("Cut (Ctrl+B)"); A.btn_cut.setFocusPolicy(Qt.FocusPolicy.NoFocus); A.btn_cut.clicked.connect(A.cut_clip_at_playhead)
		A.btn_del = QPushButton("Delete"); A.btn_del.setFocusPolicy(Qt.FocusPolicy.NoFocus); A.btn_del.clicked.connect(A.delete_clip)
		A.lbl_time = QLabel("00:00.000")
		for w in [A.btn_play, A.btn_stop, A.btn_cut, A.btn_del, A.lbl_time]: cb.addWidget(w)
		cb.addStretch(); ll.addLayout(cb); rl.addWidget(QLabel("<b>CLIP CONTROLS</b>"), alignment=Qt.AlignmentFlag.AlignCenter); A.lbl_clip = QLabel("Selected: None"); rl.addWidget(A.lbl_clip)
		def add_spin(lbl, sb_cls, r, st, v, fn):
			h = QHBoxLayout(); h.addWidget(QLabel(lbl)); sb = sb_cls(); sb.setFocusPolicy(Qt.FocusPolicy.ClickFocus); sb.setRange(*r)
			if st: sb.setSingleStep(st)
			sb.setValue(v); sb.valueChanged.connect(fn); h.addWidget(sb); rl.addLayout(h); return sb
		A.spin_start = add_spin("Start Timeline:", QDoubleSpinBox, (0, 99999), 0.1, 0, A.on_prop_chg)
		A.spin_trim_in = add_spin("Trim In (Q):", QDoubleSpinBox, (0, 99999), 0.1, 0, A.on_prop_chg)
		A.spin_trim_out = add_spin("Trim Out (E):", QDoubleSpinBox, (0, 99999), 0.1, 0, A.on_prop_chg)
		A.spin_speed = add_spin("Speed (atempo):", QDoubleSpinBox, (0.25, 4.0), 0.1, 1.0, A.on_prop_chg)
		A.spin_pitch = add_spin("Pitch (semitones):", QDoubleSpinBox, (-12.0, 12.0), 1.0, 0.0, A.on_prop_chg)
		A.spin_vol = add_spin("Volume:", QDoubleSpinBox, (0.0, 5.0), 0.1, 1.0, A.on_prop_chg)
		A.spin_track = add_spin("Track:", QSpinBox, (0, 10), None, 0, A.on_prop_chg)
		line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("background-color: #444;"); rl.addWidget(line)
		rl.addWidget(QLabel("<b>EXPORT MIX</b>"), alignment=Qt.AlignmentFlag.AlignCenter); h_fmt = QHBoxLayout(); h_fmt.addWidget(QLabel("Format:"))
		A.combo_fmt = QComboBox(); A.combo_fmt.setFocusPolicy(Qt.FocusPolicy.NoFocus); A.combo_fmt.addItems(["mp3", "wav", "flac", "aac", "m4a"]); h_fmt.addWidget(A.combo_fmt); rl.addLayout(h_fmt)
		A.btn_exp = QPushButton("Export Render (FFmpeg)"); A.btn_exp.setFocusPolicy(Qt.FocusPolicy.NoFocus); A.btn_exp.setStyleSheet("background-color: #2e7d32; padding: 8px; font-weight: bold;"); A.btn_exp.clicked.connect(A.export_render)
		rl.addWidget(A.btn_exp); A.prog = QProgressBar(); A.prog.setValue(0); rl.addWidget(A.prog); rl.addStretch()
		s.addWidget(lw); s.addWidget(rw); s.setSizes([850, 350]); A.setCentralWidget(s); A.redraw_scene()
	def keyPressEvent(A, e):
		k, m = e.key(), e.modifiers()
		if k == Qt.Key.Key_Space: A.toggle_play()
		elif k in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace): A.delete_clip()
		elif k in (Qt.Key.Key_Left, Qt.Key.Key_Comma): A.set_playhead(max(0.0, A.current_time - 5.0))
		elif k in (Qt.Key.Key_Right, Qt.Key.Key_Period): A.set_playhead(A.current_time + 5.0)
		elif k == Qt.Key.Key_B and m & Qt.KeyboardModifier.ControlModifier: A.cut_clip_at_playhead()
		elif k == Qt.Key.Key_Q and A.selected_clip:
			c = A.selected_clip; rt = A.current_time - c.start_time
			if 0 < rt < (c.clip_end - c.clip_start) / max(0.1, c.speed): c.clip_start += rt * c.speed; c.start_time = A.current_time; A.sync_clip_controls(); A.redraw_scene()
		elif k == Qt.Key.Key_E and A.selected_clip:
			c = A.selected_clip; rt = A.current_time - c.start_time
			if 0 < rt < (c.clip_end - c.clip_start) / max(0.1, c.speed): c.clip_end = c.clip_start + rt * c.speed; A.sync_clip_controls(); A.redraw_scene()
	def add_audio_file(A, p):
		d = get_dur(p); c = AudioClip(file_path=p, name=os.path.basename(p), start_time=A.current_time, duration=d, clip_start=0.0, clip_end=d, track=len(A.clips) % 4)
		A.clips.append(c); A.select_clip(c); A.redraw_scene()
	def select_clip(A, c): A.selected_clip = c; A.sync_clip_controls()
	def sync_clip_controls(A):
		c = A.selected_clip
		if not c: A.lbl_clip.setText("Selected: None"); return
		A.lbl_clip.setText(f"Selected: {c.name}")
		for sb in [A.spin_start, A.spin_trim_in, A.spin_trim_out, A.spin_speed, A.spin_pitch, A.spin_vol, A.spin_track]: sb.blockSignals(True)
		A.spin_start.setValue(c.start_time); A.spin_trim_in.setValue(c.clip_start); A.spin_trim_out.setValue(c.clip_end); A.spin_speed.setValue(c.speed); A.spin_pitch.setValue(c.pitch); A.spin_vol.setValue(c.volume); A.spin_track.setValue(c.track)
		for sb in [A.spin_start, A.spin_trim_in, A.spin_trim_out, A.spin_speed, A.spin_pitch, A.spin_vol, A.spin_track]: sb.blockSignals(False)
	def on_prop_chg(A):
		c = A.selected_clip
		if not c: return
		c.start_time, c.clip_start = A.spin_start.value(), A.spin_trim_in.value(); c.clip_end, c.speed = max(c.clip_start + 0.1, A.spin_trim_out.value()), A.spin_speed.value(); c.pitch, c.volume, c.track = A.spin_pitch.value(), A.spin_vol.value(), A.spin_track.value(); A.dirty_preview = True; A.redraw_scene()
	def toggle_play(A):
		if A.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: A.player.pause(); A.btn_play.setText("Play (Space)")
		elif not getattr(A, "dirty_preview", True) and A.player.playbackState() == QMediaPlayer.PlaybackState.PausedState and A.player.hasAudio(): A.player.play(); A.btn_play.setText("Pause (Space)")
		else:
			if A.generate_preview(): A.dirty_preview = False; A.player.setSource(QUrl.fromLocalFile(A.temp_file)); A.player.setPosition(int(A.current_time * 1000)); A.player.play(); A.btn_play.setText("Pause (Space)")
	def cut_clip_at_playhead(A):
		c = A.selected_clip
		if not c: return
		d, rt = (c.clip_end - c.clip_start) / max(0.1, c.speed), A.current_time - c.start_time
		if 0 < rt < d:
			st = c.clip_start + (rt * c.speed); nc = AudioClip(file_path=c.file_path, name=c.name, start_time=A.current_time, duration=c.duration, clip_start=st, clip_end=c.clip_end, speed=c.speed, pitch=c.pitch, volume=c.volume, track=c.track)
			c.clip_end = st; A.clips.append(nc); A.select_clip(nc); A.redraw_scene()
	def delete_clip(A):
		if A.selected_clip in A.clips: A.clips.remove(A.selected_clip); A.selected_clip = None; A.sync_clip_controls(); A.redraw_scene()
	def redraw_scene(A):
		A.scene.clear(); mt = 300.0
		for c in A.clips: mt = max(mt, c.start_time + ((c.clip_end - c.clip_start) / max(0.1, c.speed)) + 60)
		tw = mt * A.zoom_factor; A.scene.setSceneRect(0, 0, tw, 600)
		for i in range(0, int(mt), 1):
			x = i * A.zoom_factor
			if i % 5 == 0:
				A.scene.addLine(x, 0, x, 600, QPen(QColor(60, 60, 60), 1)); t = A.scene.addText(f"{i}s"); t.setPos(x + 2, 0); t.setDefaultTextColor(QColor(150, 150, 150))
			else: A.scene.addLine(x, 20, x, 30, QPen(QColor(40, 40, 40), 1))
		for tr in range(6): A.scene.addLine(0, 40 + tr * 60, tw, 40 + tr * 60, QPen(QColor(45, 45, 45), 1))
		for c in A.clips: A.scene.addItem(ClipGraphicsItem(c, A))
		px = A.current_time * A.zoom_factor; A.playhead_line = A.scene.addLine(px, 0, px, 600, QPen(QColor(255, 50, 50), 2, Qt.PenStyle.SolidLine))
	def set_playhead(A, t):
		A.current_time = t; ms, s, m = int(t * 1000), int(t % 60), int(t // 60); A.lbl_time.setText(f"{m:02d}:{s:02d}.{int(ms%1000):03d}")
		if A.playhead_line: px = t * A.zoom_factor; A.playhead_line.setLine(px, 0, px, 600)
		if abs(A.player.position() - int(t * 1000)) > 200: A.player.setPosition(int(t * 1000))
	def build_filter_chain(A, c):
		fl = []
		if c.pitch != 0.0:
			pr = 2.0 ** (c.pitch / 12.0); nsr = int(44100 * pr); fl.extend(["aresample=44100", f"asetrate={nsr}", "aresample=44100"]); s = c.speed / pr
		else: s = c.speed
		if abs(s - 1.0) > 0.001:
			while s > 2.0: fl.append("atempo=2.0"); s /= 2.0
			while s < 0.5: fl.append("atempo=0.5"); s /= 0.5
			fl.append(f"atempo={s:.3f}")
		if abs(c.volume - 1.0) > 0.001: fl.append(f"volume={c.volume:.2f}")
		d = int(c.start_time * 1000)
		if d > 0: fl.append(f"adelay={d}|{d}")
		return ",".join(fl) if fl else "anull"
	def generate_preview(A):
		if not A.clips: return False
		inp, fc = [], []
		for i, c in enumerate(A.clips): inp.extend(["-ss", str(c.clip_start), "-to", str(c.clip_end), "-i", c.file_path]); fc.append(f"[{i}:a]{A.build_filter_chain(c)}[a{i}]")
		mi = "".join([f"[a{i}]" for i in range(len(A.clips))]); fc.append(f"{mi}amix=inputs={len(A.clips)}:duration=longest:dropout_transition=0[out]")
		return subprocess.run(["ffmpeg", "-y"] + inp + ["-filter_complex", ";".join(fc), "-map", "[out]", "-c:a", "pcm_s16le", A.temp_file], stdout=-1, stderr=-1).returncode == 0
	def stop_play(A): A.player.stop(); A.btn_play.setText("Play (Space)"); A.set_playhead(0.0)
	def on_player_position(A, ms): A.set_playhead(ms / 1000.0)
	def export_render(A):
		if not A.clips: return QMessageBox.warning(A, "W", "No clips!")
		fmt = A.combo_fmt.currentText(); sp, _ = QFileDialog.getSaveFileName(A, "Save", f"mix_out.{fmt}", f"Audio (*.{fmt})")
		if not sp: return
		A.prog.setValue(10); inp, fc = [], []
		for i, c in enumerate(A.clips): inp.extend(["-ss", str(c.clip_start), "-to", str(c.clip_end), "-i", c.file_path]); fc.append(f"[{i}:a]{A.build_filter_chain(c)}[a{i}]")
		mi = "".join([f"[a{i}]" for i in range(len(A.clips))]); fc.append(f"{mi}amix=inputs={len(A.clips)}:duration=longest:dropout_transition=0[out]"); A.prog.setValue(40)
		try:
			r = subprocess.run(["ffmpeg", "-y"] + inp + ["-filter_complex", ";".join(fc), "-map", "[out]", sp], stdout=-1, stderr=-1, text=True); A.prog.setValue(100)
			QMessageBox.information(A, "OK", "Done!") if r.returncode == 0 else QMessageBox.critical(A, "Err", r.stderr)
		except Exception as e: QMessageBox.critical(A, "Err", str(e))
if __name__ == "__main__":
	app = QApplication(sys.argv); win = AudioMixerApp(); win.show(); sys.exit(app.exec())