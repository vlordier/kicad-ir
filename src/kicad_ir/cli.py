from kicad_ir.ir import Board, Pad, Net
from kicad_ir.router import astar


def main():
    board = Board(
        width=20,
        height=20,
        pads=[
            Pad(id="p1", net="n1", x=2, y=2),
            Pad(id="p2", net="n1", x=15, y=15),
        ],
        nets=[Net(id="n1", pads=["p1", "p2"])],
    )

    start = (board.pads[0].x, board.pads[0].y)
    goal = (board.pads[1].x, board.pads[1].y)

    path = astar(start, goal, blocked=set(), width=board.width, height=board.height)

    print("Route:")
    print(path)

if __name__ == "__main__":
    main()
