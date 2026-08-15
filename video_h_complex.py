import os,re,sys,math,time,subprocess
from pathlib import Path
from typing import Optional,List, get_type_hints as N,get_origin as O,get_args as P
from dataclasses import dataclass,field,fields as L,is_dataclass as M
from src.utils import agr,ext,txt,logger as lg, get_media_duration, get_video_size,\
	handle_input, listFilter, r_json
from src.configuration import TAR_LANG, P_DIR, LANGS
import torch

WITH_MAX_SOURCE=True
cpu_threads = max(1, int(os.cpu_count() * 0.8)) # 80%
class MM:
	o_ff_filter=False
	ffmpeg_level='error'
	HARDWARE = [
		'-c:v', 'hevc_nvenc',
		'-preset', 'p1',
		'-rc', 'vbr',
		'-cq', '32',
		'-multipass', 'fullres',
		'-spatial-aq', '1',
		'-temporal-aq', '1',
		'-pix_fmt', 'p010le',
		'-threads', str(cpu_threads)
	] if torch.cuda.is_available() else [
		'-c:v', 'libx265',
		'-preset', 'medium',
		'-crf', '32',
		'-pix_fmt', 'yuv420p10le',
		'-threads', str(cpu_threads)
	]
class E:
	class TimelineManager:
			def __init__(self,ts:list['E2.Timestamp'],sd=0.0):
				self.mapping,self.total_dur=[],0.0
				if WITH_MAX_SOURCE or not ts:self.total_dur=sd
				else:
					for x in ts:self.mapping.append({'start':x.start,'end':x.end,'new':self.total_dur});self.total_dur+=x.end-x.start
			def to_new_t(self,ot):
				if WITH_MAX_SOURCE or not self.mapping:return ot
				for m in self.mapping:
					if m['start']<=ot<=m['end']:return m['new']+(ot-m['start'])
	@dataclass(frozen=False)
	class Data:
		@classmethod
		def parse(cls,d):
			if not isinstance(d,dict):return d
			th,k=N(cls),{}
			for r in L(cls):
				e=r.name
				if e not in d:continue
				a=d[e];b=th.get(e);s=O(b)
				if s is list:
					g=P(b)[0]
					if M(g)and hasattr(g,'parse'):a=[getattr(g,'parse')(x)for x in a]
				elif M(b)and hasattr(b,'parse'):a=getattr(b,'parse')(a)
				k[e]=a
			return cls(**k)
class E1:
	@dataclass
	class ass(E.Data):
		name: str = "Default"
		font: str = "Cambria"
		size: int = 99
		color: str = "#fff700"
		secondarycolor: str = "#00ffff" 
		bordercolor: str = "#000000"
		backcolor: str = "#00d4ff"
		bold: bool = False
		italic: bool = False
		underline: bool = False
		strikeout: bool = False
		scalex: int = 100
		scaley: int = 100
		spacing: float = 0.0
		angle: float = 0.0
		borderstyle: int = 1
		borderw: float = 5.0
		shadow: float = 6.0
		align: int = 2
		margin_l: int = 10
		margin_r: int = 10
		margin_v: int = 10
		encoding: int = 1
		wrap_style: int = 2
