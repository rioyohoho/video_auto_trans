import cv2, numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Union
from video_auto_trans.src.enties import Canvas, Polygon, Delogo, Delogo_KeyFrames, Transcribe
from video_auto_trans.src.utils.video import get_media_duration
from video_auto_trans.src.utils.file import r_json, w_json
from video_auto_trans.src.utils.text import convert_srt
from video_auto_trans.src.utils.logger import progress
from video_auto_trans.src.utils import logger as LG
from video_auto_trans.src.configuration import READER

def get_roi_bounds(W: int, H: int, area: Union[Canvas.Area, int], ratio: float = 0.35) -> Tuple[int, int, int, int]:
    if not isinstance(area, Canvas.Area):
        try: area = Canvas.Area(int(area))
        except (ValueError, TypeError): area = Canvas.Area.DEFAULT
    A, rw, rh = Canvas.Area, int(W * ratio), int(H * ratio)
    m = {
        A.BOTTOM: (0, int(H * (1 - ratio)), W, H), A.BC: (0, int(H * (1 - ratio)), W, H),
        A.TOP: (0, 0, W, rh), A.TC: (0, 0, W, rh),
        A.LEFT: (0, 0, rw, H), A.CL: (0, 0, rw, H),
        A.RIGHT: (W - rw, 0, W, H), A.CR: (W - rw, 0, W, H),
        A.TOP_LEFT: (0, 0, rw, rh), A.TL: (0, 0, rw, rh),
        A.TOP_RIGHT: (W - rw, 0, W, rh), A.TR: (W - rw, 0, W, rh),
        A.BOTTOM_LEFT: (0, H - rh, rw, H), A.BL: (0, H - rh, rw, H),
        A.BOTTOM_RIGHT: (W - rw, H - rh, W, H), A.BR: (W - rw, H - rh, W, H),
        A.CENTER: (int(W * 0.15), int(H * 0.35), int(W * 0.85), int(H * 0.65)),
        A.CM: (int(W * 0.15), int(H * 0.35), int(W * 0.85), int(H * 0.65))
    }
    x1, y1, x2, y2 = m.get(area, (0, 0, W, H))
    return max(1, x1), max(1, y1), min(W - 1, x2), min(H - 1, y2)
def box_to_polygon(x: int, y: int, w: int, h: int, W: Optional[int] = None, H: Optional[int] = None) -> Polygon:
    if W is not None and H is not None:
        x1, y1 = max(1, int(x)), max(1, int(y))
        x2, y2 = min(W - 1, x1 + int(w)), min(H - 1, y1 + int(h))
        x, y, w, h = x1, y1, max(1, x2 - x1), max(1, y2 - y1)
    return Polygon(points=[Canvas(x=int(x), y=int(y)), Canvas(x=int(x + w), y=int(y)), Canvas(x=int(x + w), y=int(y + h)), Canvas(x=int(x), y=int(y + h))])
def polygon_to_box(poly: Polygon, W: int, H: int) -> Tuple[int, int, int, int]:
    if not poly.points: return 0, 0, 0, 0
    xs, ys = [p.x for p in poly.points], [p.y for p in poly.points]
    x_min, x_max = max(1, min(xs)), min(W - 1, max(xs))
    y_min, y_max = max(1, min(ys)), min(H - 1, max(ys))
    x_min, y_min = min(int(x_min), W - 2), min(int(y_min), H - 2)
    return x_min, y_min, max(1, int(x_max - x_min)), max(1, int(y_max - y_min))
def find_text_box_ocr(frame: np.ndarray, area: Union[Canvas.Area, int] = Canvas.Area.BOTTOM, expected_text: Optional[str] = None) -> Optional[Tuple[Tuple[int, int, int, int], str, float]]:
    if READER is None: return None
    H, W = frame.shape[:2]
    xo, yo, xm, ym = get_roi_bounds(W, H, area)
    roi = frame[yo:ym, xo:xm]
    results = READER.readtext(roi)
    if not results: return None
    candidates = []
    target_clean = expected_text.replace(" ", "").strip() if expected_text else None
    for (bbox, text, prob) in results:
        if prob < 0.2: continue
        pts = [(int(p[0] + xo), int(p[1] + yo)) for p in bbox]
        x1, y1, x2, y2 = min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
        clean_detected = text.replace(" ", "").strip()
        score = prob + ((len(set(target_clean) & set(clean_detected)) / max(len(target_clean), 1)) if target_clean else 0)
        candidates.append(((x1, y1, x2 - x1, y2 - y1), text, score))
    if not candidates: return None
    best = max(candidates, key=lambda c: c[2])
    x, y, w, h = best[0]
    px, py = 8, 4
    xc, yc = max(1, x - px), max(1, y - py)
    wc, hc = max(1, min(W - 1 - xc, w + px * 2)), max(1, min(H - 1 - yc, h + py * 2))
    return (xc, yc, wc, hc), best[1], best[2]
