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
