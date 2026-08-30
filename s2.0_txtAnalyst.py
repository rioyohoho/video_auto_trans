import os,sys
from pathlib import Path
from src.utils.logger import text as log
from src.utils import agr,ext,file, listFilter, handle_input
from src.modules.txtAnalyst import TextAnalyst
from src.configuration import P_DIR

class K:
    inp = "input_path"
    out = "output_path"
    dur = "target_duration"
    seg = 'segments'

def _exec_json(p_input:Path, p_output:Path, duration:float):
    config = {K.inp: p_input, K.out: p_output, K.dur: duration}
    if not os.path.exists(config[K.inp]):
        return log.red(f"[ERROR] File not found: {config[K.inp]}")
    raw_segments = file.r_json(config[K.inp])
    if not raw_segments: return
    log.blue(f"[HDL_SCRIPTS] Read {len(raw_segments)} segments from {config[K.inp]}")
    analyst = TextAnalyst()
    highlights = analyst.process_and_select_highlights(raw_segments, config[K.dur], PROMPT)
    if highlights:
        saved_file = file.w_json(config[K.out], highlights)
        log.green(f"[HDL_SCRIPTS] SAVED {len(highlights)} SEGMENTS TO: {saved_file}")

PROMPT = """
You are a video editor selecting top highlights.
Task: Pick 2 to 3 Scene IDs from SCENE_0 to SCENE_{total_scenes} to make a ~{target_duration}s highlight video.

OUTPUT ONLY JSON IN THIS EXACT FORMAT (NO OTHER TEXT):
{{
  "selected_scene_ids": [7, 10, 12]
}}"""
if __name__ == '__main__':
    args = handle_input(
        agr(('-i', '--input'), type=str, required=False, default=P_DIR),
        agr(('-o', '--output'), type=str, required=False,default=P_DIR),
        agr(('-d', '--duration'), type=float, required=False, default=60.0)
    ) 
    i,o,d=str(args.input),str(args.output),float(args.duration)
    path:Path = Path(i)
    if not path.exists(): sys.exit(0)

    if path.is_dir():
        for i, n in enumerate(listFilter(path, ext.VIDEO), 1):
            x=(path/n);xp=x.with_suffix('')
            _exec_json(xp/f'{x.stem}.json', xp/f'{K.seg}.json', d)
    elif path.is_file() and str(path).endswith('.json'):
        _exec_json(path,path.with_stem(K.seg),d)