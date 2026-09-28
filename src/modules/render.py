import subprocess, textwrap, copy, os, re
from datetime import timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from src.enties import *
from src.utils.video import get_media_duration, get_video_size
from src.configuration import FFMPEG
from src.utils.file import r_json
from src.utils import logger as LG

_cfg_path = Path(FFMPEG) if FFMPEG else None
_ff_data: dict = r_json(str(_cfg_path)) if _cfg_path and _cfg_path.exists() else {}

class MM:
    BIN: str = _ff_data.get('bin', 'ffmpeg')
    HARDWARE: list[str] = _ff_data.get('hardware', [])
    ffmpeg_level: str = _ff_data.get('ffmpeg_level', 'error')
    o_ff_filter: bool = _ff_data.get('o_ff_filter', False)

class is_use:
    hibernate_when_done = -1
    render_video = True
    trans_voice_atempo = 1.
    trans_voice_pitch = 1.
    rebuild_audio = True
    p_gif = False
    a_logo = False
    base_voice = False
    base_music = True
    trans_voice = True
    delogo = False
    desubs = True
    desubs_max = True
    subtitle = True
    o_ff_filter = False
    o_cre_srt = True

WITH_MAX_SOURCE = True

class TimelineManager:
    def __init__(self, timestamps: Optional[List[Timestamp]], source_dur: float = .0):
        self.mapping, self.total_dur = [], .0
        if not timestamps: self.total_dur = source_dur
        else:
            for ts in timestamps:
                start_t = getattr(ts, 'target', getattr(ts, 'start', .0))
                duration = getattr(ts, 'duration', getattr(ts, 'end', .0) - start_t)
                self.mapping.append({'st': start_t, 'en': start_t + duration, 'new': self.total_dur})
                self.total_dur += duration
    def to_new_t(self, old_t: float) -> Optional[float]:
        if not self.mapping: return old_t
        for m in self.mapping:
            if m['st'] <= old_t <= m['en']: return m['new'] + (old_t - m['st'])
        return None

