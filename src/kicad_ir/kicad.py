def tracks_to_kicad(tracks, layer_map=None):
    """Convert TrackSegments to KiCad (segment ...) strings."""
    lines = []
    for t in tracks:
        layer = (layer_map or {}).get(t.layer, "F.Cu")
        lines.append(
            f"(segment (start {t.start[0]} {t.start[1]}) (end {t.end[0]} {t.end[1]}) (width {t.width}) (layer {layer}) (net 0))"
        )
    return "\n".join(lines)


def append_tracks_to_file(path, tracks_str):
    with open(path, "a") as f:
        f.write("\n")
        f.write(tracks_str)
