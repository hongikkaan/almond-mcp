"""Domain validation before the existing preliminary egress calculation."""
import math
from numbers import Real


def validate_inputs(bounds, exits, stories, net_area, distances, dead_end):
    def number(value, label, minimum=None):
        try:
            finite = math.isfinite(value)
        except (TypeError, ValueError, OverflowError):
            finite = False
        if isinstance(value, bool) or not isinstance(value, Real) or not finite:
            raise ValueError(f"{label} must be a finite number.")
        if minimum is not None and value < minimum:
            raise ValueError(f"{label} must be at least {minimum}.")
        return value

    if len(bounds) != 4:
        raise ValueError("plate_bounds_mm must be [min_x, min_y, max_x, max_y].")
    for i, value in enumerate(bounds):
        number(value, f"plate_bounds_mm[{i}]")
    if bounds[0] == bounds[2] or bounds[1] == bounds[3]:
        raise ValueError("plate_bounds_mm must describe a nonzero area.")
    width, depth = abs(bounds[2]-bounds[0])/1000, abs(bounds[3]-bounds[1])/1000
    number(width * depth, "calculated gross area")
    number(math.hypot(width, depth), "calculated diagonal")
    number(stories, "stories", 1)
    if int(stories) != stories:
        raise ValueError("stories must be an integer.")
    number(net_area, "net_area_m2", 0)
    number(dead_end, "dead_end_m", 0)
    for i, value in enumerate(distances):
        number(value, f"travel_distances_m[{i}]", 0)
    if not exits:
        raise ValueError("exits must not be empty.")
    seen = set()
    for i, exit_ in enumerate(exits):
        if not isinstance(exit_, dict):
            raise ValueError(f"exits[{i}] must contain x_mm, y_mm and width_mm.")
        for key in ("x_mm", "y_mm", "width_mm"):
            if key not in exit_:
                raise ValueError(f"exits[{i}].{key} is required.")
            number(exit_[key], f"exits[{i}].{key}", 0 if key == "width_mm" else None)
        if "name" in exit_ and not isinstance(exit_["name"], str):
            raise ValueError(f"exits[{i}].name must be a string.")
        location = (exit_["x_mm"], exit_["y_mm"])
        if location in seen:
            raise ValueError(f"exits[{i}] duplicates an exit center; supply each physical exit once.")
        seen.add(location)
    number(sum(exit_["width_mm"] for exit_ in exits), "total exit width")
    for axis in ("x_mm", "y_mm"):
        values = [exit_[axis] for exit_ in exits]
        number(max(values) - min(values), "exit coordinate range")
