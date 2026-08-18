from PyQt6.QtMultimedia import QMediaPlayer,QAudioOutput,QVideoSink
import sys,json,math,time,easyocr,copy;import numpy as np;from dataclasses import dataclass,field
from PyQt6.QtWidgets import QApplication,QMainWindow,QComboBox,QPushButton,QHBoxLayout,QVBoxLayout,QListWidget,QWidget,QLabel,QFileDialog,QSplitter,QGraphicsView,QGraphicsScene,QGraphicsPixmapItem,QGraphicsEllipseItem,QGraphicsPolygonItem,QDoubleSpinBox,QSpinBox,QGraphicsItem,QFrame,QLineEdit,QProgressBar,QTabWidget,QAbstractItemView,QGraphicsSimpleTextItem,QCheckBox
from PyQt6.QtCore import Qt,QUrl,QPointF
from PyQt6.QtGui import QFont,QPainter,QPen,QColor,QBrush,QPolygonF,QImage,QPixmap,QFontMetrics,QPainterPath,QFontDatabase
class S:
	easyocr_reader='ch_sim'
	btn_gray='background-color: #333; color: white; font-weight: bold; font-size: 10px;'
	btn_grey='background-color: #555; color: white; font-weight: bold; font-size: 10px;'
class F:no_focus=lambda w:w.setFocusPolicy(Qt.FocusPolicy.NoFocus);style=lambda s:lambda w:w.setStyleSheet(s)
class mdl:
	@staticmethod
	def cre(w,*fns,**kws):
		for f in fns:f(w)
		for k,v in kws.items():
			if k=='style':w.setStyleSheet(v)
			elif k=='focus':w.setFocusPolicy(v)
			elif k=='range':w.setRange(*v)
			elif k=='val':w.setValue(v)
			elif k=='step':w.setSingleStep(v)
		return w
@dataclass
class Point:x:float=.0;y:float=.0
@dataclass
class TargetFrame:x:float=.0;y:float=.0;time:float=.0
@dataclass
class RecLine:
	start:float=.0;end:float=.0
	points:list[Point]=field(default_factory=lambda:[Point(1e2,1e2),Point(3e2,1e2),Point(3e2,3e2),Point(1e2,3e2)])
	target_frames:list[TargetFrame]=field(default_factory=list)
	track:int=0
	st_orig:float=.0;en_orig:float=.0
@dataclass
class RecLineText:
	start:float=.0;end:float=.0
	text:str=""
	x:int=540;y:int=1500
	style_ass:dict=field(default_factory=lambda:{
		'font':'Cambria','size':69,'color':'#ffc300','bordercolor':'#FFFFFF','backcolor':'#00E6FF',
		'bold':False,'italic':False,'underline':False,'strikeout':False,
		'scalex':100,'scaley':100,'spacing':0.0,'angle':0.0,
		'borderstyle':1,'borderw':1.0,'shadow':2.0,
		'align':2,'margin_l':10,'margin_r':10,'margin_v':10,'encoding':1
	})
	track:int=3
class Data:
	def __init__(A):A.polygons=[];A.texts=[]
class HandleItem(QGraphicsEllipseItem):
	def __init__(A,idx,mw):super().__init__(-6,-6,12,12);A.idx=idx;A.mw=mw;A.setBrush(QBrush(QColor(255,255,0)));A.setPen(QPen(QColor(0,0,0),1.5));A.setAcceptedMouseButtons(Qt.MouseButton.LeftButton);A.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,True);A.setCursor(Qt.CursorShape.SizeAllCursor)
	def itemChange(A,change,value):
		C=value;B=change
		if B==QGraphicsItem.GraphicsItemChange.ItemPositionChange and A.isVisible()and not A.mw.updating_poly:A.mw.handle_moved(A.idx,C)
		return super().itemChange(B,C)
	def mousePressEvent(A,event):A.mw.save_state();event.accept();A.setCursor(Qt.CursorShape.ClosedHandCursor)
	def mouseMoveEvent(A,event):B=event;C=B.scenePos();A.setPos(C);A.mw.handle_moved(A.idx,C);B.accept()
	def mouseReleaseEvent(A,event):A.setCursor(Qt.CursorShape.SizeAllCursor);event.accept()
class RangeHandleItem(QGraphicsEllipseItem):
	def __init__(A,idx,mw):super().__init__(-6,-6,12,12);A.idx=idx;A.mw=mw;A.setBrush(QBrush(QColor(255,0,0)));A.setPen(QPen(QColor(0,0,0),1.5));A.setAcceptedMouseButtons(Qt.MouseButton.LeftButton);A.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,True);A.setCursor(Qt.CursorShape.SizeAllCursor)
	def itemChange(A,change,value):
		C=value;B=change
		if B==QGraphicsItem.GraphicsItemChange.ItemPositionChange and A.isVisible()and not A.mw.updating_poly:A.mw.range_handle_moved(A.idx,C)
		return super().itemChange(B,C)
	def mousePressEvent(A,event):A.mw.save_state();event.accept();A.setCursor(Qt.CursorShape.ClosedHandCursor)
	def mouseMoveEvent(A,event):B=event;C=B.scenePos();A.setPos(C);A.mw.range_handle_moved(A.idx,C);B.accept()
	def mouseReleaseEvent(A,event):A.setCursor(Qt.CursorShape.SizeAllCursor);event.accept()
class InteractivePolygonItem(QGraphicsPolygonItem):
	def __init__(A,mw):super().__init__();A.mw=mw;A.setFlags(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges);A.setAcceptedMouseButtons(Qt.MouseButton.LeftButton);A.setPen(QPen(QColor(255,255,0),2.5));A.setBrush(QBrush(QColor(255,255,0,40)));A.setCursor(Qt.CursorShape.SizeAllCursor);A.idx=-1;A._press_scene_pos=None;A.drag_edge_idx=-1
	def itemChange(A,change,value):return super().itemChange(change,value)
	def mousePressEvent(A,event):
		B=event;A.mw.save_state()
		if hasattr(A,'idx')and 0<=A.idx<len(A.mw.data.polygons):
			A.mw.set_selected_rec(A.idx);scale=A.mw.image_scale;p_orig=Point(B.scenePos().x()/scale,B.scenePos().y()/scale);poly=A.mw.data.polygons[A.idx];pts=A.mw.get_rendered_pts(poly,A.mw.get_current_time());min_dist=999999.;best_edge=-1
			if A.mw.current_tool=='G':A.drag_edge_idx=-1
			else:
				for i in range(4):
					p1,p2=pts[i],pts[(i+1)%4];dx,dy=p2.x-p1.x,p2.y-p1.y;length_sq=dx*dx+dy*dy
					if length_sq==0:dist=math.hypot(p_orig.x-p1.x,p_orig.y-p1.y)
					else:t=max(.0,min(1.,((p_orig.x-p1.x)*dx+(p_orig.y-p1.y)*dy)/length_sq));dist=math.hypot(p_orig.x-(p1.x+t*dx),p_orig.y-(p1.y+t*dy))
					if dist<min_dist:min_dist=dist;best_edge=i
				if min_dist<15./scale:A.drag_edge_idx=best_edge
				else:A.drag_edge_idx=-1
		A._press_scene_pos=B.scenePos();A.setCursor(Qt.CursorShape.ClosedHandCursor);B.accept()
	def mouseMoveEvent(A,event):
		B=event
		if A._press_scene_pos is None:B.ignore();return
		C=B.scenePos();D=C-A._press_scene_pos
		if getattr(A,'drag_edge_idx',-1)!=-1:A.mw.polygon_edge_translated(A.drag_edge_idx,D)
		else:A.mw.polygon_translated(D)
		A._press_scene_pos=C;B.accept()
	def mouseReleaseEvent(A,event):A._press_scene_pos=None;A.setCursor(Qt.CursorShape.SizeAllCursor);event.accept()
class InteractiveRangePolygonItem(QGraphicsPolygonItem):
	def __init__(A,mw):super().__init__();A.mw=mw;A.setFlags(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges);A.setAcceptedMouseButtons(Qt.MouseButton.LeftButton);A.setPen(QPen(QColor(255,0,0),2.5,Qt.PenStyle.DashLine));A.setBrush(QBrush(QColor(255,0,0,20)));A.setCursor(Qt.CursorShape.SizeAllCursor);A._press_scene_pos=None;A.drag_edge_idx=-1
	def mousePressEvent(A,event):
		B=event;A.mw.save_state();scale=A.mw.image_scale;p_orig=Point(B.scenePos().x()/scale,B.scenePos().y()/scale);pts=A.mw.range_points;min_dist=999999.;best_edge=-1
		for i in range(4):
			p1,p2=pts[i],pts[(i+1)%4];dx,dy=p2.x-p1.x,p2.y-p1.y;length_sq=dx*dx+dy*dy
			if length_sq==0:dist=math.hypot(p_orig.x-p1.x,p_orig.y-p1.y)
			else:t=max(.0,min(1.,((p_orig.x-p1.x)*dx+(p_orig.y-p1.y)*dy)/length_sq));dist=math.hypot(p_orig.x-(p1.x+t*dx),p_orig.y-(p1.y+t*dy))
			if dist<min_dist:min_dist=dist;best_edge=i
		if min_dist<15./scale:A.drag_edge_idx=best_edge
		else:A.drag_edge_idx=-1
		A._press_scene_pos=B.scenePos();A.setCursor(Qt.CursorShape.ClosedHandCursor);B.accept()
	def mouseMoveEvent(A,event):
		B=event
		if A._press_scene_pos is None:B.ignore();return
		C=B.scenePos();D=C-A._press_scene_pos
		if getattr(A,'drag_edge_idx',-1)!=-1:A.mw.range_polygon_edge_translated(A.drag_edge_idx,D)
		else:A.mw.range_polygon_translated(D)
		A._press_scene_pos=C;B.accept()
	def mouseReleaseEvent(A,event):A._press_scene_pos=None;A.setCursor(Qt.CursorShape.SizeAllCursor);event.accept()
class FocusItem(QGraphicsEllipseItem):
	def __init__(A,mw):super().__init__(-7,-7,14,14);A.mw=mw;A.setPen(QPen(QColor(0,255,0),2));A.setBrush(QBrush(QColor(0,255,0,110)));A.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable|QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
	def shape(A):p=QPainterPath();p.addEllipse(A.rect());return p
	def mousePressEvent(A,event):A.mw.save_state();super().mousePressEvent(event)
	def itemChange(A,change,value):
		C=change;B=value
		if C==QGraphicsItem.GraphicsItemChange.ItemPositionChange and A.isVisible()and not A.mw.updating_poly:D=max(1e-06,A.mw.image_scale);A.mw.data.focus.x=int(B.x()/D);A.mw.data.focus.y=int(B.y()/D);A.mw.sync_data_to_widgets()
		return super().itemChange(C,B)
class RecLineFocusItem(QGraphicsEllipseItem):
	def __init__(A,mw):super().__init__(-7,-7,14,14);A.mw=mw;A.setPen(QPen(QColor(255,0,0),2));A.setBrush(QBrush(QColor(255,0,0,110)));A.setFlags(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
	def shape(A):p=QPainterPath();p.addEllipse(A.rect());return p
	def itemChange(A,change,value):return super().itemChange(change,value)
class ClickablePolyItem(QGraphicsPolygonItem):
	def __init__(A,polygon,idx,mw):super().__init__(polygon);A.idx=idx;A.mw=mw;A.setPen(QPen(QColor(0,255,255),2));A.setBrush(QBrush(QColor(0,255,255,30)));A.setAcceptedMouseButtons(Qt.MouseButton.LeftButton);A.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,True);A.setZValue(2)
	def mousePressEvent(A,event):B=event;A.mw.set_selected_rec(A.idx);A.mw.sync_data_to_widgets();B.accept();super().mousePressEvent(B)
class MediaView(QGraphicsView):
	def __init__(A,parent=None):super().__init__(parent);A.mw=parent;A.setAcceptDrops(True);A.drag_start=None;A.middle_drag_start=None;A.scale_factor=1.;A.setRenderHint(QPainter.RenderHint.Antialiasing);A.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
	def dragEnterEvent(A,event):
		if event.mimeData().hasUrls():event.acceptProposedAction()
	def dragMoveEvent(A,event):
		if event.mimeData().hasUrls():event.acceptProposedAction()
	def dropEvent(A,event):
		if event.mimeData().hasUrls():
			for C in event.mimeData().urls():
				fp=C.toLocalFile()
				if fp.lower().endswith(('.mp4','.avi','.mkv','.mov')):
					mw=A.window()
					if hasattr(mw,'load_media'):
						mw.load_media(fp)
						if hasattr(mw,'duration'):mw.player.durationChanged.connect(lambda d:mw.duration.setValue(round(d/1e3,2)))
					break
		event.acceptProposedAction()
	def wheelEvent(A,event):
		D=event;B=D.angleDelta().y();E=D.modifiers()
		if E==Qt.KeyboardModifier.ControlModifier:C=1.15 if B>0 else .85;A.scale_factor*=C;A.scale(C,C)
		elif E==Qt.KeyboardModifier.AltModifier:A.horizontalScrollBar().setValue(A.horizontalScrollBar().value()-B)
		else:A.verticalScrollBar().setValue(A.verticalScrollBar().value()-B)
	def mousePressEvent(B,event):
		A=event
		if A.button()==Qt.MouseButton.RightButton:B.drag_start=A.pos();B.setCursor(Qt.CursorShape.ClosedHandCursor)
		elif A.button()==Qt.MouseButton.MiddleButton:B.middle_drag_start=A.pos();B.setCursor(Qt.CursorShape.SizeAllCursor)
		else:super().mousePressEvent(A)
	def mouseMoveEvent(A,event):
		B=event
		if A.drag_start is not None:D=B.pos()-A.drag_start;A.drag_start=B.pos();A.horizontalScrollBar().setValue(A.horizontalScrollBar().value()-D.x());A.verticalScrollBar().setValue(A.verticalScrollBar().value()-D.y())
		elif A.middle_drag_start is not None:E=B.pos().y()-A.middle_drag_start.y();A.middle_drag_start=B.pos();C=1.02 if E<0 else .98;A.scale_factor*=C;A.scale(C,C)
		else:super().mouseMoveEvent(B)
	def mouseReleaseEvent(A,event):
		B=event
		if B.button()==Qt.MouseButton.RightButton:A.drag_start=None;A.setCursor(Qt.CursorShape.ArrowCursor)
		elif B.button()==Qt.MouseButton.MiddleButton:A.middle_drag_start=None;A.setCursor(Qt.CursorShape.ArrowCursor)
		else:super().mouseReleaseEvent(B)
