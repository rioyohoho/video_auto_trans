from src.enties import agr
from src.utils import txt,ext,handle_input,is_ext,listFilter
from src.modules import transcribe, demucs
from src.utils.text import str2bool
from src.configuration import P_DIR
from pathlib import Path
import os,sys,traceback


def run(source:Path,output:Path,language:str|None=None):
    vocal_path = source.with_suffix('')/(source.stem+f'_{demucs.C.n_voice}.mp3')
    if vocal_path.exists(): source=vocal_path
    try:transcribe.initialization(p_audio=source,target=output,language=language)
    except Exception as e: traceback.print_exception(e)


if __name__ == '__main__':
    p = os.path
    args = [
        agr(('-i', '--input')),
        agr(('-o', '--output')),
        agr(('-l', '--language'),type=str,default=None),
        agr(('-c-bs', '--beam_size'),type=int),
        agr(('-c-wt', '--word_timestamps'),type=str2bool),
        agr(('-c-copt', '--condition_on_previous_text'),type=str2bool),
        agr(('-c-vf', '--vad_filter'),type=str2bool),
    ]

    kwargs = handle_input(*args)
    source,output = P_DIR,None
    for k, v in list(vars(kwargs).items())[2:]:
        if v is not None: setattr(transcribe.C,k,v)

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
        