def estimate_box(anchor_box: Tuple[int, int, int, int], ref_text: str, target_text: str, max_w: int, max_h: int) -> Tuple[int, int, int, int]:
    x, y, w, h = anchor_box
    ppc = w / max(len(ref_text.strip()), 1)
    w_target = int(max(len(target_text.strip()), 1) * ppc)
    cx = x + w / 2.0
    half_w = w_target / 2.0
    x_min = max(1, min(int(cx - half_w), max_w - 2))
    x_max = max(x_min + 1, min(int(cx + half_w), max_w - 1))
    y_min = max(1, min(int(y), max_h - 2))
    y_max = max(y_min + 1, min(int(y + h), max_h - 1))
    return x_min, y_min, max(1, x_max - x_min), max(1, y_max - y_min)
def load_subtitles(sub_file: Path) -> List[Transcribe]:
    if not sub_file.exists(): return []
    if sub_file.suffix.lower() == '.srt':
        return [Transcribe(start=float(s['start']), end=float(s['end']), text=str(s['text'])) for s in convert_srt(sub_file.read_text(encoding='utf-8'))]
    elif sub_file.suffix.lower() == '.json':
        d = r_json(str(sub_file))
        if isinstance(d, list):
            return [Transcribe(start=float(x.get('start', 0)), end=float(x.get('end', 0)), text=str(x.get('text', ''))) for x in d if isinstance(x, dict)]
        elif isinstance(d, dict) and 'segments' in d:
            return [Transcribe(start=float(x.get('st', x.get('start', 0))), end=float(x.get('en', x.get('end', 0))), text=str(x.get('txt', x.get('text', '')))) for x in d['segments']]
    return []
def create_delogo_keyframes(source: Path, sub_file: Optional[Path] = None, area: Union[Canvas.Area, int] = Canvas.Area.BOTTOM, is_area_max: bool = True, is_timestamp_max: bool = False) -> List[Delogo_KeyFrames]:
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened(): return []
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = get_media_duration(source) or (cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1.0))
    subs = load_subtitles(sub_file) if sub_file else []; rx, ry, rw, rh = get_roi_bounds(W, H, area); clips = []
    if subs:
        if is_area_max:
            max_s = max((s for s in subs if s.text), key=lambda s: len(s.text), default=subs[0])
            t_mid = (max_s.start + max_s.end) / 2.0; cap.set(cv2.CAP_PROP_POS_MSEC, t_mid * 1000); ret, fr = cap.read()
            bx, by, bw, bh = rx, ry, rw, rh
            if ret:
                r = find_text_box_ocr(fr, area=area)
                if r: bx, by, bw, bh = r[0]
            if is_timestamp_max:
                clips.append(Delogo_KeyFrames(boxblur=20, width=bw, height=bh, keyframes=[Delogo(t=round(subs[0].start, 3), x=bx, y=by), Delogo(t=round(subs[-1].end, 3), x=bx, y=by)]))
            else:
                for s in subs: clips.append(Delogo_KeyFrames(boxblur=20, width=bw, height=bh, keyframes=[Delogo(t=round(s.start, 3), x=bx, y=by), Delogo(t=round(s.end, 3), x=bx, y=by)]))
        else:
            last_box = (rx, ry, rw, rh)
            for s in subs:
                t_mid = (s.start + s.end) / 2.0; cap.set(cv2.CAP_PROP_POS_MSEC, t_mid * 1000); ret, fr = cap.read()
                if ret:
                    r = find_text_box_ocr(fr, area=area)
                    if r: last_box = r[0]
                bx, by, bw, bh = last_box
                clips.append(Delogo_KeyFrames(boxblur=20, width=bw, height=bh, keyframes=[Delogo(t=round(s.start, 3), x=bx, y=by), Delogo(t=round(s.end, 3), x=bx, y=by)]))
    else:
        dt = []
        for t in [dur * 0.15, dur * 0.5, dur * 0.85]:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ret, fr = cap.read()
            if ret:
                r = find_text_box_ocr(fr, area=area)
                if r: dt.append(r[0])
        bx, by, bw, bh = dt[0] if dt else (rx, ry, rw, rh)
        clips.append(Delogo_KeyFrames(boxblur=20, width=bw, height=bh, keyframes=[Delogo(t=0.0, x=bx, y=by), Delogo(t=round(dur, 3), x=bx, y=by)]))
    cap.release()
    return clips
