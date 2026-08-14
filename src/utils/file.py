import os, json

def load_json(path: str) -> dict | list:
    if not os.path.exists(path): return {}
    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    def to_tuple(data):
        if isinstance(data, list):
            if data and all(isinstance(x, (int, float)) for x in data):
                return tuple(data)
            return [to_tuple(i) for i in data]
        elif isinstance(data, dict):
            return {k: to_tuple(v) for k, v in data.items()}
        return data
    return to_tuple(config)
def save_json(path: str, data: dict | list, indent:int|str|None=None) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, default=str)
    return path
def load_text(path: str) -> str:
    if not os.path.exists(path): return ""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
def save_text(path: str, data: str|list) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'w', encoding='utf-8') as f:
        f.write('\n'.join(data) if isinstance(data,list) else data)
    return path

r_json = load_json
w_json = save_json
r_text = load_text
w_text = save_text