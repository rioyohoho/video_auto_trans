import sys
import os
import subprocess
import re
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QListWidget, 
                             QListWidgetItem, QCheckBox, QLabel, QLineEdit, 
                             QSplitter, QSlider, QProgressDialog)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
class C:
    title = 'Resize Video'
    w = 1440
    h = int(w * 9 / 18)
    left_w = int(w * 1 / 5)
    mid_w = int(w * 3 / 5)
    mid_t = int(h * 2 / 3)
    mid_b = int(h * 1 / 3)
    right_w = int(w * 1 / 5)
class VideoItem:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.old_size = self.get_video_resolution()
        self.orig_w = 1920
        self.orig_h = 1080
        self.parse_initial_size()
        self.target_w = str(self.orig_w)
        self.target_h = str(self.orig_h)
        self.target_fps = "30"
        self.ratio = "1.0"
    def get_video_resolution(self):
        try:
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', self.filepath]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            res = result.stdout.strip()
            return res if res else "Unknown"
        except:
            return "Unknown"
    def parse_initial_size(self):
        if self.old_size and "x" in self.old_size:
            try:
                parts = self.old_size.split('x')
                self.orig_w = int(parts[0])
                self.orig_h = int(parts[1])
            except:
                pass
class ExportWorker(QThread):
    progress = pyqtSignal(str, int, str)
    finished = pyqtSignal()
    def __init__(self, items, output_dir):
        super().__init__()
        self.items = items
        self.output_dir = output_dir
        self._is_cancelled = False
        self.process = None
    def run(self):
        total_videos = len(self.items)
        for idx, item in enumerate(self.items, 1):
            if self._is_cancelled:
                break
            out_path = os.path.join(self.output_dir, f"resized_{item.filename}")
            status_text = f"({idx}/{total_videos})"
            self.progress.emit(item.filename, 0, status_text)
            duration = self.get_duration(item.filepath)
            cmd = ['ffmpeg', '-y', '-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda', 
                '-i', item.filepath, 
                '-vf', f'scale_cuda={item.target_w}:{item.target_h},fps={item.target_fps}', 
                '-c:v', 'h264_nvenc', '-rc', 'constqp', '-cq', '28', '-c:a', 'copy', out_path]
            self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, bufsize=1, encoding='utf-8')
            time_pattern = re.compile(r"time=(\d+):(\d+):(\d+.\d+)")
            while self.process.poll() is None:
                if self._is_cancelled:
                    self.process.terminate()
                    break
                line = self.process.stderr.readline()
                if not line:
                    continue
                match = time_pattern.search(line)
                if match and duration > 0:
                    hours, minutes, seconds = match.groups()
                    current_time = int(hours)*3600 + int(minutes)*60 + float(seconds)
                    percentage = min(100, int((current_time / duration) * 100))
                    self.progress.emit(item.filename, percentage, status_text)
            if self.process:
                self.process.wait()
        self.finished.emit()
    def get_duration(self, filepath):
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(result.stdout.strip())
        except:
            return 0.0
    def cancel(self):
        self._is_cancelled = True
        if self.process:
            self.process.terminate()
class HoverSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self.hover_pos = -1
    def mouseMoveEvent(self, event):
        self.hover_pos = event.position().x()
        self.update()
        super().mouseMoveEvent(event)
    def leaveEvent(self, event):
        self.hover_pos = -1
        self.update()
        super().leaveEvent(event)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            self.setValue(int(val))
            self.sliderMoved.emit(int(val))
        super().mousePressEvent(event)
    def paintEvent(self, event):
        super().paintEvent(event)
        if hasattr(self, 'hover_pos') and self.hover_pos >= 0:
            from PyQt6.QtGui import QPainter, QPen
            painter = QPainter(self)
            pen = QPen(Qt.GlobalColor.yellow, 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(self.hover_pos), 0, int(self.hover_pos), self.height())
            painter.end()
