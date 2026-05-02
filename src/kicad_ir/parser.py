from sexpdata import loads, Symbol
from kicad_ir.ir import Board, Pad, Net


def parse_kicad_pcb(path: str) -> Board:
    with open(path) as f:
        data = loads(f.read())

    nets = {}
    pads = []

    def is_sym(x, name):
        return isinstance(x, Symbol) and x.value() == name

    def walk(node, footprint_pos=(0.0, 0.0)):
        if not isinstance(node, list):
            return

        if node and is_sym(node[0], "net"):
            code = int(node[1])
            name = node[2].value() if isinstance(node[2], Symbol) else str(node[2])
            nets[name] = Net(id=name, pads=[], kicad_net_code=code)

        if node and is_sym(node[0], "footprint"):
            pos = footprint_pos
            for n in node:
                if isinstance(n, list) and n and is_sym(n[0], "at"):
                    pos = (float(n[1]), float(n[2]))
            for n in node:
                walk(n, pos)
            return

        if node and is_sym(node[0], "pad"):
            local_pos = (0.0, 0.0)
            net_name = None

            for n in node:
                if isinstance(n, list) and n:
                    if is_sym(n[0], "at"):
                        local_pos = (float(n[1]), float(n[2]))
                    if is_sym(n[0], "net"):
                        net_name = n[2].value() if isinstance(n[2], Symbol) else str(n[2])

            gx = int((footprint_pos[0] + local_pos[0]) / 0.25)
            gy = int((footprint_pos[1] + local_pos[1]) / 0.25)

            pad_id = f"pad_{len(pads)}"
            pads.append(Pad(id=pad_id, net=net_name or "", x=gx, y=gy))

            if net_name and net_name in nets:
                nets[net_name].pads.append(pad_id)

        for n in node:
            walk(n, footprint_pos)

    walk(data)

    return Board(width=400, height=400, pads=pads, nets=list(nets.values()))
