import numpy as np
from dataclasses import dataclass, field
from enum import IntEnum, Enum
from ._enties import Data, Timestamp

@dataclass
class Canvas(Data):
    x: int = 0
    y: int = 0

    class Area(IntEnum):
        DEFAULT = D = 0
        BOTTOM = B = 123; CENTER = C = 456; TOP = T = 789
        LEFT = L = 147; MID = M = 258; RIGHT = R = 369
        TOP_LEFT = TL = 7; TOP_CENTER = TC = 8; TOP_RIGHT = TR = 9
        CENTER_LEFT = CL = 4; CENTER_MID = CM = 5; CENTER_RIGHT = CR = 6
        BOTTOM_LEFT = BL = 1; BOTTOM_CENTER = BC = 2; BOTTOM_RIGHT = BR = 3

    @staticmethod
    def on_frame(frame: 'Canvas', item: 'Canvas', area: Area = Area.DEFAULT, margin: float = .0) -> 'Canvas':
        if not isinstance(area, Canvas.Area):
            try: area = Canvas.Area(area)
            except ValueError: area = Canvas.Area.DEFAULT
        X, Y = frame.x, frame.y; a, b = item.x, item.y
        mx, my = X * margin, Y * margin; cx, cy = X / 2, Y / 2
        lx, rx = mx + a / 2, X - mx - a / 2; ty, by = my + b / 2, Y - my - b / 2
        A = Canvas.Area
        coords = {
            A.D: (cx, cy), A.B: (cx, by), A.C: (cx, cy), A.T: (cx, ty),
            A.L: (lx, cy), A.M: (cx, cy), A.R: (rx, cy),
            A.BL: (lx, by), A.BC: (cx, by), A.BR: (rx, by),
            A.CL: (lx, cy), A.CM: (cx, cy), A.CR: (rx, cy),
            A.TL: (lx, ty), A.TC: (cx, ty), A.TR: (rx, ty)
        }
        res_x, res_y = coords.get(area, coords[A.DEFAULT])
        return Canvas(int(res_x), int(res_y))

@dataclass
class Polygon(Data):
    points: list[Canvas] = field(default_factory=list)
    def get_focus(self): return Polygon.focus(self.points)

    @staticmethod
    def focus(points: list[Canvas]) -> Canvas:
        if not points: return Canvas(x=0, y=0)
        xs = np.fromiter((p.x for p in points), dtype=np.int32)
        ys = np.fromiter((p.y for p in points), dtype=np.int32)
        return Canvas(x=int(np.mean(xs)), y=int(np.mean(ys)))

@dataclass
class Source(Timestamp):
    path: str = ''
    trim: Timestamp = field(default_factory=Timestamp)

@dataclass
class Clip(Timestamp):
    layer: int = 0
    source: Source = field(default_factory=Source)

@dataclass
class Frame(Timestamp):
    scale: float = 1.0
    opacity: float = 1.0
    focus: Canvas = field(default_factory=Canvas)

@dataclass
class Clip_Video(Clip, Frame):
    pass

@dataclass
class Video_Keyframes(Data):
    clip: Clip = field(default_factory=Clip)
    frames: list[Frame] = field(default_factory=list)

@dataclass
class Delogo(Data):
    t: float = 0.0
    x: int = 0
    y: int = 0

@dataclass
class Delogo_KeyFrames(Data):
    class Mode(str,Enum):
        DELOGO = 'delogo'
        BLUR = 'blur'
        PIXELATE = 'pixelate'
        SOLID = 'solid'
        GBLUR = 'gblur'
    boxblur: int = 20
    width: int = 200
    height: int = 50
    mode: Mode = Mode.DELOGO
    color: str = "#00000080"
    keyframes: list[Delogo] = field(default_factory=list)

@dataclass
class Clip_Audio(Clip):
    volume: float = 1.0
    tempo: float = 1.0
    pitch: float = 1.0
    repeat: bool = False

    def __init__(self, volume: float = 1.0, source: Source = None, start: float = 0.0, end: float = 0.0, layer: int = 0, tempo: float = 1.0, pitch: float = 1.0, repeat: bool = False, **kwargs):
        super().__init__(start=start, end=end, layer=layer, source=source or Source())
        self.volume = float(volume)
        self.tempo = float(tempo)
        self.pitch = float(pitch)
        self.repeat = bool(repeat)
        for k, v in kwargs.items():
            setattr(self, k, v)
