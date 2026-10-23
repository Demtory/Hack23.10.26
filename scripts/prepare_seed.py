#!/usr/bin/env python3
"""Prepare a demo seed from the provided data.json.

The source fixture is a static snapshot: some `active` services are already
expired and `prolong_wait` rows are months old.  For a coherent demo we shift
dates relative to a fixed `as_of`, while keeping statuses, money and relations
untouched.  Raw data stays immutable in data/raw/.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Days relative to as_of for each status.  Values are deterministic per
# service within its status group, so reruns produce the same seed.
OFFSETS = {
    "active": [0.5, 2.0, 6.0, 13.0, 28.0, 75.0, 180.0, 330.0],
    "suspended": [120.0, 90.0, 60.0, 180.0],
    "prolong_wait": [-0.5, -1.5, -3.0, -4.5],
    "blocked": [-20.0, 15.0, 60.0, 200.0],
    "deleted": [-10.0, -40.0, -120.0, -300.0],
}


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def shift_service(service: dict, delta: timedelta) -> None:
    service["createdAt"] = iso(parse_iso(service["createdAt"]) + delta)
    service["expiresAt"] = iso(parse_iso(service["expiresAt"]) + delta)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/raw/data.json", type=Path)
    parser.add_argument("--out", default="data/seed.json", type=Path)
    parser.add_argument("--meta", default="data/seed.meta.json", type=Path)
    parser.add_argument(
        "--as-of",
        default="2026-10-23T18:00:00.000Z",
        help="demo snapshot time; app must use the same AS_OF",
    )
    parser.add_argument(
        "--demo-balance-account",
        type=int,
        default=6,
        help="account id to make cash-poor for a visible funds-gap demo; 0 disables",
    )
    parser.add_argument("--demo-balance", type=int, default=300, help="new balance in eurocents")
    args = parser.parse_args()

    as_of = parse_iso(args.as_of).astimezone(timezone.utc)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    services = data["services"]
    transactions = data["transactions"]

    by_service = defaultdict(list)
    for txn in transactions:
        by_service[txn["serviceId"]].append(txn)

    status_index: dict[str, int] = defaultdict(int)
    for service in services:
        status = service["status"]
        offsets = OFFSETS.get(status)
        if not offsets:
            continue
        index = status_index[status] % len(offsets)
        status_index[status] += 1
        old_created = parse_iso(service["createdAt"])
        old_expiry = parse_iso(service["expiresAt"])
        duration = old_expiry - old_created
        # A service cannot be created in the future.  For short terms an
        # offset larger than the term would imply exactly that, so clamp the
        # target expiry to `as_of + duration` minus a small margin.
        max_expiry = as_of + duration
        target_expiry = as_of + timedelta(days=offsets[index])
        if target_expiry > max_expiry:
            target_expiry = max_expiry - min(duration * 0.1, timedelta(hours=1))
        delta = target_expiry - old_expiry
        shift_service(service, delta)
        for txn in by_service[service["id"]]:
            txn["createdAt"] = iso(parse_iso(txn["createdAt"]) + delta)
            if txn["performedAt"]:
                txn["performedAt"] = iso(parse_iso(txn["performedAt"]) + delta)

    if args.demo_balance_account:
        for account in data["accounts"]:
            if account["id"] == args.demo_balance_account:
                account["balance"] = args.demo_balance
                account["withdrawBalance"] = 0
                account["bonusBalance"] = 0
                account["bonusState"] = "locked"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    meta = {
        "asOf": iso(as_of),
        "source": str(args.input),
        "counts": {key: len(data[key]) for key in ("accounts", "services", "transactions")},
        "offsetsDays": OFFSETS,
        "note": "Dates shifted for demo; one account made cash-poor for a visible funds-gap case.",
    }
    args.meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"seed: {args.out} ({meta['counts']}) asOf={meta['asOf']}")


if __name__ == "__main__":
    main()