class LeftWidget(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.main_win = main_win
        self.setAcceptDrops(True)
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("Load Videos")
        self.btn_load.clicked.connect(self.load_videos_dialog)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.main_win.clear_selected_videos)
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)
        self.lbl_count = QLabel("Total: 0")
        self.chk_all = QCheckBox("Select All")
        self.chk_all.setChecked(True)
        self.chk_all.stateChanged.connect(self.toggle_all)
        top_bar = QHBoxLayout()
        top_bar.addWidget(self.lbl_count)
        top_bar.addWidget(self.chk_all)
        layout.addLayout(top_bar)
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.item_clicked)
        layout.addWidget(self.list_widget)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.main_win.add_videos(files)
    def load_videos_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Videos", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if files:
            self.main_win.add_videos(files)
    def toggle_all(self, state):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk:
                    chk.setChecked(state == Qt.CheckState.Checked.value)
    def item_clicked(self, item):
        v_item = item.data(Qt.ItemDataRole.UserRole)
        if v_item:
            self.main_win.play_video(v_item.filepath)
class ElidedLabel(QLabel):
    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QFontMetrics
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided_text = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided_text)
        painter.end()
class RightWidget(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self.main_win = main_win
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.lbl_count = QLabel("Selected: 0")
        layout.addWidget(self.lbl_count)
        self.list_widget = QListWidget()
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.list_widget)
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.export_videos)
        layout.addWidget(self.btn_export)
    def update_list(self, selected_items):
        self.list_widget.clear()
        self.lbl_count.setText(f"Selected: {len(selected_items)}")
        for v_item in selected_items:
            item = QListWidgetItem(self.list_widget)
            widget = QWidget()
            w_layout = QVBoxLayout(widget)
            w_layout.setContentsMargins(2, 2, 2, 2)
            w_layout.setSpacing(2)
            lbl_title = ElidedLabel(f"{v_item.filename} ({v_item.old_size})")
            w_layout.addWidget(lbl_title)
            inputs_layout = QHBoxLayout()
            inputs_layout.addWidget(QLabel("w"))
            txt_w = QLineEdit(v_item.target_w)
            txt_w.setFixedWidth(40)
            inputs_layout.addWidget(txt_w)
            inputs_layout.addWidget(QLabel("h"))
            txt_h = QLineEdit(v_item.target_h)
            txt_h.setFixedWidth(40)
            inputs_layout.addWidget(txt_h)
            inputs_layout.addWidget(QLabel("fps"))
            txt_fps = QLineEdit(v_item.target_fps)
            txt_fps.setFixedWidth(30)
            inputs_layout.addWidget(txt_fps)
            inputs_layout.addWidget(QLabel("scale"))
            txt_ratio = QLineEdit(v_item.ratio)
            txt_ratio.setFixedWidth(40)
            inputs_layout.addWidget(txt_ratio)
            inputs_layout.addStretch()
            w_layout.addLayout(inputs_layout)
            def make_change_w(vi, tw, th, tr):
                return lambda text: self._handle_w_changed(text, vi, tw, th, tr)
            def make_change_h(vi, tw, th, tr):
                return lambda text: self._handle_h_changed(text, vi, tw, th, tr)
            def make_change_ratio(vi, tw, th, tr):
                return lambda text: self._handle_ratio_changed(text, vi, tw, th, tr)
            def make_change_fps(vi):
                return lambda text: setattr(vi, 'target_fps', text)
            txt_w.textEdited.connect(make_change_w(v_item, txt_w, txt_h, txt_ratio))
            txt_h.textEdited.connect(make_change_h(v_item, txt_w, txt_h, txt_ratio))
            txt_ratio.textEdited.connect(make_change_ratio(v_item, txt_w, txt_h, txt_ratio))
            txt_fps.textEdited.connect(make_change_fps(v_item))
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
    def _handle_w_changed(self, text, vi, tw, th, tr):
        vi.target_w = text
        if text.isdigit() and int(text) > 0:
            try:
                new_h = str(int(int(text) * vi.orig_h / vi.orig_w))
                vi.target_h = new_h
                th.setText(new_h)
                new_scale = f"{int(text)/vi.orig_w:.2f}"
                vi.ratio = new_scale
                tr.setText(new_scale)
            except: pass
    def _handle_h_changed(self, text, vi, tw, th, tr):
        vi.target_h = text
        if text.isdigit() and int(text) > 0:
            try:
                new_w = str(int(int(text) * vi.orig_w / vi.orig_h))
                vi.target_w = new_w
                tw.setText(new_w)
                new_scale = f"{int(text)/vi.orig_h:.2f}"
                vi.ratio = new_scale
                tr.setText(new_scale)
            except: pass
    def _handle_ratio_changed(self, text, vi, tw, th, tr):
        vi.ratio = text
        try:
            val = float(text)
            if val > 0:
                new_w = str(int(vi.orig_w * val))
                new_h = str(int(vi.orig_h * val))
                vi.target_w = new_w
                vi.target_h = new_h
                tw.setText(new_w)
                th.setText(new_h)
        except: pass
    def export_videos(self):
        selected_items = self.main_win.get_selected_items()
        if not selected_items:
            return
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if output_dir:
            self.btn_export.setEnabled(False)
            self.progress_dialog = QProgressDialog("Initializing export...", "Cancel", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setWindowTitle("Exporting Videos")
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setAutoClose(True)
            self.worker = ExportWorker(selected_items, output_dir)
            self.worker.progress.connect(self.update_progress_ui)
            self.worker.finished.connect(self.export_finished)
            self.progress_dialog.canceled.connect(self.worker.cancel)
            self.worker.start()
    def update_progress_ui(self, filename, percentage, status_text):
        if hasattr(self, 'progress_dialog') and self.progress_dialog.isVisible():
            self.progress_dialog.setLabelText(f"Exporting: {filename} {status_text}\nProgress: {percentage}%")
            self.progress_dialog.setValue(percentage)
    def export_finished(self):
        self.btn_export.setEnabled(True)
        self.btn_export.setText("Export")
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_list = []
        self.setWindowTitle(C.title)
        self.resize(C.w, C.h)
        self.init_ui()
    def init_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(main_splitter)
        self.left_panel = LeftWidget(self)
        main_splitter.addWidget(self.left_panel)
        mid_splitter = QSplitter(Qt.Orientation.Vertical, main_splitter)
        main_splitter.addWidget(mid_splitter)
        self.video_widget = QVideoWidget(mid_splitter)
        mid_splitter.addWidget(self.video_widget)
        self.timeline_panel = QWidget(mid_splitter)
        timeline_layout = QVBoxLayout(self.timeline_panel)
        timeline_layout.setContentsMargins(5, 5, 5, 5)
        self.slider = HoverSlider(Qt.Orientation.Horizontal, self.timeline_panel)
        self.slider.sliderMoved.connect(self.set_position)
        timeline_layout.addWidget(self.slider)
        ctrl_layout = QHBoxLayout()
        self.btn_pre = QPushButton("pre-video")
        self.btn_back = QPushButton("back-10s")
        self.btn_play = QPushButton("pause/play")
        self.btn_next10 = QPushButton("next-10s")
        self.btn_next = QPushButton("next-video")
        self.btn_pre.clicked.connect(self.play_prev_video)
        self.btn_back.clicked.connect(self.back_10s)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_next10.clicked.connect(self.next_10s)
        self.btn_next.clicked.connect(self.play_next_video)
        ctrl_layout.addWidget(self.btn_pre)
        ctrl_layout.addWidget(self.btn_back)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_next10)
        ctrl_layout.addWidget(self.btn_next)
        timeline_layout.addLayout(ctrl_layout)
        mid_splitter.addWidget(self.timeline_panel)
        self.right_panel = RightWidget(self)
        main_splitter.addWidget(self.right_panel)
        main_splitter.setSizes([C.left_w, C.mid_w, C.right_w])
        mid_splitter.setSizes([C.mid_t, C.mid_b])
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self.play_prev_video()
        elif event.key() == Qt.Key.Key_Down:
            self.play_next_video()
        elif event.key() == Qt.Key.Key_Left:
            self.back_10s()
        elif event.key() == Qt.Key.Key_Right:
            self.next_10s()
        elif event.key() == Qt.Key.Key_Space:
            self.toggle_play()
        else:
            super().keyPressEvent(event)
    def add_videos(self, filepaths):
        for path in filepaths:
            if any(v.filepath == path for v in self.video_list):
                continue
            v_item = VideoItem(path)
            self.video_list.append(v_item)
            item = QListWidgetItem(self.left_panel.list_widget)
            widget = QWidget()
            w_layout = QHBoxLayout(widget)
            w_layout.setContentsMargins(5, 2, 5, 2)
            chk = QCheckBox()
            chk.setChecked(True)
            chk.stateChanged.connect(self.update_right_panel)
            lbl = QLabel(f"{v_item.filename} ({v_item.old_size})")
            w_layout.addWidget(chk)
            w_layout.addWidget(lbl)
            w_layout.addStretch()
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, v_item)
            self.left_panel.list_widget.addItem(item)
            self.left_panel.list_widget.setItemWidget(item, widget)
        self.left_panel.lbl_count.setText(f"Total: {len(self.video_list)}")
        self.update_right_panel()
    def clear_selected_videos(self):
        rows_to_remove = []
        selected_items_to_remove = []
        for i in range(self.left_panel.list_widget.count()):
            item = self.left_panel.list_widget.item(i)
            widget = self.left_panel.list_widget.itemWidget(item)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    rows_to_remove.append(i)
                    selected_items_to_remove.append(item.data(Qt.ItemDataRole.UserRole))
        if not rows_to_remove:
            return
        current_source = self.player.source().toLocalFile()
        if any(v.filepath == current_source for v in selected_items_to_remove):
            self.player.stop()
            self.player.setSource(QUrl())
        for row in reversed(rows_to_remove):
            self.left_panel.list_widget.takeItem(row)
        for v in selected_items_to_remove:
            if v in self.video_list:
                self.video_list.remove(v)
        self.left_panel.lbl_count.setText(f"Total: {len(self.video_list)}")
        self.update_right_panel()
    def get_selected_items(self):
        selected = []
        for i in range(self.left_panel.list_widget.count()):
            item = self.left_panel.list_widget.item(i)
            widget = self.left_panel.list_widget.itemWidget(item)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected
    def update_right_panel(self):
        self.right_panel.update_list(self.get_selected_items())
    def play_video(self, filepath):
        self.player.setSource(QUrl.fromLocalFile(filepath))
        self.player.play()
    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    def back_10s(self):
        self.player.setPosition(max(0, self.player.position() - 10000))
    def next_10s(self):
        self.player.setPosition(min(self.player.duration(), self.player.position() + 10000))
    def play_prev_video(self):
        curr_row = self.left_panel.list_widget.currentRow()
        if curr_row > 0:
            self.left_panel.list_widget.setCurrentRow(curr_row - 1)
            item = self.left_panel.list_widget.currentItem()
            if item: self.play_video(item.data(Qt.ItemDataRole.UserRole).filepath)
    def play_next_video(self):
        curr_row = self.left_panel.list_widget.currentRow()
        if curr_row < self.left_panel.list_widget.count() - 1:
            self.left_panel.list_widget.setCurrentRow(curr_row + 1)
            item = self.left_panel.list_widget.currentItem()
            if item: self.play_video(item.data(Qt.ItemDataRole.UserRole).filepath)
    def position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
    def duration_changed(self, duration):
        if duration > 0:
            self.slider.setRange(0, duration)
    def set_position(self, position):
        self.player.setPosition(position)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())