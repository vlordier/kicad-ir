def tracks_to_kicad(tracks, vias, net_map, layer_map=None):
    lines = []

    for t in tracks:
        net_code = net_map.get(t.net, 0)
        layer = (layer_map or {}).get(t.layer, "F.Cu")
        lines.append(
            f"(segment (start {t.start[0]} {t.start[1]}) (end {t.end[0]} {t.end[1]}) (width {t.width}) (layer {layer}) (net {net_code}))"
        )

    for v in vias:
        net_code = net_map.get(v.net, 0)
        lines.append(
            f"(via (at {v.x} {v.y}) (size {v.diameter}) (drill {v.drill}) (layers F.Cu B.Cu) (net {net_code}))"
        )

    return "\n".join(lines)


def append_tracks_to_file(path, tracks_str):
    with open(path, "a") as f:
        f.write("\n")
        f.write(tracks_str)
