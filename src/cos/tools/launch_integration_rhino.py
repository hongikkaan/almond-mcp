"""Launch a detached Rhino for acceptance and report the exact child identity."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detached_process import launch_detached
from winpipe import process_identity_from_handle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rhino", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    process = launch_detached(
        [str(args.rhino), "/nosplash", str(args.model)],
        cwd=str(args.model.parent),
        env=dict(os.environ),
        startup_script="_almondconnect",
    )
    try:
        try:
            identity = process_identity_from_handle(process.pid, process.handle)
        except OSError as exc:
            raise RuntimeError(f"Started Rhino PID {process.pid}, but could not verify its creation time.") from exc
        print(json.dumps(identity), flush=True)
    finally:
        process.close()


if __name__ == "__main__":
    main()
