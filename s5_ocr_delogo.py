import argparse
from pathlib import Path
from src.modules.delogo import create_blurs_json,preview_delogo
from src.modules.prepare_render import RC
from src.enties import Canvas
from src.utils import txt
from src.utils.text import str2bool
from src.configuration import ext

def get_video_list(inp:Path)->list[Path]:
    videos=[]
    if inp.is_file():
        if inp.suffix.lower()in ext.VIDEO:videos.append(inp)
        else:
            p_dir=inp.parent
            for e in ext.VIDEO:
                c=p_dir.parent/f"{p_dir.name}{e}"
                if c.exists():videos.append(c);break
            if not videos:
                for e in ext.VIDEO:
                    c=p_dir/f"{inp.stem}{e}"
                    if c.exists():videos.append(c);break
    elif inp.is_dir():
        for e in ext.VIDEO:videos.extend(list(inp.glob(f"*{e}")));videos.extend(list(inp.glob(f"*{e.upper()}")))
        videos=sorted(list(set(videos)))
        if not videos:
            for e in ext.VIDEO:
                c=inp.parent/f"{inp.name}{e}"
                if c.exists():videos.append(c);break
    if not videos:raise FileNotFoundError(f"Không tìm thấy file video nào hợp lệ từ đường dẫn: {inp}")
    return videos

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('-i','--input',required=True)
    p.add_argument('-o','--output',default=None)
    p.add_argument('-s','--sub',default=None)
    p.add_argument('-p','--preview',default=None)
    p.add_argument('-a','--area',default=Canvas.Area.BOTTOM.value,type=int)
    p.add_argument('-am','--is-area-max',default=True,type=str2bool)
    p.add_argument('-tm','--is-timestamp-max',default=False,type=str2bool)
    p.add_argument('-c','--config',default=None)
    args=p.parse_args()
    is_time_max=bool(args.is_timestamp_max)
    is_area_max=True if is_time_max else bool(args.is_area_max)
    inp=Path(args.input).resolve()
    cfg=RC.load(args.config)if args.config else RC()
    video_list=get_video_list(inp)
    for src in video_list:
        txt.yellow(f"--- Đang xử lý video: {src.name} ---")
        out=Path(args.output).resolve()if args.output else(src.parent/src.stem/"blurs.json")
        if out.exists()and out.stat().st_size>0:
            txt.magenta(f'[PASS] "{str(out)}"')
            continue
        sub=None
        if args.sub:sub=Path(args.sub).resolve()
        elif cfg.subtitle_path and Path(cfg.subtitle_path).exists():sub=Path(cfg.subtitle_path).resolve()
        if not sub:
            cand=src.parent/src.stem/f"{src.stem}.json"
            if cand.exists():sub=cand
        dkf=create_blurs_json(source=src,output_json=out,sub_file=sub,area=Canvas.Area(args.area),is_area_max=is_area_max,is_timestamp_max=is_time_max)
        if out.exists()and out.stat().st_size>0:txt.green(f'[DONE]: "{str(out)}"')
        if args.preview and dkf:preview_delogo(src,dkf[0]if isinstance(dkf,list)else dkf,Path(args.preview).resolve())