def to_ass_time(seconds: float) -> str:
    td = timedelta(seconds=max(.0, seconds))
    h, m, s = int(td.total_seconds() // 3600), int(td.total_seconds() % 3600 // 60), int(td.total_seconds() % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100: s += 1; cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def _color_to_ass(color_obj) -> str:
    hex_color = ""
    if isinstance(color_obj, Solid): hex_color = color_obj.value.lstrip('#')
    elif isinstance(color_obj, Gradian) and color_obj.values: hex_color = color_obj.values[0].lstrip('#')
    elif isinstance(color_obj, str): hex_color = color_obj.lstrip('#')
    if len(hex_color) == 6: r, g, b, a = hex_color[0:2], hex_color[2:4], hex_color[4:6], '00'
    elif len(hex_color) == 8: r, g, b, a = hex_color[0:2], hex_color[2:4], hex_color[4:6], hex_color[6:8]
    else: return '&H00FFFFFF'
    return f"&H{a}{b}{g}{r}"

def _html_to_ass_tags(text: str, default_color_ass: str) -> str:
    text = text.replace('<\\font>', '</font>').replace('”', '"').replace('“', '"')
    def _replace_font(match):
        hex_color = match.group(1).lstrip('#')
        content = match.group(2)
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"{{\\c&H{b}{g}{r}&}}{content}{{\\c{default_color_ass}&}}"
        return content
    pattern = '<font\\s+color\\s*=\\s*["\\\']?#?([0-9a-fA-F]{6})["\\\']?\\s*>(.*?)</font>'
    text = re.sub(pattern, _replace_font, text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub('</?font[^>]*>', '', text, flags=re.IGNORECASE)

def create_ass_file(subs: List[Transcribe], W: int, H: int, style_cfg: Subtitle, output_path: Path, tm: Optional[TimelineManager] = None):
    fnt = Path(style_cfg.font.name).stem
    color, bordercolor, shadowcolor = _color_to_ass(style_cfg.color.primary), _color_to_ass(style_cfg.color.outline), _color_to_ass(style_cfg.color.shadow)
    alignment_val = style_cfg.alignment.value if hasattr(style_cfg.alignment, 'value') else 2
    scale_factor = min(W, H) / 1080.0
    margin_v, margin_lr = max(20, round(H * 0.065)), max(15, round(W * 0.05))
    pos_y = H - margin_v
    outline_w, shadow_d = max(1, round(style_cfg.outline_width * scale_factor)), max(0, round(style_cfg.shadow_depth * scale_factor))
    header = textwrap.dedent(f"""
    [Script Info]
    ScriptType: v4.00+
    PlayResX: {W}
    PlayResY: {H}
    WrapStyle: 0
    ScaledBorderAndShadow: yes

    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,{fnt},{style_cfg.font.size},{color},{bordercolor},{shadowcolor},{1 if style_cfg.font.bold else 0},{1 if style_cfg.font.italic else 0},{1 if style_cfg.font.underline else 0},{1 if style_cfg.font.strikeout else 0},{style_cfg.font.scaleX},{style_cfg.font.scaleY},{style_cfg.font.spacing},{style_cfg.font.angle},1,{outline_w},{shadow_d},{alignment_val},{margin_lr},{margin_lr},{margin_v},1
    """)
    lines = [header.strip(), '\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    default_c = color.replace('&H', '').replace('&', '')
    if len(default_c) == 8: default_c = default_c[2:]
    for s in subs:
        raw_text = getattr(s, 'text', '') or ''
        clean_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        if not clean_lines: continue
        st = getattr(s, 'start', getattr(s, 'start_time', .0))
        en = getattr(s, 'end', getattr(s, 'end_time', .0))
        if tm and tm.mapping:
            mst, men = tm.mapping[0]['st'], tm.mapping[-1]['en']
            if en <= mst or st >= men: continue
            st, en = max(.0, st - mst), min(tm.total_dur, en - mst)
        txt = '\\N'.join(clean_lines).replace("'", '’')
        txt = _html_to_ass_tags(txt, default_c)
        lines.append(f"Dialogue: 0,{to_ass_time(st)},{to_ass_time(en)},Default,,0,0,0,,{{\\an2\\pos({W // 2},{pos_y})}}{txt}")
    with open(output_path, 'w', encoding='utf-8') as f: f.write('\n'.join(lines))

def build_video_trim(timestamps: Optional[List[Timestamp]], W: int, H: int) -> Tuple[str, str]:
    sc = f"scale={W}:{H},setsar=1"
    if not timestamps: return f"[0:v]{sc}[vbase]", 'vbase'
    v_expr = ' + '.join([f"between(t,{getattr(t,'target',getattr(t,'start',.0))},{getattr(t,'target',getattr(t,'start',.0))+getattr(t,'duration',getattr(t,'end',.0)-getattr(t,'start',.0))})" for t in timestamps])
    return f"[0:v]select='{v_expr}',setpts=N/FRAME_RATE/TB,{sc}[vbase]", 'vbase'

def build_movement_blurs(v_cur: str, blurs: list, tm: TimelineManager, W: int, H: int) -> Tuple[str, str]:
    fv, f_idx, FPS = [], 0, 15
    for dk in blurs:
        if not getattr(dk, 'keyframes', None): continue
        kfs = sorted(dk.keyframes, key=lambda k: k.t); w, h, bb = min(dk.width, W - 2), min(dk.height, H - 2), max(1, getattr(dk, 'boxblur', 1))
        mode = getattr(dk, 'mode', 'delogo')
        if hasattr(mode, 'value'): mode = mode.value
        col = str(getattr(dk, 'color', 'black')).replace('#', '0x')
        for i in range(len(kfs) - 1 if len(kfs) > 1 else 1):
            k1 = kfs[i]; k2 = kfs[i + 1] if len(kfs) > 1 else k1; st, en = k1.t, (k2.t if len(kfs) > 1 else tm.total_dur)
            if tm.mapping:
                mst, men = tm.mapping[0]['st'], tm.mapping[-1]['en']
                if en <= mst or st >= men: continue
                act_st, act_en = max(st, mst), min(en, men)
                t1, t2 = max(.0, act_st - mst), min(tm.total_dur, act_en - mst)
            else:
                act_st, act_en = st, en
                t1, t2 = st, en
            dt = t2 - t1
            if dt <= 0.001 and len(kfs) > 1: continue
            dur_orig = max(1e-4, en - st) if len(kfs) > 1 else 1.0
            r1 = (act_st - st) / dur_orig if len(kfs) > 1 else .0
            r2 = (act_en - st) / dur_orig if len(kfs) > 1 else .0
            sx, sy = int(k1.x + (k2.x - k1.x) * r1), int(k1.y + (k2.y - k1.y) * r1)
            ex, ey = int(k1.x + (k2.x - k1.x) * r2), int(k1.y + (k2.y - k1.y) * r2)
            
            # sx, sy là tâm (focus) -> quy đổi sang góc trái trên: x - w//2, y - h//2
            tl_sx, tl_sy = sx - w // 2, sy - h // 2
            tl_ex, tl_ey = ex - w // 2, ey - h // 2

            if mode == 'delogo':
                is_static = (sx == ex and sy == ey)
                steps = 1 if is_static else max(1, int(dt * FPS))
                step_t = dt / steps
                for s in range(steps):
                    ts, te = t1 + s * step_t, t1 + (s + 1) * step_t
                    a = s / max(1, steps - 1) if steps > 1 else .0
                    cur_cx = int(sx + (ex - sx) * a)
                    cur_cy = int(sy + (ey - sy) * a)
                    cx = max(1, min(cur_cx - w // 2, W - w - 1))
                    cy = max(1, min(cur_cy - h // 2, H - h - 1))
                    v_next = f"vbl{f_idx}"
                    fv.append(f"[{v_cur}]delogo=x={cx}:y={cy}:w={w}:h={h}:enable='between(t,{ts:.3f},{te:.3f})'[{v_next}]")
                    v_cur = v_next; f_idx += 1
            else:
                x1, y1 = max(1, min(tl_sx, W - w - 1)), max(1, min(tl_sy, H - h - 1))
                x2, y2 = max(1, min(tl_ex, W - w - 1)), max(1, min(tl_ey, H - h - 1))
                xe = f"{x1}" if x1 == x2 else f"clip({x1}+({x2-x1})*(t-{t1:.3f})/{dt:.3f},1,{W-w-1})"
                ye = f"{y1}" if y1 == y2 else f"clip({y1}+({y2-y1})*(t-{t1:.3f})/{dt:.3f},1,{H-h-1})"
                if mode == 'solid':
                    v_next = f"vbl{f_idx}"
                    fv.append(f"[{v_cur}]drawbox=x='{xe}':y='{ye}':w={w}:h={h}:color={col}:t=fill:enable='between(t,{t1:.3f},{t2:.3f})'[{v_next}]")
                else:
                    vm, vc, vb, v_next = f"vm{f_idx}", f"vc{f_idx}", f"vb{f_idx}", f"vbl{f_idx}"
                    fv.append(f"[{v_cur}]split=2[{vm}][{vc}]")
                    if mode == 'pixelate': fv.append(f"[{vc}]crop=w={w}:h={h}:x='{xe}':y='{ye}',scale=iw/10:ih/10,scale={w}:{h}:flags=neighbor[{vb}]")
                    elif mode == 'gblur': fv.append(f"[{vc}]crop=w={w}:h={h}:x='{xe}':y='{ye}',gblur=sigma={bb}[{vb}]")
                    else: fv.append(f"[{vc}]crop=w={w}:h={h}:x='{xe}':y='{ye}',boxblur={bb}[{vb}]")
                    fv.append(f"[{vm}][{vb}]overlay=x='{xe}':y='{ye}':enable='between(t,{t1:.3f},{t2:.3f})'[{v_next}]")
                v_cur = v_next; f_idx += 1
    return ';\n'.join(fv), v_cur

def build_images(v_cur: str, images: List[Clip_Video], tm: TimelineManager, img_map: List[int], W: int, H: int) -> Tuple[str, str]:
    fv = []
    for i, (img, idx) in enumerate(zip(images, img_map)):
        t = tm.to_new_t(img.source.start)
        if t is None: continue
        te = tm.to_new_t(img.source.end) or (t + (img.source.end - img.source.start))
        fx, fy = max(0, min(img.focus.x, W)), max(0, min(img.focus.y, H))
        fv.append(f"[{idx}:v]scale=w=iw*{img.scale}:h=-2,format=rgba,colorchannelmixer=aa={img.opacity},setpts=PTS-STARTPTS[sc{i}]")
        fv.append(f"[{v_cur}][sc{i}]overlay=x={fx}-w/2:y={fy}-h/2:enable='between(t,{t:.3f},{te:.3f})'[vim{i}]")
        v_cur = f"vim{i}"
    return ';\n'.join(fv), v_cur

def build_audios(audios: List[Clip_Audio], tm: TimelineManager, aud_map: List[int]) -> str:
    fa, valid_audios, TARGET_SAMPLE_RATE = [], [], 44100
    for i, (a, idx) in enumerate(zip(audios, aud_map)):
        if a.volume <= 0.0001: continue
        if a.source.end <= a.source.start and a.source.path and Path(a.source.path).exists():
            a.source.end = a.source.start + get_media_duration(Path(a.source.path))
        s_dur = a.source.end - a.source.start
        if s_dur <= 0.001: continue
        flt = []
        if tm.mapping:
            mst, men = tm.mapping[0]['st'], tm.mapping[-1]['en']
            ast, aen = max(a.source.start, mst), min(a.source.end, men)
            if aen <= ast: continue
            flt.append(f"atrim=start={ast:.3f}:end={aen:.3f},asetpts=PTS-STARTPTS")
            t_start = max(.0, a.source.start - mst)
        else:
            t_start = a.source.start
            if a.source.start > 0 or a.source.end > 0: flt.append(f"atrim=start={a.source.start:.3f}:end={a.source.end:.3f},asetpts=PTS-STARTPTS")
        p = a.pitch
        if p > 0 and abs(p - 1.) > 0.01: flt.append(f"rubberband=pitch={p:.3f}")
        elif p < 0: flt.append(f"rubberband=pitch={2.**(p/12.):.3f}")
        sp = a.tempo
        if sp > 0 and abs(sp - 1.) > 0.01:
            while sp > 2.: flt.append('atempo=2.0'); sp /= 2.
            while sp < 0.5: flt.append('atempo=0.5'); sp /= 0.5
            flt.append(f"atempo={sp:.3f}")
        flt.append(f"volume={a.volume:.3f}")
        fa.append(f"[{idx:d}:a]{','.join(flt)}[processed{i}]")
        valid_audios.append((i, t_start))
    if not valid_audios: return f"anullsrc=cl=stereo:r={TARGET_SAMPLE_RATE}:d={tm.total_dur:.3f}[aout]"
    fa.append(f"anullsrc=cl=stereo:r={TARGET_SAMPLE_RATE}:d={tm.total_dur:.3f}[bg_silent]")
    mix_tags = ['[bg_silent]']
    for i, t_start in valid_audios:
        ms = int(round(t_start * 1000))
        if ms > 0:
            fa.append(f"[processed{i}]adelay={ms}|{ms}[delayed{i}]")
            mix_tags.append(f"[delayed{i}]")
        else: mix_tags.append(f"[processed{i}]")
    n_inputs = len(mix_tags)
    fa.append(f"{''.join(mix_tags)}amix=inputs={n_inputs}:duration=longest:dropout_transition=0:normalize=0[amix_flat]")
    fa.append("[amix_flat]alimiter=limit=0.95:level=0[aout]")
    return ';\n'.join(fa)

def _get_scaled_font(W: int, H: int, base_font: Font) -> Font:
    scaled = copy.deepcopy(base_font)
    ref = min(W, H)
    scale_factor = ref / 1080.0
    if not base_font.size or base_font.size <= 0: scaled.size = max(16, round(ref * 0.048))
    else: scaled.size = max(12, round(base_font.size * scale_factor))
    scaled.scaleX = round(base_font.scaleX * scale_factor) if base_font.scaleX else 100
    scaled.scaleY = round(base_font.scaleY * scale_factor) if base_font.scaleY else 100
    scaled.spacing = round(base_font.spacing * scale_factor)
    return scaled

def build_subtitles(v_cur: str, subs: List[Transcribe], W: int, H: int, source: Path, style: Subtitle, tm: Optional[TimelineManager] = None) -> Tuple[str, str, Optional[Path]]:
    if not subs: return '', v_cur, None
    project_dir = source.parent / source.stem
    project_dir.mkdir(parents=True, exist_ok=True)
    ass = project_dir / f"{source.stem}_sub.ass"
    scaled_style = copy.deepcopy(style)
    scaled_style.font = _get_scaled_font(W, H, style.font)
    create_ass_file(subs, W, H, scaled_style, ass, tm=tm)
    p = os.path.relpath(ass, source.parent).replace('\\', '/')
    v_n = 'v_sub'
    return f"[{v_cur}]subtitles=filename='{p}'[{v_n}]", v_n, ass

def video_complex(source: Path, timestamps: Optional[List[Timestamp]], audios: Optional[List[Clip_Audio]], subtitles: Optional[List[Transcribe]] = None, images: Optional[List[Clip_Video]] = None, blurs: Optional[List[Polygon]] = None, target: Optional[Path] = None, subtitle_style: Optional[Subtitle] = None) -> Path:
    target = target or source.with_name(source.stem + '_final.mp4')
    W, H = get_video_size(source)
    tm = TimelineManager(timestamps, get_media_duration(source))
    ui = []
    def get_idx(p, loop=False):
        if Path(p).resolve() == source.resolve() and not loop: return 0
        k = str(p), loop
        if k not in ui: ui.append(k)
        return ui.index(k) + 1
    img_map = [get_idx(i.source.path, str(i.source.path).lower().endswith('.gif')) for i in (images or [])]
    aud_map = [get_idx(a.source.path, a.repeat) for a in (audios or [])]
    base_dir = source.parent
    cmd = ['ffmpeg', '-y', '-progress', 'pipe:1']
    hw_in = [x for (i, x) in enumerate(MM.HARDWARE) if x == '-hwaccel' or (i > 0 and MM.HARDWARE[i - 1] == '-hwaccel')]
    cmd += hw_in
    if getattr(MM, 'ffmpeg_level', None): cmd += ['-loglevel', MM.ffmpeg_level]
    cmd += ['-i', os.path.relpath(source, base_dir)]
    for p, loop in ui:
        if str(p).lower().endswith('.gif'): cmd += ['-ignore_loop', '0']
        elif loop: cmd += ['-stream_loop', '-1']
        cmd += ['-i', os.path.relpath(Path(p), base_dir)]
    fg = []
    ft, v_c = build_video_trim(timestamps, W, H)
    if ft: fg.append(ft)
    if blurs:
        f, v_c = build_movement_blurs(v_c, blurs, tm, W, H)
        if f: fg.append(f)
    if images:
        f, v_c = build_images(v_c, images, tm, img_map, W, H)
        if f: fg.append(f)
    p_ass = None
    if subtitles:
        style_to_use = subtitle_style or Subtitle()
        f, v_temp, p_ass = build_subtitles(v_c, subtitles, W, H, source, style_to_use, tm=tm)
        if f: fg.append(f); v_c = v_temp
    fg.append(build_audios(audios or [], tm, aud_map))
    fpath = source.parent / source.stem / f"{source.stem}_filter.txt"
    fpath.parent.mkdir(parents=True, exist_ok=True)
    with open(fpath, 'w', encoding='utf-8') as f: f.write(';\n'.join(filter(None, fg)))
    cmd += ['-filter_complex_script', os.path.relpath(fpath, base_dir), '-map', f"[{v_c}]", '-map', '[aout]']
    hw_out = [x for x in MM.HARDWARE if x not in hw_in]
    cmd += hw_out
    cmd += ['-c:a', 'aac', '-b:a', '192k', '-t', f"{tm.total_dur:.3f}", os.path.relpath(target, base_dir)]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, encoding='utf-8', errors='replace', cwd=base_dir)
    dur = round(tm.total_dur, 2)
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None: break
        if 'out_time_us=' in line:
            try:
                time_sec = int(line.strip().split('=')[1]) / 1e6
                LG.pr(round(time_sec, 2), dur, txt='VIDEO-RENDERING...', bar_color=LG.C, tab=3)
            except ValueError: pass
    stderr_output = process.stderr.read()
    process.wait()
    if process.returncode != 0:
        LG.ln(f"\n❌ FFmpeg Error:\n{stderr_output}", LG.R)
        raise subprocess.CalledProcessError(process.returncode, cmd, output=stderr_output)
    LG.cl(1); LG.ln('✅ Render successfully!', LG.G)
    if not is_use.o_ff_filter:
        fpath.unlink(True)
        if subtitles and p_ass: p_ass.unlink(True)
    return target