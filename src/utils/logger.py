import sys, time

from colorama import init
init(autoreset=True)
# ANSI
R   = "\033[31m"    # Red
G   = "\033[32m"    # Green
Y   = "\033[33m"    # Yellow
B   = "\033[34m"    # Blue
M   = "\033[35m"    # Magenta
C   = "\033[36m"    # Cyan
W   = "\033[37m"    # White
GR  = "\033[90m"    # Gray
RS  = "\033[0m"     # Reset
CCL = "\033[K"      # Clear Line

class style:
    "## Styles"
    RED = R
    GREEN = G
    YELLOW = Y
    BLUE = B
    MAGENTA = M
    CYAN = C
    WHITE = W
    GRAY = GR
    RESET = RS
    CLEAR = CCL

def clear(n=1): n > 0 and sys.stdout.write(f"\033[{n}A\r\033[J");sys.stdout.flush()
cl = clear
def line(txt='', color=W, tab=0): print(f"{'\t'*tab}{color or W}{txt}{RS}")
ln = line
def replace(txt, color=None, tab=0): sys.stdout.write(f"\r{CCL}{'\t'*tab}{color or W}{txt}{RS}"); sys.stdout.flush()
re = replace
def progress(current=0, total=100, txt="Process", suffix=None, bar_color=None, tab=0, **bar):
    f,l,s = bar.get('fill', '█'), bar.get('line', '-'), bar.get('size', 25)
    total = total or 1; percent = current / total; pk = int(percent * s)
    sfx = suffix if suffix is not None else f"({(percent*100):.2f})%"
    bar = f"{W}|{bar_color or W}{f*pk}{GR}{l*(s-pk)}{W}|"
    msg = f"{'\t'*tab}{C}{txt} ({Y}{current}{C}/{Y}{total}{C}): {bar} : {GR}\"{sfx}\"{RS}"
    sys.stdout.write(f"\r{CCL}{msg}"); sys.stdout.flush()
    if current >= total: print()
pr = progress
def cal_time(fun, txt=None, tab=0, clear=0):
    L=lambda x,k=W:print(f"{'\t'*tab}{k}{x}{RS}")
    p,m,cl,y=time.strftime,time.perf_counter,f'{B} : ',f'{GR}"{txt or fun.__name__}"'
    s,k=m(),f'{Y}{p("%H:%M:%S")}'
    L(f'{C}START{cl}{k}{cl}{y}',Y)
    e=fun();d=m()
    z,x=f'{Y}{p("%H:%M:%S")}',f' {W}({R}{d-s:.2f}{W})s'
    if clear>0:sys.stdout.write(f"\r{CCL}\033[F"*clear);sys.stdout.flush();L(f'TIME{cl}{k} {W}~ {z}{x}{cl}{y}',C)
    else:L(f'END{cl}{z}{x}{cl}{y}',C)
    return e
ct = cal_time

class text:
    def red(txt, tab=0): ln(txt, R, tab)
    def green(txt, tab=0): ln(txt, G, tab)
    def yellow(txt, tab=0): ln(txt, Y, tab)
    def blue(txt, tab=0): ln(txt, B, tab)
    def magenta(txt, tab=0): ln(txt, M, tab)
    def cyan(txt, tab=0): ln(txt, C, tab)
    def white(txt, tab=0): ln(txt, W, tab)
    def gray(txt, tab=0): ln(txt, GR, tab)

