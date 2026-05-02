import heapq
from typing import Dict, Iterable

from kicad_ir.ir import Board, LayerPoint, Net, Route, TrackSegment, Via

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def heuristic(a: LayerPoint, b: LayerPoint) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) * 10


def inflate(points: Iterable[LayerPoint], clearance: int, board: Board) -> set[LayerPoint]:
    """Inflate occupied routing cells by Manhattan/Chebyshev grid clearance.

    This is intentionally conservative: it blocks the square around every routed
    point or obstacle cell. That is safer than under-blocking for a first router.
    """
    out: set[LayerPoint] = set()
    for x, y, layer in points:
        for dx in range(-clearance, clearance + 1):
            for dy in range(-clearance, clearance + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < board.width and 0 <= ny < board.height:
                    out.add((nx, ny, layer))
    return out


def neighbors(p: LayerPoint, board: Board) -> Iterable[LayerPoint]:
    x, y, layer = p
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < board.width and 0 <= ny < board.height:
            yield (nx, ny, layer)

    for l in board.layer_ids:
        if l != layer:
            yield (x, y, l)


def build_blocked(board: Board) -> set[LayerPoint]:
    blocked: set[LayerPoint] = set()

    for obs in board.obstacles:
        blocked |= obs.occupied_cells(board.layer_ids)

    for pad in board.pads:
        blocked |= pad.occupied_cells(board.layer_ids)

    return blocked


def cost(a: LayerPoint, b: LayerPoint, net: Net) -> int:
    c = 1
    if a[2] != b[2]:
        c += 20
    if net.preferred_layer is not None and b[2] != net.preferred_layer:
        c += 2
    return c


def astar_3d(
    start: LayerPoint,
    goal: LayerPoint,
    board: Board,
    net: Net,
    blocked: set[LayerPoint],
    allowed: set[LayerPoint] | None = None,
) -> list[LayerPoint] | None:
    open_set = [(0, start)]
    came_from: Dict[LayerPoint, LayerPoint] = {}
    g = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        for nxt in neighbors(current, board):
            if nxt in blocked and (allowed is None or nxt not in allowed):
                continue

            tentative = g[current] + cost(current, nxt, net)
            if tentative < g.get(nxt, 1_000_000_000):
                came_from[nxt] = current
                g[nxt] = tentative
                f = tentative + heuristic(nxt, goal)
                heapq.heappush(open_set, (f, nxt))

    return None


def path_to_route(path: list[LayerPoint], net: Net) -> Route:
    segments: list[TrackSegment] = []
    vias: list[Via] = []

    # Coalesce consecutive same-layer collinear unit moves into longer segments.
    current_start: LayerPoint | None = None
    previous: LayerPoint | None = None
    previous_dir: tuple[int, int] | None = None

    def flush_segment() -> None:
        nonlocal current_start, previous, previous_dir
        if current_start is not None and previous is not None and current_start != previous:
            segments.append(
                TrackSegment(
                    net=net.id,
                    layer=current_start[2],
                    start=(current_start[0], current_start[1]),
                    end=(previous[0], previous[1]),
                    width=net.width,
                )
            )
        current_start = None
        previous = None
        previous_dir = None

    for a, b in zip(path[:-1], path[1:]):
        if a[2] != b[2]:
            flush_segment()
            vias.append(
                Via(
                    x=a[0],
                    y=a[1],
                    from_layer=a[2],
                    to_layer=b[2],
                    net=net.id,
                )
            )
            continue

        direction = (b[0] - a[0], b[1] - a[1])
        if current_start is None:
            current_start = a
            previous = b
            previous_dir = direction
        elif previous_dir == direction and previous == a:
            previous = b
        else:
            flush_segment()
            current_start = a
            previous = b
            previous_dir = direction

    flush_segment()
    return Route(net=net.id, path=path, segments=segments, vias=vias)


def _pad_layer_point(board: Board, pad_id: str, net: Net) -> LayerPoint:
    pad = board.pads_by_id[pad_id]
    layer = pad.layer if pad.layer is not None else (net.preferred_layer or board.layer_ids[0])
    return (pad.x, pad.y, layer)


def route_board(board: Board) -> tuple[list[Route], list[str]]:
    base_blocked = build_blocked(board)
    blocked = set(base_blocked)
    routes: list[Route] = []
    failed: list[str] = []

    for net in board.nets:
        if len(net.pads) < 2:
            continue

        # Allow this net to start/end on its own pads despite pad occupancy.
        own_pad_cells: set[LayerPoint] = set()
        for pad_id in net.pads:
            own_pad_cells |= board.pads_by_id[pad_id].occupied_cells(board.layer_ids)

        full_path: list[LayerPoint] = []
        routed_ok = True

        # Steiner-lite: nearest-neighbor chain from first pad.
        remaining = list(net.pads[1:])
        current = net.pads[0]
        while remaining:
            start = _pad_layer_point(board, current, net)
            next_pad = min(
                remaining,
                key=lambda pid: heuristic(start, _pad_layer_point(board, pid, net)),
            )
            goal = _pad_layer_point(board, next_pad, net)

            path = astar_3d(start, goal, board, net, blocked, allowed=own_pad_cells)
            if not path:
                routed_ok = False
                break

            full_path.extend(path if not full_path else path[1:])
            blocked |= inflate(path, net.clearance, board)
            current = next_pad
            remaining.remove(next_pad)

        if not routed_ok:
            failed.append(net.id)
            continue

        routes.append(path_to_route(full_path, net))

    return routes, failed