class TimelineWidget(QWidget):
	def __init__(A,main_window,parent=None):super().__init__(parent);A.main_window=main_window;A.setMouseTracking(True);A.hover_x=-1;A.zoom_level=25.;A.offset_x=0;A.drag_start_x=None;A.dragging_rec_idx=-1;A.dragging_mode=None;A.drag_init_st=.0;A.drag_init_en=.0;A.drag_click_time=.0;A.dragging_playhead=False;A.sel_start=None;A.sel_end=None;A.dragging_tf_poly_idx=-1;A.dragging_tf_idx=-1;A.dragging_tf_edge=None
	def paintEvent(B,event):
		A=QPainter(B);E,L=B.width(),B.height();A.fillRect(0,0,E,L,QColor(25,25,25));S_dur=B.main_window.get_duration()or 1e2;D=30;A.setPen(QPen(QColor(100,100,100),1));A.drawLine(0,D,E,D);N=max(10,int(B.zoom_level))
		for C in range(0,E+N,N):
			I=(C-B.offset_x)/B.zoom_level
			if I<0 or I>S_dur+10:continue
			if int(I*10)%10==0:A.drawLine(C,D-12,C,D);A.setFont(QFont('consolas',7));A.drawText(C+2,D-2,f"{I:.1f}s")
			else:A.drawLine(C,D-6,C,D)
		G,H=D+5,20;A.fillRect(0,G,E,H,QColor(35,35,35));A.setPen(QColor(120,120,120));A.drawText(10,G+14,'Audio Tracker (dB)')
		for C in range(0,E,5):O=(math.sin(C*.03)+1)*.5*H*.6;A.setPen(QColor(0,180,90,100));A.drawLine(C,int(G+H/2-O/2),C,int(G+H/2+O/2))
		M=24
		for(P,Q)in enumerate(B.main_window.data.polygons):
			J=60+Q.track*(M+4);K=int(Q.start*B.zoom_level+B.offset_x);T=int(Q.end*B.zoom_level+B.offset_x);R=max(6,T-K);U=P in B.main_window.selected_recs and B.main_window.right_tabs.currentIndex()!=1;V=QColor(255,255,0,180)if U else QColor(0,255,255,140);A.fillRect(K,J,R,M,V);A.setPen(QPen(QColor(0,0,0),1.5));A.drawRect(K,J,R,M);A.setFont(QFont('consolas',8,QFont.Weight.Bold));A.drawText(K+5,J+16,f"RecLine [{P}]")
			for tf_idx,tf in enumerate(Q.target_frames):
				X_tf=int(tf.time*B.zoom_level+B.offset_x);Y_tf=J+M//2;diamond=QPolygonF([QPointF(X_tf-5,Y_tf),QPointF(X_tf,Y_tf-5),QPointF(X_tf+5,Y_tf),QPointF(X_tf,Y_tf+5)]);A.setPen(QPen(QColor(0,0,0),1));is_out=(tf_idx==0)or(tf_idx==len(Q.target_frames)-1);A.setBrush(QBrush((QColor(255,0,0)if is_out else QColor(0,255,255))if U else QColor(255,255,255)));A.drawPolygon(diamond)
		for(P,Q)in enumerate(B.main_window.data.texts):
			if not Q.text: continue
			J=60+Q.track*(M+4);K=int(Q.start*B.zoom_level+B.offset_x);T=int(Q.end*B.zoom_level+B.offset_x);R=max(6,T-K);U=P in B.main_window.selected_texts and B.main_window.right_tabs.currentIndex()==1;V=QColor(255,100,0,180)if U else QColor(255,165,0,140);A.fillRect(K,J,R,M,V);A.setPen(QPen(QColor(0,0,0),1.5));A.drawRect(K,J,R,M);A.setFont(QFont('consolas',8,QFont.Weight.Bold));A.drawText(K+5,J+16,f"Text [{P}]: {Q.text[:10]}")
		if B.sel_start is not None and B.sel_end is not None:
			A.setPen(QPen(QColor(0,255,255,100),1,Qt.PenStyle.DashLine))
			A.setBrush(QBrush(QColor(0,255,255,30)))
			x1,x2=B.sel_start.x(),B.sel_end.x()
			y1,y2=B.sel_start.y(),B.sel_end.y()
			A.drawRect(min(x1,x2),min(y1,y2),abs(x1-x2),abs(y1-y2))
		if B.hover_x>=0:
			t_h=max(.0,(B.hover_x-B.offset_x)/B.zoom_level);h_str=f"times: {t_h:.3f}"
			A.setPen(QPen(QColor(255,255,0),1,Qt.PenStyle.DotLine));A.drawLine(B.hover_x,0,B.hover_x,L)
			A.setFont(QFont('consolas',8));A.setPen(QPen(QColor(255,255,0),1))
			A.drawText(B.hover_x+5,L-8,h_str)
		W=B.main_window.get_current_time();F=int(W*B.zoom_level+B.offset_x)
		if 0<=F<=E:
			A.setPen(QPen(QColor(255,50,50),1.5));A.drawLine(F,0,F,L);A.setBrush(QBrush(QColor(255,50,50)));A.drawPolygon(QPolygonF([QPointF(F-6,0),QPointF(F+6,0),QPointF(F,9)]))
			h=int(W//3600);m=int((W%3600)//60);s=int(W%60);ms=int((W-int(W))*1000);t_str=f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
			A.setFont(QFont('consolas',8));A.setPen(QPen(QColor(255,50,50),1));A.drawText(F-78,12,t_str)
	def mousePressEvent(A,event):
		if QApplication.focusWidget():QApplication.focusWidget().clearFocus()
		E=event;C,L=E.pos().x(),E.pos().y();H=(C-A.offset_x)/A.zoom_level;M=24;D=-1;track=max(0,int((L-60)/(M+4)));clicked_diamond=False
		is_ass_tab=(A.main_window.right_tabs.currentIndex()==1)
		items=A.main_window.data.texts if is_ass_tab else A.main_window.data.polygons
		if not is_ass_tab:
			for (P,Q) in enumerate(items):
				J=60+Q.track*(M+4)
				for tf_idx,tf in enumerate(Q.target_frames):
					X_tf=int(tf.time*A.zoom_level+A.offset_x);Y_tf=J+M//2
					if abs(C-X_tf)<8 and abs(L-Y_tf)<8:A.dragging_tf_poly_idx=P;A.dragging_tf_idx=tf_idx;A.dragging_tf_edge='time';A.drag_click_time=H;clicked_diamond=True;break
				if clicked_diamond:break
			if clicked_diamond:A.main_window.save_state();A.main_window.set_selected_rec(A.dragging_tf_poly_idx);A.update();return
		for(J,B)in enumerate(items):
			if B.track==track:
				F_val=int(B.start*A.zoom_level+A.offset_x);G=int(B.end*A.zoom_level+A.offset_x)
				if F_val<=C<=G:D=J;break
		if L<30 or abs(C-(A.main_window.get_current_time()*A.zoom_level+A.offset_x))<10:A.dragging_playhead=True;A.main_window.seek_time(max(.0,H))
		elif D!=-1:
			if is_ass_tab:A.main_window.set_selected_text_idx(D)
			else:A.main_window.toggle_select_rec(D)
			if D!=-1:
				B=items[D];F_val=int(B.start*A.zoom_level+A.offset_x);G=int(B.end*A.zoom_level+A.offset_x);A.dragging_rec_idx=D;A.drag_init_st=B.start;A.drag_init_en=B.end;A.drag_click_time=H
				if abs(C-F_val)<8 and A.main_window.current_tool!='G':A.dragging_mode='resize-start'
				elif abs(C-G)<8 and A.main_window.current_tool!='G':A.dragging_mode='resize-end'
				else:A.dragging_mode='move'
				A.main_window.save_state()
		elif E.button()==Qt.MouseButton.LeftButton:A.sel_start=E.pos();A.sel_end=E.pos()
		elif E.button()==Qt.MouseButton.RightButton:A.drag_start_x=C;A.setCursor(Qt.CursorShape.ClosedHandCursor)
	def mouseReleaseEvent(A,event):
		try:
			if A.sel_start is not None and A.sel_end is not None:
				x1,x2=A.sel_start.x(),A.sel_end.x();y1,y2=A.sel_start.y(),A.sel_end.y();t_st=(min(x1,x2)-A.offset_x)/A.zoom_level;t_en=(max(x1,x2)-A.offset_x)/A.zoom_level;track_min=max(0,int((min(y1,y2)-60)/28));track_max=max(0,int((max(y1,y2)-60)/28));new_sel=set()
				is_ass_tab=(A.main_window.right_tabs.currentIndex()==1)
				items=A.main_window.data.texts if is_ass_tab else A.main_window.data.polygons
				for idx,B in enumerate(items):
					if track_min<=B.track<=track_max and max(t_st,B.start)<min(t_en,B.end):new_sel.add(idx)
				if is_ass_tab:
					A.main_window.selected_texts=new_sel;A.main_window.selected_text_idx=list(new_sel)[0]if new_sel else-1
				else:
					A.main_window.selected_recs=new_sel;A.main_window.selected_rec_idx=list(new_sel)[0]if new_sel else-1
				A.main_window.sync_data_to_widgets()
		finally:
			A.sel_start=None;A.sel_end=None;A.drag_start_x=None;A.dragging_rec_idx=-1;A.dragging_mode=None;A.dragging_playhead=False;A.dragging_tf_poly_idx=-1;A.dragging_tf_idx=-1;A.dragging_tf_edge=None;A.setCursor(Qt.CursorShape.ArrowCursor);A.update()
		event.accept()
	def mouseMoveEvent(A,event):
		E=event;C=E.pos().x();A.hover_x=C;F_h=24
		if A.sel_start is not None:A.sel_end=E.pos();A.update()
		elif A.dragging_tf_poly_idx!=-1:
			poly=A.main_window.data.polygons[A.dragging_tf_poly_idx];tf=poly.target_frames[A.dragging_tf_idx];dur=A.main_window.get_duration() or 99999.;new_t=max(poly.start,min(poly.end,(C-A.offset_x)/A.zoom_level))
			tf.time=new_t
			poly.target_frames.sort(key=lambda x:x.time);A.main_window.sync_data_to_widgets()
		elif A.dragging_playhead:K=(C-A.offset_x)/A.zoom_level;A.main_window.seek_time(max(.0,K))
		elif A.dragging_rec_idx!=-1 and A.dragging_mode:
			is_ass_tab=(A.main_window.right_tabs.currentIndex()==1)
			items=A.main_window.data.texts if is_ass_tab else A.main_window.data.polygons
			B=items[A.dragging_rec_idx];K=(C-A.offset_x)/A.zoom_level;D=K-A.drag_click_time;dur=A.main_window.get_duration()or 99999.;L_len=A.drag_init_en-A.drag_init_st
			if A.dragging_mode=='move':
				G_st=max(.0,A.drag_init_st+D);G_en=G_st+L_len;target_track=max(0,int((E.pos().y()-60)/(F_h+4)))
				if not A.main_window.check_overlap(G_st,G_en,target_track,A.dragging_rec_idx,is_ass=is_ass_tab):
					sh=G_st-B.start;B.start=G_st;B.end=G_en;B.track=target_track
					if not is_ass_tab:
						for tf in B.target_frames:tf.time+=sh
				elif not A.main_window.check_overlap(G_st,G_en,B.track,A.dragging_rec_idx,is_ass=is_ass_tab):
					sh=G_st-B.start;B.start=G_st;B.end=G_en
					if not is_ass_tab:
						for tf in B.target_frames:tf.time+=sh
				elif not A.main_window.check_overlap(B.start,B.end,target_track,A.dragging_rec_idx,is_ass=is_ass_tab):B.track=target_track
			elif A.dragging_mode=='resize-start':
				G_st=max(.0,min(A.drag_init_en-.1,A.drag_init_st+D))
				if not A.main_window.check_overlap(G_st,B.end,B.track,A.dragging_rec_idx,is_ass=is_ass_tab):
					B.start=G_st
					if not is_ass_tab and B.target_frames:B.target_frames[0].time=B.start
			elif A.dragging_mode=='resize-end':
				G_en=max(A.drag_init_st+.1,min(dur,A.drag_init_en+D))
				if not A.main_window.check_overlap(B.start,G_en,B.track,A.dragging_rec_idx,is_ass=is_ass_tab):
					B.end=G_en
					if not is_ass_tab and B.target_frames:B.target_frames[-1].time=B.end
			A.main_window.sync_data_to_widgets()
		elif A.drag_start_x is not None:A.offset_x+=C-A.drag_start_x;A.drag_start_x=C
		else:
			H_found=False;L=E.pos().y()
			is_ass_tab=(A.main_window.right_tabs.currentIndex()==1)
			items=A.main_window.data.texts if is_ass_tab else A.main_window.data.polygons
			for(M,B)in enumerate(items):
				I=60+B.track*(F_h+4);N=int(B.start*A.zoom_level+A.offset_x);O=int(B.end*A.zoom_level+A.offset_x)
				if I<=L<=I+F_h and(abs(C-N)<8 or abs(C-O)<8):H_found=True
			A.setCursor(Qt.CursorShape.SizeHorCursor if H_found else Qt.CursorShape.ArrowCursor)
		A.update()
	def mouseDoubleClickEvent(A,event):
		if event.button()==Qt.MouseButton.LeftButton:
			C,L=event.pos().x(),event.pos().y();H=(C-A.offset_x)/A.zoom_level;track=max(0,int((L-60)/28));found=False
			for idx,poly in enumerate(A.main_window.data.polygons):
				if poly.track==track and poly.start<=H<=poly.end:
					found=True
					if A.main_window.current_tool=='B':A.main_window.cut_at_time(idx,H)
					break
			if not found:A.main_window.set_selected_rec(-1)
	def leaveEvent(A,event):A.hover_x=-1;A.update()
	def wheelEvent(A,event):
		B=event;C=B.angleDelta().y();D=B.modifiers();E=B.position().x()
		if D==Qt.KeyboardModifier.ControlModifier:F_val=(E-A.offset_x)/A.zoom_level;A.zoom_level=max(1.,min(1e3,A.zoom_level*(1.15 if C>0 else .85)));A.offset_x=int(E-F_val*A.zoom_level)
		elif D==Qt.KeyboardModifier.AltModifier:A.offset_x+=int(C*.5)
		else:A.offset_x+=int(C*.2)
		A.update()
class ClickableListWidget(QListWidget):
	def __init__(A,mw):super().__init__();A.mw=mw;A.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
	def mousePressEvent(A,event):
		if event.button()==Qt.MouseButton.RightButton:A.clearSelection();A.mw.selected_recs=set();A.mw.selected_rec_idx=-1;A.mw.sync_data_to_widgets()
		else:super().mousePressEvent(event)
class InteractiveTextItem(QGraphicsSimpleTextItem):
	def __init__(A,text,idx,mw):
		super().__init__(text);A.idx=idx;A.mw=mw;A._resizing=False;A._drag_start=None;A._start_w=0
		A.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable|QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
		A.setCursor(Qt.CursorShape.SizeAllCursor);A.setZValue(6)
	def _get_lines_and_path(A,font,st):
		fm=QFontMetrics(font);text=A.text();wrap=st.get('wrap',False);wrap_w=st.get('wrap_w',0)
		lines=[]
		if wrap and wrap_w>0:
			words=text.split(' ')
			cur=""
			for w in words:
				test=f"{cur} {w}".strip()
				if fm.horizontalAdvance(test)<=wrap_w or not cur:cur=test
				else:lines.append(cur);cur=w
			if cur:lines.append(cur)
		else:lines=text.split('\n')
		path=QPainterPath();y=fm.ascent();lh=fm.lineSpacing()
		for i,line in enumerate(lines):path.addText(0,y+i*lh,font,line)
		return lines,path
	def text_rect(A):
		if not(0<=A.idx<len(A.mw.data.texts)):return super().boundingRect()
		txt_obj=A.mw.data.texts[A.idx];st=A.mw.ensure_style_dict(txt_obj.style_ass)
		f=A.font();lines,path=A._get_lines_and_path(f,st)
		return path.boundingRect()
	def boundingRect(A):
		r=A.text_rect()
		if not(0<=A.idx<len(A.mw.data.texts)):return r
		st=A.mw.ensure_style_dict(A.mw.data.texts[A.idx].style_ass)
		pad=max(5.0,st.get('borderw',1.0)+st.get('shadow',2.0)+st.get('glow',0.0))
		return r.adjusted(-pad,-pad,pad,pad)
	def paint(A,painter,option,widget):
		if not(0<=A.idx<len(A.mw.data.texts)):return
		txt_obj=A.mw.data.texts[A.idx];st=A.mw.ensure_style_dict(txt_obj.style_ass)
		f=A.font()
		f.setBold(st.get('bold',False));f.setItalic(st.get('italic',False))
		f.setUnderline(st.get('underline',False));f.setStrikeOut(st.get('strikeout',False))
		f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,st.get('spacing',0.0))
		painter.setFont(f)
		lines,path=A._get_lines_and_path(f,st)
		rect=path.boundingRect()
		scx=st.get('scalex',100)/100.0;scy=st.get('scaley',100)/100.0
		if scx!=1.0 or scy!=1.0:painter.save();painter.scale(scx,scy)
		borderw=st.get('borderw',0.0);shadow=st.get('shadow',0.0);borderstyle=st.get('borderstyle',1);glow=st.get('glow',0.0)
		pad=max(5.0,borderw+shadow+glow)
		bg_rect=rect.adjusted(-pad,-pad,pad,pad)
		if borderstyle==3:
			bg_color=QColor(st.get('backcolor','#00E6FF'))
			painter.fillRect(bg_rect,QBrush(bg_color))
		if glow>0:
			glow_col=QColor(st.get('glowcolor','#00FFFF'))
			painter.save()
			for g in range(int(glow),0,-1):
				glow_col.setAlpha(int(150/max(1,glow)))
				pen=QPen(glow_col,borderw*2+g*2,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)
				painter.setPen(pen);painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawPath(path)
			painter.restore()
		if shadow>0:
			sh_color=QColor(st.get('shadowcolor','#000000'))
			painter.save();painter.translate(shadow,shadow)
			if borderw>0:
				pen=QPen(sh_color,borderw*2,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)
				painter.setPen(pen);painter.setBrush(QBrush(sh_color));painter.drawPath(path)
			else:
				painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QBrush(sh_color));painter.drawPath(path)
			painter.restore()
		if borderw>0:
			out_color=QColor(st.get('bordercolor','#FFFFFF'))
			painter.save()
			pen=QPen(out_color,borderw*2,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)
			painter.setPen(pen);painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawPath(path)
			painter.restore()
		pri_color=QColor(st.get('color','#ffc300'))
		painter.save();painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QBrush(pri_color));painter.drawPath(path);painter.restore()
		if scx!=1.0 or scy!=1.0:painter.restore()
		if A.idx==A.mw.selected_text_idx:
			painter.save()
			painter.setPen(QPen(QColor(0,255,255),1.0,Qt.PenStyle.DashLine))
			painter.setBrush(Qt.BrushStyle.NoBrush)
			painter.drawRect(bg_rect)
			painter.setPen(QPen(QColor(0,255,255),1.0))
			painter.setBrush(QBrush(QColor(255,255,255)))
			painter.drawEllipse(QPointF(bg_rect.right(),bg_rect.center().y()),4,4)
			painter.restore()
	def itemChange(A,change,value):
		if change==QGraphicsItem.GraphicsItemChange.ItemPositionChange and A.isVisible() and not A.mw.updating_poly and not A._resizing:
			if not(0<=A.idx<len(A.mw.data.texts)):return super().itemChange(change,value)
			C=max(1e-06,A.mw.image_scale);txt_obj=A.mw.data.texts[A.idx];st=A.mw.ensure_style_dict(txt_obj.style_ass)
			align_val=st.get('align',2);br=A.text_rect()
			offset_x=0.0 if align_val in(1,4,7) else(br.width()/2.0 if align_val in(2,5,8) else br.width())
			offset_y=br.height() if align_val in(1,2,3) else(br.height()/2.0 if align_val in(4,5,6) else 0.0)
			txt_obj.x=int((value.x()+offset_x)/C);txt_obj.y=int((value.y()+offset_y)/C)
			if A.idx==A.mw.selected_text_idx:
				A.mw.spin_ass_x.blockSignals(True);A.mw.spin_ass_y.blockSignals(True)
				A.mw.spin_ass_x.setValue(txt_obj.x);A.mw.spin_ass_y.setValue(txt_obj.y)
				A.mw.spin_ass_x.blockSignals(False);A.mw.spin_ass_y.blockSignals(False)
		return super().itemChange(change,value)
	def mousePressEvent(A,event):
		A.mw.save_state();A.mw.set_selected_text_idx(A.idx)
		if 0<=A.idx<len(A.mw.data.texts):
			st=A.mw.ensure_style_dict(A.mw.data.texts[A.idx].style_ass)
			br=A.boundingRect()
			if abs(event.pos().x()-br.right())<15:
				A._resizing=True;A._drag_start=event.scenePos()
				A._start_w=st.get('wrap_w',0) or int(br.width())
				event.accept();return
		super().mousePressEvent(event)
	def mouseMoveEvent(A,event):
		if A._resizing and 0<=A.idx<len(A.mw.data.texts):
			diff=(event.scenePos().x()-A._drag_start.x())/max(1e-06,A.mw.image_scale)
			new_w=max(20,int(A._start_w+diff))
			st=A.mw.ensure_style_dict(A.mw.data.texts[A.idx].style_ass)
			st['wrap_w']=new_w;st['wrap']=True
			A.mw.data.texts[A.idx].style_ass=st
			A.mw.spin_ass_w.blockSignals(True);A.mw.spin_ass_w.setValue(new_w);A.mw.spin_ass_w.blockSignals(False)
			A.mw.sync_data_to_widgets();event.accept();return
		super().mouseMoveEvent(event)
	def mouseReleaseEvent(A,event):
		if A._resizing:A._resizing=False;event.accept();return
		super().mouseReleaseEvent(event);A.mw.sync_data_to_widgets()
