#!/usr/bin/env python
"""
EPIC 1 / Step 2 — Download selected assets (e.g., B04=RED, B08=NIR)

Usage:
  python src/02_download.py --item-id <STAC_ITEM_ID> --red-asset B04 --nir-asset B08
  (Optionally specify --out-dir and --timeout)
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import requests
from pystac_client import Client
from utils.cfg import load_config
from utils.log import get_logger

def fetch(url: str, out_path: Path, timeout: int, log):
    log.info(f"GET {url}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(r.content)
    log.info(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item-id", required=True, help="STAC item id to download from (must be in the catalog)")
    ap.add_argument("--red-asset", default="B04", help="Asset key for red band")
    ap.add_argument("--nir-asset", default="B08", help="Asset key for NIR band")
    ap.add_argument("--out-dir", default="data/raw", help="Directory to save bands")
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    cfg = load_config()
    log = get_logger("download")

    catalog = Client.open(cfg["stac"]["url"])
    search = catalog.search(bbox=cfg["aoi"]["bbox"], datetime=cfg["aoi"]["date"], collections=["sentinel-2-l2a"])
    candidates = list(search.get_items())

    item = None
    for it in candidates:
        if it.id == args.item_id:
            item = it
            break
    if item is None:
        log.error("Item id not found in current search scope. Try adjusting bbox/date or verify the id from discover.json")
        sys.exit(1)

    # Resolve asset hrefs
    assets = item.assets
    for key in (args.red_asset, args.nir_asset):
        if key not in assets:
            log.error(f"Asset {key} not found. Available: {list(assets.keys())[:10]}")
            sys.exit(2)

    red_href = assets[args.red_asset].href
    nir_href = assets[args.nir_asset].href

    out_dir = Path(args.out_dir)
    fetch(red_href, out_dir/"red.tif", args.timeout, log)
    fetch(nir_href, out_dir/"nir.tif", args.timeout, log)

    manifest = {
        "item_id": item.id,
        "datetime": item.datetime.isoformat() if item.datetime else None,
        "red_asset": args.red_asset,
        "nir_asset": args.nir_asset,
        "red_path": str((out_dir/"red.tif").as_posix()),
        "nir_path": str((out_dir/"nir.tif").as_posix())
    }
    (out_dir/"download_manifest.json").write_text(json.dumps(manifest, indent=2))
    log.info(f"Wrote {out_dir/'download_manifest.json'}")

if __name__ == "__main__":
    main()
