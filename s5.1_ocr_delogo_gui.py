import sys,os,copy,cv2,argparse,numpy as np
from pathlib import Path
from PyQt6.QtCore import Qt,QTimer,QThread,pyqtSignal,QPointF,QRectF,QPoint
from PyQt6.QtGui import QPainter,QColor,QPen,QBrush,QImage,QPixmap,QWheelEvent,QMouseEvent,QKeyEvent,QKeySequence,QShortcut,QCursor
from PyQt6.QtWidgets import QApplication,QMainWindow,QWidget,QSplitter,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDoubleSpinBox,QSpinBox,QComboBox,QCheckBox,QProgressBar,QListWidget,QListWidgetItem,QFileDialog,QMessageBox,QScrollArea,QFrame,QSizePolicy
from video_auto_trans.src.enties import Canvas,Polygon,Delogo,Delogo_KeyFrames,Transcribe
from video_auto_trans.src.modules.delogo import get_roi_bounds,box_to_polygon,polygon_to_box,find_text_box_ocr,load_subtitles,estimate_box
from video_auto_trans.src.utils.file import r_json,w_json
from video_auto_trans.src.utils.text import str2bool
from video_auto_trans.src.utils.video import get_media_duration
from video_auto_trans.src.configuration import READER
def get_box_at(clip:Delogo_KeyFrames,t:float)->tuple[int,int,int,int]:
	if not clip.keyframes:return 0,0,clip.width,clip.height
	kfs=sorted(clip.keyframes,key=lambda k:k.t)
	if t<=kfs[0].t:cx,cy=kfs[0].x,kfs[0].y
	elif t>=kfs[-1].t:cx,cy=kfs[-1].x,kfs[-1].y
	else:
		cx,cy=kfs[0].x,kfs[0].y
		for i in range(len(kfs)-1):
			k1,k2=kfs[i],kfs[i+1]
			if k1.t<=t<=k2.t:
				a=(t-k1.t)/max(1e-3,k2.t-k1.t);cx,cy=int(k1.x+(k2.x-k1.x)*a),int(k1.y+(k2.y-k1.y)*a);break
	bx = cx - clip.width // 2
	by = cy - clip.height // 2
	return bx,by,clip.width,clip.height
