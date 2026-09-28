import os, cv2, easyocr, numpy as np
from src.enties import Delogo_KeyFrames, Delogo, Canvas

class C:
    step = 1.0
    quality = 0.25
    tolerance = 25.0
    conf = 0.35

def _check_area(x, y, w, h, area):
    if area == Canvas.Area.DEFAULT or area == 0: return True
    r = 0 if y < h / 3 else (1 if y < 2 * h / 3 else 2)
    c = 0 if x < w / 3 else (1 if x < 2 * w / 3 else 2)
    val = [[7, 8, 9], [4, 5, 6], [1, 2, 3]][r][c]
    return str(val) in str(int(area))

def _is_match(d1, d2):
    t1, t2 = d1["text"], d2["text"]
    text_ok = (t1 in t2) or (t2 in t1) or (len(set(t1) & set(t2)) / max(1, min(len(t1), len(t2))) >= 0.5)
    b1, b2 = d1["box"], d2["box"]
    return text_ok and abs(b1[1] - b2[1]) <= 35 and (abs(b1[0] - b2[0]) <= 60 or abs(b1[2] - b2[2]) <= 60)

def get_position_txt(source: str, txt: str = "", start: float = 0.0, end: float = 0.0, area: Canvas.Area = Canvas.Area.DEFAULT, out_images=None):
    if out_images: os.makedirs(out_images, exist_ok=True)
    cap = cv2.VideoCapture(source)
    fps, total = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fw, fh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = total / fps if fps > 0 else 0
    end = min(end, dur) if end > 0 else dur

    reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
    t, scale, raw, frames = start, 1.0 / C.quality, [], {}

    while t <= end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if not ret: break
        h, w = frame.shape[:2]
        res = reader.readtext(cv2.resize(frame, (int(w * C.quality), int(h * C.quality))), detail=1)
        has_det = False
        for (bbox, text, prob) in res:
            text = text.strip()
            if prob < C.conf or not text: continue
            if txt and not ((txt in text) or (text in txt) or (len(set(txt) & set(text)) / len(txt) >= 0.4)): continue
            (tl, _, br, _) = bbox
            x1, y1 = max(0, int(tl[0] * scale)), max(0, int(tl[1] * scale))
            x2, y2 = min(fw, int(br[0] * scale)), min(fh, int(br[1] * scale))
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            if not _check_area(cx, cy, fw, fh, area): continue
            raw.append({"t": round(t, 3), "text": text, "ocr_box": [x1, y1, x2, y2], "box": [x1, y1, x2, y2]})
            has_det = True
        if has_det and out_images: frames[round(t, 3)] = frame
        t += C.step
    cap.release()

    raw.sort(key=lambda x: x["t"])
    segs = []
    for d in raw:
        matched = False
        for s in segs:
            if 0 < d["t"] - s[-1]["t"] <= 4.0 and _is_match(d, s[0]):
                s.append(d)
                matched = True
                break
        if not matched: segs.append([d])

    delogo_objs = []
    for s in [s for s in segs if len(s) >= 2]:
        ref = txt if txt else max(s, key=lambda x: len(x["text"]))["text"]
        ref_item = max(s, key=lambda x: (x["box"][2] - x["box"][0]))
        base_w, base_h = ref_item["box"][2] - ref_item["box"][0], ref_item["box"][3] - ref_item["box"][1]
        mw, mh = int(base_w * 1.15), int(base_h * 1.25)

        for d in s:
            x1, y1, x2, y2 = d["box"]
            cur_t = d["text"]
            if cur_t in ref and 0 < len(cur_t) < len(ref):
                cw = (x2 - x1) / len(cur_t)
                idx = ref.find(cur_t)
                x1 -= int(idx * cw)
                x2 += int((len(ref) - idx - len(cur_t)) * cw)
            x1, y1 = max(0, min(x1, fw - 1)), max(0, min(y1, fh - 1))
            x2, y2 = max(x1 + 1, min(x2, fw)), max(y1 + 1, min(y2, fh))
            d["box"] = [x1, y1, x2, y2]
            d["center"] = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

        A, B = s[0], s[-1]
        cA, cB = A["center"], B["center"]
        is_static = all(np.hypot(d["center"][0] - cA[0], d["center"][1] - cA[1]) <= C.tolerance for d in s)

        for d in s:
            if is_static:
                cx, cy = cA[0], cA[1]
            else:
                ratio = (d["t"] - A["t"]) / (B["t"] - A["t"]) if B["t"] > A["t"] else 0
                cx = cA[0] + (cB[0] - cA[0]) * ratio
                cy = cA[1] + (cB[1] - cA[1]) * ratio
            d["delogo_center"] = (int(cx), int(cy))
            d["calc_box"] = [max(0, int(cx - mw / 2)), max(0, int(cy - mh / 2)), min(fw, int(cx + mw / 2)), min(fh, int(cy + mh / 2))]

        kfs = [Delogo(t=A["t"], x=int(cA[0]), y=int(cA[1])), Delogo(t=B["t"], x=int(cA[0]), y=int(cA[1]))] if is_static else [Delogo(t=d["t"], x=d["delogo_center"][0], y=d["delogo_center"][1]) for d in s]
        delogo_objs.append(Delogo_KeyFrames(boxblur=20, width=mw, height=mh, mode=Delogo_KeyFrames.Mode.SOLID, color="#FF000080", keyframes=kfs).asdict())

    if out_images:
        rendered = {}
        for s in segs:
            for d in s:
                t_val = d["t"]
                if t_val in frames and "calc_box" in d:
                    img = rendered.get(t_val, frames[t_val].copy())
                    ox1, oy1, ox2, oy2 = d["ocr_box"]
                    cx1, cy1, cx2, cy2 = d["calc_box"]
                    cv2.rectangle(img, (ox1, oy1), (ox2, oy2), (0, 0, 255), 2)
                    overlay = img.copy()
                    cv2.rectangle(overlay, (cx1, cy1), (cx2, cy2), (255, 255, 0), -1)
                    cv2.circle(overlay, d["delogo_center"], 4, (0, 0, 255), -1)
                    cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)
                    rendered[t_val] = img
        for t_val, img in rendered.items():
            cv2.imwrite(os.path.join(out_images, f"{t_val:.3f}.jpg"), img)

    return delogo_objs
