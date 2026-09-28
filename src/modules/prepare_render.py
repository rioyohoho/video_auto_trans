from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from src.enties import (
    Data, Clip_Audio, Source, Clip_Video, Video_Keyframes,
    Delogo, Delogo_KeyFrames, Polygon, Transcribe,
    Font, Solid, Color, Alignment, Subtitle, Timestamp
)
from src.utils.video import get_media_duration
from src.utils.file import r_json
from src.utils.text import convert_srt
from src.utils import logger as LG
from src.modules.render import video_complex
from src.configuration import ext, TAR_LANG

def _resolve_color_val(val: Any, default: str = "#ffffffff") -> str:
    if not val: return default
    if isinstance(val, str) and val.strip(): return val.strip()
    if isinstance(val, dict):
        c = val.get('color') or val.get('value')
        if isinstance(c, str) and c.strip(): return c.strip()
        grad = val.get('gradient') or val.get('gradian')
        if isinstance(grad, dict):
            cols = grad.get('colors') or grad.get('values') or []
            if cols and isinstance(cols[0], str) and cols[0].strip(): return cols[0].strip()
        elif isinstance(grad, list) and grad and isinstance(grad[0], str): return grad[0].strip()
    return default

@dataclass
class RC(Data):
    is_max_source: bool = True
    is_desub: bool = False
    is_subtitles: bool = True
    subtitle_path: Optional[str] = None
    subtitle_style_path: Optional[str] = None
    subtitle_style: Optional[Dict[str, Any]] = None
    target_path: str = ''
    base_audio: Clip_Audio = field(default_factory=lambda: Clip_Audio(.0))
    new_vocal: Optional[Clip_Audio] = None
    new_audios: list[Clip_Audio] = field(default_factory=list)
    audios: list[Clip_Audio] = field(default_factory=list)
    add_images: list[Video_Keyframes] = field(default_factory=list)
    delogo: list[Delogo_KeyFrames] = field(default_factory=list)

    @classmethod
    def load(cls, path: Optional[Union[str, Path]] = None) -> 'RC':
        inst = cls()
        if not path: return inst
        cfg_path = Path(path)
        if not cfg_path.exists(): return inst
        data = r_json(str(cfg_path.resolve()))
        if not isinstance(data, dict): return inst
        for k, v in data.items():
            if k == 'base_audio' and isinstance(v, dict): inst.base_audio = Clip_Audio.parse(v)
            elif k == 'new_vocal' and isinstance(v, dict): inst.new_vocal = Clip_Audio.parse(v)
            elif k == 'new_audios' and isinstance(v, list): inst.new_audios = [Clip_Audio.parse(i) for i in v if isinstance(i, dict)]
            elif k == 'audios' and isinstance(v, list): inst.audios = [Clip_Audio.parse(i) for i in v if isinstance(i, dict)]
            elif k == 'add_images' and isinstance(v, list): inst.add_images = [Video_Keyframes.parse(i) for i in v if isinstance(i, dict)]
            elif k == 'delogo' and isinstance(v, list): inst.delogo = [Delogo_KeyFrames.parse(i) for i in v if isinstance(i, dict)]
            elif hasattr(inst, k): setattr(inst, k, v)
        return inst

def resolve_file_priority(folder: Path, stem: str, lang: str, extensions: tuple) -> Optional[Path]:
    patterns = [
        f"{stem}_S.{lang}",
        f"{stem}_G.{lang}",
        f"{stem}_AI.{lang}",
        f"{stem}.{lang}",
        f"{stem}_S",
        f"{stem}_G",
        f"{stem}_AI",
        f"{stem}"
    ]
    for p in patterns:
        for e in extensions:
            cand = folder / f"{p}{e}"
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0: return cand.resolve()
    return None

def resolve_subtitle_path(media_path: Path, lang: str, custom_path: Optional[str] = None) -> Optional[Path]:
    if custom_path and Path(custom_path).exists(): return Path(custom_path).resolve()
    stem = media_path.stem
    for folder in [media_path.parent / stem, media_path.parent]:
        if not folder.exists(): continue
        found = resolve_file_priority(folder, stem, lang, ('.srt', '.json', '.txt'))
        if found: return found
    return None

