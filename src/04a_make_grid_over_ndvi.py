#!/usr/bin/env python
"""
Generate a simple grid of polygons over the NDVI raster extent.
Use this to simulate fields if you don't have a fields.geojson.

Usage:
  python src/04a_make_grid_over_ndvi.py --raster data/processed/ndvi.tif \
                                        --rows 3 --cols 3 \
                                        --out data/vector/fields.geojson
"""
from __future__ import annotations
from pathlib import Path
import argparse
import geopandas as gpd
from shapely.geometry import Polygon
import rasterio

def make_grid_over_raster(raster_path: Path, rows: int, cols: int) -> gpd.GeoDataFrame:
    with rasterio.open(raster_path) as src:
        bounds = src.bounds
        crs = src.crs

    minx, miny, maxx, maxy = bounds.left, bounds.bottom, bounds.right, bounds.top
    dx = (maxx - minx) / cols
    dy = (maxy - miny) / rows

    polys = []
    fid = 1
    for r in range(rows):
        for c in range(cols):
            x0 = minx + c*dx
            y0 = miny + r*dy
            x1 = x0 + dx
            y1 = y0 + dy
            polys.append({"id": fid, "name": f"Cell {fid}", "geometry": Polygon([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])})
            fid += 1

    gdf = gpd.GeoDataFrame(polys, crs=crs)
    # Save in EPSG:4326 for portability
    gdf = gdf.to_crs("EPSG:4326")
    return gdf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raster", default="data/processed/ndvi.tif")
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--out", default="data/vector/fields.geojson")
    args = ap.parse_args()

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    gdf = make_grid_over_raster(Path(args.raster), args.rows, args.cols)
    gdf.to_file(out, driver="GeoJSON")
    print(f"✅ Wrote {len(gdf)} grid polygons to {out}")

if __name__ == "__main__":
    main()
