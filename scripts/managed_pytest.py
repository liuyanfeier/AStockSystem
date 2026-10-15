"""Run synthetic tests in a fresh recorded workspace, or show retention candidates."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from astock.runtime.test_runs import finish_test_run, prepare_test_run, retention_status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selections", nargs="*", help="Repository tests paths or node IDs")
    parser.add_argument("--expected-peak-bytes", type=int)
    parser.add_argument("--status", action="store_true", help="Read-only; never deletes")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.status:
            print(json.dumps(retention_status(root), ensure_ascii=False, indent=2))
            return 0
        run = prepare_test_run(root, args.selections, args.expected_peak_bytes)
        environment = {key: value for key, value in os.environ.items()
                       if not any(word in key.upper() for word in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))
                       and key not in {"PYTEST_ADDOPTS", "ASTOCK_DATA_DIR", "ASTOCK_DB_PATH"}}
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        print(f"Managed synthetic test run: {run.directory.name}", flush=True)
        with (run.directory / "pytest.log").open("xb") as log:
            child = subprocess.Popen([sys.executable, *run.command], cwd=root, env=environment,
                                     stdout=log, stderr=subprocess.STDOUT)
            try:
                returncode = child.wait()
            except KeyboardInterrupt:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                returncode = 130
        result = finish_test_run(run, returncode)
        print(json.dumps(dict(run_id=run.directory.name, state=result["state"],
                              counts=result["counts"], workspace=result["workspace"],
                              deletion_performed=False), ensure_ascii=False))
        return returncode if returncode else (0 if result["state"] == "PASSED" else 1)
    except Exception:
        print("Managed tests: FAIL; private details suppressed; existing artifacts retained.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