def parse_subtitles_from_file(sub_path: Path) -> List[Transcribe]:
    if not sub_path.exists(): return []
    ext_name = sub_path.suffix.lower()
    if ext_name == '.srt': return [Transcribe(start=float(s['start']), end=float(s['end']), text=str(s['text'])) for s in convert_srt(sub_path.read_text(encoding='utf-8'))]
    if ext_name == '.json':
        data, subs = r_json(str(sub_path)), []
        if isinstance(data, list):
            for d in data:
                if isinstance(d, dict): subs.append(Transcribe(start=float(d.get('start', d.get('st', 0))), end=float(d.get('end', d.get('en', 0))), text=str(d.get('text', d.get('txt', ''))).strip()))
        elif isinstance(data, dict) and 'segments' in data:
            for d in data['segments']: subs.append(Transcribe(start=float(d.get('start', d.get('st', 0))), end=float(d.get('end', d.get('en', 0))), text=str(d.get('text', d.get('txt', ''))).strip()))
        return subs
    return []

def parse_subtitle_style(cfg: RC) -> Subtitle:
    data = cfg.subtitle_style
    if not data and cfg.subtitle_style_path and Path(cfg.subtitle_style_path).exists(): data = r_json(str(Path(cfg.subtitle_style_path).resolve())) or {}
    if not data or not isinstance(data, dict): return Subtitle()
    font_data = data.get('font', {})
    raw_size = font_data.get('size', 60)
    size_val = 0 if str(raw_size).lower() == 'auto' else int(raw_size)
    font = Font(name=font_data.get('name', 'Arial'), size=size_val, bold=bool(font_data.get('bold', True)), italic=bool(font_data.get('italic', False)), spacing=int(font_data.get('spacing', 1)))
    c_data = data.get('color', {})
    pri = _resolve_color_val(c_data.get('primary'), '#ffe600')
    outl = _resolve_color_val(c_data.get('outline'), '#000000ff')
    shad = _resolve_color_val(c_data.get('shadow'), '#00000080')
    color = Color(primary=Solid(pri), outline=Solid(outl), shadow=Solid(shad))
    align_val = data.get('alignment', Alignment.BOTTOM_CENTER)
    try: align = Alignment(int(align_val))
    except (ValueError, TypeError): align = Alignment.BOTTOM_CENTER
    return Subtitle(font=font, color=color, alignment=align, outline_width=int(data.get('outline_width', 3)), shadow_depth=int(data.get('shadow_depth', 1)))

def _find_audio_file(source_media: Path, lang: str, is_music: bool = False) -> Optional[Path]:
    stem = source_media.stem
    work_dir = source_media.parent / stem
    if is_music:
        for f in (work_dir, source_media.parent):
            for e in ext.AUDIO:
                for p in (f"{stem}_music", "music"):
                    cand = f / f"{p}{e}"
                    if cand.exists() and cand.is_file() and cand.stat().st_size > 0: return cand.resolve()
        return None
    for f in (work_dir, source_media.parent):
        found = resolve_file_priority(f, stem, lang, ext.AUDIO)
        if found: return found
        for e in ext.AUDIO:
            cand = f / f"{stem}_vocal{e}"
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0: return cand.resolve()
    return None

def build_audio_tracks(source_media: Path, lang: str, cfg: RC, total_dur: float) -> List[Clip_Audio]:
    audios: List[Clip_Audio] = []
    if cfg.base_audio.volume > 0 and source_media.exists():
        audios.append(Clip_Audio(volume=cfg.base_audio.volume, tempo=getattr(cfg.base_audio, 'tempo', 1.), pitch=getattr(cfg.base_audio, 'pitch', 1.), source=Source(path=str(source_media.resolve()), start=.0, end=total_dur), start=.0, end=total_dur))
    audio_list = list(cfg.audios)
    if not audio_list:
        if cfg.new_vocal and cfg.new_vocal.volume > 0: audio_list.append(cfg.new_vocal)
        audio_list.extend(cfg.new_audios)
    for a in audio_list:
        if a.volume <= 0.0001: continue
        p_str = a.source.path if a.source else None
        p_target = Path(p_str).resolve() if p_str and Path(p_str).exists() else _find_audio_file(source_media, lang, is_music=a.repeat)
        if not p_target: continue
        dur = get_media_duration(p_target)
        audios.append(Clip_Audio(volume=a.volume, tempo=a.tempo, pitch=a.pitch, repeat=a.repeat, source=Source(path=str(p_target), start=.0, end=total_dur if a.repeat else dur), start=.0, end=total_dur if a.repeat else dur))
    return audios

