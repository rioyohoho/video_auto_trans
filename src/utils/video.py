import subprocess, json, math, os
from pathlib import Path
from src import configuration as C

def extract_audio(video_path: Path, suffix=".m4a") -> Path:
    output = video_path.with_suffix(suffix=suffix)
    if output.exists(): return output
    subprocess.run([C.FFMPEG,
        "-hide_banner", "-loglevel", "error",
        "-i", str(video_path), "-vn", "-acodec", "copy", str(output)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return output

def get_media_duration(path: str) -> float:
	cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]
	result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
	No = result.stdout.strip()
	return float(No if No != 'N/A' else '.0')

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
