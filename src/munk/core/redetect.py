from __future__ import annotations


def redetect_icon_conf(
    base_conf: float,
    redetect_index: int,
    min_conf: float = 0.01,
    decay: float = 0.5,
) -> float:
    base_value = max(0.0, float(base_conf))
    min_value = max(0.0, float(min_conf))
    if redetect_index <= 0:
        return round(max(base_value, min_value), 4)
    scaled = base_value * (float(decay) ** redetect_index)
    return round(max(min_value, scaled), 4)