def build_images_from_keyframes(keyframes_list: List[Video_Keyframes], total_dur: float) -> List[Clip_Video]:
    imgs: List[Clip_Video] = []
    for vk in keyframes_list:
        if not vk.clip.source.path or not Path(vk.clip.source.path).exists(): continue
        p = str(Path(vk.clip.source.path).resolve())
        for f in vk.frames: imgs.append(Clip_Video(start=getattr(f, 'start', .0), end=getattr(f, 'end', total_dur) or total_dur, layer=vk.clip.layer, scale=f.scale, opacity=f.opacity, focus=f.focus, source=Source(path=p, start=.0, end=total_dur)))
    return imgs

def prepare_and_render(input_media: Union[str, Path], output_target: Optional[Union[str, Path]] = None, lang: str = TAR_LANG, config_path: Optional[Union[str, Path]] = None, start: float = 0.0, end: float = 0.0) -> Optional[Path]:
    source = Path(input_media).resolve()
    if not source.exists(): return None
    cfg = RC.load(config_path); total_dur = get_media_duration(source); st, en = max(.0, float(start)), float(end)
    if en > st: en_val = min(total_dur, en)
    elif 0 < en <= st: en_val = min(total_dur, st + en)
    else: en_val = total_dur
    st_val = min(st, en_val); ts = [Timestamp(start=st_val, end=en_val)] if (st_val > 0 or en_val < total_dur) else None
    dur_to_use = (en_val - st_val) if ts else total_dur
    final_target = Path(output_target).resolve() if output_target else (Path(cfg.target_path).resolve() if cfg.target_path else source.parent / f"{source.stem}_{lang or 're-rendered'}.mp4")
    final_target.parent.mkdir(parents=True, exist_ok=True)
    LG.ln(f"Source: {source.resolve()}", LG.C); LG.ln(f"Output: {final_target.resolve()}", LG.C)
    LG.ln(f"Render Dur: {dur_to_use:.2f}s (from {st_val:.2f}s to {en_val:.2f}s) | Lang: [{lang}]", LG.C)
    subtitles, sub_style, blurs = [], None, []
    if cfg.is_subtitles:
        sub_file = resolve_subtitle_path(source, lang, cfg.subtitle_path)
        if sub_file: LG.ln(f"Subtitle: {sub_file.resolve()}", LG.G); subtitles = parse_subtitles_from_file(sub_file)
        sub_style = parse_subtitle_style(cfg)
    if cfg.is_desub:
        bf = (source.parent / source.stem / 'blurs.json').resolve()
        if bf.exists():
            LG.ln(f"Delogo: {bf.resolve()}", LG.G); bd = r_json(str(bf))
            if isinstance(bd, dict):
                if 'frames' in bd: blurs.extend([Delogo_KeyFrames.parse(x) for x in bd['frames'] if isinstance(x, dict)])
                elif 'delogos' in bd: blurs.extend([Delogo_KeyFrames.parse(x) for x in bd['delogos'] if isinstance(x, dict)])
                elif 'keyframes' in bd: blurs.append(Delogo_KeyFrames.parse(bd))
            elif isinstance(bd, list): blurs.extend([Delogo_KeyFrames.parse(x) for x in bd if isinstance(x, dict)])
    blurs.extend(cfg.delogo); audios = build_audio_tracks(source, lang, cfg, total_dur)
    for a in audios:
        if a.source and a.source.path: LG.ln(f"Audio: {Path(a.source.path).resolve()}", LG.G)
    images = build_images_from_keyframes(cfg.add_images, total_dur)
    for im in images:
        if im.source and im.source.path: LG.ln(f"Image: {Path(im.source.path).resolve()}", LG.G)
    return video_complex(source=source, timestamps=ts, audios=audios, subtitles=subtitles if subtitles else None, images=images if images else None, blurs=blurs if blurs else None, target=final_target, subtitle_style=sub_style)