class OCRWorker(QThread):
	progress=pyqtSignal(float,float,object,object);finished=pyqtSignal()
	def __init__(self,src_path,sub_path,area_roi,is_area_max,is_time_max):super().__init__();self.src,self.sub,self.roi,self.iam,self.itm=src_path,sub_path,area_roi,is_area_max,is_time_max;self._run=True;self._pause=False
	def pause(self):self._pause=True
	def resume(self):self._pause=False
	def stop(self):self._run=False;self._pause=False
	def detect_in_roi(self,fr,ref_text=''):
		rx,ry,rw,rh=self.roi;crop=fr[ry:ry+rh,rx:rx+rw]
		try:
			res=READER.readtext(crop)
			if not res:return
			clean_ref=ref_text.replace(' ','').strip();valid_boxes=[]
			for(bbox,text,prob)in res:
				clean_t=text.replace(' ','').strip()
				if not clean_t:continue
				if clean_ref:
					common=set(clean_t)&set(clean_ref)
					if not common and clean_t not in clean_ref and clean_ref not in clean_t:continue
				valid_boxes.append((bbox,clean_t))
			if not valid_boxes:res_sorted=sorted(res,key=lambda r:max(p[1]for p in r[0]),reverse=True);valid_boxes=[(res_sorted[0][0],res_sorted[0][1].replace(' ','').strip())]
			pts=[p for b in valid_boxes for p in b[0]];x1,x2=int(min(p[0]for p in pts)),int(max(p[0]for p in pts));y1,y2=int(min(p[1]for p in pts)),int(max(p[1]for p in pts));detected_text=''.join(b[1]for b in valid_boxes)
			if clean_ref and detected_text and detected_text in clean_ref and len(detected_text)<len(clean_ref):char_w=(x2-x1)/max(1,len(detected_text));idx=clean_ref.find(detected_text);x1-=int(idx*char_w);x2+=int((len(clean_ref)-idx-len(detected_text))*char_w)
			bw=int((x2-x1)*1.1);bh=min(85,max(60,int((y2-y1)*1.25)));cx=rx+rw//2;cy=ry+(y1+y2)//2;return cx,cy,max(40,bw),bh,len(detected_text)
		except Exception:return
	def run(self):
		cap=cv2.VideoCapture(str(self.src))
		if not cap.isOpened():self.finished.emit();return
		W,H=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));dur=get_media_duration(self.src)or cap.get(cv2.CAP_PROP_FRAME_COUNT)/max(cap.get(cv2.CAP_PROP_FPS),1.);subs=load_subtitles(Path(self.sub))if self.sub and Path(self.sub).exists()else[];rx,ry,rw,rh=self.roi;default_cx,default_cy=rx+rw//2,ry+rh//2
		if subs:
			if self.iam:
				max_s=max((s for s in subs if s.text),key=lambda s:len(s.text),default=subs[0]);best_det=None
				for ratio in[.5,.3,.7]:
					t_check=max_s.start+(max_s.end-max_s.start)*ratio;cap.set(cv2.CAP_PROP_POS_MSEC,t_check*1000);ret,fr=cap.read()
					if ret:
						r=self.detect_in_roi(fr,ref_text=max_s.text)
						if r and(best_det is None or r[4]>best_det[4]):
							best_det=r
							if r[4]>=len(max_s.text)*.8:break
				if best_det:cx,cy,bw,bh,_=best_det
				else:cx,cy,bw,bh=default_cx,default_cy,int(rw*.9),int(rh*.4)
				t_mid=(max_s.start+max_s.end)/2.;box=cx-bw//2,cy-bh//2,bw,bh
				if self.itm:c=Delogo_KeyFrames(boxblur=20,width=bw,height=bh,keyframes=[Delogo(t=round(subs[0].start,3),x=cx,y=cy),Delogo(t=round(subs[-1].end,3),x=cx,y=cy)]);self.progress.emit(1e2,t_mid,box,c)
				else:
					for(i,s)in enumerate(subs):
						while self._pause and self._run:self.msleep(100)
						if not self._run:break
						c=Delogo_KeyFrames(boxblur=20,width=bw,height=bh,keyframes=[Delogo(t=round(s.start,3),x=cx,y=cy),Delogo(t=round(s.end,3),x=cx,y=cy)]);self.progress.emit((i+1)/len(subs)*1e2,(s.start+s.end)/2.,box,c)
			else:
				last_box=default_cx,default_cy,int(rw*.9),int(rh*.4)
				for(i,s)in enumerate(subs):
					while self._pause and self._run:self.msleep(100)
					if not self._run:break
					t_mid=(s.start+s.end)/2.;cap.set(cv2.CAP_PROP_POS_MSEC,t_mid*1000);ret,fr=cap.read()
					if ret:
						r=self.detect_in_roi(fr,ref_text=s.text)
						if r:last_box=r[0],r[1],r[2],r[3]
					cx,cy,bw,bh=last_box;box=cx-bw//2,cy-bh//2,bw,bh;c=Delogo_KeyFrames(boxblur=20,width=bw,height=bh,keyframes=[Delogo(t=round(s.start,3),x=cx,y=cy),Delogo(t=round(s.end,3),x=cx,y=cy)]);self.progress.emit((i+1)/len(subs)*1e2,t_mid,box,c)
		else:
			checks=[dur*.15,dur*.5,dur*.85];dt=[]
			for(i,t)in enumerate(checks):
				while self._pause and self._run:self.msleep(100)
				if not self._run:break
				cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ret,fr=cap.read();box=None
				if ret:
					r=self.detect_in_roi(fr)
					if r:cx,cy,bw,bh,_=r;box=cx-bw//2,cy-bh//2,bw,bh;dt.append((cx,cy,bw,bh))
				self.progress.emit((i+1)/len(checks)*1e2,t,box,None)
			if dt and self._run:cx,cy,bw,bh=max(dt,key=lambda x:x[2]);c=Delogo_KeyFrames(boxblur=20,width=bw,height=bh,keyframes=[Delogo(t=.0,x=cx,y=cy),Delogo(t=round(dur,3),x=cx,y=cy)]);self.progress.emit(1e2,dur/2.,(cx-bw//2,cy-bh//2,bw,bh),c)
		cap.release();self.finished.emit()
class VideoView(QWidget):
	def __init__(self,main_win):super().__init__();self.mw=main_win;self.setAcceptDrops(True);self.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.scale,self.pan=1.,QPointF(0,0);self.drag_start,self.is_panning=QPoint(),False;self.active_handle,self.drag_box_start,self.drag_target=-1,None,None;self.setMouseTracking(True)
	def enterEvent(self,e):self.setFocus();super().enterEvent(e)
	def dragEnterEvent(self,e):
		if e.mimeData().hasUrls():e.acceptProposedAction()
	def dropEvent(self,e):
		for u in e.mimeData().urls():
			p=Path(u.toLocalFile())
			if p.suffix.lower()in('.mp4','.mkv','.avi','.mov'):self.mw.load_video(p);break
	def wheelEvent(self,e:QWheelEvent):fac=1.15 if e.angleDelta().y()>0 else 1/1.15;self.scale=max(.1,min(1e1,self.scale*fac));self.update()
	def mousePressEvent(self,e:QMouseEvent):
		self.setFocus()
		if e.button()==Qt.MouseButton.RightButton:self.is_panning,self.drag_start=True,e.pos()
		elif e.button()==Qt.MouseButton.LeftButton:
			pt=self.to_video_coords(e.pos());clip=self.mw.get_active_clip()
			if clip and clip.keyframes:
				x,y,w,h=get_box_at(clip,self.mw.cur_time);h_idx=self.get_handle_under_mouse(e.pos(),x,y,w,h)
				if h_idx!=-1:self.drag_target,self.active_handle='clip',h_idx;self.drag_box_start=pt.x(),pt.y(),x,y,w,h;return
			if self.mw.sub_path:
				rx,ry,rw,rh=self.mw.get_area_roi();h_area=self.get_handle_under_mouse(e.pos(),rx,ry,rw,rh)
				if h_area!=-1:self.drag_target,self.active_handle='area',h_area;self.drag_box_start=pt.x(),pt.y(),rx,ry,rw,rh
	def mouseMoveEvent(self,e:QMouseEvent):
		if self.is_panning:self.pan+=QPointF(e.pos().x()-self.drag_start.x(),e.pos().y()-self.drag_start.y());self.drag_start=e.pos();self.update()
		elif self.drag_box_start:
			pt=self.to_video_coords(e.pos());dx,dy=pt.x()-self.drag_box_start[0],pt.y()-self.drag_box_start[1];ox,oy,ow,oh=self.drag_box_start[2],self.drag_box_start[3],self.drag_box_start[4],self.drag_box_start[5];vw,vh=self.mw.vid_w,self.mw.vid_h
			if self.active_handle in(0,3,5):
				dx=min(dx,ow-5);nx,nw=ox+dx,ow-dx
				if nx<0:nw+=nx;nx=0
			elif self.active_handle in(2,4,7):
				nw=max(5,ow+dx)
				if ox+nw>vw:nw=vw-ox
				nx=ox
			else:nx,nw=ox,ow
			if self.active_handle in(0,1,2):
				dy=min(dy,oh-5);ny,nh=oy+dy,oh-dy
				if ny<0:nh+=ny;ny=0
			elif self.active_handle in(5,6,7):
				nh=max(5,oh+dy)
				if oy+nh>vh:nh=vh-oy
				ny=oy
			else:ny,nh=oy,oh
			if self.active_handle==8:
				nx,ny=ox+dx,oy+dy;nw,nh=ow,oh
				if nx<0:nw=max(5,nw+nx);nx=0
				if nx+nw>vw:nw=max(5,vw-nx)
				if ny<0:nh=max(5,nh+ny);ny=0
				if ny+nh>vh:nh=max(5,vh-ny)
			nw,nh=max(5,nw),max(5,nh)
			if self.drag_target=='clip':
				clip=self.mw.get_active_clip()
				if clip:
					clip.width,clip.height=int(nw),int(nh)
					self.mw.set_keyframe_at_cur_time(clip, int(nx + nw // 2), int(ny + nh // 2))
					self.mw.update_active_ui()
			elif self.drag_target=='area':self.mw.set_area_roi(int(nx),int(ny),int(nw),int(nh))
			self.update()
	def mouseReleaseEvent(self,e:QMouseEvent):
		if e.button()==Qt.MouseButton.RightButton:self.is_panning=False
		elif e.button()==Qt.MouseButton.LeftButton:
			if self.drag_box_start and self.drag_target=='clip':self.mw.save_history()
			self.drag_box_start,self.active_handle,self.drag_target=None,-1,None
	def to_video_coords(self,p):vw,vh=self.mw.vid_w or 1,self.mw.vid_h or 1;cw,ch=self.width(),self.height();ox=(cw-vw*self.scale)/2+self.pan.x();oy=(ch-vh*self.scale)/2+self.pan.y();return QPointF((p.x()-ox)/self.scale,(p.y()-oy)/self.scale)
	def from_video_coords(self,x,y):vw,vh=self.mw.vid_w or 1,self.mw.vid_h or 1;ox=(self.width()-vw*self.scale)/2+self.pan.x();oy=(self.height()-vh*self.scale)/2+self.pan.y();return QPointF(ox+x*self.scale,oy+y*self.scale)
	def get_handle_under_mouse(self,mpos,x,y,w,h):
		pts=[(x,y),(x+w/2,y),(x+w,y),(x,y+h/2),(x+w,y+h/2),(x,y+h),(x+w/2,y+h),(x+w,y+h)]
		for(i,(hx,hy))in enumerate(pts):
			sp=self.from_video_coords(hx,hy)
			if abs(sp.x()-mpos.x())+abs(sp.y()-mpos.y())<10:return i
		box_p1,box_p2=self.from_video_coords(x,y),self.from_video_coords(x+w,y+h)
		return 8 if QRectF(box_p1,box_p2).contains(QPointF(mpos.x(),mpos.y()))else -1
	def paintEvent(self,e):
		p=QPainter(self);p.fillRect(self.rect(),QColor(15,17,23))
		if self.mw.cur_frame is not None:
			vw,vh=self.mw.vid_w,self.mw.vid_h;ox=(self.width()-vw*self.scale)/2+self.pan.x();oy=(self.height()-vh*self.scale)/2+self.pan.y();p.drawImage(QRectF(ox,oy,vw*self.scale,vh*self.scale),self.mw.cur_frame)
			if self.mw.sub_path:
				rx,ry,rw,rh=self.mw.get_area_roi();p1,p2=self.from_video_coords(rx,ry),self.from_video_coords(rx+rw,ry+rh);p.setPen(QPen(QColor(255,0,0,220),2,Qt.PenStyle.DashLine));p.setBrush(Qt.BrushStyle.NoBrush);p.drawRect(QRectF(p1,p2));p.setBrush(QBrush(QColor(255,50,50)))
				for(hx,hy)in[(rx,ry),(rx+rw/2,ry),(rx+rw,ry),(rx,ry+rh/2),(rx+rw,ry+rh/2),(rx,ry+rh),(rx+rw/2,ry+rh),(rx+rw,ry+rh)]:hp=self.from_video_coords(hx,hy);p.drawRect(QRectF(hp.x()-3,hp.y()-3,6,6))
			act=self.mw.get_active_clip()
			for c in self.mw.clips:
				if not c.keyframes:continue
				st,en=self.mw.clip_st(c),self.mw.clip_en(c)
				if st<=self.mw.cur_time<=en:
					bx,by,bw,bh=get_box_at(c,self.mw.cur_time);sp1,sp2=self.from_video_coords(bx,by),self.from_video_coords(bx+bw,by+bh);rect=QRectF(sp1,sp2);is_act=c==act
					p.setPen(QPen(QColor(255,255,0)if is_act else QColor(0,255,255),2));p.setBrush(Qt.BrushStyle.NoBrush);p.drawRect(rect)
					if is_act:
						p.setBrush(QBrush(QColor(255,255,255)))
						for(hx,hy)in[(bx,by),(bx+bw/2,by),(bx+bw,by),(bx,by+bh/2),(bx+bw,by+bh/2),(bx,by+bh),(bx+bw/2,by+bh),(bx+bw,by+bh)]:hp=self.from_video_coords(hx,hy);p.drawRect(QRectF(hp.x()-4,hp.y()-4,8,8))
			if self.mw.ocr_box:ox,oy,ow,oh=self.mw.ocr_box;p1,p2=self.from_video_coords(ox,oy),self.from_video_coords(ox+ow,oy+oh);p.setPen(QPen(QColor(0,255,0),2));p.setBrush(Qt.BrushStyle.NoBrush);p.drawRect(QRectF(p1,p2))
class TimelineWidget(QWidget):
	def __init__(self,main_win):super().__init__();self.mw=main_win;self.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.hover_x,self.drag_mode=-1,None;self.drag_start_pos,self.rubber_rect=None,None;self.zoom,self.scroll_t=1.,.0;self.pan_start_x,self.pan_start_t=0,.0;self.drag_layer_start=0;self.init_layers={};self.init_keyframes={};self.setMouseTracking(True)
	def enterEvent(self,e):self.setFocus();super().enterEvent(e)
	def vis_dur(self):return max(.01,self.mw.total_dur/self.zoom)
	def t_to_x(self,t):return int((t-self.scroll_t)/self.vis_dur()*self.width())
	def x_to_t(self,x):return max(.0,min(self.mw.total_dur,self.scroll_t+x/max(self.width(),1)*self.vis_dur()))
	def get_clip_y(self,layer):return 30+((layer+5)%5)*28
	def wheelEvent(self,e:QWheelEvent):cur_t=self.x_to_t(e.position().x());fac=1.25 if e.angleDelta().y()>0 else 1/1.25;nz=max(1.,min(1e2,self.zoom*fac));nvd=self.mw.total_dur/nz;self.scroll_t=max(.0,min(max(.0,self.mw.total_dur-nvd),cur_t-(e.position().x()/max(self.width(),1))*nvd));self.zoom=nz;self.update()
	def mousePressEvent(self,e:QMouseEvent):
		self.setFocus()
		if e.button()in(Qt.MouseButton.RightButton,Qt.MouseButton.MiddleButton):self.drag_mode='pan_timeline';self.pan_start_x=e.pos().x();self.pan_start_t=self.scroll_t;return
		if e.button()==Qt.MouseButton.LeftButton:
			x,y=e.pos().x(),e.pos().y()
			if y<26:self.drag_mode='seek';self.mw.seek_time(self.x_to_t(x),instant=True);return
			clicked_clip,h_mode=None,None
			for c in reversed(self.mw.clips):
				rx1,rx2=self.t_to_x(self.mw.clip_st(c)),self.t_to_x(self.mw.clip_en(c));ry=self.get_clip_y(getattr(c,'layer',0))
				if QRectF(rx1,ry,max(6,rx2-rx1),22).contains(QPointF(x,y)):
					clicked_clip=c
					if abs(x-rx1)<=7:h_mode='left'
					elif abs(x-rx2)<=7:h_mode='right'
					else:h_mode='move'
					break
			if clicked_clip:
				cid=id(clicked_clip)
				if e.modifiers()&Qt.KeyboardModifier.ControlModifier:
					if cid in self.mw.selected_ids:self.mw.selected_ids.remove(cid)
					else:self.mw.selected_ids.add(cid)
				elif e.modifiers()&Qt.KeyboardModifier.AltModifier:self.mw.selected_ids.discard(cid)
				elif cid not in self.mw.selected_ids:self.mw.selected_ids={cid}
				self.drag_mode=h_mode;self.target_clip=clicked_clip;self.drag_t_start=self.x_to_t(x);self.drag_layer_start=max(0,min(4,(y-30)//28));self.init_times={id(c):(c,self.mw.clip_st(c),self.mw.clip_en(c))for c in self.mw.clips if id(c)in self.mw.selected_ids};self.init_layers={id(c):getattr(c,'layer',0)for c in self.mw.clips if id(c)in self.mw.selected_ids};self.init_keyframes={id(c):[copy.deepcopy(k)for k in c.keyframes]for c in self.mw.clips if id(c)in self.mw.selected_ids};self.mw.active_clip=clicked_clip;self.mw.sync_list_selection();self.mw.update_active_ui()
			else:
				if not e.modifiers()&(Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier):self.mw.selected_ids.clear()
				self.drag_mode,self.drag_start_pos='rubber',e.pos()
			self.update()
	def mouseReleaseEvent(self,e:QMouseEvent):
		if self.drag_mode in('move','left','right'):self.mw.save_history()
		self.drag_mode,self.rubber_rect=None,None;self.setCursor(Qt.CursorShape.ArrowCursor);self.update()
	def paintEvent(self,e):
		p=QPainter(self);p.fillRect(self.rect(),QColor(18,20,28));p.fillRect(0,0,self.width(),26,QColor(28,32,44));p.setPen(QColor(113,113,122));p.drawText(6,18,f"Timeline (Dur: {self.mw.total_dur:.2f}s | Zoom: {self.zoom:.1f}x)")
		for l in range(5):
			ly=self.get_clip_y(l);p.fillRect(0,ly,self.width(),24,QColor(23,26,36)if l%2==0 else QColor(19,22,30));p.setPen(QPen(QColor(40,44,60),1,Qt.PenStyle.DashLine));p.drawLine(0,ly+24,self.width(),ly+24);p.setPen(QColor(80,85,100));p.drawText(6,ly+16,f"L{l}")
		for c in self.mw.clips:
			st,en=self.mw.clip_st(c),self.mw.clip_en(c);x1,x2=self.t_to_x(st),self.t_to_x(en);w=max(8,x2-x1);y=self.get_clip_y(getattr(c,'layer',0));is_sel=id(c)in self.mw.selected_ids;is_act=c==self.mw.active_clip;base_c=QColor(255,215,0)if is_act else QColor(0,229,255)if is_sel else QColor(0,140,170);p.setPen(QPen(QColor(255,255,255)if is_sel or is_act else QColor(30,30,30),1));p.setBrush(QBrush(base_c));p.drawRoundedRect(QRectF(x1,y,w,22),3,3);cap_c=QColor(255,255,255)if is_sel or is_act else QColor(200,240,255);p.fillRect(QRectF(x1,y+2,4,18),QBrush(cap_c));p.fillRect(QRectF(x1+w-4,y+2,4,18),QBrush(cap_c));p.setPen(QColor(0,0,0));p.drawText(int(x1+8),int(y+15),f"{st:.1f}-{en:.1f}")
			p.setBrush(QBrush(QColor(255,50,50)))
			for kf in c.keyframes:kx=self.t_to_x(kf.t);p.drawPolygon([QPoint(kx,y+2),QPoint(kx+4,y+11),QPoint(kx,y+20),QPoint(kx-4,y+11)])
		if 0<=self.hover_x<=self.width():p.setPen(QPen(QColor(255,255,0),1,Qt.PenStyle.DotLine));p.drawLine(self.hover_x,0,self.hover_x,self.height())
		px=self.t_to_x(self.mw.cur_time);p.setPen(QPen(QColor(255,0,0),2));p.drawLine(px,0,px,self.height())
		if self.rubber_rect:p.setPen(QPen(QColor(0,229,255),1,Qt.PenStyle.DashLine));p.fillRect(self.rubber_rect,QColor(0,229,255,45));p.drawRect(self.rubber_rect)
class MainWindow(QMainWindow):
	def __init__(self,init_video=None,init_area=0,init_iam=True,init_itm=False,*args,**kwargs):
		super().__init__();self.setWindowTitle('OCR Delogo Studio');self.resize(C.w,C.h+C.th+200);self.clips,self.selected_ids,self.active_clip=[],set(),None;self.history,self.redo_stack,self.clipboard=[],[],[];self.src_path,self.sub_path=None,None;self.cap,self.cur_frame,self.cur_time,self.total_dur=None,None,.0,.0;self.vid_w,self.vid_h,self.fps=1,1,30.;self.preview_w,self.preview_h=1,1;self.ocr_box,self.target_seek_time=None,.0;self.worker=None;self.seek_timer=QTimer(self);self.seek_timer.setSingleShot(True);self.seek_timer.timeout.connect(self._do_seek);self.play_timer=QTimer(self);self.play_timer.timeout.connect(self.advance_playback);self.setup_ui();self.setup_shortcuts();self.chk_iam.setChecked(init_iam);self.chk_itm.setChecked(init_itm);self.on_iam_toggled(init_iam);idx=self.area_cb.findData(init_area)
		if idx>=0:self.area_cb.setCurrentIndex(idx)
		if init_video and Path(init_video).exists():self.load_video(Path(init_video))
	def setup_ui(self):
		main_widget=QWidget(self);self.setCentralWidget(main_widget);main_layout=QHBoxLayout(main_widget);main_layout.setContentsMargins(0,0,0,0);main_layout.setSpacing(0);h_split=QSplitter(Qt.Orientation.Horizontal);h_split.setChildrenCollapsible(False);main_layout.addWidget(h_split);v_split=QSplitter(Qt.Orientation.Vertical);v_split.setChildrenCollapsible(False);h_split.addWidget(v_split);self.view=VideoView(self);self.view.setMinimumSize(100,60);v_split.addWidget(self.view);t_container=QWidget();t_layout=QVBoxLayout(t_container);t_layout.setContentsMargins(2,2,2,2);t_layout.setSpacing(2);ctrl_bar=QHBoxLayout();self.btn_magnet=QPushButton('🧲');self.btn_magnet.setCheckable(True);self.btn_magnet.setChecked(True);self.btn_magnet.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.btn_magnet.toggled.connect(self.update_magnet_style);ctrl_bar.addWidget(self.btn_magnet);self.update_magnet_style(True);ctrl_bar.addWidget(QLabel('Speed:'));self.speed_box=QDoubleSpinBox();self.speed_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.speed_box.setRange(.1,1e1);self.speed_box.setValue(1.);self.speed_box.setSingleStep(.5);self.speed_box.setMinimumWidth(45);ctrl_bar.addWidget(self.speed_box);self.step_box=QDoubleSpinBox();self.step_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.step_box.setRange(.01,6e1);self.step_box.setValue(.5);self.step_box.setMinimumWidth(45);ctrl_bar.addWidget(QLabel('Step:'));ctrl_bar.addWidget(self.step_box);self.play_btn=QPushButton('Play');self.play_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.play_btn.clicked.connect(self.toggle_play);ctrl_bar.addWidget(self.play_btn);self.b_left=QPushButton('←');self.b_left.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.b_left.setFixedWidth(24);self.b_left.clicked.connect(lambda:self.seek_relative(-self.step_box.value()));self.b_right=QPushButton('→');self.b_right.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.b_right.setFixedWidth(24);self.b_right.clicked.connect(lambda:self.seek_relative(self.step_box.value()));self.b_up=QPushButton('↑');self.b_up.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.b_up.setFixedWidth(24);self.b_up.clicked.connect(lambda:self.seek_relative(self.step_box.value()*10));self.b_down=QPushButton('↓');self.b_down.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.b_down.setFixedWidth(24);self.b_down.clicked.connect(lambda:self.seek_relative(-self.step_box.value()*10));ctrl_bar.addWidget(self.b_left);ctrl_bar.addWidget(self.b_right);ctrl_bar.addWidget(self.b_down);ctrl_bar.addWidget(self.b_up);ctrl_bar.addWidget(QLabel('Time:'));self.time_box=QDoubleSpinBox();self.time_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.time_box.setRange(0,99999);self.time_box.setDecimals(3);self.time_box.setMinimumWidth(60);self.time_box.valueChanged.connect(lambda v:self.seek_time(v,instant=True)if not self.play_timer.isActive()else None);ctrl_bar.addWidget(self.time_box);t_layout.addLayout(ctrl_bar);self.timeline=TimelineWidget(self);self.timeline.setMinimumSize(100,50);t_layout.addWidget(self.timeline);v_split.addWidget(t_container);nav_scroll=QScrollArea();nav_scroll.setWidgetResizable(True);nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded);nav_scroll.setMinimumWidth(100);nav_widget=QWidget();nav_widget.setMinimumWidth(0);nav_layout=QVBoxLayout(nav_widget);nav_layout.setSpacing(6);b_imp_v=QPushButton('Import video');b_imp_v.setFocusPolicy(Qt.FocusPolicy.NoFocus);b_imp_v.clicked.connect(self.pick_video);b_imp_s=QPushButton('Import subtitle');b_imp_s.setFocusPolicy(Qt.FocusPolicy.NoFocus);b_imp_s.clicked.connect(self.pick_subtitle);b_clr_s=QPushButton('Clear');b_clr_s.setFocusPolicy(Qt.FocusPolicy.NoFocus);b_clr_s.clicked.connect(self.clear_subtitle);row1=QHBoxLayout();row1.addWidget(b_imp_v);row1.addWidget(b_imp_s);row1.addWidget(b_clr_s);nav_layout.addLayout(row1);row2=QHBoxLayout();row2.addWidget(QLabel('Area:'));self.area_cb=QComboBox();self.area_cb.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
		for(k,v)in Canvas.Area.__members__.items():
			if len(k)>1 or k in('B','T','C','L','M','R'):self.area_cb.addItem(f"{k} ({v.value})",v.value)
		self.area_cb.currentIndexChanged.connect(self.on_area_cb_changed);row2.addWidget(self.area_cb);nav_layout.addLayout(row2);rd1=QHBoxLayout();self.area_w=QSpinBox();self.area_w.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.area_w.setRange(1,99999);self.area_w.setMinimumWidth(45);self.area_w.valueChanged.connect(self.on_area_spin_changed);self.area_h=QSpinBox();self.area_h.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.area_h.setRange(1,99999);self.area_h.setMinimumWidth(45);self.area_h.valueChanged.connect(self.on_area_spin_changed);rd1.addWidget(QLabel('Width:'));rd1.addWidget(self.area_w);rd1.addWidget(QLabel('Height:'));rd1.addWidget(self.area_h);nav_layout.addLayout(rd1);rd2=QHBoxLayout();self.area_pos_x=QSpinBox();self.area_pos_x.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.area_pos_x.setRange(0,99999);self.area_pos_x.setMinimumWidth(45);self.area_pos_x.valueChanged.connect(self.on_area_spin_changed);self.area_pos_y=QSpinBox();self.area_pos_y.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.area_pos_y.setRange(0,99999);self.area_pos_y.setMinimumWidth(45);self.area_pos_y.valueChanged.connect(self.on_area_spin_changed);rd2.addWidget(QLabel('Position:'));rd2.addWidget(self.area_pos_x);rd2.addWidget(self.area_pos_y);nav_layout.addLayout(rd2);row3=QHBoxLayout();self.chk_iam=QCheckBox("Subtitle's max");self.chk_iam.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.chk_iam.setChecked(True);self.chk_itm=QCheckBox("Timestamp's max");self.chk_itm.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.chk_itm.setChecked(False);self.chk_iam.toggled.connect(self.on_iam_toggled);row3.addWidget(self.chk_iam);row3.addWidget(self.chk_itm);nav_layout.addLayout(row3);row_prog=QHBoxLayout();self.start_ocr_btn=QPushButton('Start');self.start_ocr_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.start_ocr_btn.clicked.connect(self.start_ocr);self.prog_bar=QProgressBar();self.prog_bar.setRange(0,100);self.prog_bar.setValue(0);self.pause_ocr_btn=QPushButton('Pause');self.pause_ocr_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.pause_ocr_btn.setEnabled(False);self.pause_ocr_btn.clicked.connect(self.toggle_ocr_pause);self.stop_ocr_btn=QPushButton('Stop');self.stop_ocr_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.stop_ocr_btn.setEnabled(False);self.stop_ocr_btn.clicked.connect(self.stop_ocr);row_prog.addWidget(self.start_ocr_btn);row_prog.addWidget(self.prog_bar);row_prog.addWidget(self.pause_ocr_btn);row_prog.addWidget(self.stop_ocr_btn);nav_layout.addLayout(row_prog);row4=QHBoxLayout();self.chk_all=QCheckBox('All');self.chk_all.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.chk_all.stateChanged.connect(self.toggle_check_all);b_clear=QPushButton('Clear all ❌');b_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus);b_clear.clicked.connect(self.clear_all_clips);row4.addWidget(QLabel('List Desub'));row4.addWidget(self.chk_all);row4.addWidget(b_clear);nav_layout.addLayout(row4);self.clip_list=QListWidget();self.clip_list.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.clip_list.itemClicked.connect(self.list_item_clicked);nav_layout.addWidget(self.clip_list);nav_layout.addWidget(QLabel('<b>Active clip:</b>'));r_ed=QHBoxLayout();self.ed_st=QDoubleSpinBox();self.ed_st.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.ed_st.setRange(0,99999);self.ed_st.setDecimals(3);self.ed_st.setMinimumWidth(50);self.ed_en=QDoubleSpinBox();self.ed_en.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.ed_en.setRange(0,99999);self.ed_en.setDecimals(3);self.ed_en.setMinimumWidth(50);self.ed_ly=QSpinBox();self.ed_ly.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.ed_ly.setRange(-99,99);self.ed_ly.setMinimumWidth(35);self.ed_st.valueChanged.connect(self.on_active_time_changed);self.ed_en.valueChanged.connect(self.on_active_time_changed);self.ed_ly.valueChanged.connect(self.on_active_time_changed);r_ed.addWidget(QLabel('Start:'));r_ed.addWidget(self.ed_st);r_ed.addWidget(QLabel('End:'));r_ed.addWidget(self.ed_en);r_ed.addWidget(QLabel('L:'));r_ed.addWidget(self.ed_ly);nav_layout.addLayout(r_ed);r_sz=QHBoxLayout();self.clip_w=QSpinBox();self.clip_w.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.clip_w.setRange(1,99999);self.clip_w.setMinimumWidth(45);self.clip_w.valueChanged.connect(self.on_clip_size_changed);self.clip_h=QSpinBox();self.clip_h.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.clip_h.setRange(1,99999);self.clip_h.setMinimumWidth(45);self.clip_h.valueChanged.connect(self.on_clip_size_changed);self.clip_blur=QSpinBox();self.clip_blur.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.clip_blur.setRange(0,100);self.clip_blur.setMinimumWidth(40);self.clip_blur.valueChanged.connect(self.on_clip_size_changed);r_sz.addWidget(QLabel('W:'));r_sz.addWidget(self.clip_w);r_sz.addWidget(QLabel('H:'));r_sz.addWidget(self.clip_h);r_sz.addWidget(QLabel('Blur:'));r_sz.addWidget(self.clip_blur);nav_layout.addLayout(r_sz);nav_layout.addWidget(QLabel('<b>Keyframe:</b>'));r_kf1=QHBoxLayout();self.btn_prev_kf=QPushButton('◀ KF');self.btn_prev_kf.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.btn_prev_kf.clicked.connect(self.prev_kf);self.btn_next_kf=QPushButton('KF ▶');self.btn_next_kf.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.btn_next_kf.clicked.connect(self.next_kf);self.btn_add_kf=QPushButton('➕ KF');self.btn_add_kf.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.btn_add_kf.clicked.connect(self.add_keyframe_from_ui);self.btn_del_kf=QPushButton('➖ KF');self.btn_del_kf.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.btn_del_kf.clicked.connect(self.del_keyframe_from_ui);[r_kf1.addWidget(b) for b in(self.btn_prev_kf,self.btn_next_kf,self.btn_add_kf,self.btn_del_kf)];nav_layout.addLayout(r_kf1);r_kf2=QHBoxLayout();self.kf_t=QDoubleSpinBox();self.kf_t.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.kf_t.setRange(0,99999);self.kf_t.setDecimals(3);self.kf_t.setMinimumWidth(50);self.kf_x=QSpinBox();self.kf_x.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.kf_x.setRange(0,99999);self.kf_x.setMinimumWidth(45);self.kf_y=QSpinBox();self.kf_y.setFocusPolicy(Qt.FocusPolicy.ClickFocus);self.kf_y.setRange(0,99999);self.kf_y.setMinimumWidth(45);self.kf_t.valueChanged.connect(self.on_kf_spin_changed);self.kf_x.valueChanged.connect(self.on_kf_spin_changed);self.kf_y.valueChanged.connect(self.on_kf_spin_changed);r_kf2.addWidget(QLabel('T:'));r_kf2.addWidget(self.kf_t);r_kf2.addWidget(QLabel('X:'));r_kf2.addWidget(self.kf_x);r_kf2.addWidget(QLabel('Y:'));r_kf2.addWidget(self.kf_y);nav_layout.addLayout(r_kf2);b_add=QPushButton('Add desub');b_add.setFocusPolicy(Qt.FocusPolicy.NoFocus);b_add.clicked.connect(self.add_desub_from_ui);r_j=QHBoxLayout();b_imp=QPushButton('Import blurs.json');b_imp.setFocusPolicy(Qt.FocusPolicy.NoFocus);b_imp.clicked.connect(self.import_json);b_exp=QPushButton('Export blurs.json');b_exp.setFocusPolicy(Qt.FocusPolicy.NoFocus);b_exp.clicked.connect(self.export_json);[r_j.addWidget(b) for b in [b_imp,b_exp]];[nav_layout.addWidget(w) for w in [b_add]];nav_layout.addLayout(r_j);nav_layout.addStretch();nav_scroll.setWidget(nav_widget);h_split.addWidget(nav_scroll);h_split.setSizes([C.vw,C.nw]);v_split.setSizes([C.vh,C.th]);self.on_area_cb_changed()
	def update_magnet_style(self,chk):self.btn_magnet.setStyleSheet('background:#22c55e;color:#000;font-weight:bold;'if chk else'background:#282c3c;color:#fff;')
	def setup_shortcuts(self):QShortcut(QKeySequence(Qt.Key.Key_Space),self,self.toggle_play);QShortcut(QKeySequence(Qt.Key.Key_Delete),self,self.delete_selected);QShortcut(QKeySequence('Ctrl+B'),self,self.split_clip);QShortcut(QKeySequence('Ctrl+C'),self,self.copy_clips);QShortcut(QKeySequence('Ctrl+V'),self,self.paste_clips);QShortcut(QKeySequence('Ctrl+Z'),self,self.undo);QShortcut(QKeySequence('Ctrl+Shift+Z'),self,self.redo);QShortcut(QKeySequence('Ctrl+Up'),self,lambda:self.seek_time(.0,instant=True));QShortcut(QKeySequence('Ctrl+Down'),self,lambda:self.seek_time(self.total_dur,instant=True));QShortcut(QKeySequence('Ctrl+Left'),self,self.goto_clip_start);QShortcut(QKeySequence('Ctrl+Right'),self,self.goto_clip_end)
	def clip_st(self,c):return min(k.t for k in c.keyframes)if c and c.keyframes else.0
	def clip_en(self,c):return max(k.t for k in c.keyframes)if c and c.keyframes else.0
	def set_keyframe_at_cur_time(self,clip,x,y):
		for k in clip.keyframes:
			if abs(k.t-self.cur_time)<.05:k.x,k.y=x,y;return
		clip.keyframes.append(Delogo(t=round(self.cur_time,3),x=x,y=y));clip.keyframes.sort(key=lambda k:k.t)
	def prev_kf(self):
		c=self.active_clip
		if not c or not c.keyframes:return
		prevs=[k.t for k in c.keyframes if k.t<self.cur_time-.02]
		if prevs:self.seek_time(max(prevs),instant=True)
	def next_kf(self):
		c=self.active_clip
		if not c or not c.keyframes:return
		nxts=[k.t for k in c.keyframes if k.t>self.cur_time+.02]
		if nxts:self.seek_time(min(nxts),instant=True)
	def add_keyframe_from_ui(self):
		c=self.active_clip
		if not c:return
		self.save_history();self.set_keyframe_at_cur_time(c,self.kf_x.value(),self.kf_y.value());self.update_active_ui();self.timeline.update();self.view.update()
	def del_keyframe_from_ui(self):
		c=self.active_clip
		if not c or len(c.keyframes)<=1:return
		self.save_history();c.keyframes=[k for k in c.keyframes if abs(k.t-self.cur_time)>=.05]
		if not c.keyframes:c.keyframes.append(Delogo(t=round(self.cur_time,3),x=self.kf_x.value(),y=self.kf_y.value()))
		self.update_active_ui();self.timeline.update();self.view.update()
	def on_kf_spin_changed(self):
		c=self.active_clip
		if not c or not c.keyframes:return
		for k in c.keyframes:
			if abs(k.t-self.cur_time)<.05:k.x,k.y=self.kf_x.value(),self.kf_y.value();k.t=round(self.kf_t.value(),3);break
		c.keyframes.sort(key=lambda k:k.t);self.view.update();self.timeline.update()
	def on_clip_size_changed(self):
		c=self.active_clip
		if not c:return
		c.width,c.height,c.boxblur=self.clip_w.value(),self.clip_h.value(),self.clip_blur.value();self.view.update()
	def on_area_cb_changed(self):rx1,ry1,rx2,ry2=get_roi_bounds(self.vid_w,self.vid_h,self.area_cb.currentData());self.set_area_roi(rx1,ry1,max(1,rx2-rx1),max(1,ry2-ry1))
	def on_area_spin_changed(self):self.view.update()
	def set_area_roi(self,x,y,w,h):
		self.area_w.blockSignals(True);self.area_w.setValue(w);self.area_w.blockSignals(False)
		self.area_h.blockSignals(True);self.area_h.setValue(h);self.area_h.blockSignals(False)
		self.area_pos_x.blockSignals(True);self.area_pos_x.setValue(x+w//2);self.area_pos_x.blockSignals(False)
		self.area_pos_y.blockSignals(True);self.area_pos_y.setValue(y+h//2);self.area_pos_y.blockSignals(False)
		self.view.update()
	def get_area_roi(self):
		w,h=self.area_w.value(),self.area_h.value();x=max(0,min(self.vid_w-w,self.area_pos_x.value()-w//2));y=max(0,min(self.vid_h-h,self.area_pos_y.value()-h//2));return x,y,w,h
	def save_history(self):
		self.history.append(copy.deepcopy(self.clips))
		if len(self.history)>50:self.history.pop(0)
		self.redo_stack.clear()
	def undo(self):
		if self.history:self.redo_stack.append(copy.deepcopy(self.clips));self.clips=self.history.pop();self.selected_ids.clear();self.active_clip=None;self.sync_list_ui();self.view.update();self.timeline.update()
	def redo(self):
		if self.redo_stack:self.history.append(copy.deepcopy(self.clips));self.clips=self.redo_stack.pop();self.selected_ids.clear();self.active_clip=None;self.sync_list_ui();self.view.update();self.timeline.update()
	def resolve_layers(self):
		self.clips.sort(key=self.clip_st)
		for(i,c1)in enumerate(self.clips):
			s1,e1=self.clip_st(c1),self.clip_en(c1)
			used={getattr(c2,'layer',0)for c2 in self.clips[:i]if not(e1<=self.clip_st(c2)or s1>=self.clip_en(c2))}
			l=getattr(c1,'layer',0)
			if l in used:
				for cand in range(5):
					if cand not in used:l=cand;break
				else:l=(max(used)+1)%5
			c1.layer=l
	def get_active_clip(self):return self.active_clip
	def pick_video(self):
		p,_=QFileDialog.getOpenFileName(self,'Select video','','Video Files (*.mp4 *.mkv *.avi *.mov)')
		if p:self.load_video(Path(p))
	def pick_subtitle(self):
		p,_=QFileDialog.getOpenFileName(self,'Select subtitle','','Subtitles (*.srt *.json)')
		if p:self.sub_path=Path(p);self.view.update()
	def clear_subtitle(self):self.sub_path=None;self.view.update()
	def load_video(self,p:Path):
		if self.src_path:
			ret=QMessageBox.question(self,'Replace video?',f"Thay thế video {self.src_path.name} cũ?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
			if ret!=QMessageBox.StandardButton.Yes:return
		self.src_path=p
		if self.cap:self.cap.release()
		self.cap=cv2.VideoCapture(str(p));self.vid_w=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))or 1;self.vid_h=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))or 1;self.fps=max(self.cap.get(cv2.CAP_PROP_FPS),1.);fc=self.cap.get(cv2.CAP_PROP_FRAME_COUNT);self.total_dur=get_media_duration(p)or fc/self.fps;self.preview_w=min(self.vid_w,960);self.preview_h=max(1,int(self.preview_w*self.vid_h/self.vid_w));self.on_area_cb_changed();self.seek_time(.0,instant=True)
	def seek_time(self,t,instant=False):
		self.cur_time=max(.0,min(self.total_dur,t));self.target_seek_time=self.cur_time;self.time_box.blockSignals(True);self.time_box.setValue(self.cur_time);self.time_box.blockSignals(False);self.timeline.update();self.view.update();self.update_active_ui()
		if instant:self._do_seek()
		else:self.seek_timer.start(10)
	def _do_seek(self):
		if self.cap and self.cap.isOpened():
			self.cap.set(cv2.CAP_PROP_POS_MSEC,self.target_seek_time*1000);ret,fr=self.cap.read()
			if ret:
				if self.preview_w<self.vid_w:fr=cv2.resize(fr,(self.preview_w,self.preview_h),interpolation=cv2.INTER_NEAREST)
				rgb=cv2.cvtColor(fr,cv2.COLOR_BGR2RGB);self.cur_frame=QImage(rgb.data,self.preview_w,self.preview_h,3*self.preview_w,QImage.Format.Format_RGB888).copy();self.view.update()
	def seek_relative(self,dt):self.seek_time(self.cur_time+dt,instant=True)
	def toggle_play(self):
		if self.play_timer.isActive():self.play_timer.stop();self.play_btn.setText('Play')
		else:
			if self.cur_time>=self.total_dur:self.seek_time(.0,instant=True)
			else:self.cap.set(cv2.CAP_PROP_POS_MSEC,self.cur_time*1000)
			self.play_timer.start(max(1,int(1000/(self.fps*self.speed_box.value()))));self.play_btn.setText('Pause')
	def advance_playback(self):
		if not self.cap or not self.cap.isOpened()or self.cur_time>=self.total_dur:self.toggle_play();return
		ret,fr=self.cap.read()
		if not ret:self.toggle_play();return
		self.cur_time=self.cap.get(cv2.CAP_PROP_POS_MSEC)/1000.
		if self.preview_w<self.vid_w:fr=cv2.resize(fr,(self.preview_w,self.preview_h),interpolation=cv2.INTER_NEAREST)
		rgb=cv2.cvtColor(fr,cv2.COLOR_BGR2RGB);self.cur_frame=QImage(rgb.data,self.preview_w,self.preview_h,3*self.preview_w,QImage.Format.Format_RGB888).copy();self.time_box.blockSignals(True);self.time_box.setValue(self.cur_time);self.time_box.blockSignals(False);self.timeline.update();self.view.update()
	def start_ocr(self):
		if not self.src_path:return
		self.save_history();self.clips.clear();self.selected_ids.clear();self.active_clip=None;self.sync_list_ui();self.timeline.update();self.view.update();self.start_ocr_btn.setEnabled(False);self.pause_ocr_btn.setEnabled(True);self.pause_ocr_btn.setText('Pause');self.stop_ocr_btn.setEnabled(True);self.prog_bar.setValue(0);self.worker=OCRWorker(self.src_path,self.sub_path,self.get_area_roi(),self.chk_iam.isChecked(),self.chk_itm.isChecked());self.worker.progress.connect(self.on_ocr_progress);self.worker.finished.connect(self.on_ocr_finished);self.worker.start()
	def toggle_ocr_pause(self):
		if not self.worker or not self.worker.isRunning():return
		if self.worker._pause:self.worker.resume();self.pause_ocr_btn.setText('Pause')
		else:self.worker.pause();self.pause_ocr_btn.setText('Continue')
	def stop_ocr(self):
		if self.worker and self.worker.isRunning():self.worker.stop()
	def on_ocr_progress(self,pct,t,box,clip):
		self.prog_bar.setValue(int(pct));self.seek_time(t,instant=True);self.ocr_box=box
		if clip:self.clips.append(clip);self.resolve_layers();self.active_clip=clip;self.sync_list_ui();self.update_active_ui();self.timeline.update()
		self.view.update()
	def on_ocr_finished(self):
		self.start_ocr_btn.setEnabled(True);self.pause_ocr_btn.setEnabled(False);self.pause_ocr_btn.setText('Pause');self.stop_ocr_btn.setEnabled(False);self.ocr_box=None
		self.resolve_layers();self.sync_list_ui();self.view.update();self.timeline.update()
	def delete_selected(self):
		if not self.selected_ids:return
		self.save_history();self.clips=[c for c in self.clips if id(c)not in self.selected_ids];self.selected_ids.clear();self.active_clip=None;self.sync_list_ui();self.view.update();self.timeline.update()
	def split_clip(self):
		c=self.active_clip
		if c and c.keyframes and self.clip_st(c)<self.cur_time<self.clip_en(c):
			self.save_history();bx,by,_,_=get_box_at(c,self.cur_time);ct=round(self.cur_time,3)
			k1=[copy.deepcopy(k)for k in c.keyframes if k.t<ct]+[Delogo(t=ct,x=bx,y=by)];k2=[Delogo(t=ct,x=bx,y=by)]+[copy.deepcopy(k)for k in c.keyframes if k.t>ct]
			c.keyframes=k1;c2=copy.deepcopy(c);c2.keyframes=k2;self.clips.append(c2);self.resolve_layers();self.sync_list_ui();self.view.update();self.timeline.update()
	def copy_clips(self):self.clipboard=copy.deepcopy([c for c in self.clips if id(c)in self.selected_ids])
	def paste_clips(self):
		if not self.clipboard:return
		self.save_history();min_st=min(self.clip_st(c)for c in self.clipboard);self.selected_ids.clear()
		for c in self.clipboard:
			nc=copy.deepcopy(c);dt=self.cur_time-min_st
			for k in nc.keyframes:k.t=round(k.t+dt,3)
			self.clips.append(nc);self.selected_ids.add(id(nc))
		self.resolve_layers();self.sync_list_ui();self.view.update();self.timeline.update()
	def goto_clip_start(self):
		if self.active_clip:self.seek_time(self.clip_st(self.active_clip),instant=True)
	def goto_clip_end(self):
		if self.active_clip:self.seek_time(self.clip_en(self.active_clip),instant=True)
	def sync_list_ui(self):
		self.clip_list.clear()
		for c in self.clips:
			it=QListWidgetItem();w=QWidget();lay=QHBoxLayout(w);lay.setContentsMargins(2,2,2,2);cb=QCheckBox();cb.setFocusPolicy(Qt.FocusPolicy.NoFocus);cb.setChecked(id(c)in self.selected_ids);cb.stateChanged.connect(lambda s,clip=c:self.on_clip_checked(clip,s));lbl=QLabel(f"{self.clip_st(c):.3f} -> {self.clip_en(c):.3f} ({getattr(c,'layer',0)})");btn_del=QPushButton('❌');btn_del.setFocusPolicy(Qt.FocusPolicy.NoFocus);btn_del.setFixedWidth(28);btn_del.clicked.connect(lambda _,clip=c:self.remove_clip(clip));lay.addWidget(cb);lay.addWidget(lbl);lay.addWidget(btn_del);it.setSizeHint(w.sizeHint());it.setData(Qt.ItemDataRole.UserRole,c);self.clip_list.addItem(it);self.clip_list.setItemWidget(it,w)
	def on_clip_checked(self,c,s):
		if s==2:self.selected_ids.add(id(c))
		else:self.selected_ids.discard(id(c))
		self.timeline.update()
	def sync_list_selection(self):
		for i in range(self.clip_list.count()):
			it=self.clip_list.item(i);c=it.data(Qt.ItemDataRole.UserRole);w=self.clip_list.itemWidget(it)
			if w:
				cb=w.findChild(QCheckBox)
				if cb:cb.blockSignals(True);cb.setChecked(id(c)in self.selected_ids);cb.blockSignals(False)
	def list_item_clicked(self,it):
		c=it.data(Qt.ItemDataRole.UserRole);mods=QApplication.keyboardModifiers()
		if mods&Qt.KeyboardModifier.ControlModifier:
			if id(c)in self.selected_ids:self.selected_ids.remove(id(c))
			else:self.selected_ids.add(id(c))
		else:self.selected_ids={id(c)}
		self.active_clip=c;self.update_active_ui();self.sync_list_selection();self.timeline.update();self.view.update()
	def remove_clip(self,c):
		self.save_history()
		if c in self.clips:self.clips.remove(c)
		self.selected_ids.discard(id(c))
		if self.active_clip==c:self.active_clip=None
		self.sync_list_ui();self.timeline.update();self.view.update()
	def clear_all_clips(self):self.save_history();self.clips.clear();self.selected_ids.clear();self.active_clip=None;self.sync_list_ui();self.timeline.update();self.view.update()
	def toggle_check_all(self,s):self.selected_ids={id(c)for c in self.clips}if s==2 else set();self.sync_list_selection();self.timeline.update()
	def on_active_time_changed(self):
		c=self.active_clip
		if not c or not c.keyframes:return
		old_st,old_en=self.clip_st(c),self.clip_en(c);nst,nen=round(self.ed_st.value(),3),round(self.ed_en.value(),3);c.layer=self.ed_ly.value()
		if len(c.keyframes)>1 and old_en>old_st:
			for k in c.keyframes:k.t=round(nst+(k.t-old_st)/(old_en-old_st)*(nen-nst),3)
		elif c.keyframes:c.keyframes[0].t=nst
		self.resolve_layers();self.sync_list_ui();self.timeline.update();self.view.update()
	def on_iam_toggled(self, checked):
		self.chk_itm.setEnabled(checked)
		if not checked:
			self.chk_itm.setChecked(False)
	def on_itm_toggled(self, checked):
		if checked:
			self.chk_iam.setChecked(True)
	def update_active_ui(self):
		c=self.active_clip
		if not c or not c.keyframes:return
		st,en=self.clip_st(c),self.clip_en(c);self.ed_st.blockSignals(True);self.ed_st.setValue(st);self.ed_st.blockSignals(False);self.ed_en.blockSignals(True);self.ed_en.setValue(en);self.ed_en.blockSignals(False);self.ed_ly.blockSignals(True);self.ed_ly.setValue(getattr(c,'layer',0));self.ed_ly.blockSignals(False);self.clip_w.blockSignals(True);self.clip_w.setValue(c.width);self.clip_w.blockSignals(False);self.clip_h.blockSignals(True);self.clip_h.setValue(c.height);self.clip_h.blockSignals(False);self.clip_blur.blockSignals(True);self.clip_blur.setValue(getattr(c,'boxblur',20));self.clip_blur.blockSignals(False)
		cur_kf=min(c.keyframes,key=lambda k:abs(k.t-self.cur_time))if c.keyframes else None
		kt=cur_kf.t if cur_kf and abs(cur_kf.t-self.cur_time)<.05 else self.cur_time
		cx=cur_kf.x if cur_kf else (c.keyframes[0].x if c.keyframes else 0)
		cy=cur_kf.y if cur_kf else (c.keyframes[0].y if c.keyframes else 0)
		self.kf_t.blockSignals(True);self.kf_t.setValue(kt);self.kf_t.blockSignals(False)
		self.kf_x.blockSignals(True);self.kf_x.setValue(cx);self.kf_x.blockSignals(False)
		self.kf_y.blockSignals(True);self.kf_y.setValue(cy);self.kf_y.blockSignals(False)
	def add_desub_from_ui(self):
		st,en,ly=self.ed_st.value(),self.ed_en.value(),self.ed_ly.value()
		if en<=st:en=min(self.total_dur,st+2.)
		self.save_history();w,h=self.clip_w.value(),self.clip_h.value();rx,ry,rw,rh=self.get_area_roi()
		if w<=5 or h<=5:w=min(self.vid_w-4,max(40,int(rw*0.95)));h=min(rh,max(20,int(rh*0.75)))
		cx,cy=rx+rw//2,ry+rh//2
		c=Delogo_KeyFrames(boxblur=self.clip_blur.value()or 20,width=w,height=h,keyframes=[Delogo(t=round(st,3),x=cx,y=cy),Delogo(t=round(en,3),x=cx,y=cy)]);c.layer=ly;self.clips.append(c);self.resolve_layers();self.active_clip=c;self.update_active_ui();self.sync_list_ui();self.timeline.update();self.view.update()
	def import_json(self):
		p,_=QFileDialog.getOpenFileName(self,'Import blurs.json','','JSON Files (*.json)')
		if p:
			d=r_json(p);self.save_history();new_clips=[]
			if isinstance(d,dict):
				if'frames'in d:new_clips=[Delogo_KeyFrames.parse(x)for x in d['frames']if isinstance(x,dict)]
				elif'delogos'in d:new_clips=[Delogo_KeyFrames.parse(x)for x in d['delogos']if isinstance(x,dict)]
				elif'keyframes'in d:new_clips=[Delogo_KeyFrames.parse(d)]
			elif isinstance(d,list):new_clips=[Delogo_KeyFrames.parse(x)for x in d if isinstance(x,dict)]
			if new_clips:self.clips.extend(new_clips);self.resolve_layers();self.sync_list_ui();self.timeline.update();self.view.update()
	def export_json(self):
		p,_=QFileDialog.getSaveFileName(self,'Export blurs.json','blurs.json','JSON Files (*.json)')
		if p:w_json(p,{'frames':[c.asdict()if hasattr(c,'asdict')else c.__dict__ for c in self.clips]})
class C:
	w,h=1080,300
	vw,vh=int(w*2/3),int(h*3/4)
	tw,th=vw,int(h*1/4)
	nw,nh=w-vw,h-vh
if __name__=='__main__':
	parser=argparse.ArgumentParser()
	parser.add_argument('-i','--input',required=False,default=None)
	parser.add_argument('-a','--area',default=0,type=int)
	parser.add_argument('-am','--is-area-max',default=True,type=str2bool)
	parser.add_argument('-tm','--is-timestamp-max',default=False,type=str2bool)
	args,_=parser.parse_known_args()
	init_itm = bool(args.is_timestamp_max)
	init_iam = True if init_itm else bool(args.is_area_max)
	app=QApplication(sys.argv)
	MainWindow(init_video=args.input, init_area=args.area, init_iam=init_iam, init_itm=init_itm).show()
	sys.exit(app.exec())