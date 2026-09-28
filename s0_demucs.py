import sys,traceback
from video_auto_trans.src.enties import agr
from video_auto_trans.src.utils import txt,cal_time,handle_input
from video_auto_trans.src.configuration import P_DIR,UVR_MODEL
from video_auto_trans.src.modules import demucs
from video_auto_trans.src.workspace import find_workspaces,Workspace

def run(ws:Workspace):
    voc_dst,mus_dst=ws.vocal_path('.mp3'),ws.music_path('.mp3')
    if voc_dst.exists()and voc_dst.stat().st_size>0 and mus_dst.exists()and mus_dst.stat().st_size>0:
        txt.magenta(f'[PASS] "{str(voc_dst)}"')
        txt.magenta(f'[PASS] "{str(mus_dst)}"')
        return
    try:
        process.separate(source=ws.media_path,output=ws.work_dir)
        v_out,m_out=ws.work_dir/f"{ws.stem}_{demucs.C.n_voice}.mp3",ws.work_dir/f"{ws.stem}_{demucs.C.n_instrumental}.mp3"
        if v_out.exists()and v_out!=voc_dst:v_out.rename(voc_dst)
        if m_out.exists()and m_out!=mus_dst:m_out.rename(mus_dst)
        txt.green(f'[DONE]: "{str(voc_dst)}"')
        txt.green(f'[DONE]: "{str(mus_dst)}"')
    except Exception as e:traceback.print_exception(e)

if __name__=='__main__':
    process:demucs.Processor=cal_time(lambda:demucs.Processor(),'Load Processor')
    args=handle_input(agr(('-i','--input'),default=P_DIR),agr(('-m','--model'),default='voc'))
    if args.model.lower()=='inst':UVR_MODEL='UVR-MDX-NET-Inst_HQ_3.onnx'
    elif args.model.lower()=='voc':UVR_MODEL='UVR-MDX-NET-Voc_FT.onnx'
    demucs.C.mn_audio_separate=UVR_MODEL
    workspaces=find_workspaces(args.input)
    if not workspaces:sys.exit(0)
    for ws in workspaces:
        txt.cyan(f"Processing Separation: {ws.stem}")
        run(ws)