class E2:
	@dataclass
	class Timestamp(E.Data):start:float;end:float
	@dataclass
	class Point(E.Data):x:int;y:int
	@dataclass
	class TsImage(Timestamp):
		path:Path
		scale:float=1.0
		opacity:float=1.0
		focus:'E2.Point' = field(default_factory=lambda: E2.Point(0, 0))
		@staticmethod
		def build_images(vc,imgs:list['E2.TsImage'],tm:'E.TimelineManager',imap:list[int],W:int,H:int):
			fv=[]
			for i,(img,idx) in enumerate(zip(imgs,imap)):
				t=tm.to_new_t(img.start)
				if t is None:continue
				te=tm.to_new_t(img.end) or (t+(img.end-img.start))
				fx,fy=max(0,min(img.focus.x,W)),max(0,min(img.focus.y,H))
				fv.append(f"[{idx}:v]scale=w=iw*{img.scale}:h=-2,format=rgba,colorchannelmixer=aa={img.opacity},setpts=PTS-STARTPTS[sc{i}]")
				fv.append(f"[{vc}][sc{i}]overlay=x={fx}-w/2:y={fy}-h/2:enable='between(t,{t:.3f},{te:.3f})'[vim{i}]")
				vc=f"vim{i}"
			return ";\n".join(fv),vc
	@dataclass(frozen=False)
	class TargetFrames(Timestamp,Point):None
	@dataclass(frozen=False)
	class Polygon(Timestamp,E.Data):
		points:list['E2.Point']=field(default_factory=list)
		target_frames:list['E2.TargetFrames']=field(default_factory=list)
	@dataclass(frozen=False)
	class TsAudio:
		start:float=0;end:float=0
		path:Path;volume:float=1.0;fade:float=0.0
		sst:float=0.0;sen:float=0.0
		pitch:float=1.0;atempo:float=1.0;is_loop:bool=False
		@property
		def path(self) -> Path: return self._path
		@path.setter
		def path(self, value: Path):self._path = value;self.end = get_media_duration(str(value))
	@dataclass(frozen=False)
	class TsText(Timestamp):text:str
	@dataclass(frozen=False)
	class TsSubtitle(TsText, E.Data):
		x:int=0
		y:int=0
		style_ass:E1.ass=field(default_factory=E1.ass)
		track:int=0
