from sexpdata import loads
from kicad_ir.ir import Board, Pad, Net


def parse_kicad_pcb(path: str) -> Board:
    with open(path) as f:
        data = loads(f.read())

    pads = []
    nets = []

    def walk(node):
        if isinstance(node, list):
            if node and node[0] == 'pad':
                # simplified extraction
                pads.append(Pad(id=str(len(pads)), net="", x=0, y=0))
            for n in node:
                walk(n)

    walk(data)

    return Board(width=200, height=200, pads=pads, nets=nets)
