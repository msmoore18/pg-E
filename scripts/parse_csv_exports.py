#!/usr/bin/env python3
"""
Parse PG&E "Green Button" manual usage export CSVs (the ones you download
from Energy Usage Details -> Green Button icon -> Download my Data) into
the same JSON shape the dashboard reads.

Usage:
    python scripts/parse_csv_exports.py

Reads every *.csv in data/raw/, writes:
    data/usage_latest.json   - just this run's files
    data/usage_history.json  - merged, deduped rolling history

Friendly meter names come from data/meter_labels.json, a simple hand-edited
mapping of PG&E's "Service N" label (+ address) to what you actually call
that meter. Anything not in the mapping falls back to "Service N (address)"
so it still shows up, just unlabeled, until you fill it in.
"""

import csv
import io
import json
import os
import re
import datetime as dt
from pathlib import Path

RAW_DIR = Path("data/raw")
# Processed output lives under docs/ so GitHub Pages can serve it directly.
# Raw CSVs (which contain your account holder name, account number, and
# service addresses) stay in data/raw/ and are NOT published — see README
# for why this repo should be private.
LATEST_PATH = Path("docs/data/usage_latest.json")
HISTORY_PATH = Path("docs/data/usage_history.json")
LABELS_PATH = Path("data/meter_labels.json")


def load_labels() -> dict:
    if LABELS_PATH.exists():
        with open(LABELS_PATH) as f:
            return json.load(f)
    return {}


def parse_header(lines: list[str]) -> dict:
    """Pull Name / Address / Account Number / Service out of the metadata
    block at the top of the export before the TYPE,DATE,... header row."""
    meta = {}
    for line in lines:
        if line.startswith("TYPE,DATE"):
            break
        if "," not in line:
            continue
        key, _, rest = line.partition(",")
        meta[key.strip()] = rest.strip().strip('"')
    return meta


def parse_csv_file(path: Path) -> tuple[str, list[dict]]:
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    lines = text.splitlines(keepends=True)
    meta = parse_header(lines)

    service = meta.get("Service", path.stem)
    # Deliberately NOT including the property address in the default key —
    # this becomes the dashboard's display name, and the address is PII you
    # may not want published. Rename via data/meter_labels.json instead.
    key = service

    # Re-read as CSV starting from the TYPE,DATE... header row
    header_idx = next(i for i, l in enumerate(lines) if l.startswith("TYPE,DATE"))
    reader = csv.DictReader(io.StringIO("".join(lines[header_idx:])))

    readings = []
    for row in reader:
        date = row.get("DATE", "").strip()
        start = row.get("START TIME", "").strip()
        end = row.get("END TIME", "").strip()
        usage = row.get("USAGE (kWh)", "").strip()
        cost = row.get("COST", "").strip().lstrip("$")
        if not date or not start or usage == "":
            continue
        ts = dt.datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M")

        # duration: infer from start/end (handles both hourly and 15-min exports)
        end_h, end_m = (int(x) for x in end.split(":"))
        start_h, start_m = (int(x) for x in start.split(":"))
        duration_min = (end_h * 60 + end_m) - (start_h * 60 + start_m) + 1

        readings.append({
            "timestamp": ts.isoformat(),
            "kwh": float(usage),
            "cost": float(cost) if cost else None,
            "duration_min": duration_min,
        })

    return key, readings, meta


def main():
    labels = load_labels()
    if not RAW_DIR.exists() or not any(RAW_DIR.glob("*.csv")):
        print(f"No CSVs found in {RAW_DIR}/ — drop PG&E Green Button exports "
              f"there and re-run.")
        return

    latest = {"generated_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
              "meters": {}}

    for path in sorted(RAW_DIR.glob("*.csv")):
        raw_key, readings, meta = parse_csv_file(path)
        service = meta.get("Service", raw_key)
        friendly = labels.get(service)
        display_name = friendly or raw_key
        latest["meters"].setdefault(display_name, [])
        latest["meters"][display_name].extend(readings)
        print(f"Parsed {path.name}: {len(readings)} readings -> '{display_name}'")

    for name in latest["meters"]:
        latest["meters"][name].sort(key=lambda r: r["timestamp"])

    LATEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LATEST_PATH, "w") as f:
        json.dump(latest, f, indent=2)

    # merge into rolling history, deduped by timestamp per meter
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH) as f:
            history = json.load(f)
    else:
        history = {"meters": {}}

    for name, readings in latest["meters"].items():
        existing = {r["timestamp"]: r for r in history["meters"].get(name, [])}
        for r in readings:
            existing[r["timestamp"]] = r
        history["meters"][name] = sorted(existing.values(), key=lambda r: r["timestamp"])

    history["last_updated"] = latest["generated_at"]
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)

    total = sum(len(v) for v in latest["meters"].values())
    print(f"\nWrote {total} readings across {len(latest['meters'])} meters to "
          f"{LATEST_PATH} and merged into {HISTORY_PATH}.")

    unlabeled = [m for m in latest["meters"] if m not in labels.values()
                 and not any(m == labels.get(s) for s in labels)]
    services_seen = set()
    for path in sorted(RAW_DIR.glob("*.csv")):
        _, _, meta = parse_csv_file(path)
        services_seen.add(meta.get("Service", ""))
    unmapped = [s for s in services_seen if s not in labels]
    if unmapped:
        print(f"\nNote: {len(unmapped)} service(s) have no friendly name yet "
              f"({', '.join(sorted(unmapped))}). Add them to "
              f"{LABELS_PATH} to label them on the dashboard.")


if __name__ == "__main__":
    main()
