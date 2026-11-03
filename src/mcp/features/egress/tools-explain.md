# tools.py explain

## check_egress

<!-- instruction:check_egress -->
Screen a supplied floor layout against the local construction library's egress rules without reading or changing Rhino geometry.

When to use: Compare exit count, separation, widths and supplied path measurements after laying out cores/exits and before detailing.
Before calling: Provide a four-value plate bounding rectangle and nonempty exits with door-center coordinates and clear widths in mm. Confirm occupancy, stories and sprinkler assumptions; net_area_m2 overrides occupied area only, while plate bounds still set the separation diagonal.
Inputs from earlier results: No discovery call is required. Convert verified floor bounds to [min_x,min_y,max_x,max_y] in mm and measured exit centers/clear widths to exits[].x_mm/y_mm/width_mm. Supply measured path lengths in metres as travel_distances_m and the longest dead end as dead_end_m; geometry IDs alone are not inputs.
Interpretation: occupant_load is the ceiling of area divided by the occupancy factor. checks[].required/provided use units named in check (m or mm), passed is each comparison and basis explains it. Overall passed covers only checks actually performed. Multi-story layouts require at least two exits and use stair width factors; separation uses the most remote exit pair.
Limits: Empty travel_distances_m and dead_end_m=0 skip those checks; routes and obstacles are not inferred. Gross area is the bounding rectangle, not a measured irregular plate. Travel limits use business values even for other occupancies and warn; dead-end rules are also simplified. BCI A.10-A.13/IBC-typical factors are screening guidance, not governing-code certification; verify local requirements and source_note.

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
