"""Download the public datasets into data/raw/ (git-ignored; we never redistribute them).

    python -m backend.data_engine.ml.fetch_datasets            # Bank Marketing (needed for the lead model)
    python -m backend.data_engine.ml.fetch_datasets --retail   # Online Retail II (optional RFM; ~45 MB)

UCI Bank Marketing: Moro, Cortez and Rita (2014). Check the terms on the UCI dataset page before reuse.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

RAW = Path(__file__).resolve().parents[3] / "data" / "raw"
BANK_URL = "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip"
RETAIL_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
BANK_CSV = RAW / "bank-additional-full.csv"
BANK_ROWS = 41188


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def fetch_bank(force: bool = False) -> Path:
    if BANK_CSV.exists() and not force:
        return BANK_CSV
    RAW.mkdir(parents=True, exist_ok=True)
    outer = zipfile.ZipFile(io.BytesIO(_download(BANK_URL)))
    inner = zipfile.ZipFile(io.BytesIO(outer.read("bank-additional.zip")))
    name = next(n for n in inner.namelist() if n.endswith("bank-additional-full.csv"))
    data = inner.read(name)
    BANK_CSV.write_bytes(data)
    return BANK_CSV


def fetch_retail(force: bool = False) -> Path:
    target = RAW / "online-retail-ii.zip"
    if target.exists() and not force:
        return target
    RAW.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_download(RETAIL_URL))
    return target


def checksum(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--retail", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    p = fetch_bank(args.force)
    print(f"bank marketing: {p} sha1={checksum(p)[:12]}")
    if args.retail:
        r = fetch_retail(args.force)
        print(f"online retail II: {r}")
