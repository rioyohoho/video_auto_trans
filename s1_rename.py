import json,re;from pathlib import Path
S=lambda n:re.sub(r'[\\/*?:"<>|]','',str(n))
def rename(D,F,R,E,fk='url',tk='vi_VN'):
	try:
		with open(F,'r',encoding='utf-8')as f:d=json.load(f)
	except:return
	l=[]
	for fp in Path(D).iterdir():
		if fp.is_file()and fp.suffix in E:
			mi=next((i for i in d if i.get(fk) and Path(str(i.get(fk))).name in fp.stem),None)
			if mi and mi.get(tk):
				n=fp.name.split('.',1);nn=f"{S(mi[tk])}{"."+n[1]if len(n)>1 else""}";np=fp.with_name(nn)
				if not np.exists():
					try:fp.rename(np);l.append({'old':fp.name,'new':nn});print(f"{fp.name} -> {nn}")
					except:continue
	try:
		with open(R,'w',encoding='utf-8')as f:json.dump(l,f,ensure_ascii=False,indent=4)
	except:pass



class K:
	cre='create_time'
	it='item_title'
	ai='aweme_id'
	url='url'
	vi='vi_VN'
	en='en_US'
VD=Path(r'D:\vds\en')
DA=Path(r"D:\vds\data_178.json")
RE=DA.with_name(f'{DA.name}_re.json')
rename(VD,DA,RE,[".mp4",'.mp3',".mkv",".srt"], K.url,K.cre)