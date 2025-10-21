#!/usr/bin/env python
"""
EPIC 3 — Zonal Statistics (mean NDVI per polygon)

Usage:
  python src/04_zonal_stats.py --vector data/vector/fields.geojson \
                               --raster data/processed/ndvi.tif \
                               --out-geojson data/processed/ndvi_zonal.geojson \
                               --out-csv data/processed/ndvi_zonal.csv
"""
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping
from utils.log import get_logger  # 👈 Make sure you have this in src/utils/log.py

def compute_zonal_mean(raster_path: Path, vector_path: Path) -> gpd.GeoDataFrame:
    log = get_logger("zonal")

    if not Path(raster_path).exists():
        raise FileNotFoundError(f"Raster not found: {raster_path}")
    if not Path(vector_path).exists():
        raise FileNotFoundError(f"Vector not found: {vector_path}")

    log.info(f"Loading raster: {raster_path}")
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        nodata = src.nodata

    log.info(f"Loading polygons: {vector_path}")
    gdf = gpd.read_file(vector_path)
    if gdf.empty:
        raise ValueError("Vector file has no features.")
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)

    # Reproject polygons to match raster CRS
    gdf = gdf.to_crs(raster_crs)
    log.info(f"Reprojected vector to raster CRS: {raster_crs}")

    # Compute NDVI statistics for each polygon
    means, mins, maxs, counts = [], [], [], []
    with rasterio.open(raster_path) as src:
        for idx, row in gdf.iterrows():
            geom = [mapping(row.geometry)]
            try:
                out_img, _ = mask(src, geom, crop=True)
                arr = out_img[0].astype("float32")
                if nodata is not None:
                    arr[arr == nodata] = np.nan
                valid = arr[np.isfinite(arr)]
                if valid.size == 0:
                    means.append(np.nan); mins.append(np.nan); maxs.append(np.nan); counts.append(0)
                else:
                    means.append(float(valid.mean()))
                    mins.append(float(valid.min()))
                    maxs.append(float(valid.max()))
                    counts.append(int(valid.size))
            except Exception as e:
                log.warning(f"Polygon {idx} failed: {e}")
                means.append(np.nan); mins.append(np.nan); maxs.append(np.nan); counts.append(0)

    # Add statistics to GeoDataFrame
    gdf = gdf.copy()
    if "id" not in gdf.columns:
        gdf["id"] = gdf.index.astype(str)

    gdf["ndvi_mean"] = means
    gdf["ndvi_min"] = mins
    gdf["ndvi_max"] = maxs
    gdf["ndvi_count"] = counts
    return gdf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vector", default="data/vector/fields.geojson")
    ap.add_argument("--raster", default="data/processed/ndvi.tif")
    ap.add_argument("--out-geojson", default="data/processed/ndvi_zonal.geojson")
    ap.add_argument("--out-csv", default="data/processed/ndvi_zonal.csv")
    args = ap.parse_args()

    out_geo = Path(args.out_geojson)
    out_geo.parent.mkdir(parents=True, exist_ok=True)
    out_csv = Path(args.out_csv)

    gdf = compute_zonal_mean(Path(args.raster), Path(args.vector))

    # Save outputs
    gdf.to_file(out_geo, driver="GeoJSON")
    gdf.drop(columns="geometry").to_csv(out_csv, index=False)

    log = get_logger("zonal")
    log.info(f"✅ Saved zonal GeoJSON: {out_geo}")
    log.info(f"✅ Saved zonal CSV:     {out_csv}")
    log.info(
        f"Rows: {len(gdf)} | NDVI mean range: "
        f"{np.nanmin(gdf['ndvi_mean']):.3f}..{np.nanmax(gdf['ndvi_mean']):.3f}"
    )

if __name__ == "__main__":
    main()
