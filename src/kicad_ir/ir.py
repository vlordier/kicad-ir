from pydantic import BaseModel
from typing import List, Tuple

Point = Tuple[int, int]

class Pad(BaseModel):
    id: str
    net: str
    x: int
    y: int

class Net(BaseModel):
    id: str
    pads: List[str]

class Board(BaseModel):
    width: int
    height: int
    pads: List[Pad]
    nets: List[Net]
