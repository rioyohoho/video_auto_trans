import re,sys
from pathlib import Path
from dataclasses import astuple,asdict
from src.enties import Transcribe
from src.utils.text import str2bool
from src.modules.transcribe import mdl,C as trC
from src.utils import txt, agr, ext, r_json, w_json, w_text, to_srt, handle_input, listFilter
from src.configuration import P_DIR, LANGS, MAP_LANGS

def _exec(path:Path, lang:str, words=1):
    print(f'LANG: {lang}, WORDS: {words}', path)
    if not path.exists(): return
    name = path.name.split('.')[0]
    json_path = path.with_name(name+f'{'_'+str(words) if words>0 else ''}.{MAP_LANGS.get(lang, lang)}.json'); jhs = json_path.exists()
    srt_path = json_path.with_suffix('.srt')
    data:list[Transcribe] = mdl.transcribe_length(str(path),lang,words) if words and words>0 else \
        [Transcribe(**d) for d in r_json(str(json_path))] if jhs else mdl.transcribe(str(path),lang)
    
    if w==1:
        for d in data: re.sub(r'[,.!@]', '', d.text)
    if not jhs:
        txt.green(f'TRANSCRIBE: {srt_path}')
        w_json(str(json_path), [asdict(d) for d in data])
    if not srt_path.exists(): 
        txt.magenta(f'SRT PATH: {srt_path}')
        w_text(str(srt_path), to_srt([astuple(d) for d in data]))

if __name__ == '__main__':
    args = handle_input(
        agr(('-i', '--input'), type=str, required=False, default=P_DIR),
        agr(('-l', '--language'), type=str, required=False,default=','.join(LANGS)),
        agr(('-w', '--words'), type=int, required=False,default=1),
        agr(('-c-bs', '--beam_size'),type=int),
        agr(('-c-wt', '--word_timestamps'),type=str2bool),
        agr(('-c-copt', '--condition_on_previous_text'),type=str2bool),
        agr(('-c-vf', '--vad_filter'),type=str2bool),
    ) 
    path,l,w=Path(args.input),str(args.language).split(','),int(args.words)
    for k, v in list(vars(args).items())[2:]:
        if v is not None: setattr(trC,k,v)
    if not path.exists() or not l: sys.exit(0)

    if path.is_dir():
        for i, n in enumerate(listFilter(path, ext.VIDEO), 1):
            x=(path/n);xp=x.with_suffix('')/x.stem
            for _l in l: _exec(xp.with_suffix(f'.{_l}.mp3'),_l,w)
    elif path.is_file() and str(path).endswith(ext.AUDIO):
        for _l in [l for l in LANGS]: _exec(path,_l,w)