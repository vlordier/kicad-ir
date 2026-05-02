from __future__ import annotations

import argparse
from pathlib import Path

from kicad_ir.exporter import segments_to_kicad, write_routed_board
from kicad_ir.ir import Board, Layer, Net, Pad
from kicad_ir.parser import parse_kicad_pcb
from kicad_ir.router import route_board


def _flatten_routes(routes):
    tracks = []
    vias = []
    for route in routes:
        tracks.extend(route.segments)
        vias.extend(route.vias)
    return tracks, vias


def _demo_board() -> Board:
    return Board(
        width=40,
        height=40,
        layers=[Layer(id=0, name="F.Cu"), Layer(id=1, name="B.Cu")],
        pads=[
            Pad(id="p1", net="n1", x=2, y=2),
            Pad(id="p2", net="n1", x=30, y=25),
            Pad(id="p3", net="n2", x=2, y=30),
            Pad(id="p4", net="n2", x=35, y=3),
        ],
        nets=[
            Net(id="n1", pads=["p1", "p2"], kicad_net_code=1),
            Net(id="n2", pads=["p3", "p4"], kicad_net_code=2),
        ],
    )


def main() -> None:
    board = _demo_board()
    routes, failed = route_board(board)
    tracks, _vias = _flatten_routes(routes)
    net_map = {net.id: net.kicad_net_code for net in board.nets}
    print(segments_to_kicad(board, tracks, net_map))
    if failed:
        print(f"Failed nets: {', '.join(failed)}")


def route_board_file() -> None:
    parser = argparse.ArgumentParser(description="Route a KiCad board")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()

    board = parse_kicad_pcb(str(args.input))
    routes, failed = route_board(board)
    tracks, _vias = _flatten_routes(routes)
    net_map = {net.id: net.kicad_net_code for net in board.nets}
    snippet = segments_to_kicad(board, tracks, net_map)

    if args.in_place:
        backup = args.input.with_suffix(".bak.kicad_pcb")
        backup.write_text(args.input.read_text(encoding="utf-8"), encoding="utf-8")
        write_routed_board(args.input, args.input, snippet)
        print(f"updated {args.input} (backup at {backup})")
    else:
        out = args.out or args.input.with_suffix(".routed.kicad_pcb")
        write_routed_board(args.input, out, snippet)
        print(f"wrote {out}")

    print(f"routes={len(routes)} tracks={len(tracks)} failed={len(failed)}")
    if failed:
        print("failed nets:")
        for net in failed:
            print(f"  - {net}")


if __name__ == "__main__":
    route_board_file()
