from dataclasses import dataclass


@dataclass(frozen=True)
class RouterConfig:
    via_penalty: int = 20
    off_preferred_layer_penalty: int = 2
    congestion_weight: int = 4
    turn_penalty: int = 3
    guide_penalty: int = 8
    global_bin_size: int = 8
    max_passes: int = 4
