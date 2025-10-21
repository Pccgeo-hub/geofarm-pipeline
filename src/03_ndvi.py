#!/usr/bin/env python
"""
EPIC 2 — NDVI Computation

Usage:
  python src/03_ndvi.py
"""

from pathlib import Path
import numpy as np
import rasterio
from utils.log import get_logger

def main():
    log = get_logger("ndvi")

    red_path = Path("data/raw/red.tif")
    nir_path = Path("data/raw/nir.tif")
    out_path = Path("data/processed/ndvi.tif")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not red_path.exists() or not nir_path.exists():
        log.error("Missing input files red.tif or nir.tif — run Epic 1 first.")
        return

    # Read both bands
    with rasterio.open(red_path) as red_ds, rasterio.open(nir_path) as nir_ds:
        red = red_ds.read(1).astype("float32")
        nir = nir_ds.read(1).astype("float32")

        # Basic NDVI formula
        ndvi = (nir - red) / (nir + red + 1e-6)

        # Copy metadata from red band
        profile = red_ds.profile
        profile.update(dtype="float32", count=1)

        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(ndvi, 1)

    log.info(f"✅ NDVI written to {out_path}")

    # Optional: show summary stats
    log.info(f"NDVI range: min={float(np.nanmin(ndvi)):.3f}, max={float(np.nanmax(ndvi)):.3f}")

if __name__ == "__main__":
    main()