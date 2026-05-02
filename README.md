# kicad-ir

Minimal **PCB routing IR + A\* router** to augment KiCad.

## What this repo gives you

- Minimal **lossy routing IR** (pads, nets, obstacles)
- Grid builder
- A\* single-net router
- Very simple KiCad track injector (S-expression append)

## Quick demo

```bash
pip install -e .
kicad-ir-route-demo
```

## Architecture

```
KiCad board
 → IR (pads, nets)
 → grid
 → A* routing
 → tracks
 → back to KiCad
```

## Next steps

- multi-net routing
- rip-up / reroute
- congestion cost
- DSN export
- ML cost maps
