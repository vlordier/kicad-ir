from __future__ import annotations

from enum import Enum
from typing import Iterable, Literal

from pydantic import BaseModel, Field, model_validator

Point2D = tuple[int, int]
LayerPoint = tuple[int, int, int]
PadShape = Literal["circle", "oval", "rect", "roundrect", "custom", "unknown"]


class Layer(BaseModel):
    id: int
    name: str


class NetClass(BaseModel):
    name: str
    width: int = 1
    clearance: int = 1
    via_diameter: int = 2
    via_drill: int = 1


class Pad(BaseModel):
    id: str
    net: str
    x: int
    y: int
    layer: int | None = None
    radius: int = 1
    half_width: int | None = None
    half_height: int | None = None
    shape: PadShape = "unknown"
    footprint_ref: str | None = None
    pad_name: str | None = None

    def occupied_cells(self, layers: Iterable[int]) -> set[LayerPoint]:
        target_layers = list(layers) if self.layer is None else [self.layer]
        rx = self.half_width if self.half_width is not None else self.radius
        ry = self.half_height if self.half_height is not None else self.radius
        cells: set[LayerPoint] = set()
        for layer in target_layers:
            for dx in range(-rx, rx + 1):
                for dy in range(-ry, ry + 1):
                    if self.shape in {"circle", "oval"}:
                        nx = dx / max(rx, 1)
                        ny = dy / max(ry, 1)
                        if nx * nx + ny * ny > 1.0:
                            continue
                    cells.add((self.x + dx, self.y + dy, layer))
        return cells


class Net(BaseModel):
    id: str
    pads: list[str]
    width: int = 1
    clearance: int = 1
    preferred_layer: int | None = None
    kicad_net_code: int | None = None
    netclass: str | None = None


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
        return {(x, y, layer) for layer in target_layers for x in range(self.x0, self.x1 + 1) for y in range(self.y0, self.y1 + 1)}


class Via(BaseModel):
    x: int
    y: int
    from_layer: int
    to_layer: int
    net: str
    diameter: int = 2
    drill: int = 1


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
    netclasses: list[NetClass] = Field(default_factory=list)
    obstacles: list[Obstacle] = Field(default_factory=list)
    grid_mm: float = 0.25
    origin_x_mm: float = 0.0
    origin_y_mm: float = 0.0
    default_track_width_mm: float = 0.25
    default_via_diameter_mm: float = 0.8
    default_via_drill_mm: float = 0.4

    @property
    def layer_ids(self) -> list[int]:
        return [layer.id for layer in self.layers]

    @property
    def layer_name_by_id(self) -> dict[int, str]:
        return {layer.id: layer.name for layer in self.layers}

    @property
    def layer_id_by_name(self) -> dict[str, int]:
        return {layer.name: layer.id for layer in self.layers}

    @property
    def pads_by_id(self) -> dict[str, Pad]:
        return {pad.id: pad for pad in self.pads}

    @property
    def nets_by_id(self) -> dict[str, Net]:
        return {net.id: net for net in self.nets}

    @property
    def netclasses_by_name(self) -> dict[str, NetClass]:
        return {netclass.name: netclass for netclass in self.netclasses}

    def grid_to_mm(self, point: Point2D) -> tuple[float, float]:
        return (self.origin_x_mm + point[0] * self.grid_mm, self.origin_y_mm + point[1] * self.grid_mm)

    def mm_to_grid(self, x_mm: float, y_mm: float) -> Point2D:
        return (round((x_mm - self.origin_x_mm) / self.grid_mm), round((y_mm - self.origin_y_mm) / self.grid_mm))


class RouteStatus(str, Enum):
    routed = "routed"
    failed = "failed"


class RouteResult(BaseModel):
    status: RouteStatus
    routes: list[Route] = Field(default_factory=list)
    failed_nets: list[str] = Field(default_factory=list)
