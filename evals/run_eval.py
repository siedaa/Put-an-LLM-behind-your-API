import json
import sys
from pathlib import Path

import requests

CASES_PATH = Path(__file__).resolve().parent / "cases.json"
DEFAULT_PORT = 8000


def run_eval(port: int = DEFAULT_PORT):
    endpoint = f"http://localhost:{port}/triage"
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    total = len(cases)
    passed = 0
    failed_ids = []

    for case in cases:
        case_id = case["id"]
        expected = case["expected_category"]

        try:
            resp = requests.post(endpoint, json=case["input"], timeout=60)
            resp.raise_for_status()
            actual = resp.json()["category"]
        except requests.RequestException as e:
            actual = f"ERROR ({e})"
        except (KeyError, ValueError) as e:
            actual = f"PARSE_ERROR ({e})"

        ok = actual == expected
        if ok:
            passed += 1
        else:
            failed_ids.append(case_id)

        status = "PASS" if ok else "FAIL"
        print(f"{case_id}: expected={expected} actual={actual} {status}")

    print()
    pct = round(passed / total * 100) if total else 0
    print(f"{passed} / {total} correct on category ({pct}%)")

    if failed_ids:
        print(f"Failed: {', '.join(failed_ids)}")
    else:
        print("Failed: none")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    try:
        run_eval(port)
    except FileNotFoundError:
        print(f"Error: cases file not found at {CASES_PATH}", file=sys.stderr)
        sys.exit(1)
    except requests.ConnectionError:
        print(f"Error: could not connect to http://localhost:{port}/triage", file=sys.stderr)
        sys.exit(1)
