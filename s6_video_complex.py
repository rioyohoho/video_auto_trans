import argparse
from pathlib import Path
from src.modules.prepare_render import prepare_and_render
from src.configuration import TAR_LANG,RENDER_CONFIG
from src.workspace import find_workspaces
from src.utils import txt

def main():
    parser=argparse.ArgumentParser(description="Render video complex")
    parser.add_argument('-i','--input',required=True)
    parser.add_argument('-o','--output',default=None)
    parser.add_argument('-l','--lang',default=TAR_LANG)
    parser.add_argument('-c','--config',default=RENDER_CONFIG)
    parser.add_argument('-st','--start',default=0,type=float)
    parser.add_argument('-en','--end',default=0,type=float)
    args=parser.parse_args()
    wss=find_workspaces(args.input)
    if not wss:
        out=Path(args.output).resolve()if args.output else Path(args.input).parent/f"{Path(args.input).stem}_{args.lang}_final.mp4"
        if out.exists()and out.stat().st_size>0:return txt.magenta(f'[PASS] "{str(out)}"')
        prepare_and_render(input_media=Path(args.input),output_target=out,lang=args.lang,config_path=args.config,start=args.start,end=args.end)
        if out.exists()and out.stat().st_size>0:txt.green(f'[DONE]: "{str(out)}"')
        return
    for ws in wss:
        out=Path(args.output).resolve()if args.output else ws.final_video(args.lang)
        if out.exists()and out.stat().st_size>0:
            txt.magenta(f'[PASS] "{str(out)}"')
            continue
        prepare_and_render(input_media=ws.media_path,output_target=out,lang=args.lang,config_path=args.config,start=args.start,end=args.end)
        if out.exists()and out.stat().st_size>0:txt.green(f'[DONE]: "{str(out)}"')

if __name__=='__main__':main()