class mdl:
	def _build_video_trim(ts:List[E2.Timestamp],W:int,H:int):
		sc=f"scale={W}:{H},setsar=1"
		if WITH_MAX_SOURCE or not ts:return f"[0:v]{sc}[vbase]","vbase"
		v_expr=" + ".join([f"between(t,{t.start},{t.end})" for t in ts])
		return f"[0:v]select='{v_expr}',setpts=N/FRAME_RATE/TB,{sc}[vbase]","vbase"
	def _build_movement_blurs(vc,blurs:list[E2.Polygon],tm:E.TimelineManager,W:int,H:int):
		fv,f_idx,m=[],0,4
		for b in blurs:
			pts=b.points
			if not pts:continue
			min_x,max_x=min(p.x for p in pts),max(p.x for p in pts)
			min_y,max_y=min(p.y for p in pts),max(p.y for p in pts)
			w,h=max(1,min(int(max_x-min_x),W-2*m)),max(1,min(int(max_y-min_y),H-2*m))
			cx,cy=sum(p.x for p in pts)/4.0,sum(p.y for p in pts)/4.0
			off_x,off_y=cx-min_x,cy-min_y
			if not b.target_frames:
				st=tm.to_new_t(b.start);en=tm.to_new_t(b.end)or(st+(b.end-b.start))
				if en-st<=0:continue
				x,y=max(m,min(int(round(min_x)),W-w-m)),max(m,min(int(round(min_y)),H-h-m))
				vn=f"vbl{f_idx}";fv.append(f"[{vc}]delogo=x={x}:y={y}:w={w}:h={h}:enable='between(t,{st:.3f},{en:.3f})'[{vn}]");vc,f_idx=vn,f_idx+1
				continue
			tfs=sorted(b.target_frames,key=lambda tf:getattr(tf,'end',getattr(tf,'time',.0)))
			st_head=tm.to_new_t(b.start);en_head=tm.to_new_t(getattr(tfs[0],'end',getattr(tfs[0],'time',.0)))
			if en_head>st_head:
				x0,y0=max(m,min(int(round(tfs[0].x-off_x)),W-w-m)),max(m,min(int(round(tfs[0].y-off_y)),H-h-m))
				vn=f"vbl{f_idx}";fv.append(f"[{vc}]delogo=x={x0}:y={y0}:w={w}:h={h}:enable='between(t,{st_head:.3f},{en_head:.3f})'[{vn}]");vc,f_idx=vn,f_idx+1
			for i in range(len(tfs)-1):
				st=tm.to_new_t(getattr(tfs[i],'end',getattr(tfs[i],'time',.0)))
				en=tm.to_new_t(getattr(tfs[i+1],'end',getattr(tfs[i+1],'time',.0)))
				dur=en-st
				if dur<=0:continue
				p1_x,p1_y=tfs[i].x-off_x,tfs[i].y-off_y
				p2_x,p2_y=tfs[i+1].x-off_x,tfs[i+1].y-off_y
				if int(round(p1_x))==int(round(p2_x))and int(round(p1_y))==int(round(p2_y)):
					x=max(m,min(int(round(p1_x)),W-w-m));y=max(m,min(int(round(p1_y)),H-h-m))
					vn=f"vbl{f_idx}";fv.append(f"[{vc}]delogo=x={x}:y={y}:w={w}:h={h}:enable='between(t,{st:.3f},{en:.3f})'[{vn}]");vc,f_idx=vn,f_idx+1
				else:
					steps=max(1,int(round(dur*10)));dt=dur/steps
					for k in range(steps):
						ts_k,te_k=st+k*dt,st+(k+1)*dt;frac=(k+0.5)/steps
						xk=max(m,min(int(round(p1_x+frac*(p2_x-p1_x))),W-w-m))
						yk=max(m,min(int(round(p1_y+frac*(p2_y-p1_y))),H-h-m))
						vn=f"vbl{f_idx}";fv.append(f"[{vc}]delogo=x={xk}:y={yk}:w={w}:h={h}:enable='between(t,{ts_k:.3f},{te_k:.3f})'[{vn}]");vc,f_idx=vn,f_idx+1
			st_tail=tm.to_new_t(getattr(tfs[-1],'end',getattr(tfs[-1],'time',.0)));en_tail=tm.to_new_t(b.end)or(st_tail+(b.end-getattr(tfs[-1],'end',getattr(tfs[-1],'time',.0))))
			if en_tail>st_tail:
				xt,yt=max(m,min(int(round(tfs[-1].x-off_x)),W-w-m)),max(m,min(int(round(tfs[-1].y-off_y)),H-h-m))
				vn=f"vbl{f_idx}";fv.append(f"[{vc}]delogo=x={xt}:y={yt}:w={w}:h={h}:enable='between(t,{st_tail:.3f},{en_tail:.3f})'[{vn}]");vc,f_idx=vn,f_idx+1
		return ";\n".join(fv),vc
	def _build_audios(audios:List[E2.TsAudio],tm:E.TimelineManager,aud_map):
		fa,valid_audios,with_max_source=[],[],globals().get('WITH_MAX_SOURCE',False)
		SR=44100
		for i,(a,idx) in enumerate(zip(audios,aud_map)):
			if with_max_source or not tm.mapping:t_start=a.start
			else:
				best_m,max_ov=None,-1
				for m in tm.mapping:
					ov=min(a.end,m['end'])-max(a.start,m['start'])
					if ov>max_ov:max_ov,best_m=ov,m
				if not best_m or max_ov<=-1*(a.end-a.start):
					min_d=float('inf')
					for m in tm.mapping:
						d=min(abs(a.start-m['start']),abs(a.start-m['end']))
						if d<min_d:min_d,best_m=d,m
				if not best_m:continue
				t_start=best_m['new']+(a.start-best_m['start'])
			s_dur=(a.sen-a.sst) if a.sen>a.sst else (get_media_duration(a.path)-a.sst)
			max_possible_dur=s_dur/a.atempo if a.atempo>0 else s_dur
			t_dur=a.end-a.start
			if t_start<0:t_dur+=t_start;t_start=0.0
			t_dur=min(t_dur,max_possible_dur,tm.total_dur-t_start)
			if t_dur<=0.001:continue
			flt=[]
			if a.sen>a.sst:flt.append(f"atrim=start={a.sst:.3f}:end={a.sen:.3f},asetpts=PTS-STARTPTS")
			elif a.sst>0:flt.append(f"atrim=start={a.sst:.3f},asetpts=PTS-STARTPTS")
			if a.is_loop and s_dur>0:flt.append(f"aloop=loop=-1:size={int(s_dur*SR)}")
			if abs(a.pitch-1.0)>0.01:flt.append(f"rubberband=pitch={a.pitch:.3f}")
			sp=a.atempo
			if abs(sp-1.0)>0.01:
				while sp>2.0:flt.append("atempo=2.0");sp/=2.0
				while sp<0.5:flt.append("atempo=0.5");sp/=0.5
				flt.append(f"atempo={sp:.3f}")
			flt.append(f"atrim=0:{t_dur:.3f},asetpts=PTS-STARTPTS,volume={a.volume:.3f}")
			if a.fade>0:
				fd=min(a.fade,t_dur/2)
				flt.append(f"afade=t=in:start=0:d={fd:.3f},afade=t=out:start={t_dur-fd:.3f}:d={fd:.3f}")
			fa.append(f"[{idx:d}:a]{','.join(flt)}[processed{i}]")
			valid_audios.append((i,t_start))
		fa.append(f"anullsrc=cl=stereo:r={SR}:d={tm.total_dur:.3f}[bg_silent]")
		mix_tags=["[bg_silent]"]
		for i,t_start in valid_audios:
			ms=int(t_start*1000)
			fa.append(f"[processed{i}]adelay={ms}|{ms}[delayed{i}]")
			mix_tags.append(f"[delayed{i}]")
		fa.append(f"{''.join(mix_tags)}amix=inputs={len(mix_tags)}:duration=longest:dropout_transition=0:normalize=0[amix_flat]")
		fa.append(f"[amix_flat]alimiter=limit=0.95:level=1[aout]")
		return ';\n'.join(fa)
	def _build_subtitles(vc,subs:List[E2.TsSubtitle]|str,W:int,H:int,source:Path):
		A='utf-8-sig';ass_path=source.with_suffix('')/f"{source.stem}.ass"
		
		def get_safe_path(p):
			abs_path = p.resolve().as_posix()
			if ":" in abs_path:
				drive, path_part = abs_path.split(":", 1)
				return f"{drive}\\:{path_part}"
			return abs_path

		if isinstance(subs,str):
			with open(ass_path,'w',encoding=A)as f:f.write(subs)
			safe_path = get_safe_path(ass_path)
			vn = "vsub"
			filter_str = f"[{vc}]subtitles='{safe_path}'[{vn}]"
			return filter_str, vn, ass_path

		def fmt_t(seconds):hours=int(seconds//3600);minutes=int(seconds%3600//60);secs=seconds%60;return f"{hours}:{minutes:02d}:{secs:05.2f}"
		def c_conv(hex_str):
			hex_str=hex_str.lstrip('#')
			if len(hex_str)==6:r,g,b=hex_str[0:2],hex_str[2:4],hex_str[4:6];return f"&H00{b}{g}{r}&"
			return'&H00FFFF00&'
		
		ass_lines=['[Script Info]','ScriptType: v4.00+',f"PlayResX: {W}",f"PlayResY: {H}",'ScaledBorderAndShadow: yes','','[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding, WrapStyle'];styles_dict={}
		for sub in subs:
			s=sub.style_ass;s_name=s.name
			if s_name not in styles_dict:styles_dict[s_name]=f"Style: {s_name},{s.font},{s.size},{c_conv(s.color)},{c_conv(s.secondarycolor)},{c_conv(s.bordercolor)},{c_conv(s.backcolor)},{-1 if s.bold else 0},{-1 if s.italic else 0},{-1 if s.underline else 0},{-1 if s.strikeout else 0},{s.scalex},{s.scaley},{s.spacing},{s.angle},{s.borderstyle},{s.borderw},{s.shadow},{s.align},{s.margin_l},{s.margin_r},{s.margin_v},{s.encoding},{s.wrap_style}"
		ass_lines.extend(styles_dict.values());ass_lines.extend(['','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text'])
		for sub in subs:start_str=fmt_t(sub.start);end_str=fmt_t(sub.end);s_name=sub.style_ass.name;pos_tag=f"{{\\pos({sub.x},{sub.y})}}";sanitized_text=sub.text.replace('\n','\\N');dialogue=f"Dialogue: 0,{start_str},{end_str},{s_name},,0,0,0,,{pos_tag}{sanitized_text}";ass_lines.append(dialogue)
		
		with open(ass_path,'w',encoding=A)as f:f.write('\n'.join(ass_lines))
		
		safe_path = get_safe_path(ass_path)
		vn = "vsub"
		filter_str = f"[{vc}]subtitles='{safe_path}'[{vn}]"
		return filter_str, vn, ass_path
	def get_mean_db(file_path:str):
		cmd = ['ffmpeg',
 '-i', file_path,
 '-filter:a', 'volumedetect',
 '-f', 'null', '/dev/null']
		result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
		match = re.search(r"mean_volume: ([-+]?\d*\.\d+|\d+) dB", result.stderr)
		return float(match.group(1)) if match else 0.0
	def volume_balancer(audios: list[E2.TsAudio]):
		db_values = [mdl.get_mean_db(a.path) for a in audios]
		db_base = db_values[0]
		for i in range(len(audios)):
			db_diff = db_base - db_values[i]
			amplitude_factor = math.pow(10, db_diff / 20)
			audios[i].volume = amplitude_factor * audios[i].volume
		return audios

def video_complex(
    source: Path,
    timestamps: Optional[List[E2.Timestamp]],
    audios: Optional[List[E2.TsAudio]],
    subtitles: Optional[List[E2.TsSubtitle]]=None,
    images: Optional[List[E2.TsImage]]=None,
    blurs: Optional[List[E2.Polygon]]=None,
    target: Optional[Path] = None
) -> Path:
	target=target or source.with_name(source.stem+'_h.mp4')
	if target.exists(): return target
	W,H=get_video_size(source);tm=E.TimelineManager(timestamps,get_media_duration(source));ui=[]
	get_idx=lambda p,lp:ui.index((str(p),lp))+1 if (str(p),lp) in ui else (ui.append((str(p),lp)) or len(ui))
	img_map=[get_idx(i.path,str(i.path).lower().endswith('.gif')) for i in (images or [])]
	aud_map=[get_idx(a.path,a.is_loop) for a in (audios or [])]
	base_dir=source.parent;cmd=['ffmpeg','-y']
	hw_in=[x for i,x in enumerate(MM.HARDWARE) if x=='-hwaccel' or (i>0 and MM.HARDWARE[i-1]=='-hwaccel')]
	cmd+=hw_in
	if getattr(MM,'ffmpeg_level',None):cmd+=['-loglevel',MM.ffmpeg_level]
	cmd+=['-i',os.path.relpath(source,base_dir)]
	for p,loop in ui:
		if str(p).lower().endswith('.gif'):cmd+=['-ignore_loop','0']
		elif loop:cmd+=['-stream_loop','-1']
		cmd+=['-i',os.path.relpath(Path(p),base_dir)]
	fg=[];ft,v_c=mdl._build_video_trim(timestamps,W,H)
	if ft:fg.append(ft)
	if blurs:f,v_c=mdl._build_movement_blurs(v_c,blurs,tm,W,H);fg.append(f)
	if images:f,v_c=E2.TsImage.build_images(v_c,images,tm,img_map,W,H);fg.append(f)
	if subtitles:
		f,v_temp,p_ass=mdl._build_subtitles(v_c,subtitles,W,H,source)
		if f:fg.append(f);v_c=v_temp
	fg.append(mdl._build_audios(audios or [],tm,aud_map))
	fpath=source.parent/source.stem/f"{source.stem}_filter.text"
	fpath.parent.mkdir(parents=True,exist_ok=True)
	with open(fpath,'w',encoding='utf-8') as f:f.write(";\n".join(filter(None,fg)))
	cmd+=['-filter_complex_script',os.path.relpath(fpath,base_dir),'-map',f'[{v_c}]','-map','[aout]']
	cmd+=[x for x in MM.HARDWARE if x not in hw_in]
	cmd+=['-c:a','aac','-b:a','192k','-t',f'{tm.total_dur:.3f}',os.path.relpath(target,base_dir),'-progress','pipe:1']

	proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,universal_newlines=True,cwd=base_dir)
	dur=round(tm.total_dur,2)
	t0=time.time()
	while True:
		line=proc.stdout.readline()
		if not line and proc.poll() is not None:break
		if "out_time_us=" in line:
			try:
				curr=int(line.strip().split('=')[1])/1e6
				elap=time.time()-t0
				eta=(dur-curr)*(elap/curr) if curr>0 else 0
				h,r=divmod(int(eta),3600)
				m,s=divmod(r,60)
				lg.pr(round(curr,2),dur,txt='VIDEO-RENDERING...',sfx=f"{(curr/dur):.2f}% ({h}h:{m}m:{s}s)",b_col=lg.C,tab=3)
			except:pass
	txt.green('✅ Render successfully!')
	if proc.returncode!=0:raise subprocess.CalledProcessError(proc.returncode,cmd)
	if not MM.o_ff_filter:
		fpath.unlink(True)
		if subtitles:p_ass.unlink(True)
	return target

