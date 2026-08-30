import subprocess, json, math
from pathlib import Path

def extract_audio(video_path,suffix='.m4a',ffmpeg_path='ffmpeg'):
	output=video_path.with_suffix(suffix)
	if output.exists():return output
	probe_cmd=['ffprobe','-v','error','-select_streams','a','-show_entries','stream=index','-of','json',str(video_path)]
	try:
		res=subprocess.check_output(probe_cmd,stderr=subprocess.STDOUT)
		if not json.loads(res).get('streams'):raise ValueError('File không có audio')
	except(subprocess.CalledProcessError,FileNotFoundError):pass
	cmd_copy=[ffmpeg_path,'-hide_banner','-loglevel','error','-y','-i',str(video_path),'-vn','-acodec','copy',str(output)]
	if subprocess.run(cmd_copy,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return output
	cmd_encode=[ffmpeg_path,'-hide_banner','-loglevel','error','-y','-i',str(video_path),'-vn','-c:a','aac',str(output)];subprocess.run(cmd_encode,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);return output

def get_media_duration(path):
    p=Path(path)
    if not p.exists(): return .0
    cmd=['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(p)]
    try:
        res=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True)
        s=res.stdout.strip()
        return float(s if s and s!='N/A' else .0)
    except subprocess.CalledProcessError as e: return .0

def get_video_size(src: Path) -> tuple[int, int]:
    """ ### return: x,y"""
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', str(src)]
    res = json.loads(subprocess.check_output(cmd))
    w = int(res['streams'][0]['width'])
    h = int(res['streams'][0]['height'])
    return w,h

def get_video_ratio(w:int,h:int):
    gcd = math.gcd(w, h)
    return f'{w//gcd}:{h//gcd}'
