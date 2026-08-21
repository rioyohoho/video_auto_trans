import os
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
env = os.getenv
env_p=lambda p,dir:p if not p or os.path.isabs(p)or not isinstance(p,str)else dir/p if isinstance(dir,Path)else p

P_DIR = Path(env('PATH_DIR'))
class ext:
    AUDIO = ('.mp3','.m4a','.wav','.flac','.aac')
    VIDEO = ('.mp4','.mkv','.avi','.mov')
    MEDIA = AUDIO + VIDEO
    DOC = ('.json', '.txt')
class aud(Enum):
    speechs = float(env('AUD_SPEECHS', 1.0))
    vocal = float(env('AUD_VOCAL', .0))
    music = float(env('AUD_MUSIC', .0))


PATH_BASE = Path(__file__).parent.parent
FFMPEG,FFPROBE = env('FFMPEG'),env('FFPROBE')

UVR_MODEL = env('UVR_MODEL', 'UVR-MDX-NET-Voc_FT.onnx')
UVR_DIR_PATH = env_p(env('UVR_DIR_PATH', 'assets/audio-models'), PATH_BASE)

XTTS_REPO_ID = env('XTTS_REPO_ID','coqui/XTTS-v2')
XTTS_DIR_PATH = env_p(env('XTTS_DIR_PATH','assets/voice_model'), PATH_BASE)
XTTS_TMP_VOICE = env_p(env('XTTS_TMP_VOICE', 'assets/temple.wav'), PATH_BASE)

GEMINI_MODEL = env('GEMINI_MODEL', 'gemini-3-flash-preview')
KEY_STATUS_PATH = env_p(env('KEY_STATUS_PATH','assets/_curren_key'), PATH_BASE)

LANGS = env('LANGS').split(',')
TAR_LANG = LANGS[0] if LANGS else 'vi'
MAP_LANGS = {
    'vi':'vi_VN',
    'en':'en_US'
}