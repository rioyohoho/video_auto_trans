import re,os,torch,torchaudio
from typing import BinaryIO,List,Union
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from huggingface_hub import snapshot_download
from src.configuration import XTTS_REPO_ID,XTTS_DIR_PATH,TAR_LANG,XTTS_TMP_VOICE
class XTTSProcessor:
    _inst=None
    def __new__(cls,*args,**kwargs):
        if cls._inst is None: cls._inst=super(XTTSProcessor,cls).__new__(cls);cls._inst._init=False
        return cls._inst
    def __init__(self,ckpt:str=str(XTTS_DIR_PATH)):
        if self._init: return
        self.ckpt,self.dev,self.m,self._init=ckpt,"cuda" if torch.cuda.is_available() else "cpu",None,True
    def get_model(self)->Xtts:
        if self.m: return self.m
        os.makedirs(self.ckpt,exist_ok=True)
        cp=os.path.join(self.ckpt,"config.json")
        if not os.path.exists(cp): snapshot_download(repo_id=XTTS_REPO_ID,repo_type="model",local_dir=self.ckpt)
        cfg=XttsConfig()
        cfg.load_json(cp)
        self.m=Xtts.init_from_config(cfg)
        self.m.load_checkpoint(cfg,checkpoint_dir=self.ckpt,eval=True)
        self.m.to(self.dev)
        return self.m
    def _tlen(self,txt:str,lang:str)->int:
        tm=self.get_model().tokenizer
        try: return len(tm.encode(txt,lang))
        except NotImplementedError: return len(tm.encode(txt,"en"))
        except TypeError: return len(tm.encode(txt))
    def split_text_by_tokens(self,text:str,lang:str,mt:int=200)->List[str]:
        c,cur,cl=[],'',0
        for s in re.split(r'(?<=[.!?])\s+',text):
            sl=self._tlen(s,lang)
            if sl>mt:
                if cur: c.append(cur.strip());cur,cl='',0
                tmp=''
                for w in s.split():
                    tst=tmp+(' '+w if tmp else w)
                    if self._tlen(tst,lang)<=mt: tmp=tst
                    else: c.append(tmp.strip());tmp=w
                if tmp: c.append(tmp.strip())
                continue
            if cl+sl<=mt: cur+=(' '+s if cur else s);cl+=sl
            else: c.append(cur.strip());cur,cl=s,sl
        if cur: c.append(cur.strip())
        return c
    def text_to_ai_speeches(self,texts:List[str],language:str=TAR_LANG or 'en',tmp_voice:str=str(XTTS_TMP_VOICE))->List[torch.Tensor]:
        if not os.path.exists(tmp_voice): raise FileNotFoundError(tmp_voice)
        m,res=self.get_model(),[]
        gl,se=m.get_conditioning_latents(audio_path=tmp_voice,gpt_cond_len=m.config.gpt_cond_len,max_ref_length=m.config.max_ref_len,sound_norm_refs=m.config.sound_norm_refs)
        for t in texts:
            if not t.strip(): continue
            kargs=dict(text=t,gpt_cond_latent=gl,speaker_embedding=se,temperature=0.3,length_penalty=1.0,repetition_penalty=10.0,top_k=30,top_p=0.85,enable_text_splitting=False)
            try: o=m.inference(**kargs,language=language)
            except NotImplementedError: o=m.inference(**kargs,language="en")
            w=torch.tensor(o['wav'])
            res.append(w.unsqueeze(0) if w.dim()==1 else w)
        return res
    @staticmethod
    def save(tgt:Union[BinaryIO,os.PathLike,str],tns:torch.Tensor,sr:int=24000):
        if isinstance(tgt,(str,os.PathLike)): os.makedirs(os.path.dirname(os.path.abspath(tgt)),exist_ok=True)
        return torchaudio.save(tgt,tns,sr)
    @staticmethod
    def concat(tns:List[torch.Tensor])->torch.Tensor:
        return torch.cat(tns,dim=1) if tns else torch.tensor([[]])