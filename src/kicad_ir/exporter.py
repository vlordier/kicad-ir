from pathlib import Path


def _fmt(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def segments_to_kicad(board, tracks, net_map, layer_map=None):
    layer_map = layer_map or board.layer_name_by_id
    lines = []
    for track in tracks:
        sx, sy = board.grid_to_mm(track.start)
        ex, ey = board.grid_to_mm(track.end)
        width = track.width * board.grid_mm
        layer = layer_map.get(track.layer, "F.Cu")
        net_code = net_map.get(track.net) or 0
        lines.append(
            f"(segment (start {_fmt(sx)} {_fmt(sy)}) (end {_fmt(ex)} {_fmt(ey)}) (width {_fmt(width)}) (layer {layer}) (net {net_code}))"
        )
    return "\n".join(lines)


def vias_to_kicad(board, vias, net_map):
    lines = []
    for via in vias:
        x, y = board.grid_to_mm((via.x, via.y))
        size = via.diameter * board.grid_mm
        drill = via.drill * board.grid_mm
        net_code = net_map.get(via.net) or 0
        lines.append(
            f"(via (at {_fmt(x)} {_fmt(y)}) (size {_fmt(size)}) (drill {_fmt(drill)}) (layers F.Cu B.Cu) (net {net_code}))"
        )
    return "\n".join(lines)


def routes_to_kicad(board, tracks, vias, net_map, layer_map=None):
    parts = [segments_to_kicad(board, tracks, net_map, layer_map)]
    via_text = vias_to_kicad(board, vias, net_map)
    if via_text:
        parts.append(via_text)
    return "\n".join(part for part in parts if part)


def insert_snippet_before_final_paren(board_text: str, snippet: str) -> str:
    stripped = board_text.rstrip()
    idx = stripped.rfind(")")
    if idx < 0:
        raise ValueError("input does not look like a KiCad S-expression board")
    return stripped[:idx] + "\n  " + snippet.replace("\n", "\n  ") + "\n" + stripped[idx:] + "\n"


def write_routed_board(input_path, output_path, snippet: str):
    input_path = Path(input_path)
    output_path = Path(output_path)
    text = input_path.read_text(encoding="utf-8")
    output_path.write_text(insert_snippet_before_final_paren(text, snippet), encoding="utf-8")
