import heapq
from typing import Dict, Iterable, Optional

from kicad_ir.ir import Board, LayerPoint, Net, Route, TrackSegment, Via

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def heuristic(a: LayerPoint, b: LayerPoint) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def neighbors(p: LayerPoint, board: Board) -> Iterable[LayerPoint]:
    x, y, layer = p
    # same layer moves
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < board.width and 0 <= ny < board.height:
            yield (nx, ny, layer)

    # vias (layer changes)
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
    # base move cost
    c = 1
    # via penalty
    if a[2] != b[2]:
        c += 10
    return c


def astar_3d(start: LayerPoint, goal: LayerPoint, board: Board, net: Net, blocked: set[LayerPoint]):
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
            if nxt in blocked:
                continue

            tentative = g[current] + cost(current, nxt, net)
            if tentative < g.get(nxt, 1e9):
                came_from[nxt] = current
                g[nxt] = tentative
                f = tentative + heuristic(nxt, goal)
                heapq.heappush(open_set, (f, nxt))

    return None


def path_to_route(path: list[LayerPoint], net: Net) -> Route:
    segments: list[TrackSegment] = []
    vias: list[Via] = []

    for a, b in zip(path[:-1], path[1:]):
        if a[2] == b[2]:
            segments.append(
                TrackSegment(
                    net=net.id,
                    layer=a[2],
                    start=(a[0], a[1]),
                    end=(b[0], b[1]),
                    width=net.width,
                )
            )
        else:
            vias.append(Via(x=a[0], y=a[1], from_layer=a[2], to_layer=b[2], net=net.id))

    return Route(net=net.id, path=path, segments=segments, vias=vias)


def route_board(board: Board):
    blocked = build_blocked(board)
    routes: list[Route] = []
    failed: list[str] = []

    for net in board.nets:
        if len(net.pads) < 2:
            continue

        p0 = board.pads_by_id[net.pads[0]]
        p1 = board.pads_by_id[net.pads[1]]

        start = (p0.x, p0.y, net.preferred_layer or 0)
        goal = (p1.x, p1.y, net.preferred_layer or 0)

        path = astar_3d(start, goal, board, net, blocked)

        if not path:
            failed.append(net.id)
            continue

        route = path_to_route(path, net)
        routes.append(route)

        # reserve routed path
        blocked |= set(path)

    return routes, failed
