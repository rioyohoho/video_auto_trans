import argparse
from dataclasses import dataclass
from typing import Callable, Any, Iterable

@dataclass
class agr:
    name_or_flags: list[str] | str
    action: str | type[argparse.Action] | None = None
    nargs: int | str | None = None
    const: Any = None
    default: Any = None
    type: Callable[[str], Any] | None = None
    choices: Iterable[Any] | None = None
    required: bool | None = None
    help: str | None = None
    metavar: str | tuple[str, ...] | None = None
    dest: str | None = None