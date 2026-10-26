# native_structure.py explain

## response-897

<!-- instruction:response-897 -->
Linear-elastic 3D frame analysis (Almond native solver); second-order (P-Delta) where the stability check calls for it (see Stability).
<!-- /instruction:response-897 -->

## response-898

<!-- instruction:response-898 -->
Joints as stated under Connections; supports as described in support_mode.
<!-- /instruction:response-898 -->

## response-899

<!-- instruction:response-899 -->
Imposed load shared equally by the free nodes, acting downward; self weight included when enabled.
<!-- /instruction:response-899 -->

## response-900

<!-- instruction:response-900 -->
Member checks per member (EN 1993-1-1): section class from Table 5.2 for the actual stresses (Class 4 flagged as not covered); cross-section 6.2.1(7) with elastic moduli (plastic only for Class 1/2 when plastic design is requested); flexural buckling about both axes (6.3.1, curves from Table 6.2, L_cr = the member between its joints, 5.2.2(7)b); compression + bending by 6.3.3 (6.61)/(6.62) with Annex B factors and Table B.3 Cm. Not checked: lateral-torsional buckling, shear (6.2.6), torsion, local bow imperfections.
<!-- /instruction:response-900 -->

## response-901

<!-- instruction:response-901 -->
Preliminary design check, not an engineer's sign-off.
<!-- /instruction:response-901 -->

## response-912

<!-- instruction:response-912 -->
Design code '{0}': {1} value(s) not yet verified against the published document ({2}). Treat the results as provisional.
<!-- /instruction:response-912 -->

## response-920

<!-- instruction:response-920 -->
Increase member depth or use a stiffer cross-section
<!-- /instruction:response-920 -->

## response-921

<!-- instruction:response-921 -->
Add intermediate supports to reduce effective span
<!-- /instruction:response-921 -->

## response-923

<!-- instruction:response-923 -->
Use thicker walls: Class 4 starts at d/t = 90 x 235/fy for CHS (59.6 for S355)
<!-- /instruction:response-923 -->

## response-925

<!-- instruction:response-925 -->
Use a larger cross-section or higher-grade material
<!-- /instruction:response-925 -->

## response-927

<!-- instruction:response-927 -->
Have the members designed to {0} (an engineer); use the forces in the results as the starting point.
<!-- /instruction:response-927 -->

## response-931

<!-- instruction:response-931 -->
Brace the frame, fix the column bases, or use stiffer columns: it buckles before reaching the design loads.
<!-- /instruction:response-931 -->

## response-932

<!-- instruction:response-932 -->
Add supports or bracing so every part of the structure is restrained.
<!-- /instruction:response-932 -->

## response-942

<!-- instruction:response-942 -->
With simple (pinned) connections the frame needs bracing, fixed column bases or rigid joints for stability.
<!-- /instruction:response-942 -->
