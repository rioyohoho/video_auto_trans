import re,os,torch,torchaudio
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from transformers import AutoTokenizer
from huggingface_hub import snapshot_download
from src.utils import cal_time
from src.configuration import XTTS_REPO_ID, XTTS_DIR_PATH


tokenizer = cal_time(lambda: AutoTokenizer.from_pretrained("bert-base-multilingual-cased"), 'LOAD: AutoTokenizer', tab=3) 
def split_text_by_tokens(text:str,max_tokens=200):
        sentences=re.split('(?<=[.!?])\\s+',text);chunks=[];current_chunk='';current_tokens_count=0
        for sentence in sentences:
            sentence_tokens=tokenizer.encode(sentence,add_special_tokens=False);sentence_token_len=len(sentence_tokens)
            if sentence_token_len>max_tokens:
                if current_chunk:chunks.append(current_chunk.strip());current_chunk='';current_tokens_count=0
                words=sentence.split();temp_sub_chunk=''
                for word in words:
                    test_chunk=temp_sub_chunk+(' '+word if temp_sub_chunk else word)
                    if len(tokenizer.encode(test_chunk,add_special_tokens=False))<=max_tokens:temp_sub_chunk=test_chunk
                    else:chunks.append(temp_sub_chunk.strip());temp_sub_chunk=word
                if temp_sub_chunk:chunks.append(temp_sub_chunk.strip())
                continue
            if current_tokens_count+sentence_token_len<=max_tokens:current_chunk+=' '+sentence if current_chunk else sentence;current_tokens_count+=sentence_token_len
            else:chunks.append(current_chunk.strip());current_chunk=sentence;current_tokens_count=sentence_token_len
        if current_chunk:chunks.append(current_chunk.strip())
        return chunks
def save(target:os.BinaryIO|os.PathLike|str,audio_tensor:torch.Tensor, sr=24e3):return torchaudio.save(target, audio_tensor, sr)
def get_xtts_model(checkpoint_dir=str(XTTS_DIR_PATH)) -> Xtts:
    os.makedirs(checkpoint_dir, exist_ok=True)
    snapshot_download(repo_id=XTTS_REPO_ID, repo_type="model", local_dir=checkpoint_dir)
    config_path = os.path.join(checkpoint_dir, "config.json")
    config = XttsConfig()
    config.load_json(config_path)
    return Xtts.init_from_config(config)
def text_to_ai_speechs(texts: list[str], tmp_voice: str, xtts_model: Xtts = None) -> torch.Tensor:
	if xtts_model is None:
		xtts_model = get_xtts_model()
	device = "cuda" if torch.cuda.is_available() else "cpu"
	xtts_model.to(device)
	gpt_cond_latent, speaker_embedding = xtts_model.get_conditioning_latents(
		audio_path=tmp_voice,
		gpt_cond_len=xtts_model.config.gpt_cond_len,
		max_ref_length=xtts_model.config.max_ref_len,
		sound_norm_refs=xtts_model.config.sound_norm_refs,
	)
	audio_tensors = []
	for text_to_speak in texts:
		out = xtts_model.inference(
			text=text_to_speak,
			language="en",
			gpt_cond_latent=gpt_cond_latent,
			speaker_embedding=speaker_embedding,
			enable_text_splitting=False,
		)
		audio_tensors.append(torch.tensor(out["wav"]))
	return torch.cat(audio_tensors).unsqueeze(0)