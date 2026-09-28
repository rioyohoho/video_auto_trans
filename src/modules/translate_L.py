import translators as ts
from video_auto_trans.src.utils import logger as log
from video_auto_trans.src.configuration import TAR_LANG

def local_translation(texts:str|list[str],from_lang:str='auto',tar_lang:str=TAR_LANG,chunk_size:int=45)->str|list[str]:
    f_code='auto'if from_lang in('auto','',None)else from_lang.lower().split('_')[0].split('-')[0]
    t_code=tar_lang.lower().split('_')[0].split('-')[0]
    is_single=isinstance(texts,str)
    lines=[texts]if is_single else list(texts)
    results=[]
    for i in range(0,len(lines),chunk_size):
        chunk=lines[i:i+chunk_size]
        log.pr(min(i+chunk_size,len(lines)),len(lines),txt=f"FastLocalBatch({f_code}->{t_code})...")
        joined_text="\n".join([t if t.strip()else "..."for t in chunk])
        res=None
        for engine in('bing','google'):
            try:
                res=ts.translate_text(joined_text,translator=engine,from_language=f_code,to_language=t_code)
                if res:break
            except Exception:pass
        if res:
            trans_lines=str(res).split('\n')
            if len(trans_lines)<len(chunk):trans_lines.extend(chunk[len(trans_lines):])
            results.extend([t.replace("...","").strip()for t in trans_lines[:len(chunk)]])
        else:results.extend(chunk)
    return results[0]if is_single else results