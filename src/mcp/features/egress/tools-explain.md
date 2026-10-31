# tools.py explain

## check_egress

<!-- instruction:check_egress -->
Checks a floor plate's means of egress against the construction library's egress rules (BCI A.10-A.13 framework + IBC-typical numeric factors - always verify against the governing code; the response repeats this).

Call AFTER laying out cores/exits and BEFORE detailing: it verifies exit count, exit separation, egress width, travel distances and dead ends in one pass, and names the failing requirement so the layout can be fixed (add an exit, move a core, widen a stair) instead of guessed at.

Args:
    plate_bounds_mm: Floor plate [min_x, min_y, max_x, max_y] in mm
        (sets gross area and the diagonal used for exit separation).
    exits: One entry per exit (stair door or exterior exit door):
        {"name": str, "x_mm": float, "y_mm": float, "width_mm": float}.
        Positions are the door centers; width is the clear egress width.
    occupancy: Occupant-load key: business, mercantile, assembly_
        unconcentrated, classroom, residential, storage.
    stories: Stories served. Above 1, at least two exits are required
        and exit width demand uses the stair factor (7.6 mm/occupant)
        instead of the door factor (5.1).
    sprinklered: Sprinklered throughout (affects separation fraction,
        travel-distance and dead-end limits).
    net_area_m2: Override the occupied area; 0 uses the gross plate area.
    travel_distances_m: Measured worst-case travel distances (e.g. from
        drawn egress paths); empty skips the travel check.
    dead_end_m: Longest dead-end corridor in metres; 0 skips the check.
Returns:
    JSON: {passed, occupant_load, checks: [{check, required, provided,
    passed, basis}], warnings, source_note}.
<!-- /instruction:check_egress -->

## response-651

<!-- instruction:response-651 -->
; no {0}-specific limit in the library - verify
<!-- /instruction:response-651 -->

## response-656

<!-- instruction:response-656 -->
Travel-distance limit uses business values for '{0}' occupancy; verify the governing code.
<!-- /instruction:response-656 -->
