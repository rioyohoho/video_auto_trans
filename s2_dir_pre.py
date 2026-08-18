import os, shutil, fnmatch

def pre_dir(src_dir: str, deep_child=1, *ext):
    for root, dirs, files in os.walk(src_dir):
        depth = root[len(src_dir) :].count(os.sep)
        if depth == 0 or depth > deep_child:
            continue
        for f in files:
            if ext and not any(fnmatch.fnmatch(f.lower(), e.lower() if e.startswith('*') else f'*{e.lower()}') for e in ext):
                continue
            sf = os.path.join(root, f)
            nf = (
                f"{os.path.basename(root)}_{f}"
                if depth >= 2
                else f
            )
            df = os.path.join(src_dir, nf)
            if os.path.exists(df):
                b, e_ = os.path.splitext(nf)
                c = 1
                while os.path.exists(os.path.join(src_dir, f"{b} ({c}){e_}")):
                    c += 1
                df = os.path.join(src_dir, f"{b} ({c}){e_}")
            shutil.move(sf, df)

pre_dir(r"D:\vds\AP_exports", 1, *['.en_US.srt', '.en_US.mp3'])
# pre_dir(r"D:\vds\AP_exports", 1, *[".mp4",".mkv",'.vi_VN.srt','.vi_VN.mp3', '*_music.mp3'])
# pre_dir(r"D:\vds\cn_1080x1920", 1, *['.srt'])