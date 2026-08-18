import os, re, shutil

def in_dir(src_dir: str, is_deep=False, *ext):
    for f in os.listdir(src_dir):
        sf = os.path.join(src_dir, f)
        if os.path.isdir(sf) or (
            ext and not f.lower().endswith(tuple(e.lower() for e in ext))
        ):
            continue
        if is_deep and "_" in f:
            parts = f.split("_")
            curr_dir = src_dir
            for p in parts[:-1]:
                curr_dir = os.path.join(curr_dir, p)
                os.makedirs(curr_dir, exist_ok=True)
            shutil.move(sf, os.path.join(curr_dir, parts[-1]))
        else:
            m = re.match(r"^([^._]+)", f)
            if m:
                td = os.path.join(src_dir, m.group(1))
                os.makedirs(td, exist_ok=True)
                shutil.move(sf, os.path.join(td, f))

# in_dir(r'D:\vds\cn_1080x1920', False, *[".mp4", '.mp3',".mkv", ".srt",'.json'])
# in_dir(r'D:\vds\cn_1080x1920@', False, *['.en_US.mp3', '.en_US.srt']) 
