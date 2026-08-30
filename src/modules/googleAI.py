import time
from google import genai
from google.genai import types, errors
from src.configuration import GEMINI_MODEL,KEY_STATUS_PATH
from src.utils import logger as log, execute_after_countdown

class T:
    list_APIkeys=[] # https://aistudio.google.com/api-keys
    key_enable_in=86400 # 24h
    gemini_model=GEMINI_MODEL
    key_status_path=KEY_STATUS_PATH

def _load_key_data():
    p=T.key_status_path
    list_keys=getattr(T, 'list_APIkeys', [])
    file_data={}
    if p.exists():
        for line in p.read_text().splitlines():
            line=line.strip()
            if not line: continue
            if ':' in line:
                k, ts=line.split(':', 1)
                file_data[k.strip()]=float(ts.strip())
            else:
                file_data[line]=0.0
    need_update=False
    for k in list_keys:
        if k not in file_data:
            file_data[k]=0.0
            need_update=True
    if need_update:
        _save_key_data(file_data)
    T.list_APIkeys=list(file_data.keys())
    return file_data
def _save_key_data(data):
    content="\n".join([f"{k}:{ts}" for k, ts in data.items()])
    T.key_status_path.write_text(content)
def _get_next_available_key():
    data=_load_key_data()
    if not data: return None
    now=time.time()
    for k in data:
        if now >= data[k]: return k
    return None

current_key=_get_next_available_key()
client=genai.Client(api_key=current_key) if current_key else None
is_resource_exhauted=current_key is None

def request(prompt: str = None, trials = 3, sleep=5, tab = 1):
    if not prompt: return
    global is_resource_exhauted, current_key, client
    while current_key:
        try:
            response = client.models.generate_content(
                model=T.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(include_thoughts=True))
            )
            return response.text
        except errors.ServerError as e:
            log.ln(f'Google AI ServerError ({e.code}): "{e.message}"', log.R, tab)
            if e.code == 503:
                if trials <= 0: break
                execute_after_countdown(sleep, lambda: log.cl(3))
                trials -= 1
            else: break
        except errors.ClientError as e:
            log.ln(f'Google AI ClientError ERROR({e.code}): "{e.message}"', log.R, tab)
            data = _load_key_data()
            if current_key in data:
                data[current_key] = time.time() + T.key_enable_in
                _save_key_data(data)
            current_key = _get_next_available_key()
            if current_key:
                client = genai.Client(api_key=current_key)
            else:
                is_resource_exhauted = True
                break
