import os
import sys
from pathlib import Path
from tabulate import tabulate
from src.modules.speech_ai import XTTSProcessor
from src.utils import ext, txt, file, agr, r_json, listFilter, handle_input, txt_normalize, cal_time, normalize_vietnamese_text
from src.configuration import PATH_BASE, P_DIR, TAR_LANG, XTTS_TMP_VOICE
P = os.path
processor = cal_time(lambda: XTTSProcessor(), 'LOAD: XTTSProcessor', 1, 1)

def run(text: str, output: Path, language: str = TAR_LANG, tmp_voice: str = str(XTTS_TMP_VOICE)):
    if language == 'vi': text = normalize_vietnamese_text(text)
    ts = processor.split_text_by_tokens(text, lang=language, mt=100)
    mini_text = lambda txt,sz=100: txt if len(txt)<=sz else txt[:sz//2]+' ... '+txt[-sz//2:]
    txt.cyan(tabulate(
        maxcolwidths=[None, None, None, 50],
        headers=['language', 'output', 'tmp_voice', 'texts'],
        tabular_data=[(language, str(output), str(tmp_voice), mini_text('\n'.join(ts), 50))],
        tablefmt="grid"
    ))
    processor.save(output, processor.concat(processor.text_to_ai_speeches(ts, language=language, tmp_voice=tmp_voice)))

def _exec(p: Path, o: Path, l: str = TAR_LANG, t: Path = XTTS_TMP_VOICE):
    if p.suffix == '.json':
        d = '\n'.join([x.get('text', '') for x in list[dict](r_json(str(p))) if x.get('text')])
    elif p.suffix == '.txt':
        d = file.r_text(str(p))
    else:
        txt.red(f'"{p}" is not a valid file!')
        return
    run(d, o or p.with_suffix(f'.{l}.wav'), l, t)
def _exec_str(text: str, o: Path, l: str = TAR_LANG, t: Path = XTTS_TMP_VOICE):
    run(text, o or Path(f'./{txt_normalize(text, 39)}.{l}.wav'), l, t)

if __name__ == '__main__':
    args = handle_input(
        agr(('-i', '--input'), type=str, required=False, default=P_DIR),
        agr(('-o', '--output'), type=str, required=False, default=''),
        agr(('-t', '--temple'), type=str, required=False, default=XTTS_TMP_VOICE),
        agr(('-l', '--language'), type=str, required=False, default='en')
    )
    i, o, t, l = str(args.input), str(args.output), Path(args.temple), str(args.language)
    op = Path(o) if o else None

    if not t.absolute(): t = PATH_BASE / t

    try:
        p, is_d, is_f = Path(i), Path(i).is_dir(), Path(i).is_file()
    except OSError:
        p, is_d, is_f = Path('.'), False, False
    if is_d:
        if not p.exists():
            sys.exit(0)
        for _, n in enumerate(listFilter(p, exts=ext.DOC), 1):
            _exec((p / n), op, l, t)
    elif is_f and str(p).endswith(ext.DOC):
        if not p.exists():
            sys.exit(0)
        _exec(p, op, l, t)
    else:
        _exec_str(i, op, l, t)