class DropButton(QPushButton):
	def __init__(A,text='',parent=None,callback=None,exts=()):
		super().__init__(text,parent);A.cb=callback;A.exts=exts;A.setAcceptDrops(True)
	def dragEnterEvent(A,e):
		if e.mimeData().hasUrls():
			for u in e.mimeData().urls():
				if not A.exts or u.toLocalFile().lower().endswith(A.exts):e.acceptProposedAction();return
	def dragMoveEvent(A,e):
		if e.mimeData().hasUrls():e.acceptProposedAction()
	def dropEvent(A,e):
		if e.mimeData().hasUrls():
			for u in e.mimeData().urls():
				fp=u.toLocalFile()
				if not A.exts or fp.lower().endswith(A.exts):
					if A.cb:A.cb(fp)
					break
		e.acceptProposedAction()
class AutoDesubPanel(QWidget):
	def __init__(A,mw):
		super().__init__();A.mw=mw;L=QVBoxLayout(A);L.setContentsMargins(4,4,4,4);L.setSpacing(6);L.addWidget(QLabel('De-subtitles'))
		mw.btn_import_trans=mdl.cre(DropButton('Import transcribe.json',callback=mw.import_transcribe,exts=('.json',)),F.no_focus,style='background-color: #1a5f7a; border: 1px solid #00f7ff; padding: 5px;');mw.btn_import_trans.clicked.connect(lambda:mw.import_transcribe());L.addWidget(mw.btn_import_trans)
		H_range=QHBoxLayout();H_range.addWidget(QLabel('Range overlay:'));H_range=QHBoxLayout();H_range.addWidget(QLabel('Range overlay:'));H_range.addWidget(QLabel('Set AREA:'));combo_ass_key=QComboBox();combo_ass_key.setStyleSheet('background-color:#333');H_range.addWidget(combo_ass_key);combo_ass_key.addItems(list(AREA.__members__.keys()));combo_ass_key.currentIndexChanged.connect(lambda: mw.set_area_desub_video(AREA[combo_ass_key.currentText()]));btn_reset=mdl.cre(QPushButton('Reset (Full)'),F.no_focus,style='background-color: #333; padding: 2px;');btn_reset.clicked.connect(lambda: mw.set_area_desub_video());H_range.addWidget(btn_reset);L.addLayout(H_range)
		mw.range_spins=[]
		for b in range(4):
			G=QHBoxLayout();I=mdl.cre(QSpinBox(),range=(-9999,9999),val=int(mw.range_points[b].x));I.valueChanged.connect(mw.on_range_spins_changed)
			J=mdl.cre(QSpinBox(),range=(-9999,9999),val=int(mw.range_points[b].y));J.valueChanged.connect(mw.on_range_spins_changed)
			G.addWidget(QLabel(f"p{b+1} x:"));G.addWidget(I);G.addWidget(QLabel('y:'));G.addWidget(J);L.addLayout(G);mw.range_spins.append((I,J))
		H_pad=QHBoxLayout();mw.spin_pad=mdl.cre(QDoubleSpinBox(),range=(.0,500.),val=.0);mw.txt_lang=QLineEdit(S.easyocr_reader);H_pad.addWidget(QLabel('Padding:'));H_pad.addWidget(mw.spin_pad);H_pad.addWidget(QLabel('Lang:'));H_pad.addWidget(mw.txt_lang);L.addLayout(H_pad)
		H_add=QHBoxLayout();mw.spin_add_st=mdl.cre(QDoubleSpinBox(),range=(.0,100.),val=.25);mw.spin_add_en=mdl.cre(QDoubleSpinBox(),range=(.0,100.),val=.25);mw.chk_use_text=QCheckBox('Use text');mw.chk_use_text.setChecked(False);H_add.addWidget(QLabel('Add time: start'));H_add.addWidget(mw.spin_add_st);H_add.addWidget(QLabel('end'));H_add.addWidget(mw.spin_add_en);H_add.addWidget(mw.chk_use_text);L.addLayout(H_add)
		H_btn=QHBoxLayout();mw.btn_start_all=mdl.cre(QPushButton('Start all'),F.no_focus);mw.btn_start_all.clicked.connect(mw.start_auto_desub_all);mw.btn_start_max=mdl.cre(QPushButton('Start max'),F.no_focus);mw.btn_start_max.clicked.connect(lambda:mw.start_auto_desub(True));mw.btn_start=mdl.cre(QPushButton('Start'),F.no_focus);mw.btn_start.clicked.connect(lambda:mw.start_auto_desub(False));mw.btn_stop=mdl.cre(QPushButton('Stop'),F.no_focus);mw.btn_stop.clicked.connect(mw.stop_auto_desub);mw.btn_clear=mdl.cre(QPushButton('Clear'),F.no_focus);mw.btn_clear.clicked.connect(mw.clear_transcribe);H_btn.addWidget(mw.btn_start_all);H_btn.addWidget(mw.btn_start_max);H_btn.addWidget(mw.btn_start);H_btn.addWidget(mw.btn_stop);H_btn.addWidget(mw.btn_clear);L.addLayout(H_btn)
		mw.prog_bar=mdl.cre(QProgressBar(),range=(0,100),val=0);L.addWidget(mw.prog_bar)
		S_line=QFrame();S_line.setFrameShape(QFrame.Shape.HLine);S_line.setStyleSheet('background-color: #333;');L.addWidget(S_line)
		H_json_btns=QHBoxLayout()
		mw.btn_import_json=mdl.cre(DropButton('Import blurs.json',callback=mw.import_json,exts=('.json',)),F.no_focus,style='background-color: #ffa600; border: 1px solid #00f7ff; padding: 5px;');mw.btn_import_json.clicked.connect(lambda:mw.import_json());H_json_btns.addWidget(mw.btn_import_json)
		L.addLayout(H_json_btns)
		mw.lbl_active_rec=QLabel('Active RecLine [None]');L.addWidget(mw.lbl_active_rec)
		mw.rec_list=ClickableListWidget(mw);mw.rec_list.setStyleSheet('background-color: #1e1e1e; border: 1px solid #00f7ff; max-height: 100px;');mw.rec_list.itemSelectionChanged.connect(mw.on_list_selection_changed);L.addWidget(mw.rec_list)
		F_layout=QHBoxLayout();mw.spin_st=mdl.cre(QDoubleSpinBox(),range=(.0,99999.),step=.1);mw.spin_st.valueChanged.connect(mw.on_spin_times_changed);mw.spin_en=mdl.cre(QDoubleSpinBox(),range=(.0,99999.),step=.1);mw.spin_en.valueChanged.connect(mw.on_spin_times_changed);F_layout.addWidget(QLabel('Start:'));F_layout.addWidget(mw.spin_st);F_layout.addWidget(QLabel('End:'));F_layout.addWidget(mw.spin_en);L.addLayout(F_layout)
		mw.tab_widget=QTabWidget();L.addWidget(mw.tab_widget)
		mw.tab_pts_widget=QWidget();layout_pts=QVBoxLayout(mw.tab_pts_widget);layout_pts.setContentsMargins(0,4,0,4);mw.point_spins=[]
		for b in range(4):
			G=QHBoxLayout();I=mdl.cre(QSpinBox(),range=(-9999,9999),val=int(mw.range_points[b].x));I.valueChanged.connect(mw.on_spin_points_changed)
			J=mdl.cre(QSpinBox(),range=(-9999,9999),val=int(mw.range_points[b].y));J.valueChanged.connect(mw.on_spin_points_changed)
			G.addWidget(QLabel(f"p{b+1} x:"));G.addWidget(I);G.addWidget(QLabel('y:'));G.addWidget(J);layout_pts.addLayout(G);mw.point_spins.append((I,J))
		mw.tab_widget.addTab(mw.tab_pts_widget,'Points')
		mw.tab_tf_widget=QWidget();layout_tf=QVBoxLayout(mw.tab_tf_widget);layout_tf.setContentsMargins(0,4,0,4);mw.tf_list=QListWidget();mw.tf_list.setStyleSheet('background-color: #1e1e1e; border: 1px solid #00f7ff; max-height: 80px;');mw.tf_list.currentRowChanged.connect(mw.on_tf_select);layout_tf.addWidget(mw.tf_list)
		H_tf_btn=QHBoxLayout();mw.btn_add_tf=mdl.cre(QPushButton('Add TF'),F.no_focus);mw.btn_add_tf.clicked.connect(mw.add_target_frame);mw.btn_del_tf=mdl.cre(QPushButton('Del TF'),F.no_focus);mw.btn_del_tf.clicked.connect(mw.delete_target_frame);H_tf_btn.addWidget(mw.btn_add_tf);H_tf_btn.addWidget(mw.btn_del_tf);layout_tf.addLayout(H_tf_btn)
		H_tf_se=QHBoxLayout();mw.spin_tf_st=mdl.cre(QDoubleSpinBox(),range=(0.0,99999.0),step=0.1);mw.spin_tf_en=mdl.cre(QDoubleSpinBox(),range=(0.0,99999.0),step=0.1);mw.spin_tf_en.valueChanged.connect(mw.on_tf_spins_changed);H_tf_se.addWidget(QLabel('Time:'));H_tf_se.addWidget(mw.spin_tf_en);layout_tf.addLayout(H_tf_se)
		H_tf_xy=QHBoxLayout();mw.spin_tf_x=mdl.cre(QSpinBox(),range=(-9999,9999));mw.spin_tf_x.valueChanged.connect(mw.on_tf_spins_changed);mw.spin_tf_y=mdl.cre(QSpinBox(),range=(-9999,9999));mw.spin_tf_y.valueChanged.connect(mw.on_tf_spins_changed);H_tf_xy.addWidget(QLabel('X:'));H_tf_xy.addWidget(mw.spin_tf_x);H_tf_xy.addWidget(QLabel('Y:'));H_tf_xy.addWidget(mw.spin_tf_y);layout_tf.addLayout(H_tf_xy)
		mw.tab_widget.addTab(mw.tab_tf_widget,'Target_frames')
		H_rec_btns=QHBoxLayout()
		T=mdl.cre(QPushButton('Add Rectangle overlay'),F.no_focus,style='background-color: #1a5f7a; border: 1px solid #00f7ff; padding: 5px;');T.clicked.connect(mw.add_rectangle);H_rec_btns.addWidget(T)
		U=mdl.cre(QPushButton('Delete Selected'),F.no_focus,style='background-color: #d32f2f; border: 1px solid #00f7ff; padding: 5px;');U.clicked.connect(mw.delete_rectangle);H_rec_btns.addWidget(U)
		L.addLayout(H_rec_btns)
		mw.btn_export_json=mdl.cre(QPushButton('Export blurs.json'),F.no_focus,style='background-color: #2e7d32; border: 1px solid #00f7ff; padding: 5px; font-weight: bold;');mw.btn_export_json.clicked.connect(mw.export_json);L.addWidget(mw.btn_export_json)
