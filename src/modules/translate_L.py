import re,time,translators as ts
from src.utils import logger as log
from src.configuration import TAR_LANG

engs = ('google','bing','caiyun')

def _s_trans(t:str,f:str,to:str)->str:
    for e in engs:
        try:
            r=ts.translate_text(t,translator=e,from_language=f,to_language=to)
            if r:return str(r).strip()
        except Exception:time.sleep(0.5)
    return t

def local_translation(texts:str|list[str],from_lang:str='auto',tar_lang:str=TAR_LANG,chunk_size:int=20)->str|list[str]:
    f_code='auto'if from_lang in('auto','',None)else from_lang.lower().split('_')[0].split('-')[0]
    t_code=tar_lang.lower().split('_')[0].split('-')[0]
    is_single=isinstance(texts,str)
    lines=[texts]if is_single else list(texts)
    results=[]
    for i in range(0,len(lines),chunk_size):
        chunk=lines[i:i+chunk_size]
        log.pr(min(i+chunk_size,len(lines)),len(lines),txt=f"FastLocalBatch({f_code}->{t_code})...")
        joined="\n".join([f"⟦{j}⟧ {t.strip()if t.strip()else '...'}"for j,t in enumerate(chunk)])
        res=None
        for e in engs:
            try:
                res=ts.translate_text(joined,translator=e,from_language=f_code,to_language=t_code)
                if res:break
            except Exception:time.sleep(0.5)
        parsed=[None]*len(chunk)
        if res:
            for idx,val in re.findall(r'⟦(\d+)⟧\s*([\s\S]*?)(?=(?:⟦\d+⟧|$))',str(res)):
                if idx.isdigit()and int(idx)<len(chunk):parsed[int(idx)]=val.replace("...","").strip()
        for j in range(len(chunk)):
            if not parsed[j]:parsed[j]=_s_trans(chunk[j],f_code,t_code)
        results.extend(parsed)
        time.sleep(0.3)
    return results[0]if is_single else results