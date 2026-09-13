from pathlib import Path
import os,sys,traceback
from src.enties import agr
from src.utils import txt,ext,cal_time,is_ext,listFilter,handle_input
from src.configuration import P_DIR, UVR_MODEL
from src.modules import demucs

def run(source,output):
    try:process.separate(source,output)
    except Exception as e: traceback.print_exception(e)
    
if __name__ == '__main__':
    process:demucs.Processor = cal_time(lambda: demucs.Processor(), 'Load Processor')
    p = os.path
    args = [
        agr(('-i', '--input')),
        agr(('-o', '--output')),
        agr(('-m', '--model'), default='voc') # voc || inst
    ]

    kwargs = handle_input(*args)
    source,output = P_DIR,None
    model = UVR_MODEL
    if kwargs.model:
        if kwargs.model.lower() == 'inst': model = 'UVR-MDX-NET-Inst_HQ_3.onnx'
        elif kwargs.model.lower() == 'voc': model = 'UVR-MDX-NET-Voc_FT.onnx'
    txt.yellow(f'Model: "{model}"')
    demucs.C.mn_audio_separate = model
    
    if kwargs.input:
        if p.exists(kwargs.input):source = Path(kwargs.input)
        else: txt.yellow(f'"{kwargs.input}" not exist!');sys.exit(0)

    txt.cyan(source)
    if kwargs.output:output=Path(kwargs.output);output.mkdir(exist_ok=True)

    if source.is_dir():
        for i, v in enumerate(listFilter(source, ext.VIDEO), 1):
            x=(source/v);x=x.with_suffix('')/x.stem
            run(source=source/v,output=((output or source)/v).with_suffix(''))
    elif source.is_file() and is_ext(str(source)):
        run(source=source,output=output or source.with_suffix(''))
    
        
