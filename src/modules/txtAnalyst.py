import json, re, time
from src.modules.googleAI import request
from src.utils.logger import text as log

class K:
    id = "id"
    st = "start"
    en = "end"
    dur = "duration"
    tx = "text"
    _st_keys = ("start", "start_time", "begin", "from")
    _en_keys = ("end", "end_time", "stop", "to")
    _tx_keys = ("text", "content", "transcript", "subtitle", "val")

class TextAnalyst:
    def __init__(self):
        log.green("[HDL_SCRIPTS] TextAnalyst ready with GoogleAI!")

    def _val(self, d: dict, keys: tuple, default=0.0):
        return next((d[k] for k in keys if k in d and d[k] is not None), default)

    def process_and_select_highlights(self, raw_segments: list, target_duration: float, system_prompt_template: str) -> list:
        if not raw_segments: return []
        chunk_dur = max(15.0, min(35.0, target_duration / 2.5))
        scenes = self._aggregate_to_scenes(raw_segments, scene_dur=chunk_dur)
        tot_dur = self._val(raw_segments[-1], K._en_keys) - self._val(raw_segments[0], K._st_keys)
        log.yellow(f"[HDL_SCRIPTS] Gom {len(raw_segments)} segments -> {len(scenes)} Scenes ({tot_dur/60:.1f}m).")
        formatted = "\n".join([f"SCENE_{s[K.id]} (~{s[K.dur]}s): {s[K.tx][:120]}..." for s in scenes])
        sys_p = system_prompt_template.format(target_duration=target_duration, total_scenes=len(scenes)-1)
        prompt = f"{sys_p}\n\nLIST OF {len(scenes)} SCENES:\n{formatted}\n\nSelect Scene IDs to sum up to ~{target_duration}s total:"
        log.magenta(f"[HDL_SCRIPTS] AI selecting best scenes for target ~{target_duration}s...")
        t0 = time.time()
        raw_output = request(prompt) or ""
        print(f"\033[96m[AI Output]: \033[0m{raw_output}")
        log.green(f'[HDL_SCRIPTS] Processed in {time.time() - t0:.2f}s!')
        ranges = self._extract_scene_ranges(raw_output, scenes, target_duration) or self._fallback_top_scenes(scenes, target_duration)
        ranges = self._merge_overlapping_ranges(ranges)
        log.cyan(f"[HDL_SCRIPTS] Selected: {sum(r[K.en] - r[K.st] for r in ranges):.1f}s / {target_duration}s")
        return self._filter_original_segments(raw_segments, ranges)

    def _aggregate_to_scenes(self, segments: list, scene_dur: float = 30.0) -> list:
        scenes, curr, s_id = [], [], 0
        for i, seg in enumerate(segments):
            curr.append(seg)
            s_st, s_et = self._val(curr[0], K._st_keys), self._val(curr[-1], K._en_keys)
            dur = s_et - s_st
            gap = (self._val(segments[i+1], K._st_keys) - self._val(seg, K._en_keys)) if i < len(segments)-1 else 0
            if i == len(segments) - 1 or (dur >= scene_dur and gap > 0.8) or dur >= scene_dur * 1.3:
                text_content = " ".join([str(self._val(x, K._tx_keys, '')).strip() for x in curr]).strip()
                scenes.append({K.id: s_id, K.st: round(s_st, 2), K.en: round(s_et, 2), K.dur: round(dur, 1), K.tx: text_content})
                s_id += 1; curr = []
        return scenes

    def _extract_scene_ranges(self, raw_output: str, scenes: list, target_duration: float) -> list:
        time_ranges, s_dict, selected = [], {s[K.id]: s for s in scenes}, []
        try:
            m = re.search(r'\{.*\}', raw_output, re.DOTALL)
            data = json.loads(m.group(0) if m else raw_output.strip())
            for val in (data.values() if isinstance(data, dict) else [data]):
                for it in (val if isinstance(val, list) else [val]):
                    n = int(re.sub(r'\D', '', str(it))) if re.search(r'\d+', str(it)) else None
                    if n is not None and n in s_dict and n not in selected: selected.append(n)
        except Exception: pass
        if not selected:
            selected = [int(x) for x in re.findall(r'\b(?:SCENE_)?(\d+)\b', raw_output) if int(x) in s_dict and int(x) not in selected]
        acc = 0.0
        for sid in selected:
            sc = s_dict[sid]
            rem = target_duration - acc
            if rem <= 0: break
            if sc[K.dur] > rem * 1.25 and acc > 0:
                time_ranges.append({K.st: sc[K.st], K.en: round(sc[K.st] + rem, 2)})
                acc += rem
                break
            time_ranges.append({K.st: sc[K.st], K.en: sc[K.en]})
            acc += sc[K.dur]
        return time_ranges

    def _fallback_top_scenes(self, scenes: list, target_duration: float) -> list:
        scored = []
        for s in scenes:
            words = re.findall(r'\w+', s.get(K.tx, ""))
            density = (len(words) / max(s.get(K.dur, 1.0), 1.0)) * (len(set(words)) / max(len(words), 1.0))
            scored.append((density, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        chosen, acc = [], 0.0
        for _, s in scored:
            rem = target_duration - acc
            if rem <= 0: break
            if s[K.dur] > rem * 1.25 and acc > 0:
                chosen.append({K.st: s[K.st], K.en: round(s[K.st] + rem, 2), K.id: s[K.id]})
                break
            chosen.append(s)
            acc += s[K.dur]
        return sorted([{K.st: s[K.st], K.en: s[K.en]} for s in chosen], key=lambda x: x[K.st])

    def _merge_overlapping_ranges(self, ranges: list) -> list:
        if not ranges: return []
        sr = sorted(ranges, key=lambda x: x[K.st])
        res = [sr[0]]
        for c in sr[1:]:
            if c[K.st] <= res[-1][K.en] + 0.5: res[-1][K.en] = max(res[-1][K.en], c[K.en])
            else: res.append(c)
        return res

    def _filter_original_segments(self, original_segments: list, ranges: list, tol: float = 0.5) -> list:
        return [seg for seg in original_segments if any((r[K.st] - tol) <= self._val(seg, K._st_keys) and self._val(seg, K._en_keys) <= (r[K.en] + tol) for r in ranges)]