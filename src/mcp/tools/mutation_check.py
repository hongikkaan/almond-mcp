"""Mutation check of the structural test suite: does it catch real engineering mistakes?

Plants one known error at a time (a wrong factor, a dropped term, a wrong table column), runs the
structural tests, and reports CAUGHT (a test failed) or MISSED (every test passed). Every file is
restored from its original bytes after each run, also on failure. Run from the repo root:

    uv run python src/mcp/tools/mutation_check.py

Add a mutant whenever a new structural feature lands; a MISSED line means the tests need a case."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TESTS = ["src/mcp/tests/test_frame_solver.py", "src/mcp/tests/test_native_structure.py", "src/mcp/tests/test_load_combinations.py",
         "src/mcp/tests/test_end_releases.py", "src/mcp/tests/test_stability.py", "src/mcp/tests/test_floor_loads.py",
         "src/mcp/tests/test_asset_loads.py", "src/mcp/tests/test_design_codes.py", "src/mcp/tests/test_structure_study.py",
         "src/mcp/tests/test_validate_engines.py", "src/mcp/tests/test_visualize_native.py", "src/mcp/tests/test_hand_calculations.py", "src/mcp/tests/test_ec3.py"]

MUTANTS = [
    ("load factor gamma_G 1.35 -> 1.30", "src/mcp/almond_mcp/code_profiles/eurocode.json", '"gamma_G": {"value": 1.35', '"gamma_G": {"value": 1.30'),
    ("6.10b reduction xi 0.85 -> 0.925", "src/mcp/almond_mcp/code_profiles/eurocode.json", '"xi": {"value": 0.85', '"xi": {"value": 0.925'),
    ("psi_0 0.7 -> 0.5", "src/mcp/almond_mcp/code_profiles/eurocode.json", '"psi_0": {"value": 0.7', '"psi_0": {"value": 0.5'),
    ("buckling curve a imperfection 0.21 -> 0.34", "src/mcp/almond_mcp/features/structure/frame_solver.py", '"a": 0.21', '"a": 0.34'),
    ("gamma_M1 ignored in member buckling", "src/mcp/almond_mcp/features/structure/frame_solver.py",
     "buck = ncomp / (chi * s.A * fy / gamma_m1)", "buck = ncomp / (chi * s.A * fy)"),
    ("geometric stiffness 36 -> 30 (wrong K_G)", "src/mcp/almond_mcp/features/structure/frame_solver.py",
     "v = c * np.array([[36, 3 * L, -36, 3 * L]", "v = c * np.array([[30, 3 * L, -30, 3 * L]"),
    ("sway imperfection phi_0 1/200 -> 1/300", "src/mcp/almond_mcp/features/structure/native_structure.py", "PHI_0 = 1 / 200", "PHI_0 = 1 / 300"),
    ("alpha_cr first-order threshold 10 -> 5", "src/mcp/almond_mcp/features/structure/native_structure.py",
     "ALPHA_CR_FIRST_ORDER = 10.0", "ALPHA_CR_FIRST_ORDER = 5.0"),
    ("imperfection only in +x (no -x/+y/-y)", "src/mcp/almond_mcp/features/structure/native_structure.py",
     'for label, axis, sign in (("+x", 0, 1), ("-x", 0, -1), ("+y", 1, 1), ("-y", 1, -1)):',
     'for label, axis, sign in (("+x", 0, 1),):'),
    ("two-way / one-way switch at 2:1 -> 3:1", "src/mcp/almond_mcp/features/structure/floor_loads.py", "if l / s > 2.0:", "if l / s > 3.0:"),
    ("two-way 45-degree peak q*s/2 -> q*s/3", "src/mcp/almond_mcp/features/structure/floor_loads.py",
     "pts = [(0.0, 0.0), (r, q * s / 2), (1 - r, q * s / 2), (1.0, 0.0)]",
     "pts = [(0.0, 0.0), (r, q * s / 3), (1 - r, q * s / 3), (1.0, 0.0)]"),
    ("results table: shear only at element start", "src/mcp/almond_mcp/features/structure/native_structure.py",
     "V = max(max(math.hypot(ef[1], ef[2]), math.hypot(ef[7], ef[8]))", "V = max(max(math.hypot(ef[1], ef[2]), 0.0)"),
    ("results table: supports lose ULS reactions", "src/mcp/almond_mcp/features/structure/native_structure.py",
     '"uls": {name: forces(r_, n) for name, _, r_ in ulss}}', '"uls": {}}'),
    ("results table: deflection = absolute movement", "src/mcp/almond_mcp/features/structure/native_structure.py",
     "sag = float(np.max(np.linalg.norm(disp - (np.outer(1 - t, dA) + np.outer(t, dB)), axis=1)))",
     "sag = float(np.max(np.linalg.norm(disp, axis=1)))"),
    ("Annex B class-3 kyy 0.6 -> 0.3", "src/mcp/almond_mcp/features/structure/ec3.py",
     "kyy = cm_y * min(1 + 0.6 * lam_y * n_y, 1 + 0.6 * n_y)", "kyy = cm_y * min(1 + 0.3 * lam_y * n_y, 1 + 0.3 * n_y)"),
    ("Table B.3 Cm floor 0.4 -> 0.2", "src/mcp/almond_mcp/features/structure/ec3.py", "return max(0.4, 0.6 + 0.4 * psi)", "return max(0.2, 0.6 + 0.4 * psi)"),
    ("cold-formed tubes on the hot-finished curve", "src/mcp/almond_mcp/features/structure/ec3.py",
     'if fabrication == "hot_finished":', "if True:"),
    ("CHS class-3 limit not scaled by fy", "src/mcp/almond_mcp/features/structure/ec3.py",
     "3 if r <= 90 * eps ** 2 else 4", "3 if r <= 90 else 4"),
    ("buckling length = analysis element, not member", "src/mcp/almond_mcp/features/structure/ec3.py",
     'out.setdefault(e.group if getattr(e, "group", None) is not None else i, []).append(i)',
     "out.setdefault(i, []).append(i)"),
    ("deflection limit ratio ignored by the overlay", "src/mcp/almond_mcp/features/structure/structure_study.py",
     '"deflection_limit_ratio": limit_ratio}', '"deflection_limit_ratio": 250.0}'),
]


def run_tests():
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *TESTS],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]


def main():
    only = [a.lower() for a in sys.argv[1:]]          # optional: run only mutants whose name contains one of these
    code, tail = run_tests()
    print(f"baseline: exit {code} | {tail}", flush=True)
    if code != 0:
        sys.exit("baseline must pass")
    survived = []
    for name, rel, old, new in MUTANTS:
        if only and not any(o in name.lower() for o in only):
            continue
        path = ROOT / rel
        original = path.read_bytes()
        text = original.decode("utf-8")
        if text.count(old) != 1:
            print(f"SKIP {name}: target found {text.count(old)} times", flush=True)
            continue
        try:
            path.write_bytes(text.replace(old, new).encode("utf-8"))
            code, tail = run_tests()
        finally:
            path.write_bytes(original)
        caught = code != 0
        if not caught:
            survived.append(name)
        print(f"{'CAUGHT  ' if caught else 'MISSED  '} {name} | {tail}", flush=True)
    ran = [m for m in MUTANTS if not only or any(o in m[0].lower() for o in only)]
    print(f"\n{len(ran) - len(survived)}/{len(ran)} planted errors caught")


if __name__ == "__main__":
    main()