def exec(source:Path, name:str, langs:list[str], target:Path=None):
	if not source or not source.exists(): return 'Source is not exist!'
	parse = lambda pth,T: callable(txt.green if pth.exists() else txt.gray)(f'READ: {pth}') or ([T.parse(d) for d in r_json(str(pth))] if pth.exists() else [])
	dr = (source.with_suffix('')/name)

	timestamps:Optional[List[E2.Timestamp]]	=	parse(dr.with_suffix('.json'), E2.Timestamp)
	audios:Optional[List[E2.TsAudio]]		=	[
		E2.TsAudio(path=p, volume=v)
		for (p,v) in [
			(dr.with_name(f'{name}_music.mp3'), 2.0),
			(dr.with_name(f'{name}.{TAR_LANG}.mp3'), 2.0)
		] if p.exists()
	]
	subtitles:Optional[List[E2.TsSubtitle]]	=	parse(dr.with_name('ass_data.json'), E2.TsSubtitle)
	images:Optional[List[E2.TsImage]]		=	[
		# E2.TsImage(0,timestamps[-1].end,Path(r"D:\vds\original.gif"),.5,.25, E2.Point(430,768))
	]
	blurs:Optional[List[E2.Polygon]]		= 	parse(dr.with_name('blurs.json'), E2.Polygon)
	target:Optional[Path]					=	dr.with_name(f'{name}_h.mp4')


	#=============================================
	output = video_complex(source, timestamps, audios, subtitles, images, blurs, target)
	txt.magenta(output)
	

if __name__ == '__main__':
    args = handle_input(
        agr(('-i','--input'), type=str, required=False, default=P_DIR),
        agr(('-l','--language'), type=str, required=False,default=','.join(LANGS))
    ) 
    path,l=Path(args.input),str(args.language).split(',')
    if not path.exists() or not l: sys.exit(0)

    if path.is_dir():
        for i, n in enumerate(listFilter(path, ext.VIDEO), 1):
            x=(path/n);exec(x,x.stem, l)
    elif path.is_file() and str(path).endswith(ext.VIDEO):
        exec(path,path.stem,l)