class SubtitlesPanel(QWidget):
	def __init__(A,mw):
		super().__init__();A.mw=mw;L=QVBoxLayout(A);L.setContentsMargins(4,4,4,4);L.setSpacing(6)
		mw.btn_import_ass_json=mdl.cre(DropButton('Import data.json',callback=mw.import_ass_json,exts=('.json',)),F.no_focus,style='background-color: #1a5f7a; padding: 5px;');mw.btn_import_ass_json.clicked.connect(lambda:mw.import_ass_json());L.addWidget(mw.btn_import_ass_json)
		H_sel=QHBoxLayout();mw.combo_ass_key=QComboBox();mw.combo_ass_key.setStyleSheet('background-color: #333;');H_sel.addWidget(QLabel('Key text:'));H_sel.addWidget(mw.combo_ass_key);L.addLayout(H_sel)
		H_btn_ass=QHBoxLayout();mw.btn_start_ass=mdl.cre(QPushButton('Start'),F.no_focus);mw.btn_start_ass.clicked.connect(mw.start_ass_process);mw.btn_stop_ass=mdl.cre(QPushButton('Stop'),F.no_focus);mw.btn_stop_ass.clicked.connect(mw.stop_ass_process);mw.btn_clear_ass=mdl.cre(QPushButton('Clear'),F.no_focus);mw.btn_clear_ass.clicked.connect(mw.clear_ass_data);H_btn_ass.addWidget(mw.btn_start_ass);H_btn_ass.addWidget(mw.btn_stop_ass);H_btn_ass.addWidget(mw.btn_clear_ass);L.addLayout(H_btn_ass)
		mw.ass_list=QListWidget();mw.ass_list.setStyleSheet('background-color: #1e1e1e; border: 1px solid #00f7ff; max-height: 120px;');mw.ass_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection);mw.ass_list.itemSelectionChanged.connect(mw.on_ass_list_selection_changed);L.addWidget(mw.ass_list)
		H_add_del=QHBoxLayout();mw.btn_add_ass=QPushButton('Add text');mw.btn_add_ass.clicked.connect(mw.add_ass_text);mw.btn_del_ass=QPushButton('Delete text');mw.btn_del_ass.clicked.connect(mw.delete_ass_text);H_add_del.addWidget(mw.btn_add_ass);H_add_del.addWidget(mw.btn_del_ass);L.addLayout(H_add_del)
		H_se_ass=QHBoxLayout();mw.spin_ass_st=mdl.cre(QDoubleSpinBox(),range=(0.0,99999.0),step=0.1);mw.spin_ass_st.valueChanged.connect(mw.on_ass_spins_changed);mw.spin_ass_en=mdl.cre(QDoubleSpinBox(),range=(0.0,99999.0),step=0.1);mw.spin_ass_en.valueChanged.connect(mw.on_ass_spins_changed);H_se_ass.addWidget(QLabel('Start:'));H_se_ass.addWidget(mw.spin_ass_st);H_se_ass.addWidget(QLabel('End:'));H_se_ass.addWidget(mw.spin_ass_en);L.addLayout(H_se_ass)
		H_wh_ass=QHBoxLayout();mw.spin_ass_w=mdl.cre(QSpinBox(),range=(0,9999),val=0);mw.spin_ass_w.valueChanged.connect(mw.on_ass_spins_changed);mw.spin_ass_h=mdl.cre(QSpinBox(),range=(0,9999),val=0);mw.spin_ass_h.setEnabled(False);H_wh_ass.addWidget(QLabel('W:'));H_wh_ass.addWidget(mw.spin_ass_w);H_wh_ass.addWidget(QLabel('H:'));H_wh_ass.addWidget(mw.spin_ass_h);L.addLayout(H_wh_ass)
		H_xy_ass=QHBoxLayout();mw.spin_ass_x=mdl.cre(QSpinBox(),range=(-9999,9999));mw.spin_ass_x.valueChanged.connect(mw.on_ass_spins_changed);mw.spin_ass_y=mdl.cre(QSpinBox(),range=(-9999,9999));mw.spin_ass_y.valueChanged.connect(mw.on_ass_spins_changed);H_xy_ass.addWidget(QLabel('X:'));H_xy_ass.addWidget(mw.spin_ass_x);H_xy_ass.addWidget(QLabel('Y:'));H_xy_ass.addWidget(mw.spin_ass_y);L.addLayout(H_xy_ass)
		H_txt_ass=QHBoxLayout();mw.txt_ass_content=QLineEdit();mw.txt_ass_content.textChanged.connect(mw.on_ass_text_changed);H_txt_ass.addWidget(QLabel('Text:'));H_txt_ass.addWidget(mw.txt_ass_content);L.addLayout(H_txt_ass)
		H_style_top=QHBoxLayout();mw.txt_ass_font=QComboBox();mw.txt_ass_font.setEditable(True);mw.txt_ass_font.addItems(QFontDatabase.families());mw.txt_ass_font.currentTextChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.spin_font_size=mdl.cre(QSpinBox(),range=(1,200),val=69);mw.spin_font_size.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());H_style_top.addWidget(QLabel('Font:'));H_style_top.addWidget(mw.txt_ass_font,stretch=2);H_style_top.addWidget(QLabel('Sz:'));H_style_top.addWidget(mw.spin_font_size,stretch=1);L.addLayout(H_style_top)
		H_decor=QHBoxLayout();mw.chk_bold=QCheckBox('Bold');mw.chk_italic=QCheckBox('Ital');mw.chk_underline=QCheckBox('Und');mw.chk_strikeout=QCheckBox('Strk');mw.chk_wrap=QCheckBox('Wrap');mw.chk_bold.stateChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.chk_italic.stateChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.chk_underline.stateChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.chk_strikeout.stateChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.chk_wrap.stateChanged.connect(lambda:mw.on_ass_style_ui_changed());H_decor.addWidget(mw.chk_bold);H_decor.addWidget(mw.chk_italic);H_decor.addWidget(mw.chk_underline);H_decor.addWidget(mw.chk_strikeout);H_decor.addWidget(mw.chk_wrap);L.addLayout(H_decor)
		H_color_pri_out=QHBoxLayout();mw.btn_color_pri=QPushButton('Pri');mw.btn_color_pri.clicked.connect(lambda:mw.pick_color(3));mw.chk_is_outer=QCheckBox('Out');mw.chk_is_outer.stateChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.btn_color_out=QPushButton('Color');mw.btn_color_out.clicked.connect(lambda:mw.pick_color(4));mw.spin_outline_size=mdl.cre(QDoubleSpinBox(),range=(0.0,50.0),val=3.0);mw.spin_outline_size.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());H_color_pri_out.addWidget(QLabel('Pri:'));H_color_pri_out.addWidget(mw.btn_color_pri);H_color_pri_out.addWidget(mw.chk_is_outer);H_color_pri_out.addWidget(mw.btn_color_out);H_color_pri_out.addWidget(mw.spin_outline_size);L.addLayout(H_color_pri_out)
		H_color_back=QHBoxLayout();mw.chk_is_bg=QCheckBox('BgBox');mw.chk_is_bg.stateChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.btn_color_back=QPushButton('Color');mw.btn_color_back.clicked.connect(lambda:mw.pick_color(5));mw.chk_is_shadow=QCheckBox('Shd');mw.chk_is_shadow.stateChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.btn_color_shadow=QPushButton('Color');mw.btn_color_shadow.clicked.connect(lambda:mw.pick_color(6));mw.spin_shadow_size=mdl.cre(QDoubleSpinBox(),range=(0.0,50.0),val=2.0);mw.spin_shadow_size.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());H_color_back.addWidget(mw.chk_is_bg);H_color_back.addWidget(mw.btn_color_back);H_color_back.addWidget(mw.chk_is_shadow);H_color_back.addWidget(mw.btn_color_shadow);H_color_back.addWidget(mw.spin_shadow_size);L.addLayout(H_color_back)
		H_scale=QHBoxLayout();mw.spin_scalex=mdl.cre(QSpinBox(),range=(1,500),val=100);mw.spin_scalex.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.spin_scaley=mdl.cre(QSpinBox(),range=(1,500),val=100);mw.spin_scaley.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());H_scale.addWidget(QLabel('ScX:'));H_scale.addWidget(mw.spin_scalex);H_scale.addWidget(QLabel('ScY:'));H_scale.addWidget(mw.spin_scaley);L.addLayout(H_scale)
		H_space=QHBoxLayout();mw.spin_spacing=mdl.cre(QDoubleSpinBox(),range=(-100.0,100.0),val=0.0);mw.spin_spacing.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.spin_angle=mdl.cre(QDoubleSpinBox(),range=(-360.0,360.0),val=0.0);mw.spin_angle.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());H_space.addWidget(QLabel('Spc:'));H_space.addWidget(mw.spin_spacing);H_space.addWidget(QLabel('Ang:'));H_space.addWidget(mw.spin_angle);L.addLayout(H_space)
		H_align_enc=QHBoxLayout();mw.spin_align_val=mdl.cre(QSpinBox(),range=(1,9),val=2);mw.spin_align_val.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.spin_enc=mdl.cre(QSpinBox(),range=(0,255),val=1);mw.spin_enc.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());H_align_enc.addWidget(QLabel('Align:'));H_align_enc.addWidget(mw.spin_align_val);H_align_enc.addWidget(QLabel('Enc:'));H_align_enc.addWidget(mw.spin_enc);L.addLayout(H_align_enc)
		H_margins=QHBoxLayout();mw.spin_ml=mdl.cre(QSpinBox(),range=(0,999),val=0);mw.spin_ml.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.spin_mr=mdl.cre(QSpinBox(),range=(0,999),val=0);mw.spin_mr.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());mw.spin_mv=mdl.cre(QSpinBox(),range=(0,999),val=0);mw.spin_mv.valueChanged.connect(lambda:mw.on_ass_style_ui_changed());H_margins.addWidget(QLabel('ML:'));H_margins.addWidget(mw.spin_ml);H_margins.addWidget(QLabel('MR:'));H_margins.addWidget(mw.spin_mr);H_margins.addWidget(QLabel('MV:'));H_margins.addWidget(mw.spin_mv);L.addLayout(H_margins)
		H_action_btns1=QHBoxLayout();mw.btn_apply_all_ass=mdl.cre(QPushButton('Apply to all'),style='background-color: #FFA600; font-weight: bold; padding: 4px; border: 1px solid #00f7ff;');mw.btn_apply_all_ass.clicked.connect(mw.apply_style_to_all);H_action_btns1.addWidget(mw.btn_apply_all_ass);mw.btn_export_ass=mdl.cre(QPushButton('Export to ASS'),style='background-color: #2e7d32; font-weight: bold; padding: 4px; border: 1px solid #00f7ff;');mw.btn_export_ass.clicked.connect(mw.export_ass_file);H_action_btns1.addWidget(mw.btn_export_ass);L.addLayout(H_action_btns1)
		H_action_btns2=QHBoxLayout();mw.btn_import_ass_json_data=mdl.cre(DropButton('Import ass_data.json',callback=mw.import_ass_data_json,exts=('.json',)),style='background-color: #1a5f7a; padding: 4px;border: 1px solid #00f7ff;');mw.btn_import_ass_json_data.clicked.connect(lambda:mw.import_ass_data_json());H_action_btns2.addWidget(mw.btn_import_ass_json_data);mw.btn_export_ass_json_data=mdl.cre(QPushButton('Export ass_data.json'),style='background-color: #8d6e63; padding: 4px;border: 1px solid #00f7ff;');mw.btn_export_ass_json_data.clicked.connect(mw.export_ass_data_json);H_action_btns2.addWidget(mw.btn_export_ass_json_data);L.addLayout(H_action_btns2)
class CanvasItems:
	@staticmethod
	def get_rect_pts(pts):return [Point(p.x, p.y) for p in pts]
class TimelineViews:
	@staticmethod
	def setup_view(view, scene):view.setScene(scene);view.setAlignment(Qt.AlignmentFlag.AlignCenter)
class SidePanels:
	@staticmethod
	def configure_tab(tabs, widget, title):tabs.addTab(widget, title)
class CoreData:
	@staticmethod
	def create_default_style():
		return {
			'font':'Cambria','size':69,'color':'#ffc300','bordercolor':"#000000",'backcolor':'#00E6FF','shadowcolor':'#000000',
			'bold':False,'italic':False,'underline':False,'strikeout':False,
			'scalex':100,'scaley':100,'spacing':0.0,'angle':0.0,
			'borderstyle':1,'borderw':1.0,'shadow':2.0,
			'align':2,'margin_l':10,'margin_r':10,'margin_v':10,'encoding':1,
			'wrap':False,'wrap_w':300,'glow':0.0,'glowcolor':"#FBFF00"
		}

from enum import Enum
class AREA(Enum):
    TOP = ("TOP", 0.25)
    BOTTOM = ("BOTTOM", 0.25)
    MID = ("MID", 0.5)
    LEFT = ("LEFT", 0.5)
    RIGHT = ("RIGHT", 0.5)
    DEFAULT = ("DEFAULT", 1.0)
