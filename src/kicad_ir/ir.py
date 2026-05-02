from __future__ import annotations

from enum import Enum
from typing import Iterable

from pydantic import BaseModel, Field, model_validator

Point2D = tuple[int, int]
LayerPoint = tuple[int, int, int]


class Layer(BaseModel):
    """A routable copper layer in the lossy routing IR."""

    id: int
    name: str


class Pad(BaseModel):
    """A simplified pad: rectangular occupancy around a grid coordinate."""

    id: str
    net: str
    x: int
    y: int
    layer: int | None = None  # None means all copper layers.
    radius: int = 1

    def occupied_cells(self, layers: Iterable[int]) -> set[LayerPoint]:
        target_layers = list(layers) if self.layer is None else [self.layer]
        cells: set[LayerPoint] = set()
        for layer in target_layers:
            for dx in range(-self.radius, self.radius + 1):
                for dy in range(-self.radius, self.radius + 1):
                    cells.add((self.x + dx, self.y + dy, layer))
        return cells


class Net(BaseModel):
    id: str
    pads: list[str]
    width: int = 1
    clearance: int = 1
    preferred_layer: int | None = None


class Obstacle(BaseModel):
    id: str
    x0: int
    y0: int
    x1: int
    y1: int
    layers: list[int] | None = None

    @model_validator(mode="after")
    def normalize(self) -> "Obstacle":
        if self.x1 < self.x0:
            self.x0, self.x1 = self.x1, self.x0
        if self.y1 < self.y0:
            self.y0, self.y1 = self.y1, self.y0
        return self

    def occupied_cells(self, board_layers: Iterable[int]) -> set[LayerPoint]:
        target_layers = self.layers or list(board_layers)
        return {
            (x, y, layer)
            for layer in target_layers
            for x in range(self.x0, self.x1 + 1)
            for y in range(self.y0, self.y1 + 1)
        }


class Via(BaseModel):
    x: int
    y: int
    from_layer: int
    to_layer: int
    net: str


class TrackSegment(BaseModel):
    net: str
    layer: int
    start: Point2D
    end: Point2D
    width: int = 1


class Route(BaseModel):
    net: str
    path: list[LayerPoint]
    segments: list[TrackSegment] = Field(default_factory=list)
    vias: list[Via] = Field(default_factory=list)


class Board(BaseModel):
    width: int
    height: int
    layers: list[Layer] = Field(default_factory=lambda: [Layer(id=0, name="F.Cu")])
    pads: list[Pad]
    nets: list[Net]
    obstacles: list[Obstacle] = Field(default_factory=list)

    @property
    def layer_ids(self) -> list[int]:
        return [layer.id for layer in self.layers]

    @property
    def pads_by_id(self) -> dict[str, Pad]:
        return {pad.id: pad for pad in self.pads}

    @property
    def nets_by_id(self) -> dict[str, Net]:
        return {net.id: net for net in self.nets}


class RouteStatus(str, Enum):
    routed = "routed"
    failed = "failed"


class RouteResult(BaseModel):
    status: RouteStatus
    routes: list[Route] = Field(default_factory=list)
    failed_nets: list[str] = Field(default_factory=list)
