from ._enties import Data, Range
from typing import List, Optional, Union
from dataclasses import dataclass,field
from enum import Enum, IntEnum

@dataclass
class Solid(Data):value: str = "#ffffff"
@dataclass
class Gradian(Data):
    deg: int = 45
    values: List[str] = field(default_factory=lambda: ["#ffffff80", "#000000ff"])
class EnumColor(Enum):
    SOLID = Solid
    GRADIAN = Gradian
class Alignment(IntEnum):
    TOP_LEFT = TL = 5
    TOP_CENTER = TC = 6
    TOP_RIGHT = TR = 7
    CENTER_LEFT = CL = 9
    CENTER_MID = CM = 10
    CENTER_RIGHT = CR = 11
    BOTTOM_LEFT = BL = 1
    BOTTOM_CENTER = BC = 2
    BOTTOM_RIGHT = BR = 3
@dataclass
class Font(Data):
    name: str = 'arial'
    size: int = 16
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikeout: bool = False
    scaleX: int = 100
    scaleY: int = 100
    spacing: int = 0
    angle: int = 0
@dataclass
class Background(Data):
    color: Union[Solid, Gradian] = field(default_factory=Solid)
    padding: int = 0
@dataclass
class Color:
    primary: Optional[Union[Solid, Gradian]] = field(default_factory=Solid)
    outline: Optional[Union[Solid, Gradian]] = field(default_factory=lambda: Solid("#000000ff"))
    shadow: Optional[Union[Solid, Gradian]] = field(default_factory=lambda: Solid("#00000000"))
@dataclass
class Subtitle:
    font: Font = field(default_factory=Font)
    color: Color = field(default_factory=Color)
    alignment: Alignment = Alignment.BOTTOM_CENTER
    outline_width: int = 2
    shadow_depth: int = 0
    background: Optional[Background] = None