class MainWindow(QMainWindow):
	def __init__(A):
		super().__init__();A.setWindowTitle('Pro Canvas Editor & Timeline');A.resize(1350,800);A.data=Data();A.selected_rec_idx=-1;A.selected_recs=set();A.copied_recs=[];A.current_tool='V';A.updating_poly=False;A.debug_actions=True;A.media_path='';A.is_video=False;A.image_bg=None;A.current_frame_img=None;A.needs_centering=True;A.frame_counter=0;A.player=QMediaPlayer();A.audio_output=QAudioOutput();A.player.setAudioOutput(A.audio_output);A.video_sink=QVideoSink();A.player.setVideoSink(A.video_sink);A.video_sink.videoFrameChanged.connect(A.on_frame_changed);A.player.positionChanged.connect(A.on_position_changed);A.player.durationChanged.connect(A.on_duration_changed);A.scene=QGraphicsScene();A.bg_item=QGraphicsPixmapItem();A.scene.addItem(A.bg_item);A.media_orig_size=0,0;A.image_scale=1.;A.recline_focus_item=RecLineFocusItem(A);A.scene.addItem(A.recline_focus_item);A.active_poly_item=InteractivePolygonItem(A);A.scene.addItem(A.active_poly_item);A.range_poly_item=InteractiveRangePolygonItem(A);A.scene.addItem(A.range_poly_item);A.range_handles=[];A.range_points=[Point(100.,600.),Point(1180.,600.),Point(1180.,700.),Point(100.,700.)];A.transcribe_data=None;A.undo_stack=[];A.redo_stack=[];A.auto_desub_running=False;A.block_tf_seek=False;A.selected_text_idx=-1;A.selected_texts=set()
		A.active_color_pri='#ffc300';A.active_color_out='#FFFFFF';A.active_color_back='#00E6FF'
		for b in range(4):H=RangeHandleItem(b,A);H.setVisible(False);A.scene.addItem(H);A.range_handles.append(H)
		A.handles=[];A.temp_poly_items=[];A.init_ui();A.sync_data_to_widgets()
	def save_state(A):
		state=(copy.deepcopy(A.data),copy.deepcopy(A.range_points),A.selected_rec_idx,set(A.selected_recs))
		A.undo_stack.append(state)
		if len(A.undo_stack)>20:A.undo_stack.pop(0)
		A.redo_stack.clear()
	def undo(A):
		if not A.undo_stack:return
		curr=(copy.deepcopy(A.data),copy.deepcopy(A.range_points),A.selected_rec_idx,set(A.selected_recs))
		A.redo_stack.append(curr)
		prev=A.undo_stack.pop();A.restore_state(prev)
	def redo(A):
		if not A.redo_stack:return
		curr=(copy.deepcopy(A.data),copy.deepcopy(A.range_points),A.selected_rec_idx,set(A.selected_recs))
		A.undo_stack.append(curr)
		if len(A.undo_stack)>20:A.undo_stack.pop(0)
		nxt=A.redo_stack.pop();A.restore_state(nxt)
	def restore_state(A,state):
		A.data,A.range_points,A.selected_rec_idx,A.selected_recs=state
		A.sync_range_spins();A.sync_data_to_widgets()
	def show_clone_dialog(A,idx):
		from PyQt6.QtWidgets import QInputDialog
		dur=A.get_duration() or 100.
		val,ok=QInputDialog.getDouble(A,"Clone Target Frames","Duration (s):",dur,.1,99999.,3)
		if ok:A.clone_target_frames(idx,val)
	def clone_target_frames(A,idx,target_dur):
		if not(0<=idx<len(A.data.polygons)):return
		rec=A.data.polygons[idx]
		if not rec.target_frames:return
		tfs=sorted(rec.target_frames,key=lambda x:x.time);min_t=tfs[0].time;max_t=tfs[-1].time;cycle_len=max_t-min_t
		if cycle_len<=0:return
		base_times=[f.time for f in tfs];T=[];k=0
		while True:
			cycle_times=[t+k*cycle_len for t in base_times]
			for t in cycle_times:
				if t>=target_dur:break
				T.append(t)
			else:k+=1;continue
			break
		if T and T[-1]<target_dur:T.append(target_dur)
		M=len(base_times)
		coords=[Point(f.x,f.y)for f in tfs[:M]];new_tfs=[]
		for i in range(len(T)):
			t_val=T[i];c=coords[i%M];new_tfs.append(TargetFrame(x=c.x,y=c.y,time=t_val))
		A.save_state()
		rec.target_frames=new_tfs;rec.start=rec.start;rec.end=max(f.time for f in rec.target_frames);A.sync_data_to_widgets()
	def set_area_desub_video(A, area=AREA.DEFAULT):
		A.save_state(); w, h = A._image_size()
		if w <= 1 or h <= 1: w, h = 1280, 720
		w, h = float(w), float(h)
		ratio = float(area.value[1] if isinstance(area.value, tuple) else area.value)
		if area == AREA.TOP: x1, y1 = .0, .0; x2, y2 = w, h * ratio
		elif area == AREA.BOTTOM: x1, y1 = .0, h * (1. - ratio); x2, y2 = w, h
		elif area == AREA.MID: offset = (1. - ratio) / 2.; x1, y1 = .0, h * offset; x2, y2 = w, h * (offset + ratio)
		elif area == AREA.LEFT: x1, y1 = .0, .0; x2, y2 = w * ratio, h
		elif area == AREA.RIGHT: x1, y1 = w * (1. - ratio), .0; x2, y2 = w, h
		else: x1, y1 = .0, .0; x2, y2 = w, h
		A.range_points = [Point(x1, y1), Point(x2, y1), Point(x2, y2), Point(x1, y2)]; A.updating_poly = True; A.update_range_overlay(); A.updating_poly = False; A.sync_range_spins()
	def run_command(A,action_name,*args,**kwargs):
		method=getattr(A,action_name,None)
		if method and callable(method):return method(*args,**kwargs)
		return None
	def on_ass_list_selection_changed(A):
		if A.updating_poly:return
		rows=[A.ass_list.row(item)for item in A.ass_list.selectedItems()]
		if rows:
			r=rows[0]
			if r<len(A.data.texts):
				target_poly=A.data.texts[r]
				A.spin_ass_st.blockSignals(True);A.spin_ass_en.blockSignals(True);A.spin_ass_x.blockSignals(True);A.spin_ass_y.blockSignals(True);A.txt_ass_content.blockSignals(True);A.spin_ass_w.blockSignals(True);A.spin_ass_h.blockSignals(True)
				A.spin_ass_st.setValue(target_poly.start);A.spin_ass_en.setValue(target_poly.end);A.spin_ass_x.setValue(target_poly.x);A.spin_ass_y.setValue(target_poly.y)
				st=A.ensure_style_dict(target_poly.style_ass)
				target_poly.style_ass=st
				wrap_w=st.get('wrap_w',0)
				A.spin_ass_w.setValue(wrap_w)
				for item in A.temp_poly_items:
					if isinstance(item,InteractiveTextItem) and item.idx==r:
						br=item.text_rect()
						A.spin_ass_h.setValue(int(br.height()))
						if wrap_w==0:A.spin_ass_w.setValue(int(br.width()))
						break
				if A.txt_ass_content.text()!=target_poly.text:
					pos=A.txt_ass_content.cursorPosition()
					A.txt_ass_content.setText(target_poly.text)
					A.txt_ass_content.setCursorPosition(min(pos,len(target_poly.text)))
				A.spin_ass_st.blockSignals(False);A.spin_ass_en.blockSignals(False);A.spin_ass_x.blockSignals(False);A.spin_ass_y.blockSignals(False);A.txt_ass_content.blockSignals(False);A.spin_ass_w.blockSignals(False);A.spin_ass_h.blockSignals(False)
				A.block_ass_style_signals(True)
				idx_font=A.txt_ass_font.findText(st.get('font','Cambria'))
				if idx_font!=-1:A.txt_ass_font.setCurrentIndex(idx_font)
				else:A.txt_ass_font.setCurrentText(st.get('font','Cambria'))
				A.spin_font_size.setValue(st.get('size',69))
				A.active_color_pri=st.get('color','#ffc300')
				A.active_color_out=st.get('bordercolor','#FFFFFF')
				A.active_color_back=st.get('backcolor','#00E6FF')
				A.active_color_shadow=st.get('shadowcolor','#000000')
				A.update_color_button_styles(A.active_color_pri,A.active_color_out,A.active_color_back,A.active_color_shadow)
				A.chk_bold.setChecked(st.get('bold',False))
				A.chk_italic.setChecked(st.get('italic',False))
				A.chk_underline.setChecked(st.get('underline',False))
				A.chk_strikeout.setChecked(st.get('strikeout',False))
				A.chk_wrap.setChecked(st.get('wrap',False))
				A.spin_scalex.setValue(st.get('scalex',100))
				A.spin_scaley.setValue(st.get('scaley',100))
				A.spin_spacing.setValue(st.get('spacing',0.0))
				A.spin_angle.setValue(st.get('angle',0.0))
				borderw_val=st.get('borderw',3.0)
				A.chk_is_outer.setChecked(borderw_val>0)
				if borderw_val>0:A.spin_outline_size.setValue(borderw_val)
				shadow_val=st.get('shadow',2.0)
				A.chk_is_shadow.setChecked(shadow_val>0)
				if shadow_val>0:A.spin_shadow_size.setValue(shadow_val)
				borderstyle_val=st.get('borderstyle',1)
				A.chk_is_bg.setChecked(borderstyle_val==3)
				A.spin_align_val.setValue(st.get('align',2))
				A.spin_ml.setValue(st.get('margin_l',10))
				A.spin_mr.setValue(st.get('margin_r',10))
				A.spin_mv.setValue(st.get('margin_v',10))
				A.spin_enc.setValue(st.get('encoding',1))
				A.block_ass_style_signals(False)
				if abs(A.get_current_time()-target_poly.start)>0.05:A.seek_time(target_poly.start)
		A.timeline.update()
		K=A.current_frame_img or A.image_bg
		if K:A.display_image(K)
	def on_ass_style_ui_changed(A):
		rows=[A.ass_list.row(item)for item in A.ass_list.selectedItems()]
		if rows:
			A.save_state()
			for r in rows:
				if r<len(A.data.texts):
					st={
						'font':A.txt_ass_font.currentText() or 'Cambria',
						'size':A.spin_font_size.value(),
						'color':A.ass_color_to_qcolor(getattr(A,'active_color_pri','#ffc300')).name(),
						'bordercolor':A.ass_color_to_qcolor(getattr(A,'active_color_out','#FFFFFF')).name(),
						'backcolor':A.ass_color_to_qcolor(getattr(A,'active_color_back','#00E6FF')).name(),
						'shadowcolor':A.ass_color_to_qcolor(getattr(A,'active_color_shadow','#000000')).name(),
						'bold':A.chk_bold.isChecked(),
						'italic':A.chk_italic.isChecked(),
						'underline':A.chk_underline.isChecked(),
						'strikeout':A.chk_strikeout.isChecked(),
						'wrap':A.chk_wrap.isChecked(),
						'wrap_w':A.spin_ass_w.value(),
						'scalex':A.spin_scalex.value(),
						'scaley':A.spin_scaley.value(),
						'spacing':A.spin_spacing.value(),
						'angle':A.spin_angle.value(),
						'borderstyle':3 if A.chk_is_bg.isChecked() else 1,
						'borderw':A.spin_outline_size.value() if A.chk_is_outer.isChecked() else 0.0,
						'shadow':A.spin_shadow_size.value() if A.chk_is_shadow.isChecked() else 0.0,
						'align':A.spin_align_val.value(),
						'margin_l':A.spin_ml.value(),
						'margin_r':A.spin_mr.value(),
						'margin_v':A.spin_mv.value(),
						'encoding':A.spin_enc.value()
					}
					A.data.texts[r].style_ass=st
			A.sync_data_to_widgets()
	def display_image(A,img):
		if img is None:return
		if A.updating_poly:return
		A.updating_poly=True;D=img;H=QPixmap.fromImage(D);A.bg_item.setPixmap(H);A.bg_item.setPos(0,0);I,J=D.width(),D.height();A.scene.setSceneRect(0,0,I,J)
		if getattr(A,'needs_centering',False):
			try:A.media_view.centerOn(A.bg_item)
			except Exception:pass
			A.needs_centering=False
		M=A.get_current_time()
		for C in A.temp_poly_items:A.scene.removeItem(C)
		A.temp_poly_items.clear();G_found=False
		for(E,B)in enumerate(A.data.polygons):
			if B.start<=M<=B.end:
				rendered_pts=A.get_rendered_pts(B,M)
				if E==A.selected_rec_idx:
					G_found=True;F_poly=QPolygonF([QPointF(p.x*A.image_scale,p.y*A.image_scale)for p in rendered_pts]);A.active_poly_item.setPolygon(F_poly)
					try:A.active_poly_item.idx=E;A.active_poly_item.setZValue(5)
					except Exception:pass
					A.active_poly_item.setVisible(True);A.update_handles_at(rendered_pts)
				else:F_poly=QPolygonF([QPointF(p.x*A.image_scale,p.y*A.image_scale)for p in rendered_pts]);C=ClickablePolyItem(F_poly,E,A);A.scene.addItem(C);A.temp_poly_items.append(C)
		for(E,B)in enumerate(A.data.texts):
			if B.start<=M<=B.end:
				txt_item=InteractiveTextItem(B.text,E,A);st=A.ensure_style_dict(B.style_ass);B.style_ass=st
				f_size=st.get('size',24);f=QFont(st.get('font','Cambria'),int(f_size*A.image_scale))
				f.setBold(st.get('bold',False));f.setItalic(st.get('italic',False))
				f.setUnderline(st.get('underline',False));f.setStrikeOut(st.get('strikeout',False))
				f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,st.get('spacing',0.0))
				txt_item.setFont(f);txt_item.setRotation(st.get('angle',0.0))
				align_val=st.get('align',2);boundingRect=txt_item.text_rect()
				offset_x=0.0 if align_val in(1,4,7) else(boundingRect.width()/2.0 if align_val in(2,5,8) else boundingRect.width())
				offset_y=boundingRect.height() if align_val in(1,2,3) else(boundingRect.height()/2.0 if align_val in(4,5,6) else 0.0)
				txt_item.setPos(B.x*A.image_scale-offset_x,B.y*A.image_scale-offset_y)
				A.scene.addItem(txt_item);A.temp_poly_items.append(txt_item)
		if G_found:
			rec=A.data.polygons[A.selected_rec_idx];rx,ry=A.get_interpolated_pos(rec,M)
			A.recline_focus_item.setPos(rx*A.image_scale,ry*A.image_scale);A.recline_focus_item.setVisible(True)
		else:A.active_poly_item.setVisible(False);A.hide_handles();A.recline_focus_item.setVisible(False)
		A.update_range_overlay();A.updating_poly=False
	def import_ass_data_json(A):
		A.player.stop();E,G=QFileDialog.getOpenFileName(A,'Open ASS Data','','JSON Files (*.json)')
		if E:
			A.save_state()
			with open(E,'r',encoding='utf-8')as F:B=json.load(F)
			A.data.texts=[]
			for item in B or []:
				raw_style=item.get('style_ass',{})
				new_txt=RecLineText(
					start=float(item.get('start',.0)),
					end=float(item.get('end',3.0)),
					text=item.get('text',''),
					x=int(item.get('x',540)),
					y=int(item.get('y',1500)),
					style_ass=A.ensure_style_dict(raw_style),
					track=int(item.get('track',3))
				)
				A.data.texts.append(new_txt)
			A.selected_text_idx=-1;A.selected_texts=set();A.sync_data_to_widgets()
	def export_ass_data_json(A):
		A.player.stop();B,E=QFileDialog.getSaveFileName(A,'Save ASS Data','_ass.json','JSON Files (*.json)')
		if B:
			texts_list=[]
			for t in A.data.texts:
				texts_list.append({
					'start':round(float(t.start),3),
					'end':round(float(t.end),3),
					'text':t.text,
					'x':int(t.x),
					'y':int(t.y),
					'style_ass':A.ensure_style_dict(t.style_ass),
					'track':int(t.track)
				})
			with open(B,'w',encoding='utf-8')as F:json.dump(texts_list,F,indent=4)
	def export_ass_file(A):
		B,E=QFileDialog.getSaveFileName(A,'Save ASS Subtitles','data_ass.ass','ASS Subtitles (*.ass)')
		if B:
			with open(B,'w',encoding='utf-8')as F:
				pw,ph=A.media_orig_size
				if not pw or not ph:pw,ph=1280,720
				wrap_val=0 if A.chk_wrap.isChecked() else 2
				F.write(f"[Script Info]\nTitle: Custom ASS Subtitles\nScriptType: v4.00+\nWrapStyle: {wrap_val}\nPlayResX: {pw}\nPlayResY: {ph}\n\n[V4+ Styles]\n")
				F.write("Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
				unique_styles={};style_idx=0
				def to_ass_color(hex_str):
					h=hex_str.lstrip('#')
					if len(h)==6:r,g,b=h[0:2],h[2:4],h[4:6];a="00"
					elif len(h)==8:r,g,b,a=h[0:2],h[2:4],h[4:6],h[6:8]
					else:return "&H00FFFFFF"
					return f"&H{a}{b}{g}{r}"
				for p in sorted(A.data.texts,key=lambda x:x.start):
					st=A.ensure_style_dict(p.style_ass)
					font=st.get('font','Cambria');size=str(st.get('size',69))
					pri=to_ass_color(st.get('color','#ffc300'));out=to_ass_color(st.get('bordercolor','#FFFFFF'));back=to_ass_color(st.get('backcolor','#00E6FF'))
					bold='-1' if st.get('bold',False) else '0';italic='-1' if st.get('italic',False) else '0'
					underline='-1' if st.get('underline',False) else '0';strike='-1' if st.get('strikeout',False) else '0'
					sx=str(st.get('scalex',100));sy=str(st.get('scaley',100))
					spacing=f"{st.get('spacing',0.0):.2f}".rstrip('0').rstrip('.');angle=f"{st.get('angle',0.0):.2f}".rstrip('0').rstrip('.')
					bstyle=str(st.get('borderstyle',1));outline=f"{st.get('borderw',1.0):.2f}".rstrip('0').rstrip('.')
					shadow=f"{st.get('shadow',2.0):.2f}".rstrip('0').rstrip('.');align=str(st.get('align',2))
					ml=str(st.get('margin_l',10));mr=str(st.get('margin_r',10));mv=str(st.get('margin_v',10));enc=str(st.get('encoding',1))
					style_key=f"{font},{size},{pri},{out},{back},{bold},{italic},{underline},{strike},{sx},{sy},{spacing},{angle},{bstyle},{outline},{shadow},{align},{ml},{mr},{mv},{enc}"
					if style_key not in unique_styles:
						style_name=f"Style_{style_idx}"
						unique_styles[style_key]=style_name;style_idx+=1
				for key,sname in unique_styles.items():F.write(f"Style: {sname},{key}\n")
				F.write("\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
				for p in sorted(A.data.texts,key=lambda x:x.start):
					st=A.ensure_style_dict(p.style_ass)
					font=st.get('font','Cambria');size=str(st.get('size',69))
					pri=to_ass_color(st.get('color','#ffc300'));out=to_ass_color(st.get('bordercolor','#FFFFFF'));back=to_ass_color(st.get('backcolor','#00E6FF'))
					bold='-1' if st.get('bold',False) else '0';italic='-1' if st.get('italic',False) else '0'
					underline='-1' if st.get('underline',False) else '0';strike='-1' if st.get('strikeout',False) else '0'
					sx=str(st.get('scalex',100));sy=str(st.get('scaley',100))
					spacing=f"{st.get('spacing',0.0):.2f}".rstrip('0').rstrip('.');angle=f"{st.get('angle',0.0):.2f}".rstrip('0').rstrip('.')
					bstyle=str(st.get('borderstyle',1));outline=f"{st.get('borderw',1.0):.2f}".rstrip('0').rstrip('.')
					shadow=f"{st.get('shadow',2.0):.2f}".rstrip('0').rstrip('.');align=str(st.get('align',2))
					ml=str(st.get('margin_l',10));mr=str(st.get('margin_r',10));mv=str(st.get('margin_v',10));enc=str(st.get('encoding',1))
					style_key=f"{font},{size},{pri},{out},{back},{bold},{italic},{underline},{strike},{sx},{sy},{spacing},{angle},{bstyle},{outline},{shadow},{align},{ml},{mr},{mv},{enc}"
					sname=unique_styles.get(style_key,"Default")
					st_str=A.format_ass_time(p.start);en_str=A.format_ass_time(p.end)
					F.write(f"Dialogue: 0,{st_str},{en_str},{sname},,0,0,0,,{{\\pos({p.x},{p.y})}}{p.text}\n")
	def block_ass_style_signals(A,val):
		A.txt_ass_font.blockSignals(val);A.spin_font_size.blockSignals(val)
		A.chk_bold.blockSignals(val);A.chk_italic.blockSignals(val);A.chk_underline.blockSignals(val);A.chk_strikeout.blockSignals(val)
		A.spin_scalex.blockSignals(val);A.spin_scaley.blockSignals(val);A.spin_spacing.blockSignals(val);A.spin_angle.blockSignals(val)
		A.chk_is_bg.blockSignals(val);A.spin_outline_size.blockSignals(val);A.spin_shadow_size.blockSignals(val)
		A.spin_align_val.blockSignals(val);A.spin_ml.blockSignals(val);A.spin_mr.blockSignals(val);A.spin_mv.blockSignals(val)
		A.spin_enc.blockSignals(val)
	def set_tool(A,tool):
		A.current_tool=tool;A.btn_select.setChecked(tool=='V');A.btn_move.setChecked(tool=='G');A.btn_cut.setChecked(tool=='B')
		A.btn_select.setStyleSheet(S.btn_grey if tool=='V' else S.btn_gray)
		A.btn_move.setStyleSheet(S.btn_grey if tool=='G' else S.btn_gray)
		A.btn_cut.setStyleSheet(S.btn_grey if tool=='B' else S.btn_gray)
	def on_speed_changed(A,val):
		if A.is_video:
			playing=A.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState
			if playing:A.player.pause()
			try:A.player.setPitchCompensation(False)
			except:pass
			A.player.setPlaybackRate(val)
			if playing:A.player.play()
	def load_media(A,file_path):
		B=file_path;A.player.stop();A.needs_centering=True
		if B.lower().endswith(('.mp4','.avi','.mkv','.mov')):A.image_bg=None;A.is_video=True;A.media_path=B;A.player.setSource(QUrl.fromLocalFile(B));A.player.setPlaybackRate(A.spin_speed.value());A.player.pause();A.btn_play.setText('Play')
	def import_video(A):
		A.player.stop();B,C=QFileDialog.getOpenFileName(A,'Open Video','','Videos (*.mp4 *.avi *.mkv *.mov)')
		if B:A.load_media(B);A.player.durationChanged.connect(lambda d: A.duration.setValue(round(d / 1000.0, 2)))
	def toggle_play(A):
		if A.is_video:
			if A.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:A.player.pause();A.btn_play.setText('Play')
			else:A.player.play();A.btn_play.setText('Pause')
	def seek_relative(A,secs):
		if A.is_video:A.seek_time(A.get_current_time()+secs)
	def zoom_view(B,factor):A=factor;B.media_view.scale_factor*=A;B.media_view.scale(A,A)
	def zoom_timeline(A,factor):A.timeline.zoom_level=max(1.,min(1e3,A.timeline.zoom_level*factor));A.timeline.update()
	def on_frame_changed(B,frame):
		B.frame_counter+=1;D=B.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState
		skip=max(1,int(round(3*B.spin_speed.value())))
		if D and B.frame_counter%skip!=0:return
		A=frame.toImage()
		if not A.isNull():
			C,E=A.width(),A.height()
			if C>1280:A=A.scaled(1280,720,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation)
			B.current_frame_img=A;B.media_orig_size=C,E;B.image_scale=A.width()/C if C else 1.;B.display_image(A)
			B.frame_updated=True
	def get_active_tf(A,rec,t):
		for tf in rec.target_frames:
			if abs(tf.time-t)<0.05:return tf
		return None
	def import_ass_json(A):
		E,G=QFileDialog.getOpenFileName(A,'Open Subtitle Data','','JSON Files (*.json)')
		if E:
			with open(E,'r',encoding='utf-8')as F:A.ass_data=json.load(F)
			if A.ass_data and isinstance(A.ass_data,list):
				keys=list(A.ass_data[0].keys());A.combo_ass_key.clear()
				for k in keys:
					if k not in('start','end'):A.combo_ass_key.addItem(k)
				if TAR_LANG in keys:A.combo_ass_key.setCurrentText(TAR_LANG)
	def stop_ass_process(A):A.ass_running=False
	def clear_ass_data(A):A.ass_data=None;A.combo_ass_key.clear()
	def start_ass_process(A):
		if not hasattr(A,'ass_data')or not A.ass_data:return
		A.save_state();A.ass_running=True;sel_key=A.combo_ass_key.currentText()or'text';total=len(A.ass_data);dur=A.get_duration()or 99999.
		for idx,item in enumerate(A.ass_data):
			if not A.ass_running:break
			st=float(item.get('start',.0));en=float(item.get('end',.0));text=item.get(sel_key,'')
			st_val=max(.0,st);en_val=min(dur,en)
			if st_val<en_val:
				track=5
				while A.check_overlap(st_val,en_val,track,is_ass=True):track+=1
				new_rec=RecLineText(start=st_val,end=en_val,track=track)
				new_rec.text=text;new_rec.x=540;new_rec.y=1500
				new_rec.style_ass={
					'font':'Cambria','size':69,'color':'#ffc300','bordercolor':'#FFFFFF','backcolor':'#00E6FF',
					'bold':False,'italic':False,'underline':False,'strikeout':False,
					'scalex':100,'scaley':100,'spacing':0.0,'angle':0.0,
					'borderstyle':1,'borderw':1.0,'shadow':2.0,
					'align':2,'margin_l':10,'margin_r':10,'margin_v':10,'encoding':1
				}
				A.data.texts.append(new_rec)
			A.prog_bar.setValue(int((idx+1)/total*100));QApplication.processEvents()
		A.ass_running=False;A.sync_data_to_widgets()
	def on_ass_spins_changed(A):
		if A.updating_poly:return
		rows=[A.ass_list.row(item)for item in A.ass_list.selectedItems()]
		if rows:
			A.save_state()
			for r in rows:
				if r<len(A.data.texts):
					p=A.data.texts[r];p.start=A.spin_ass_st.value();p.end=A.spin_ass_en.value();p.x=A.spin_ass_x.value();p.y=A.spin_ass_y.value()
					st=A.ensure_style_dict(p.style_ass)
					w_val=A.spin_ass_w.value()
					st['wrap_w']=w_val
					st['wrap']=(w_val>0)
					p.style_ass=st
			A.sync_data_to_widgets()
	def on_ass_text_changed(A):
		rows=[A.ass_list.row(item)for item in A.ass_list.selectedItems()]
		if rows:
			A.save_state()
			cursor_pos=A.txt_ass_content.cursorPosition()
			for r in rows:
				if r<len(A.data.texts):A.data.texts[r].text=A.txt_ass_content.text()
			A.txt_ass_content.blockSignals(True)
			A.sync_data_to_widgets()
			A.txt_ass_content.blockSignals(False)
			A.txt_ass_content.setCursorPosition(cursor_pos)
	def apply_style_to_all(A):
		if hasattr(A,'data') and A.data.texts:
			A.save_state()
			ref_style={
				'font':'Cambria','size':69,'color':'#ffc300','bordercolor':'#FFFFFF','backcolor':'#00E6FF',
				'bold':False,'italic':False,'underline':False,'strikeout':False,
				'scalex':100,'scaley':100,'spacing':0.0,'angle':0.0,
				'borderstyle':1,'borderw':1.0,'shadow':2.0,
				'align':2,'margin_l':10,'margin_r':10,'margin_v':10,'encoding':1
			}
			if 0<=A.selected_text_idx<len(A.data.texts):
				ref_style=copy.deepcopy(A.ensure_style_dict(A.data.texts[A.selected_text_idx].style_ass))
			for p in A.data.texts:
				p.style_ass=copy.deepcopy(ref_style);p.x=A.spin_ass_x.value();p.y=A.spin_ass_y.value()
			A.sync_data_to_widgets()
	def add_ass_text(A):
		A.save_state();cur_t=A.get_current_time();dur=A.get_duration()or 99999.
		st_val=cur_t;en_val=min(dur,cur_t+3.0);track=5
		while A.check_overlap(st_val,en_val,track,is_ass=True):track+=1
		new_rec=RecLineText(start=st_val,end=en_val,track=track)
		new_rec.text="New Subtitle";new_rec.x=540;new_rec.y=1500
		new_rec.style_ass={
			'font':'Cambria','size':69,'color':'#ffc300','bordercolor':'#FFFFFF','backcolor':'#00E6FF',
			'bold':False,'italic':False,'underline':False,'strikeout':False,
			'scalex':100,'scaley':100,'spacing':0.0,'angle':0.0,
			'borderstyle':1,'borderw':1.0,'shadow':2.0,
			'align':2,'margin_l':10,'margin_r':10,'margin_v':10,'encoding':1
		}
		A.data.texts.append(new_rec);A.sync_data_to_widgets()
	def delete_ass_text(A):
		rows=[A.ass_list.row(item)for item in A.ass_list.selectedItems()]
		if rows:
			A.save_state()
			to_delete=[A.data.texts[r]for r in rows if r<len(A.data.texts)]
			A.data.texts=[p for p in A.data.texts if p not in to_delete]
			A.sync_data_to_widgets()
	def format_ass_time(A,secs):
		h=int(secs//3600);m=int((secs%3600)//60);s=int(secs%60);cs=int(round((secs-int(secs))*100))
		if cs==100:cs=0;s+=1
		return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
	def get_interpolated_pos(A,rec,t):
		if not rec.target_frames:return sum(p.x for p in rec.points)/4.,sum(p.y for p in rec.points)/4.
		tfs=sorted(rec.target_frames,key=lambda x:x.time);n=len(tfs)
		if n==1:return tfs[0].x,tfs[0].y
		if t<=tfs[0].time:return tfs[0].x,tfs[0].y
		if t>=tfs[-1].time:return tfs[-1].x,tfs[-1].y
		for i in range(n-1):
			tf1,tf2=tfs[i],tfs[i+1]
			if tf1.time<=t<=tf2.time:
				fac=(t-tf1.time)/(tf2.time-tf1.time) if tf2.time>tf1.time else 0.0
				return tf1.x+fac*(tf2.x-tf1.x),tf1.y+fac*(tf2.y-tf1.y)
		return tfs[0].x,tfs[0].y
	def get_or_create_active_tf(A,rec,t):
		for tf in rec.target_frames:
			if abs(tf.time-t)<0.05:return tf
		new_tf=TargetFrame(x=640.0,y=360.0,time=t)
		ix,iy=A.get_interpolated_pos(rec,t)
		new_tf.x,new_tf.y=ix,iy
		rec.target_frames.append(new_tf)
		rec.target_frames.sort(key=lambda x:x.time)
		return new_tf
	def get_rendered_pts(A,rec,t):
		rx,ry=A.get_interpolated_pos(rec,t);cx=sum(p.x for p in rec.points)/4.0;cy=sum(p.y for p in rec.points)/4.0
		return[Point(p.x-cx+rx,p.y-cy+ry)for p in rec.points]
	def update_handles_at(A,pts):
		if not A.handles:
			for B in range(4):C=HandleItem(B,A);A.scene.addItem(C);C.setZValue(10);A.handles.append(C)
		E,F=A._image_size()
		for(B,D)in enumerate(pts):G=min(max(.0,D.x),float(E-1));H=min(max(.0,D.y),float(F-1));A.handles[B].setVisible(True);A.handles[B].setPos(G*A.image_scale,H*A.image_scale)
	def hide_handles(A):
		for B in A.handles:B.setVisible(False)
	def handle_moved(A,idx,new_pos):
		if not 0<=A.selected_rec_idx<len(A.data.polygons):return
		B=A.data.polygons[A.selected_rec_idx];C=max(1e-06,A.image_scale);sx=new_pos.x()/C;sy=new_pos.y()/C
		if B.target_frames:
			tf=A.get_or_create_active_tf(B,A.get_current_time())
			if tf:
				sum_ox=sum(B.points[i].x for i in range(4)if i!=idx);sum_oy=sum(B.points[i].y for i in range(4)if i!=idx)
				B.points[idx].x=(4.0/3.0)*(sx-tf.x)+(1.0/3.0)*sum_ox;B.points[idx].y=(4.0/3.0)*(sy-tf.y)+(1.0/3.0)*sum_oy
		else:
			B.points[idx].x=sx;B.points[idx].y=sy
		A.sync_data_to_widgets()
	def polygon_translated(A,offset):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			B=A.data.polygons[A.selected_rec_idx]
			C=max(1e-06,A.image_scale);dx=offset.x()/C;dy=offset.y()/C
			if B.target_frames:
				tf=A.get_or_create_active_tf(B,A.get_current_time())
				if tf:
					tf.x+=dx;tf.y+=dy
					H,I=A._image_size();tf.x=min(max(.0,tf.x),float(H-1));tf.y=min(max(.0,tf.y),float(I-1))
			else:
				for pt in B.points:
					pt.x+=dx;pt.y+=dy
			A.sync_data_to_widgets()
	def polygon_edge_translated(A,edge_idx,offset):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			B=A.data.polygons[A.selected_rec_idx];C=max(1e-06,A.image_scale);dx=offset.x()/C;dy=offset.y()/C
			if B.target_frames:
				tf=A.get_or_create_active_tf(B,A.get_current_time())
				if tf:
					i1,i2=edge_idx,(edge_idx+1)%4;B.points[i1].x+=dx;B.points[i1].y+=dy;B.points[i2].x+=dx;B.points[i2].y+=dy
					tf.x+=dx/2.0;tf.y+=dy/2.0
			else:
				i1,i2=edge_idx,(edge_idx+1)%4;B.points[i1].x+=dx;B.points[i1].y+=dy;B.points[i2].x+=dx;B.points[i2].y+=dy
			A.sync_data_to_widgets()
	def get_current_time(A):return A.player.position()/1e3 if A.is_video else .0
	def get_duration(A):return A.player.duration()/1e3 if A.is_video else .0
	def seek_time(A,seconds):
		if A.is_video:A.frame_updated=False;A.player.setPosition(int(seconds*1e3));A.timeline.update()
	def on_position_changed(A,pos):
		A.timeline.update();K=A.current_frame_img or A.image_bg;A.display_image(K)
		if hasattr(A,'time_at'):A.time_at.blockSignals(True);A.time_at.setValue(pos/1000.0);A.time_at.blockSignals(False)
	def on_duration_changed(A,dur):
		A.timeline.update()
		if hasattr(A,'time_at'):A.time_at.setRange(0.0,dur/1000.0)
	def on_time_changed(A,val):A.seek_time(val)
	def set_selected_rec(A,index):
		C=index
		if A.selected_rec_idx!=C:A.selected_rec_idx=C;A.selected_recs={C}if C!=-1 else set();A.sync_data_to_widgets()
	def toggle_select_rec(A,index):
		if index in A.selected_recs:
			A.selected_recs.remove(index)
			A.selected_rec_idx=list(A.selected_recs)[0]if A.selected_recs else-1
		else:A.selected_recs.add(index);A.selected_rec_idx=index
		A.sync_data_to_widgets()
	def on_list_selection_changed(A):
		if A.updating_poly:return
		rows=[A.rec_list.row(item)for item in A.rec_list.selectedItems()]
		A.selected_recs=set(rows);A.selected_rec_idx=rows[0]if rows else-1
		A.lbl_active_rec.setText(f"Active RecLine [{A.selected_rec_idx}]"if A.selected_rec_idx!=-1 else'Active RecLine [None]')
		A.timeline.update()
		K=A.current_frame_img or A.image_bg
		if K:A.display_image(K)
	def sync_data_to_widgets(A):
		A.rec_list.blockSignals(True);A.rec_list.clear()
		for(B,F_rec)in enumerate(A.data.polygons):A.rec_list.addItem(f"RecLine [{B}] {F_rec.start:.2f}s - {F_rec.end:.2f}s")
		for idx in A.selected_recs:
			if 0<=idx<A.rec_list.count():A.rec_list.item(idx).setSelected(True)
		A.rec_list.blockSignals(False)
		A.ass_list.blockSignals(True);A.ass_list.clear()
		for idx,p in enumerate(A.data.texts):A.ass_list.addItem(f"[{idx}]: {p.text}")
		for r in A.selected_texts:
			if 0<=r<A.ass_list.count():A.ass_list.item(r).setSelected(True)
		A.ass_list.blockSignals(False)
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			A.lbl_active_rec.setText(f"Active RecLine [{A.selected_rec_idx}]");C=A.data.polygons[A.selected_rec_idx];dur=A.get_duration()or 99999.;A.spin_st.blockSignals(True);A.spin_en.blockSignals(True);A.spin_st.setRange(.0,dur);A.spin_en.setRange(.0,dur);A.spin_st.setValue(C.start);A.spin_en.setValue(C.end);A.spin_st.blockSignals(False);A.spin_en.blockSignals(False)
			for B in range(4):
				D,E=A.point_spins[B];D.blockSignals(True);E.blockSignals(True)
				if B<len(C.points):D.setValue(int(round(C.points[B].x)));E.setValue(int(round(C.points[B].y)))
				D.blockSignals(False);E.blockSignals(False)
			A.tf_list.blockSignals(True);old_row=A.tf_list.currentRow();A.tf_list.clear()
			for idx,tf in enumerate(C.target_frames):A.tf_list.addItem(f"TF [{idx}] {tf.time:.2f}s ({int(tf.x)},{int(tf.y)})")
			A.block_tf_seek=True
			if 0<=old_row<len(C.target_frames):A.tf_list.setCurrentRow(old_row)
			else:
				act=A.get_active_tf(C,A.get_current_time())
				if act and act in C.target_frames:A.tf_list.setCurrentRow(C.target_frames.index(act))
				else:A.tf_list.setCurrentRow(-1)
			A.tf_list.blockSignals(False);A.on_tf_select(A.tf_list.currentRow());A.block_tf_seek=False
		else:
			A.lbl_active_rec.setText('Active RecLine [None]')
			A.tf_list.blockSignals(True);A.tf_list.clear();A.tf_list.blockSignals(False)
		A.on_ass_list_selection_changed()
		A.timeline.update()
		K=A.current_frame_img or A.image_bg
		if K:A.display_image(K)
	def set_selected_text_idx(A,index):
		if A.selected_text_idx!=index:A.selected_text_idx=index;A.selected_texts={index} if index!=-1 else set();A.sync_data_to_widgets()
	def create_keyframe_at_playhead(A):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			A.save_state();rec=A.data.polygons[A.selected_rec_idx];cur_t=A.get_current_time();A.get_or_create_active_tf(rec,cur_t);A.sync_data_to_widgets()
	def remove_keyframe_near_playhead(A):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			rec=A.data.polygons[A.selected_rec_idx]
			if not rec.target_frames:return
			cur_t=A.get_current_time();closest_idx=min(range(len(rec.target_frames)),key=lambda i:abs(rec.target_frames[i].time-cur_t))
			if abs(rec.target_frames[closest_idx].time-cur_t)<1.0:
				A.save_state();rec.target_frames.pop(closest_idx)
				A.sync_data_to_widgets()
	def on_tf_select(A,row):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			rec=A.data.polygons[A.selected_rec_idx]
			if 0<=row<len(rec.target_frames):
				tf=rec.target_frames[row];A.spin_tf_en.blockSignals(True);A.spin_tf_x.blockSignals(True);A.spin_tf_y.blockSignals(True)
				A.spin_tf_en.setValue(tf.time);A.spin_tf_x.setValue(int(tf.x));A.spin_tf_y.setValue(int(tf.y))
				A.spin_tf_en.blockSignals(False);A.spin_tf_x.blockSignals(False);A.spin_tf_y.blockSignals(False)
				if not getattr(A,'block_tf_seek',False) and abs(A.get_current_time()-tf.time)>0.05:A.seek_time(tf.time)
	def on_tf_spins_changed(A):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			rec=A.data.polygons[A.selected_rec_idx];row=A.tf_list.currentRow()
			if 0<=row<len(rec.target_frames):
				A.save_state()
				tf=rec.target_frames[row];tf.time=A.spin_tf_en.value();tf.x=float(A.spin_tf_x.value());tf.y=float(A.spin_tf_y.value())
				rec.target_frames.sort(key=lambda x:x.time)
				A.sync_data_to_widgets()
	def add_target_frame(A):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			A.save_state()
			rec=A.data.polygons[A.selected_rec_idx];cur_t=A.get_current_time()
			new_tf=A.get_or_create_active_tf(rec,cur_t)
			A.sync_data_to_widgets()
			for idx,tf in enumerate(rec.target_frames):
				if tf is new_tf:A.tf_list.setCurrentRow(idx);break
	def delete_target_frame(A):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			rec=A.data.polygons[A.selected_rec_idx];row=A.tf_list.currentRow()
			if 0<=row<len(rec.target_frames):
				A.save_state()
				rec.target_frames.pop(row)
				A.sync_data_to_widgets()
	def check_overlap(A,st,en,track,skip_idx=-1,is_ass=False):
		items=A.data.texts if is_ass else A.data.polygons
		for idx,poly in enumerate(items):
			if idx==skip_idx:continue
			if poly.track==track and max(st,poly.start)<min(en,poly.end):return True
		return False
	def cut_at_time(A,index,t):
		if 0<=index<len(A.data.polygons):
			P=A.data.polygons[index]
			if P.start<t<P.end:
				A.save_state()
				left_tfs=[];right_tfs=[]
				for tf in P.target_frames:
					if tf.time<=t:left_tfs.append(tf)
					else:right_tfs.append(tf)
				R_pts=CanvasItems.get_rect_pts(P.points);R_part=RecLine(start=t,end=P.end,points=R_pts,target_frames=right_tfs,track=P.track,st_orig=t,en_orig=P.en_orig)
				P.end=t;P.en_orig=t;P.target_frames=left_tfs;A.data.polygons.append(R_part);A.selected_recs={index};A.selected_rec_idx=index;A.sync_data_to_widgets()
	def copy_selected(A):
		A.copied_recs=[]
		for idx in A.selected_recs:
			if 0<=idx<len(A.data.polygons):
				P=A.data.polygons[idx];pts=CanvasItems.get_rect_pts(P.points)
				tfs=[TargetFrame(x=tf.x,y=tf.y,time=tf.time)for tf in P.target_frames]
				A.copied_recs.append((P.end-P.start,pts,P.track,tfs))
	def paste_selected(A):
		cur_t=A.get_current_time();new_sel=set()
		if A.copied_recs:A.save_state()
		for dur,pts,track,tfs in A.copied_recs:
			target_track=track
			while A.check_overlap(cur_t,cur_t+dur,target_track):target_track+=1
			new_tfs=[]
			if tfs:
				min_t=min(tf.time for tf in tfs)
				for tf in tfs:new_tfs.append(TargetFrame(x=tf.x,y=tf.y,time=cur_t+tf.time-min_t))
			else:new_tfs.append(TargetFrame(x=sum(p.x for p in pts)/4,y=sum(p.y for p in pts)/4,time=cur_t+dur))
			new_rec=RecLine(start=cur_t,end=cur_t+dur,points=pts,target_frames=new_tfs,track=target_track,st_orig=cur_t,en_orig=cur_t+dur);A.data.polygons.append(new_rec);new_sel.add(len(A.data.polygons)-1)
		if new_sel:A.selected_recs=new_sel;A.selected_rec_idx=list(new_sel)[0];A.sync_data_to_widgets()
	def on_focus_coords_changed(A):
		A.save_state()
		A.data.focus.x=float(A.spin_focus_x.value());A.data.focus.y=float(A.spin_focus_y.value())
		K=A.current_frame_img or A.image_bg
		if K:A.display_image(K)
	def on_spin_times_changed(A):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			B=A.data.polygons[A.selected_rec_idx];C=A.get_duration()or 99999.;st_val=A.spin_st.value();en_val=A.spin_en.value()
			if not A.check_overlap(st_val,en_val,B.track,A.selected_rec_idx):
				A.save_state()
				old_st=B.start;shift=st_val-old_st;B.start=max(.0,min(C-.1,st_val));B.end=max(B.start+.1,min(C,en_val))
				if len(B.target_frames)==1:B.target_frames[0].time=B.end
				else:
					for tf in B.target_frames:tf.time+=shift
				A.sync_data_to_widgets()
	def on_spin_points_changed(A):
		if 0<=A.selected_rec_idx<len(A.data.polygons):
			A.save_state()
			C=A.data.polygons[A.selected_rec_idx]
			for B in range(4):D,E=A.point_spins[B];C.points[B].x=D.value();C.points[B].y=E.value()
			A.sync_data_to_widgets()
	def add_rectangle(A):
		A.save_state()
		dur=A.get_duration()or 99999.;st_t=A.get_current_time();en_t=min(dur,st_t+3.);track=0
		while A.check_overlap(st_t,en_t,track):track+=1
		B=RecLine(start=st_t,end=en_t,track=track,st_orig=st_t,en_orig=en_t)
		A.data.polygons.append(B);A.selected_recs={len(A.data.polygons)-1};A.selected_rec_idx=len(A.data.polygons)-1;A.sync_data_to_widgets()
	def _image_size(A):
		D,E=A.media_orig_size
		if D and E:return D,E
		C=A.bg_item.pixmap()
		if not C.isNull():G,H=C.width(),C.height();F_val=max(1e-06,A.image_scale);return int(round(G/F_val)),int(round(H/F_val))
		B=A.scene.sceneRect()
		if B.width()>0 and B.height()>0:return int(B.width()),int(B.height())
		return 1,1
	def delete_rectangle(A):
		to_delete=[idx for idx in sorted(list(A.selected_recs),reverse=True) if 0<=idx<len(A.data.polygons)]
		if to_delete:
			A.save_state()
			for idx in to_delete:A.data.polygons.pop(idx)
			A.selected_recs=set();A.selected_rec_idx=-1;A.sync_data_to_widgets()
	def import_json(A,E:str=None):
		if isinstance(E,bool):E=None
		A.player.stop()
		if not E:E,_=QFileDialog.getOpenFileName(A,'Open JSON Data','','JSON Files (*.json)')
		if E:
			A.save_state()
			with open(E,'r')as F:B=json.load(F)
			A.data.polygons=[]
			for C in B or []:
				D=[Point(float(pt.get('x',.0)),float(pt.get('y',.0)))for pt in C.get('points',[])]
				while len(D)<4:D.append(Point(.0,.0))
				tfs=[]
				for tf_dict in C.get('target_frames',[]):
					t_time=tf_dict.get('end',tf_dict.get('en',tf_dict.get('time',.0)))
					tfs.append(TargetFrame(x=float(tf_dict.get('x',.0)),y=float(tf_dict.get('y',.0)),time=float(t_time)))
				tfs.sort(key=lambda x:x.time)
				st_all=float(C.get('start',C.get('st',tfs[0].time if tfs else 0.0)))
				en_all=float(C.get('end',C.get('en',tfs[-1].time if tfs else 3.0)))
				tr_val=C.get('track',max((tf.get('track',0)for tf in C.get('target_frames',[])if 'track' in tf),default=0))
				while A.check_overlap(st_all,en_all,tr_val):tr_val+=1
				A.data.polygons.append(RecLine(start=st_all,end=en_all,points=D[:4],target_frames=tfs,track=int(tr_val),st_orig=st_all,en_orig=en_all))
			A.selected_rec_idx=-1;A.selected_recs=set();A.sync_data_to_widgets()
	def export_json(A):
		A.player.stop();B,E=QFileDialog.getSaveFileName(A,'Save JSON Data','blurs.json','JSON Files (*.json)')
		if B:
			polys=[]
			for rec in A.data.polygons:
				tfs=[]
				sorted_tfs=sorted(rec.target_frames,key=lambda x:x.time)
				for idx,tf in enumerate(sorted_tfs):
					tf_start=rec.start if idx==0 else sorted_tfs[idx-1].time
					tfs.append({'x': int(round(tf.x)), 'y': int(round(tf.y)), 'start': round(float(tf_start), 3), 'end': round(float(tf.time), 3), 'track': int(getattr(tf, 'track', 0))})
				pts=[{'x':int(round(pt.x)),'y':int(round(pt.y))}for pt in rec.points]
				polys.append({'points':pts,'target_frames':tfs,'start':round(rec.start,3),'end':round(rec.end,3)})
			with open(B,'w',encoding='utf-8')as D:json.dump(polys,D,indent=4)
	def import_transcribe(A):
		A.player.stop();E,G=QFileDialog.getOpenFileName(A,'Open Transcribe JSON','','JSON Files (*.json)')
		if E:
			with open(E,'r',encoding='utf-8')as F:A.transcribe_data=json.load(F)
			A.set_area_desub_video();A.set_auto_desub_active(True)
	def clear_transcribe(A):A.transcribe_data=None;A.set_auto_desub_active(False);A.prog_bar.setValue(0)
	def on_range_spins_changed(A):
		A.save_state()
		for b in range(4):I,J=A.range_spins[b];A.range_points[b].x=float(I.value());A.range_points[b].y=float(J.value())
		A.update_range_overlay()
	def update_range_overlay(A):
		if hasattr(A,'range_points')and A.range_poly_item.isVisible():
			F_poly=QPolygonF([QPointF(pt.x*A.image_scale,pt.y*A.image_scale)for pt in A.range_points]);A.range_poly_item.setPolygon(F_poly)
			for b in range(4):A.range_handles[b].setPos(A.range_points[b].x*A.image_scale,A.range_points[b].y*A.image_scale)
	def range_handle_moved(A,idx,new_pos):
		C=max(1e-06,A.image_scale);D=new_pos.x()/C;E=new_pos.y()/C;G,H=A._image_size();D=min(max(.0,D),float(G-1));E=min(max(.0,E),float(H-1));A.range_points[idx]=Point(float(D),float(E));A.updating_poly=True;A.update_range_overlay();A.updating_poly=False;A.sync_range_spins()
	def range_polygon_translated(A,offset):
		C=max(1e-06,A.image_scale);F_val=offset.x()/C;G=offset.y()/C;H,I=A._image_size()
		for D in A.range_points:D.x=min(max(.0,D.x+F_val),float(H-1));D.y=min(max(.0,D.y+G),float(I-1))
		A.updating_poly=True;A.update_range_overlay();A.updating_poly=False;A.sync_range_spins()
	def range_polygon_edge_translated(A,edge_idx,offset):
		C=max(1e-06,A.image_scale);F_val=offset.x()/C;G=offset.y()/C;H,I=A._image_size()
		for idx in[edge_idx,(edge_idx+1)%4]:
			A.range_points[idx].x=min(max(.0,A.range_points[idx].x+F_val),float(H-1))
			A.range_points[idx].y=min(max(.0,A.range_points[idx].y+G),float(I-1))
		A.updating_poly=True;A.update_range_overlay();A.updating_poly=False;A.sync_range_spins()
	def sync_range_spins(A):
		for b in range(4):
			I,J=A.range_spins[b];I.blockSignals(True);J.blockSignals(True);I.setValue(int(round(A.range_points[b].x)));J.setValue(int(round(A.range_points[b].y)));I.blockSignals(False);J.blockSignals(False)
	def ass_color_to_qcolor(A,ass_str):
		if ass_str.startswith('#'):
			return QColor(ass_str)
		clean=ass_str.replace('&H','').replace('&','').strip().zfill(8)
		try:
			rr=int(clean[6:8],16);gg=int(clean[4:6],16);bb=int(clean[2:4],16);aa=255-int(clean[0:2],16)
			return QColor(rr,gg,bb,aa)
		except:return QColor(255,255,255)
	def qcolor_to_ass_color(A,qcol):
		rr=qcol.red();gg=qcol.green();bb=qcol.blue();aa=255-qcol.alpha()
		return f"&H{aa:02X}{bb:02X}{gg:02X}{rr:02X}"
	def update_color_button_styles(A,pri_str,out_str,back_str,shd_str='#000000'):
		A.btn_color_pri.setStyleSheet(f"background-color: {A.ass_color_to_qcolor(pri_str).name()}; border: 1px solid #00f7ff;")
		A.btn_color_out.setStyleSheet(f"background-color: {A.ass_color_to_qcolor(out_str).name()}; border: 1px solid #00f7ff;")
		A.btn_color_back.setStyleSheet(f"background-color: {A.ass_color_to_qcolor(back_str).name()}; border: 1px solid #00f7ff;")
		A.btn_color_shadow.setStyleSheet(f"background-color: {A.ass_color_to_qcolor(shd_str).name()}; border: 1px solid #00f7ff;")
	def pick_color(A,idx):
		curr_col_str=getattr(A,'active_color_pri' if idx==3 else ('active_color_out' if idx==4 else ('active_color_back' if idx==5 else 'active_color_shadow')),'#FFFFFF')
		curr_col=A.ass_color_to_qcolor(curr_col_str)
		from PyQt6.QtWidgets import QColorDialog
		col=QColorDialog.getColor(curr_col,A,"Pick Color")
		if col.isValid():
			hex_col=col.name()
			if idx==3:A.active_color_pri=hex_col
			elif idx==4:A.active_color_out=hex_col
			elif idx==5:A.active_color_back=hex_col
			elif idx==6:A.active_color_shadow=hex_col
			A.update_color_button_styles(getattr(A,'active_color_pri','#ffc300'),getattr(A,'active_color_out','#FFFFFF'),getattr(A,'active_color_back','#00E6FF'),getattr(A,'active_color_shadow','#000000'))
			A.on_ass_style_ui_changed()
	def on_ass_style_field_changed(A):
		rows=[A.ass_list.row(item)for item in A.ass_list.selectedItems()]
		if rows:
			A.save_state()
			for r in rows:
				if r<len(A.data.texts):A.data.texts[r].style_ass=A.txt_ass_style.text()
			A.sync_data_to_widgets()
	def set_auto_desub_active(A,active):
		for I,J in A.range_spins:I.setEnabled(active);J.setEnabled(active)
		A.spin_pad.setEnabled(active);A.txt_lang.setEnabled(active);A.spin_add_st.setEnabled(active);A.spin_add_en.setEnabled(active);A.btn_start_all.setEnabled(active);A.btn_start_max.setEnabled(active);A.btn_start.setEnabled(active);A.btn_stop.setEnabled(active);A.btn_clear.setEnabled(active);A.range_poly_item.setVisible(active);A.chk_use_text.setEnabled(active)
		for H in A.range_handles:H.setVisible(active)
		if active:A.update_range_overlay()
	def stop_auto_desub(A):
		if getattr(A,'auto_desub_running',False):
			A.auto_desub_paused=not getattr(A,'auto_desub_paused',False)
			A.btn_stop.setText('Stop' if not A.auto_desub_paused else 'Continue')
		else:A.auto_desub_running=False;A.auto_desub_paused=False;A.btn_stop.setText('Stop')
	def start_auto_desub(A,use_max_size=False):
		import difflib
		A.toggle_play();A.toggle_play()
		if not hasattr(A,'transcribe_data')or not A.transcribe_data:return
		lang=A.txt_lang.text()or S.easyocr_reader;reader=easyocr.Reader([lang])
		segs=A.transcribe_data
		if isinstance(segs,dict):
			for k in ('segments','sentences','data','list','transcription'):
				if k in segs:segs=segs[k];break
			else:segs=list(segs.values())
		if not isinstance(segs,list):return
		segs=[s for s in segs if isinstance(s,dict)]
		total=len(segs)
		if not total:return
		A.save_state();A.auto_desub_running=True;A.auto_desub_paused=False;A.btn_stop.setText('Stop')
		xs=[pt.x for pt in A.range_points];ys=[pt.y for pt in A.range_points];min_x,max_x=int(min(xs)),int(max(xs));min_y,max_y=int(min(ys)),int(max(ys));P=A.spin_pad.value();dur=A.get_duration()or 99999.;add_st=A.spin_add_st.value();add_en=A.spin_add_en.value();use_text=A.chk_use_text.isChecked()
		longest_txt=max((s.get('text','')for s in segs),key=len) if segs else ""
		ppc,h_template=35.0,55.0;template_found=False;template_w=len(longest_txt)*ppc
		best_seg_for_temp=max(segs,key=lambda s:len(s.get('text',''))) if segs else None
		if best_seg_for_temp:
			mst_mid=(best_seg_for_temp.get('start',.0)+best_seg_for_temp.get('end',.0))/2.0;A.seek_time(mst_mid);t0=time.time()
			while(abs(A.player.position()-mst_mid*1000)>300 or not getattr(A,'frame_updated',False))and time.time()-t0<1.5:QApplication.processEvents();time.sleep(0.01)
			time.sleep(0.15);img=A.current_frame_img
			if img and not img.isNull():
				rgb_img=img.convertToFormat(QImage.Format.Format_RGB888);w,h=rgb_img.width(),rgb_img.height();scale=A.image_scale;cx_min=max(0,int(min_x*scale));cx_max=min(w,int(max_x*scale));cy_min=max(0,int(min_y*scale));cy_max=min(h,int(max_y*scale))
				if cx_max>cx_min and cy_max>cy_min:
					ptr=rgb_img.bits();ptr.setsize(rgb_img.sizeInBytes());arr=np.frombuffer(ptr,dtype=np.uint8).reshape((h,w,3));crop=arr[cy_min:cy_max,cx_min:cx_max];results=reader.readtext(crop);best_box=None;best_score=0.0;best_text_val="";tgt="".join(c for c in best_seg_for_temp.get('text','') if c.isalnum()).lower()
					for bbox,text_val,prob in results:
						cand="".join(c for c in text_val if c.isalnum()).lower()
						if tgt and cand:
							score=difflib.SequenceMatcher(None,tgt,cand).ratio()
							if score>best_score:best_score=score;best_box=bbox;best_text_val=text_val
					if best_score<0.45:best_box=None
					if not best_box and len(results)==1:best_box=results[0][0];best_text_val=results[0][1]
					if best_box:
						bx=[p[0]for p in best_box];by=[p[1]for p in best_box]
						cand="".join(c for c in best_text_val if c.isalnum()).lower()
						idx_start=tgt.find(cand) if cand else -1
						if idx_start!=-1:left_missing=idx_start;right_missing=len(tgt)-(idx_start+len(cand))
						else:left_missing=0;right_missing=max(0,len(tgt)-len(cand))
						char_w=((max(bx)-min(bx))/scale)/max(len(cand),1)
						w_old=((max(bx)-min(bx))/scale)+((left_missing+right_missing)*char_w)
						h_template=(max(by)-min(by))/scale
						ppc=w_old/max(len(tgt),1);template_found=True;template_w=len(longest_txt)*ppc
		for idx,seg in enumerate(segs):
			if not A.auto_desub_running:break
			while getattr(A,'auto_desub_paused',False):
				if not A.auto_desub_running:break
				QApplication.processEvents();time.sleep(0.05)
			if not A.auto_desub_running:break
			st=seg.get('start',.0)
			if st>=dur:break
			en=min(dur,seg.get('end',.0));text=seg.get('text','');t_mid=(st+en)/2.;A.seek_time(t_mid);t0=time.time()
			while (abs(A.player.position() - t_mid*1000) > 300 or not getattr(A,'frame_updated',False)) and time.time()-t0<1.5:QApplication.processEvents();time.sleep(0.01)
			t_wait=time.time()
			while time.time()-t_wait<0.15:QApplication.processEvents();time.sleep(0.01)
			img=A.current_frame_img
			if img and not img.isNull()and A.auto_desub_running:
				img_format=QImage.Format.Format_RGB888;rgb_img=img.convertToFormat(img_format);w,h=rgb_img.width(),rgb_img.height();scale=A.image_scale;cx_min=max(0,int(min_x*scale));cx_max=min(w,int(max_x*scale));cy_min=max(0,int(min_y*scale));cy_max=min(h,int(max_y*scale))
				if cx_max>cx_min and cy_max>cy_min:
					ptr=rgb_img.bits();ptr.setsize(rgb_img.sizeInBytes());arr=np.frombuffer(ptr,dtype=np.uint8).reshape((h,w,3));crop=arr[cy_min:cy_max,cx_min:cx_max];results=reader.readtext(crop);best_box=None;best_score=0.0;best_text_val=""
					if use_text:
						tgt="".join(c for c in text if c.isalnum()).lower()
						for bbox,text_val,prob in results:
							cand="".join(c for c in text_val if c.isalnum()).lower()
							if tgt and cand:
								score=difflib.SequenceMatcher(None,tgt,cand).ratio()
								if score>best_score:best_score=score;best_box=bbox;best_text_val=text_val
						if best_score<0.45:best_box=None
						if not best_box and len(results)==1:best_box=results[0][0];best_text_val=results[0][1]
					else:
						if results:
							largest=max(results,key=lambda r:(r[0][2][0]-r[0][0][0])*(r[0][2][1]-r[0][0][1]))
							best_box=largest[0];best_text_val=largest[1]
					if best_box:
						bx=[p[0]for p in best_box];by=[p[1]for p in best_box]
						if use_text:
							cand="".join(c for c in best_text_val if c.isalnum()).lower()
							tgt="".join(c for c in text if c.isalnum()).lower()
							idx_start=tgt.find(cand) if cand else -1
							if idx_start!=-1:left_missing=idx_start;right_missing=len(tgt)-(idx_start+len(cand))
							else:left_missing=0;right_missing=max(0,len(tgt)-len(cand))
							char_w=((max(bx)-min(bx))/scale)/max(len(cand),1)
							b_min_x=(min(bx)+cx_min)/scale-(left_missing*char_w)
							b_max_x=(max(bx)+cx_min)/scale+(right_missing*char_w)
						else:
							b_min_x=(min(bx)+cx_min)/scale
							b_max_x=(max(bx)+cx_min)/scale
						if use_max_size and template_w is not None:
							base_cx=(b_min_x+b_max_x)/2.0
							b_min_x=base_cx-template_w/2.0
							b_max_x=base_cx+template_w/2.0
						b_min_y=(min(by)+cy_min)/scale;b_max_y=(max(by)+cy_min)/scale
						ow,oh=A._image_size();fb_min_x=max(.0,b_min_x-P);fb_max_x=min(float(ow),b_max_x+P);fb_min_y=max(.0,b_min_y-P);fb_max_y=min(float(oh),b_max_y+P);pts=[Point(fb_min_x,fb_min_y),Point(fb_max_x,fb_min_y),Point(fb_max_x,fb_max_y),Point(fb_min_x,fb_max_y)]
						st_val=max(.0,st-add_st);en_val=min(dur,en+add_en);area_new=(fb_max_x-fb_min_x)*(fb_max_y-fb_min_y);mid_new=(st+en)/2.
						for R in list(A.data.polygons):
							if max(st_val,R.start)<min(en_val,R.end):
								rx=[p.x for p in R.points];ry=[p.y for p in R.points];area_R=(max(rx)-min(rx))*(max(ry)-min(ry));mid_R=(R.start+R.end)/2.
								if mid_R<mid_new:
									if area_new>area_R:
										st_val=max(st_val,R.en_orig)
										R.end=st_val
									else:
										R.end=min(R.end,st)
										st_val=R.end
								else:
									if area_new>area_R:
										en_val=min(en_val,R.st_orig)
										R.start=en_val
									else:
										R.start=max(R.start,en)
										en_val=R.start
								if R.target_frames:R.target_frames[0].time=R.start;R.target_frames[-1].time=R.end
						A.data.polygons=[p for p in A.data.polygons if p.start<p.end]
						if st_val<en_val:
							track=0
							while A.check_overlap(st_val,en_val,track):track+=1
							tf=TargetFrame(x=sum(p.x for p in pts)/4.,y=sum(p.y for p in pts)/4.,time=en_val);new_rec=RecLine(start=st_val,end=en_val,points=pts,target_frames=[tf],track=track,st_orig=st,en_orig=en);new_rec.detected_text=best_text_val;A.data.polygons.append(new_rec);A.sync_data_to_widgets()
			A.prog_bar.setValue(int((idx+1)/total*100));QApplication.processEvents()
		A.auto_desub_running=False;A.auto_desub_paused=False;A.btn_stop.setText('Stop');A.selected_rec_idx=-1;A.selected_recs=set();A.sync_data_to_widgets()
	def start_auto_desub_all(A):
		A.toggle_play();A.toggle_play()
		if not hasattr(A,'transcribe_data')or not A.transcribe_data:return
		lang=A.txt_lang.text()or S.easyocr_reader;reader=easyocr.Reader([lang])
		segs=A.transcribe_data
		if isinstance(segs,dict):
			for k in ('segments','sentences','data','list','transcription'):
				if k in segs:segs=segs[k];break
			else:segs=list(segs.values())
		if not isinstance(segs,list):return
		segs=[s for s in segs if isinstance(s,dict)]
		total=len(segs)
		if not total:return
		A.save_state();A.auto_desub_running=True;A.auto_desub_paused=False;A.btn_stop.setText('Stop')
		xs=[pt.x for pt in A.range_points];ys=[pt.y for pt in A.range_points];min_x,max_x=int(min(xs)),int(max(xs));min_y,max_y=int(min(ys)),int(max(ys));P=A.spin_pad.value();dur=A.get_duration()or 99999.;add_st=A.spin_add_st.value();add_en=A.spin_add_en.value()
		for idx,seg in enumerate(segs):
			if not A.auto_desub_running:break
			while getattr(A,'auto_desub_paused',False):
				if not A.auto_desub_running:break
				QApplication.processEvents();time.sleep(0.05)
			if not A.auto_desub_running:break
			st=seg.get('start',.0)
			if st>=dur:break
			en=min(dur,seg.get('end',.0));t_mid=(st+en)/2.;A.seek_time(t_mid);t0=time.time()
			while (abs(A.player.position() - t_mid*1000) > 300 or not getattr(A,'frame_updated',False)) and time.time()-t0<1.5:QApplication.processEvents();time.sleep(0.01)
			t_wait=time.time()
			while time.time()-t_wait<0.15:QApplication.processEvents();time.sleep(0.01)
			img=A.current_frame_img
			if img and not img.isNull()and A.auto_desub_running:
				img_format=QImage.Format.Format_RGB888;rgb_img=img.convertToFormat(img_format);w,h=rgb_img.width(),rgb_img.height();scale=A.image_scale;cx_min=max(0,int(min_x*scale));cx_max=min(w,int(max_x*scale));cy_min=max(0,int(min_y*scale));cy_max=min(h,int(max_y*scale))
				if cx_max>cx_min and cy_max>cy_min:
					ptr=rgb_img.bits();ptr.setsize(rgb_img.sizeInBytes());arr=np.frombuffer(ptr,dtype=np.uint8).reshape((h,w,3));crop=arr[cy_min:cy_max,cx_min:cx_max];results=reader.readtext(crop)
					for bbox,text_val,prob in results:
						bx=[p[0]for p in bbox];by=[p[1]for p in bbox]
						b_min_x=(min(bx)+cx_min)/scale;b_max_x=(max(bx)+cx_min)/scale
						b_min_y=(min(by)+cy_min)/scale;b_max_y=(max(by)+cy_min)/scale
						ow,oh=A._image_size();fb_min_x=max(.0,b_min_x-P);fb_max_x=min(float(ow),b_max_x+P);fb_min_y=max(.0,b_min_y-P);fb_max_y=min(float(oh),b_max_y+P);pts=[Point(fb_min_x,fb_min_y),Point(fb_max_x,fb_min_y),Point(fb_max_x,fb_max_y),Point(fb_min_x,fb_max_y)]
						st_val=max(.0,st-add_st);en_val=min(dur,en+add_en)
						if st_val<en_val:
							track=0
							while A.check_overlap(st_val,en_val,track):track+=1
							tf=TargetFrame(x=sum(p.x for p in pts)/4.,y=sum(p.y for p in pts)/4.,time=en_val);new_rec=RecLine(start=st_val,end=en_val,points=pts,target_frames=[tf],track=track,st_orig=st,en_orig=en);new_rec.detected_text=text_val;A.data.polygons.append(new_rec)
					A.sync_data_to_widgets()
			A.prog_bar.setValue(int((idx+1)/total*100));QApplication.processEvents()
		A.auto_desub_running=False;A.auto_desub_paused=False;A.btn_stop.setText('Stop');A.selected_rec_idx=-1;A.selected_recs=set();A.sync_data_to_widgets()
	def keyPressEvent(A,event):
		B=event.key();mods=event.modifiers();C=A.media_view.mapFromGlobal(A.cursor().pos());D=A.timeline.mapFromGlobal(A.cursor().pos())
		if B==Qt.Key.Key_Z and (mods&Qt.KeyboardModifier.ControlModifier):
			if mods&Qt.KeyboardModifier.ShiftModifier:A.redo()
			else:A.undo()
			return
		if B==Qt.Key.Key_Space:
			if A.media_view.rect().contains(C)or A.timeline.rect().contains(D):A.toggle_play()
			return
		if B==Qt.Key.Key_Delete:
			if A.right_tabs.currentIndex()==1:A.delete_ass_text()
			else:A.delete_rectangle()
			return
		if B==Qt.Key.Key_V and not(mods&Qt.KeyboardModifier.ControlModifier):A.set_tool('V');return
		if B==Qt.Key.Key_G and not(mods&Qt.KeyboardModifier.ControlModifier):A.set_tool('G');return
		if B==Qt.Key.Key_B and not(mods&Qt.KeyboardModifier.ControlModifier):A.set_tool('B');return
		if B==Qt.Key.Key_B and(mods&Qt.KeyboardModifier.ControlModifier):A.cut_at_time(A.selected_rec_idx,A.get_current_time());return
		if B==Qt.Key.Key_C and(mods&Qt.KeyboardModifier.ControlModifier):A.copy_selected();return
		if B==Qt.Key.Key_V and(mods&Qt.KeyboardModifier.ControlModifier):A.paste_selected();return
		if B==Qt.Key.Key_I:
			if mods&Qt.KeyboardModifier.ShiftModifier:A.remove_keyframe_near_playhead()
			else:A.create_keyframe_at_playhead()
			return
	def ensure_style_dict(A,st):
		d=CoreData.create_default_style()
		if isinstance(st,dict):
			for k,v in d.items():
				if k not in st:st[k]=v
			return st
		if isinstance(st,str):
			p=st.split(',')
			if len(p)>=22:
				def c_to_h(c):
					cl=c.replace('&H','').replace('&','').strip().zfill(8)
					return f"#{cl[6:8]}{cl[4:6]}{cl[2:4]}"
				return {
					'font':p[1],'size':int(p[2]) if p[2].isdigit() else 69,'color':c_to_h(p[3]),'bordercolor':c_to_h(p[4]),'backcolor':c_to_h(p[5]),
					'bold':p[6] in('-1','1'),'italic':p[7] in('-1','1'),'underline':p[8] in('-1','1'),'strikeout':p[9] in('-1','1'),
					'scalex':int(p[10]) if p[10].isdigit() else 100,'scaley':int(p[11]) if p[11].isdigit() else 100,
					'spacing':float(p[12]) if p[12].replace('.','',1).isdigit() else 0.0,
					'angle':float(p[13]) if p[13].replace('.','',1).isdigit() else 0.0,
					'borderstyle':3 if p[14]=='3' else 1,
					'borderw':float(p[15]) if p[15].replace('.','',1).isdigit() else 1.0,
					'shadow':float(p[16]) if p[16].replace('.','',1).isdigit() else 2.0,
					'align':int(p[17]) if p[17].isdigit() else 2,
					'margin_l':int(p[18]) if p[18].isdigit() else 10,
					'margin_r':int(p[19]) if p[19].isdigit() else 10,
					'margin_v':int(p[20]) if p[20].isdigit() else 10,
					'encoding':int(p[21]) if p[21].isdigit() else 1
				}
		return d
	def init_ui(A):
		A.setStyleSheet('background-color: #121212; color: #ffffff; font-family: consolas;');H_split=QSplitter(Qt.Orientation.Horizontal);Z=QWidget();D=QVBoxLayout(Z);D.setContentsMargins(0,0,0,0);D.setSpacing(0)
		V_split=QSplitter(Qt.Orientation.Vertical);top_widget=QWidget();top_layout=QVBoxLayout(top_widget);top_layout.setContentsMargins(0,0,0,0);top_layout.setSpacing(0)
		A.media_view=MediaView(A);TimelineViews.setup_view(A.media_view, A.scene);top_layout.addWidget(A.media_view,stretch=3)
		K=QWidget();K.setFixedHeight(40);C=QHBoxLayout(K);C.setContentsMargins(5,0,5,0);C.addWidget(QLabel('Speed:'));A.spin_speed=QDoubleSpinBox();A.spin_speed.setRange(.25,10.);A.spin_speed.setSingleStep(.25);A.spin_speed.setValue(1.);A.spin_speed.setFocusPolicy(Qt.FocusPolicy.StrongFocus);A.spin_speed.setStyleSheet('max-width: 100px;');A.spin_speed.valueChanged.connect(A.on_speed_changed);C.addWidget(A.spin_speed);L=QPushButton('<< 5s');L.setFocusPolicy(Qt.FocusPolicy.NoFocus);L.setStyleSheet('background-color: #333333;padding: 3px; max-width: 60px;');L.clicked.connect(lambda:A.seek_relative(-5));C.addWidget(L);A.btn_play=QPushButton('Play');A.btn_play.setFocusPolicy(Qt.FocusPolicy.NoFocus);A.btn_play.setStyleSheet('background-color: #333333;padding: 3px; max-width: 60px;');A.btn_play.clicked.connect(A.toggle_play);C.addWidget(A.btn_play);M=QPushButton('5s >>');M.setFocusPolicy(Qt.FocusPolicy.NoFocus);M.setStyleSheet('background-color: #333333;padding: 3px; max-width: 60px;');M.clicked.connect(lambda:A.seek_relative(5));C.addWidget(M);C.addWidget(QLabel(' View Scale: '));N=QPushButton('+');N.setFocusPolicy(Qt.FocusPolicy.NoFocus);N.setStyleSheet('background-color: #444; max-width: 30px;');N.clicked.connect(lambda:A.zoom_view(1.2));C.addWidget(N);O=QPushButton('-');O.setFocusPolicy(Qt.FocusPolicy.NoFocus);O.setStyleSheet('background-color: #444; max-width: 30px;');O.clicked.connect(lambda:A.zoom_view(.8));C.addWidget(O);C.addWidget(QLabel(' Timeline Zoom: '));P=QPushButton('+');P.setFocusPolicy(Qt.FocusPolicy.NoFocus);P.setStyleSheet('background-color: #444; max-width: 30px;');P.clicked.connect(lambda:A.zoom_timeline(1.2));C.addWidget(P);Q=QPushButton('-');Q.setFocusPolicy(Qt.FocusPolicy.NoFocus);Q.setStyleSheet('background-color: #444; max-width: 30px;');Q.clicked.connect(lambda:A.zoom_timeline(.8));C.addWidget(Q);C.addWidget(QLabel('Time at: '));A.time_at=QDoubleSpinBox();A.time_at.setRange(0.0,9e6);A.time_at.setDecimals(3);A.time_at.setSingleStep(1.0);A.time_at.setValue(.0);A.time_at.setFocusPolicy(Qt.FocusPolicy.StrongFocus);A.time_at.setStyleSheet('max-width: 100px;');A.time_at.valueChanged.connect(A.on_time_changed);C.addWidget(A.time_at);C.addWidget(QLabel('/'));A.duration=QDoubleSpinBox();C.addWidget(A.duration);A.duration.setRange(.0,9e6);C.addStretch();top_layout.addWidget(K);V_split.addWidget(top_widget)
		A.timeline_container=QWidget();A.timeline_container.setFixedHeight(250);timeline_layout=QHBoxLayout(A.timeline_container);timeline_layout.setContentsMargins(0,0,0,0);timeline_layout.setSpacing(2);A.tools_panel=QWidget();A.tools_panel.setFixedWidth(60);tools_layout=QVBoxLayout(A.tools_panel);tools_layout.setContentsMargins(4,4,4,4);tools_layout.setSpacing(4)
		A.btn_select=QPushButton('Select (V)');A.btn_select.setFocusPolicy(Qt.FocusPolicy.NoFocus);A.btn_select.setCheckable(True);A.btn_select.setChecked(True);A.btn_select.clicked.connect(lambda:A.set_tool('V'));A.btn_select.setStyleSheet(S.btn_gray);tools_layout.addWidget(A.btn_select)
		A.btn_move=QPushButton('Move (G)');A.btn_move.setFocusPolicy(Qt.FocusPolicy.NoFocus);A.btn_move.setCheckable(True);A.btn_move.clicked.connect(lambda:A.set_tool('G'));A.btn_move.setStyleSheet(S.btn_gray);tools_layout.addWidget(A.btn_move)
		A.btn_cut=QPushButton('Cut (B)');A.btn_cut.setFocusPolicy(Qt.FocusPolicy.NoFocus);A.btn_cut.setCheckable(True);A.btn_cut.clicked.connect(lambda:A.set_tool('B'));A.btn_cut.setStyleSheet(S.btn_gray);tools_layout.addWidget(A.btn_cut);tools_layout.addStretch();timeline_layout.addWidget(A.tools_panel);A.timeline=TimelineWidget(A);timeline_layout.addWidget(A.timeline,stretch=1);V_split.addWidget(A.timeline_container);D.addWidget(V_split);H_split.addWidget(Z)
		a=QWidget();B_lay=QVBoxLayout(a);B_lay.setContentsMargins(8,8,8,8);B_lay.setSpacing(6)
		B_lay.addWidget(QLabel('Media & Config Import/Export:'))
		W=QPushButton('Import Video');W.setFocusPolicy(Qt.FocusPolicy.NoFocus);W.setStyleSheet('background-color: #2a2a2a; border: 1px solid #00f7ff; padding: 6px;');W.clicked.connect(A.import_video);B_lay.addWidget(W)
		B_lay.addStretch();H_split.addWidget(a);H_split.setSizes([950,400]);A.setCentralWidget(H_split)
		A.right_tabs=QTabWidget();B_lay.addWidget(A.right_tabs)
		tab_auto=AutoDesubPanel(A);SidePanels.configure_tab(A.right_tabs, tab_auto, 'Auto desub')
		tab_ass=SubtitlesPanel(A);SidePanels.configure_tab(A.right_tabs, tab_ass, 'Subtitles')
		A.set_auto_desub_active(False)


TAR_LANG = 'vi'
if __name__=='__main__':app=QApplication(sys.argv);window=MainWindow();window.show();sys.exit(app.exec())