import sys
from pathlib import Path
from dataclasses import asdict,astuple
from src.enties import agr
from src.utils import txt, ext, r_text, w_text, r_json, w_json, \
    is_ext, cal_time, filter_bad_words, to_srt, srt_to, handle_input, listFilter
from src.enties import Transcribe
from src.modules.translate import text_translation, ai_translation, translates
from src.configuration import P_DIR, LANGS, TAR_LANG, PATH_BASE, MAP_LANGS
RE_WORDS:dict = cal_time(lambda: r_json(
    str(PATH_BASE/f'assets/replace_bad_words.{TAR_LANG}.json')
), 'Load bad_words data!', clear=1)
USE_TRANS = translates

def _txts(texts:list[str], func=USE_TRANS, tar_lang='vi')->list[str]:
    txts = cal_time(lambda: func(texts=texts, tar_lang=tar_lang), f'Translate: {len(texts)}',tab=1,clear=1)
    return cal_time(lambda: filter_bad_words(txts, RE_WORDS.get(tar_lang)), 'Replace bad words',tab=1,clear=1)


def file_translate(i_path:str, tar_lang='vi', w_file=True, func=USE_TRANS) -> list[Transcribe|str]:
    p:Path = Path(i_path)
    if not p.exists(): print(f'"{i_path}" not exist!'); return []
    o_path = p.with_suffix(f'.{tar_lang}{p.suffix}')

    if i_path.endswith('.txt'):
        if o_path.exists():
            txt.magenta(o_path,1)
            return r_text(o_path).split('\n')
        data:list[str] = _txts(r_text(i_path).split('\n'), func, tar_lang)
        if w_file: w_text(str(o_path), '\n'.join(data))
    elif i_path.endswith('.srt'):
        if o_path.exists():
            txt.magenta(o_path,1)
            return [Transcribe(**d) for d in srt_to(r_text(o_path))]
        data:list[dict] = srt_to(r_text(i_path))
        texts = _txts([d.text for d in data], func, tar_lang)
        for d, tx in zip(data, texts): setattr(d, 'text', tx)
        w_text(str(o_path), to_srt(data))
    elif i_path.endswith('.json'):
        if o_path.exists(): 
            txt.magenta(o_path,1)
            return [Transcribe(**d) for d in r_json(o_path)]
        data:list[Transcribe] = [Transcribe(**d) for d in r_json(i_path)]
        texts = _txts([d.text for d in data], func, tar_lang)
        for d, tx in zip(data, texts): setattr(d, 'text', tx)
        if w_file: w_json(str(o_path), [asdict(d) for d in data])
    if w_file and o_path.exists(): txt.magenta(str(o_path), 1)
    return data


if __name__ == '__main__':
    args = handle_input(
        agr(('-i', '--input'), type=str, required=False, default=P_DIR),
        agr(('-l', '--language'), type=str, required=False,default=','.join(LANGS)),
        agr(('-s', '--srt'), type=bool, required=False, default=True),
    ) 
    inp,langs,with_srt=str(args.input),str(args.language).split(','),str(args.input)
    path:Path = Path(inp)
    if not path.exists() or not langs: sys.exit(0)

    if path.is_dir():
        i_data = listFilter(path, ext.VIDEO)
        szd,szl=len(i_data),len(langs);sz=szd*szl
        for i, v in enumerate(i_data, 1):
            x=(path/v);x=x.with_suffix('')/x.stem
            for j,_l in enumerate(langs, 1):
                txt.cyan(f'[{i}/{szd}] : [{j}/{szl}] : [{i+j}/{sz}]')
                res_data = file_translate(str(x.with_suffix('.json')),_l)
                if with_srt: w_text(str(x.with_suffix(f'.{MAP_LANGS.get(_l)}.srt')), to_srt([astuple(d) for d in res_data]))
    elif path.is_file():
        if is_ext(str(path), ext.VIDEO): 
            path = (path.with_suffix('')/path.stem).with_suffix('.json')
        if not str(path).endswith('.json'): sys.exit(0)
        for _l in langs:
            res_data = file_translate(str(path),_l)
            if with_srt: w_text(str(path.with_suffix(f'.{MAP_LANGS.get(_l)}.srt')), to_srt([astuple(d) for d in res_data]))

    

