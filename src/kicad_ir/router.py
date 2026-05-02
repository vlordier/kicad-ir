import heapq
from typing import Tuple, Dict, List

Point = Tuple[int, int]

DIRS = [(1,0),(-1,0),(0,1),(0,-1)]

def heuristic(a: Point, b: Point):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def astar(start: Point, goal: Point, blocked: set[Point], width: int, height: int):
    open_set = [(0, start)]
    came_from: Dict[Point, Point] = {}
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

        for dx, dy in DIRS:
            nx, ny = current[0] + dx, current[1] + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            nxt = (nx, ny)
            if nxt in blocked:
                continue

            tentative = g[current] + 1
            if tentative < g.get(nxt, 1e9):
                came_from[nxt] = current
                g[nxt] = tentative
                f = tentative + heuristic(nxt, goal)
                heapq.heappush(open_set, (f, nxt))

    return None