def preview_delogo(source: Path, delogo_kf: Delogo_KeyFrames, output_path: Path, time_at: Optional[float] = None) -> bool:
    if not delogo_kf.keyframes: return False
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened(): return False
    t = time_at if time_at is not None else delogo_kf.keyframes[0].t
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ret, fr = cap.read(); cap.release()
    if not ret: return False
    W, H = fr.shape[1], fr.shape[0]; kfs = sorted(delogo_kf.keyframes, key=lambda k: k.t); cur_x, cur_y = kfs[0].x, kfs[0].y
    for i in range(len(kfs) - 1):
        if kfs[i].t <= t <= kfs[i + 1].t:
            dt = max(0.001, kfs[i + 1].t - kfs[i].t); alpha = (t - kfs[i].t) / dt
            cur_x = int(kfs[i].x + (kfs[i + 1].x - kfs[i].x) * alpha); cur_y = int(kfs[i].y + (kfs[i + 1].y - kfs[i].y) * alpha); break
        elif t > kfs[-1].t: cur_x, cur_y = kfs[-1].x, kfs[-1].y
    x1 = max(0, min(W - delogo_kf.width, cur_x - delogo_kf.width // 2))
    y1 = max(0, min(H - delogo_kf.height, cur_y - delogo_kf.height // 2))
    cv2.rectangle(fr, (x1, y1), (x1 + delogo_kf.width, y1 + delogo_kf.height), (0, 255, 0), 2)
    cv2.putText(fr, f"DELOGO [{t:.2f}s]", (x1, max(25, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
    output_path.parent.mkdir(parents=True, exist_ok=True); cv2.imwrite(str(output_path), fr); LG.ln(f"Saved preview: {output_path}", LG.G); return True

def create_blurs_json(source: Path, output_json: Path, sub_file: Path = None, area: Canvas.Area = Canvas.Area.BOTTOM, is_area_max: bool = True, is_timestamp_max: bool = False, boxblur: int = 20):
    if is_timestamp_max: is_area_max = True
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened(): return []
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = max(cap.get(cv2.CAP_PROP_FPS), 1.0)
    dur = get_media_duration(source) or (cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps)
    area_val = area.value if hasattr(area, 'value') else area
    if area_val == 0: area_val = Canvas.Area.BOTTOM.value
    rx1, ry1, rx2, ry2 = get_roi_bounds(W, H, area_val)
    rx, ry, rw, rh = rx1, ry1, max(1, rx2 - rx1), max(1, ry2 - ry1)
    def detect_in_roi(frame, ref_text=""):
        crop = frame[ry:ry+rh, rx:rx+rw]
        try:
            res = READER.readtext(crop)
            if not res: return None
            clean_ref = ref_text.replace(" ", "").strip()
            vb = []
            for (bbox, text, prob) in res:
                ct = text.replace(" ", "").strip()
                if not ct: continue
                if clean_ref:
                    if not (set(ct) & set(clean_ref)) and (ct not in clean_ref) and (clean_ref not in ct): continue
                vb.append((bbox, ct))
            if not vb:
                rs = sorted(res, key=lambda r: max(p[1] for p in r[0]), reverse=True)
                vb = [(rs[0][0], rs[0][1].replace(" ", "").strip())]
            pts = [p for b in vb for p in b[0]]
            x1, x2 = int(min(p[0] for p in pts)), int(max(p[0] for p in pts))
            y1, y2 = int(min(p[1] for p in pts)), int(max(p[1] for p in pts))
            dt = "".join(b[1] for b in vb)
            if clean_ref and dt and (dt in clean_ref) and len(dt) < len(clean_ref):
                cw = (x2 - x1) / max(1, len(dt)); idx = clean_ref.find(dt)
                x1 -= int(idx * cw); x2 += int((len(clean_ref) - idx - len(dt)) * cw)
            bw = int((x2 - x1) * 1.1); bh = min(85, max(60, int((y2 - y1) * 1.25)))
            cx, cy = W // 2, ry + (y1 + y2) // 2
            cy = max(H - rh + bh // 2, min(H - bh // 2, cy))
            return cx, cy, min(W - 4, max(40, bw)), bh, len(dt)
        except Exception: return None
    subs = load_subtitles(Path(sub_file)) if sub_file and Path(sub_file).exists() else []
    clips, default_cx, default_cy = [], W // 2, int(H * 0.89)
    if subs:
        tot = len(subs)
        if is_area_max:
            max_s = max((s for s in subs if s.text), key=lambda s: len(s.text), default=subs[0])
            best_det = None
            for i, r_val in enumerate([0.5, 0.3, 0.7]):
                cap.set(cv2.CAP_PROP_POS_MSEC, (max_s.start + (max_s.end - max_s.start) * r_val) * 1000)
                ret, fr = cap.read()
                if ret:
                    r = detect_in_roi(fr, ref_text=max_s.text)
                    if r and (best_det is None or r[4] > best_det[4]):
                        best_det = r
                        if r[4] >= len(max_s.text) * 0.8: break
                progress(i + 1, 3, txt="DELOGO-SAMPLE", tab=3)
            cx, cy, bw, bh, _ = best_det if best_det else (default_cx, default_cy, int(W * 0.6), 75, 0)
            if is_timestamp_max:
                clips.append(Delogo_KeyFrames(boxblur=boxblur, width=bw, height=bh, keyframes=[Delogo(t=round(subs[0].start, 3), x=cx, y=cy), Delogo(t=round(subs[-1].end, 3), x=cx, y=cy)]))
                progress(tot, tot, txt="DELOGO-OCR", tab=3)
            else:
                for i, s in enumerate(subs):
                    clips.append(Delogo_KeyFrames(boxblur=boxblur, width=bw, height=bh, keyframes=[Delogo(t=round(s.start, 3), x=cx, y=cy), Delogo(t=round(s.end, 3), x=cx, y=cy)]))
                    progress(i + 1, tot, txt="DELOGO-OCR", tab=3)
        else:
            last_box = (default_cx, default_cy, int(W * 0.5), 75)
            for i, s in enumerate(subs):
                cap.set(cv2.CAP_PROP_POS_MSEC, ((s.start + s.end) / 2.0) * 1000)
                ret, fr = cap.read()
                if ret:
                    r = detect_in_roi(fr, ref_text=s.text)
                    if r: last_box = (r[0], r[1], r[2], r[3])
                cx, cy, bw, bh = last_box
                clips.append(Delogo_KeyFrames(boxblur=boxblur, width=bw, height=bh, keyframes=[Delogo(t=round(s.start, 3), x=cx, y=cy), Delogo(t=round(s.end, 3), x=cx, y=cy)]))
                progress(i + 1, tot, txt="DELOGO-OCR", tab=3)
    else:
        checks, dt = [dur * 0.15, dur * 0.5, dur * 0.85], []
        for i, t in enumerate(checks):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ret, fr = cap.read()
            if ret:
                r = detect_in_roi(fr)
                if r: dt.append(r)
            progress(i + 1, len(checks), txt="DELOGO-OCR", tab=3)
        if dt:
            cx, cy, bw, bh, _ = max(dt, key=lambda x: x[2])
            clips.append(Delogo_KeyFrames(boxblur=boxblur, width=bw, height=bh, keyframes=[Delogo(t=0.0, x=cx, y=cy), Delogo(t=round(dur, 3), x=cx, y=cy)]))
    cap.release()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    w_json(output_json, {'frames': [c.asdict() if hasattr(c, 'asdict') else c.__dict__ for c in clips]})
    return clips



