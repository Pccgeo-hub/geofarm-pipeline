#!/usr/bin/env python
"""
EPIC 1 / Step 1 — Discover imagery via STAC

Usage:
  python src/01_discover.py --bbox 19.80,50.00,20.20,50.30 --date 2025-07-01/2025-07-31 --max-cloud 20
Outputs:
  - Prints a small table of candidate items (id, datetime, cloud cover)
  - Writes results to data/raw/discover.json for downstream selection
"""
from __future__ import annotations

import argparse, json
from pathlib import Path
from pystac_client import Client
from utils.cfg import load_config
from utils.log import get_logger

def parse_bbox(bbox_str: str):
    parts = [float(x) for x in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be 'minx,miny,maxx,maxy'")
    return parts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", type=str, help="minx,miny,maxx,maxy (EPSG:4326)")
    ap.add_argument("--date", type=str, help="ISO date or range e.g. 2025-07-01/2025-07-31")
    ap.add_argument("--max-cloud", type=int, default=30)
    args = ap.parse_args()

    cfg = load_config()
    bbox = parse_bbox(args.bbox) if args.bbox else cfg["aoi"]["bbox"]
    date = args.date or cfg["aoi"]["date"]
    max_cloud = args.max_cloud

    log = get_logger("discover")

    stac_url = cfg["stac"]["url"]
    log.info(f"Connecting to STAC: {stac_url}")
    catalog = Client.open(stac_url)

    search = catalog.search(bbox=bbox, datetime=date, collections=["sentinel-2-l2a"])  # S2 L2A on Planetary Computer
    items = list(search.get_items())
    log.info(f"Found {len(items)} candidate items for bbox={bbox} date={date}")

    # Extract light metadata
    results = []
    for it in items:
        cc = (it.properties or {}).get("eo:cloud_cover") or (it.properties or {}).get("s2:cloud_cover")
        results.append({
            "id": it.id,
            "datetime": it.datetime.isoformat() if it.datetime else None,
            "cloud_cover": cc,
            "assets": list(it.assets.keys())
        })

    # Filter by cloud cover if present
    filtered = [r for r in results if r["cloud_cover"] is None or r["cloud_cover"] <= max_cloud]

    out = {
        "stac_url": stac_url,
        "bbox": bbox,
        "date": date,
        "max_cloud": max_cloud,
        "count_total": len(results),
        "count_filtered": len(filtered),
        "items": filtered[:15]
    }

    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/raw/discover.json").write_text(json.dumps(out, indent=2))
    log.info("Wrote data/raw/discover.json")
    for r in filtered[:10]:
        log.info(f"- {r['id']} | {r['datetime']} | cloud={r['cloud_cover']} | assets~{r['assets'][:5]}")

if __name__ == "__main__":
    main()
