import os,sys,shutil,copy
from pathlib import Path
from tabulate import tabulate
from dataclasses import astuple
from src.modules import speech as mdl, demucs
from src.enties import Audio,TrackAudio,agr
from src.utils import ext,txt,r_json,listFilter
from src.utils import listFilter, handle_input, get_media_duration
from src.configuration import P_DIR,LANGS,MAP_LANGS
P = os.path

def run(path:Path,pitch:float,atempo:float,volume:float,language:str, clean_audio_files=False) -> bool:
    data:list[dict] = r_json(str(path)) # READ
    path = path.with_name(f'{path.name.split('.')[0]}.{language}.mp3')
    segments:list[Audio] = [Audio(**d,pitch=pitch,atempo=atempo,volume=volume) for d in data]
    peechs:list[Audio] = [a for a in mdl.texts_to_speechs(segments, path.with_suffix(''), target_lang=language) if a is not None]
    if not path.exists():
        txt.cyan(f'SPEECH({len(peechs)}) COMBINING...', 1)
        combined_path, duration = mdl.combine_audio_files(peechs, path, auto_speed=True)
        (txt.magenta if combined_path else txt.red)(f'{duration}, {combined_path}')
        if clean_audio_files and combined_path.exists():
            shutil.rmtree(path.with_suffix(''))
        return 1 if combined_path else 0

def _exec_json(x_langs: tuple[tuple[Path, float, float, float, str]], mixes_audio: list[TrackAudio] = None):
    if mixes_audio is None:mixes_audio = []
    txt.cyan(tabulate(
        headers=['path', 'pitch', 'atempo', 'volume', 'language'],
        tabular_data=x_langs, tablefmt="grid"
    ))
    
    for xls in x_langs:
        if not xls[0].exists(): txt.yellow(f'"{xls[0]}" does not exist!'); continue
        elif run(*xls, False) and mixes_audio:
            n, _l, _s = str(xls[0]).split('.') 
            current_mixes = copy.deepcopy(mixes_audio)
            current_mixes.append(TrackAudio(0, 0, f'.{_l}.mp3', volume=2.0))
            for ma in current_mixes:
                if not Path(ma.text).is_absolute():ma.text = n + ma.text
                ma.snd = ma.end = get_media_duration(ma.text)
            output = '.'.join([n, MAP_LANGS.get(_l, _l), 'mp3'])
            txt.gray(tabulate(
                headers=list(vars(current_mixes[0]).keys()),
                tabular_data=[astuple(d) for d in current_mixes], tablefmt="grid"
            ))
            txt.cyan(output)
            try:
                mdl.mix_audio_files(current_mixes, Path(output))
            except Exception as e: txt.yellow(f'Mixing audio files: {e}')

if __name__ == '__main__':
    mixes = [
        TrackAudio(0,0,f'_{demucs.C.n_instrumental}.mp3',volume=.5),
        TrackAudio(0,0,f'_{demucs.C.n_voice}.mp3',volume=.25),
    ]
    args = handle_input(
        agr(('-i', '--input'), type=str, required=False, default=P_DIR),
        agr(('-l', '--language'), type=str, required=False,default=','.join(LANGS)),
        agr(('-p', '--pitch'), type=float, required=False, default=1.39),
        agr(('-a', '--atempo'), type=float, required=False, default=1.25),
        agr(('-v', '--volume'), type=float, required=False, default=2.0)
    ) 
    i,l,p,a,v=str(args.input),str(args.language).split(','),float(args.pitch),float(args.atempo),float(args.volume)
    path:Path = Path(i)
    if not path.exists() or not l: sys.exit(0)

    if path.is_dir():
        for i, n in enumerate(listFilter(path, ext.VIDEO), 1):
            x=(path/n);xp=x.with_suffix('')/x.stem
            _exec_json([(xp.with_suffix(f'.{_l}.json'),p,a,v, _l) for _l in l],mixes)
    elif path.is_file() and str(path).endswith('.json'):
        _exec_json([(path,p,a,v, _l) for _l in l],mixes)