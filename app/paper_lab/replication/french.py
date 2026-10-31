"""Kenneth French Data Library loader.

Downloads ``<name>_CSV.zip`` from the library (cached under ~/.cache/paper_lab/french),
or reads a pre-downloaded ``.zip`` / ``.csv`` from ``data_dir`` (for offline use or
networks that block dartmouth.edu).

French CSVs contain several blocks (monthly VW, monthly EW, annual, ...). Each block
is a title line, a header row starting with ',' and data rows keyed YYYYMM or YYYY.
``parse_french_csv`` returns {block title: DataFrame} with returns in decimals.
"""

from __future__ import annotations

import io
import logging
import os
import re
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("alphaagent.paper_lab.french")

BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{name}_CSV.zip"
DEFAULT_CACHE = Path(os.getenv("PAPER_LAB_CACHE", Path.home() / ".cache" / "paper_lab" / "french"))

FACTORS = "F-F_Research_Data_Factors"
PORTFOLIOS_ME = "Portfolios_Formed_on_ME"
PORTFOLIOS_2X3 = "6_Portfolios_2x3"


def _read_zip_bytes(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        member = next(n for n in zf.namelist() if n.lower().endswith((".csv", ".txt")))
        return zf.read(member).decode("latin-1")


def fetch_raw(name: str, data_dir: Optional[str | Path] = None, cache_dir: Optional[Path] = None,
              offline: bool = False) -> str:
    """Return the CSV text for a French dataset."""
    for d in [Path(data_dir)] if data_dir else []:
        for cand in (d / f"{name}_CSV.zip", d / f"{name}.zip", d / f"{name}.csv", d / f"{name}.CSV"):
            if cand.exists():
                logger.info("Using local French file %s", cand)
                data = cand.read_bytes()
                return _read_zip_bytes(data) if cand.suffix.lower() == ".zip" else data.decode("latin-1")

    cache_dir = Path(cache_dir or DEFAULT_CACHE)
    cached = cache_dir / f"{name}_CSV.zip"
    if cached.exists():
        return _read_zip_bytes(cached.read_bytes())
    if offline:
        raise FileNotFoundError(f"{name} not found in data_dir/cache and offline=True")

    url = BASE_URL.format(name=name)
    logger.info("Downloading %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (paper-lab replication)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
    return _read_zip_bytes(data)


_DATA_ROW = re.compile(r"^\s*(\d{4}|\d{6})\s*,")


def parse_french_csv(text: str) -> dict[str, pd.DataFrame]:
    lines = text.splitlines()
    blocks: dict[str, pd.DataFrame] = {}
    i, n_block, last_text = 0, 0, ""
    while i < len(lines):
        line = lines[i]
        cells = [c.strip() for c in line.split(",")]
        is_header = len(cells) > 1 and cells[0] == "" and any(cells[1:]) and i + 1 < len(lines) \
            and _DATA_ROW.match(lines[i + 1] or "")
        if not is_header:
            if line.strip() and not _DATA_ROW.match(line):
                last_text = line.strip()
            i += 1
            continue
        cols = cells[1:]
        rows, idx = [], []
        i += 1
        while i < len(lines) and _DATA_ROW.match(lines[i]):
            parts = [p.strip() for p in lines[i].split(",")]
            idx.append(parts[0])
            vals = []
            for p in parts[1: len(cols) + 1]:
                try:
                    vals.append(float(p))
                except ValueError:
                    vals.append(np.nan)
            rows.append(vals + [np.nan] * (len(cols) - len(vals)))
            i += 1
        df = pd.DataFrame(rows, columns=cols)
        df = df.replace([-99.99, -999.0, -999.99], np.nan) / 100.0
        if len(idx[0]) == 6:
            df.index = pd.PeriodIndex([f"{k[:4]}-{k[4:]}" for k in idx], freq="M")
        else:
            df.index = pd.Index([int(k) for k in idx], name="year")
        n_block += 1
        title = last_text or f"block{n_block}"
        if title in blocks:
            title = f"{title} #{n_block}"
        blocks[title] = df
        last_text = ""
    return blocks


def find_block(blocks: dict[str, pd.DataFrame], *keywords: str, monthly: bool = True) -> pd.DataFrame:
    """First block whose title contains all keywords (case-insensitive) and has the right frequency."""
    for title, df in blocks.items():
        if monthly != isinstance(df.index, pd.PeriodIndex):
            continue
        if all(k.lower() in title.lower() for k in keywords):
            return df
    if not keywords:
        raise KeyError("no block with requested frequency")
    raise KeyError(f"No {'monthly' if monthly else 'annual'} block matching {keywords}; have {list(blocks)}")


def load(name: str, **kw) -> dict[str, pd.DataFrame]:
    return parse_french_csv(fetch_raw(name, **kw))


def market_and_factors(**kw) -> pd.DataFrame:
    """Monthly Mkt-RF, SMB, HML, RF plus MKT = Mkt-RF + RF (total market return)."""
    df = find_block(load(FACTORS, **kw), monthly=True).copy()
    df["MKT"] = df["Mkt-RF"] + df["RF"]
    return df


def size_portfolios(weighting: str = "Value Weight", **kw) -> pd.DataFrame:
    return find_block(load(PORTFOLIOS_ME, **kw), weighting, "Monthly", monthly=True)


def size_bm_2x3(weighting: str = "Value Weight", **kw) -> pd.DataFrame:
    return find_block(load(PORTFOLIOS_2X3, **kw), weighting, "Monthly", monthly=True)
