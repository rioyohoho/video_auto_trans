import re

def filter_bad_words(texts: list[str], json_data:dict) -> list[str]:
    if not json_data: return texts
    replace_map = {}
    for k, v in json_data.items():
        if isinstance(v, dict): replace_map.update(v)
        else: replace_map[k] = v
    bad_words_pattern = "|".join(re.escape(k) for k in sorted(replace_map.keys(), key=len, reverse=True))
    reg = re.compile(bad_words_pattern, flags=re.IGNORECASE)
    def replace_func(match:re.Match[str]):
        word = match.group(0).lower()
        return replace_map.get(word, match.group(0))
    return [reg.sub(replace_func, text) for text in texts]
def revert_srt(timestamps:list[tuple[float,float,str]],max_len:int=0)->str:
	def fmt(sec:float)->str:
		ms=int(round(sec%1*1000))
		if ms>=1000:sec+=1;ms=0
		h,r=divmod(int(sec),3600);m,s=divmod(r,60);return f"{h:02}:{m:02}:{s:02},{ms:03}"
	processed_timestamps=[]
	if max_len<1:processed_timestamps=timestamps
	else:
		for(start,end,text)in timestamps:
			words=text.split();total_words=len(words);duration=end-start
			if total_words<=max_len:processed_timestamps.append((start,end,text))
			else:
				chunks=[words[i:i+max_len]for i in range(0,total_words,max_len)];current_word_count=0
				for chunk in chunks:chunk_len=len(chunk);chunk_start=start+current_word_count/total_words*duration;current_word_count+=chunk_len;chunk_end=start+current_word_count/total_words*duration;chunk_text=' '.join(chunk);processed_timestamps.append((chunk_start,chunk_end,chunk_text))
	blocks=[]
	for(i,(start,end,text))in enumerate(processed_timestamps,1):block=f"{i}\n{fmt(start)} --> {fmt(end)}\n{text}";blocks.append(block)
	return'\n\n'.join(blocks)
def convert_srt(srt_content: str) -> list[dict]:
    def time_to_sec(time_str: str) -> float:
        h, m, s = time_str.replace(',', '.').split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    srt_content = srt_content.replace('\r\n', '\n').strip()
    blocks = re.split(r'\n\s*\n', srt_content)
    result = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0].strip())
            except ValueError:
                continue
            if '-->' in lines[1]:
                start_str, end_str = lines[1].split('-->')
                result.append({
                    "index": index,
                    "start": time_to_sec(start_str.strip()),
                    "end": time_to_sec(end_str.strip()),
                    "text": "\n".join(lines[2:]).strip()
                })
    return result
def str2bool(v):
	if isinstance(v,bool):return v
	if v.lower()in('yes','true','t','y','1'):return True
	elif v.lower()in('no','false','f','n','0'):return False