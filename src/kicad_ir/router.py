import heapq
from collections import Counter
from typing import Dict, Iterable

from kicad_ir.config import RouterConfig
from kicad_ir.ir import Board, LayerPoint, Net, Route, TrackSegment, Via

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
State = tuple[LayerPoint, tuple[int, int] | None]


def heuristic(a: LayerPoint, b: LayerPoint) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) * 10


def inflate(points: Iterable[LayerPoint], clearance: int, board: Board) -> set[LayerPoint]:
    out: set[LayerPoint] = set()
    for x, y, layer in points:
        for dx in range(-clearance, clearance + 1):
            for dy in range(-clearance, clearance + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < board.width and 0 <= ny < board.height:
                    out.add((nx, ny, layer))
    return out


def route_clearance_radius(net: Net) -> int:
    return max(0, net.clearance) + max(0, net.width // 2)


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


def build_global_guide(board: Board, config: RouterConfig) -> Counter[tuple[int, int, int]]:
    guide: Counter[tuple[int, int, int]] = Counter()
    bin_size = max(1, config.global_bin_size)
    for cell in build_blocked(board):
        x, y, layer = cell
        guide[(x // bin_size, y // bin_size, layer)] += 1
    return guide


def move_cost(a: LayerPoint, b: LayerPoint, net: Net, congestion: Counter[LayerPoint], guide: Counter[tuple[int, int, int]], prev_dir: tuple[int, int] | None, config: RouterConfig) -> int:
    c = 1
    direction = (b[0] - a[0], b[1] - a[1]) if a[2] == b[2] else None
    if a[2] != b[2]:
        c += config.via_penalty
    elif prev_dir is not None and direction is not None and direction != prev_dir:
        c += config.turn_penalty
    if net.preferred_layer is not None and b[2] != net.preferred_layer:
        c += config.off_preferred_layer_penalty
    c += config.congestion_weight * congestion[b]
    bin_size = max(1, config.global_bin_size)
    c += config.guide_penalty * guide[(b[0] // bin_size, b[1] // bin_size, b[2])]
    return c


def astar_3d(start: LayerPoint, goal: LayerPoint, board: Board, net: Net, blocked: set[LayerPoint], allowed: set[LayerPoint] | None = None, congestion: Counter[LayerPoint] | None = None, config: RouterConfig | None = None, guide: Counter[tuple[int, int, int]] | None = None) -> list[LayerPoint] | None:
    congestion = congestion or Counter()
    config = config or RouterConfig()
    guide = guide or Counter()
    start_state: State = (start, None)
    open_set = [(0, start_state)]
    came_from: Dict[State, State] = {}
    g = {start_state: 0}
    while open_set:
        _, current_state = heapq.heappop(open_set)
        current, prev_dir = current_state
        if current == goal:
            path = []
            while current_state in came_from:
                path.append(current_state[0])
                current_state = came_from[current_state]
            path.append(start)
            return path[::-1]
        for nxt in neighbors(current, board):
            if nxt in blocked and (allowed is None or nxt not in allowed):
                continue
            direction = (nxt[0] - current[0], nxt[1] - current[1]) if nxt[2] == current[2] else prev_dir
            nxt_state: State = (nxt, direction)
            tentative = g[current_state] + move_cost(current, nxt, net, congestion, guide, prev_dir, config)
            if tentative < g.get(nxt_state, 1_000_000_000):
                came_from[nxt_state] = current_state
                g[nxt_state] = tentative
                heapq.heappush(open_set, (tentative + heuristic(nxt, goal), nxt_state))
    return None


def path_to_route(path: list[LayerPoint], net: Net) -> Route:
    segments: list[TrackSegment] = []
    vias: list[Via] = []
    current_start: LayerPoint | None = None
    previous: LayerPoint | None = None
    previous_dir: tuple[int, int] | None = None
    def flush_segment() -> None:
        nonlocal current_start, previous, previous_dir
        if current_start is not None and previous is not None and current_start != previous:
            segments.append(TrackSegment(net=net.id, layer=current_start[2], start=(current_start[0], current_start[1]), end=(previous[0], previous[1]), width=net.width))
        current_start = None
        previous = None
        previous_dir = None
    for a, b in zip(path[:-1], path[1:]):
        if a[2] != b[2]:
            flush_segment()
            vias.append(Via(x=a[0], y=a[1], from_layer=a[2], to_layer=b[2], net=net.id, diameter=max(2, net.width + 1), drill=max(1, net.width // 2)))
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


def _net_difficulty(board: Board, net: Net) -> int:
    pts = [board.pads_by_id[p] for p in net.pads if p in board.pads_by_id]
    if len(pts) < 2:
        return 0
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    return len(pts) * 1000 + (max(xs) - min(xs)) + (max(ys) - min(ys)) + net.width * 100


def _route_single_net(board: Board, net: Net, blocked: set[LayerPoint], congestion: Counter[LayerPoint], config: RouterConfig, guide: Counter[tuple[int, int, int]]) -> Route | None:
    own_pad_cells: set[LayerPoint] = set()
    for pad_id in net.pads:
        own_pad_cells |= board.pads_by_id[pad_id].occupied_cells(board.layer_ids)
    full_path: list[LayerPoint] = []
    remaining = list(net.pads[1:])
    current = net.pads[0]
    while remaining:
        start = _pad_layer_point(board, current, net)
        next_pad = min(remaining, key=lambda pid: heuristic(start, _pad_layer_point(board, pid, net)))
        goal = _pad_layer_point(board, next_pad, net)
        path = astar_3d(start, goal, board, net, blocked, own_pad_cells, congestion, config, guide)
        if not path:
            return None
        full_path.extend(path if not full_path else path[1:])
        current = next_pad
        remaining.remove(next_pad)
    return path_to_route(full_path, net)


def _reserve(route: Route, board: Board, net: Net) -> set[LayerPoint]:
    return inflate(route.path, route_clearance_radius(net), board)


def _route_pass(board: Board, order: list[Net], congestion: Counter[LayerPoint], config: RouterConfig) -> tuple[list[Route], list[str], Counter[LayerPoint]]:
    static_blocked = build_blocked(board)
    guide = build_global_guide(board, config)
    route_by_net: dict[str, Route] = {}
    owner: dict[LayerPoint, str] = {}
    failed: list[str] = []
    for net in order:
        if len(net.pads) < 2:
            continue
        blocked = static_blocked | set(owner)
        route = _route_single_net(board, net, blocked, congestion, config, guide)
        if route is None:
            blockers = Counter(owner[cell] for cell in congestion if owner.get(cell))
            rip = [n for n, _ in blockers.most_common(2) if n != net.id]
            for rip_net in rip:
                old = route_by_net.pop(rip_net, None)
                if old:
                    rip_cells = _reserve(old, board, board.nets_by_id[rip_net])
                    for cell in rip_cells:
                        owner.pop(cell, None)
            blocked = static_blocked | set(owner)
            route = _route_single_net(board, net, blocked, congestion, config, guide)
            if route is None:
                failed.append(net.id)
                continue
        route_by_net[net.id] = route
        for cell in _reserve(route, board, net):
            owner[cell] = net.id
    new_congestion: Counter[LayerPoint] = Counter(owner)
    return list(route_by_net.values()), failed, new_congestion


def route_board(board: Board, config: RouterConfig | None = None) -> tuple[list[Route], list[str]]:
    config = config or RouterConfig()
    base_order = sorted(board.nets, key=lambda n: _net_difficulty(board, n), reverse=True)
    congestion: Counter[LayerPoint] = Counter()
    best_routes: list[Route] = []
    best_failed = [n.id for n in base_order if len(n.pads) >= 2]
    for _ in range(config.max_passes):
        failed_set = set(best_failed)
        order = sorted(base_order, key=lambda n: (n.id not in failed_set, -_net_difficulty(board, n)))
        routes, failed, congestion = _route_pass(board, order, congestion, config)
        if len(failed) < len(best_failed):
            best_routes, best_failed = routes, failed
        if not failed:
            return routes, failed
    return best_routes, best_failed
