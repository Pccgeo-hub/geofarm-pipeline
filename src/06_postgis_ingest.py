#!/usr/bin/env python
"""
EPIC 5 — Ingest NDVI results into PostGIS.

Usage:
  python src/06_postgis_ingest.py \
    --dsn postgresql+psycopg2://geofarmer:pass@localhost:5432/geofarm \
    --fields data/vector/fields.geojson \
    --zonal  data/processed/ndvi_zonal.csv \
    --run-date 2025-07-15 --aoi "19.80,50.00,20.20,50.30" --s3-prefix s3://my-bucket/outputs/20250715T...
"""
from __future__ import annotations
from pathlib import Path
import os
import argparse
import uuid
import pandas as pd
import sqlalchemy as sa

from utils.log import get_logger
from utils.db_utils import get_engine, init_schema

# --- Windows/GeoPandas friendliness (safe no-ops on other OSes) ---
os.environ.setdefault("GEOPANDAS_IO_ENGINE", "fiona")
# If you ever see PROJ/GDAL lookup warnings, also set these:
os.environ.setdefault("PROJ_LIB", r"C:\Users\pchuk\mambaforge\envs\geofarm311\Library\share\proj")
os.environ.setdefault("GDAL_DATA", r"C:\Users\pchuk\mambaforge\envs\geofarm311\Library\share\gdal")


def upsert_fields(engine: sa.Engine, fields_geojson: Path):
    """
    Writes app 'fields' into geofarm.fields (field_id text, name text, geom geometry).
    Ensures CRS=EPSG:4326 and geometry column name = geom.
    """
    import geopandas as gpd
    from geoalchemy2 import Geometry

    log = get_logger("ingest")

    gdf = gpd.read_file(fields_geojson)
    if gdf.empty:
        log.warning("No features in fields.geojson")
        return

    # Ensure attributes exist and match DB schema
    if "field_id" not in gdf.columns:
        if "id" in gdf.columns:
            gdf = gdf.rename(columns={"id": "field_id"})
        else:
            gdf["field_id"] = gdf.index.astype(str)

    if "name" not in gdf.columns:
        gdf["name"] = "field"

    # Ensure CRS = WGS84
    if gdf.crs is None:
        gdf = gdf.set_crs(4326, allow_override=True)
    elif getattr(gdf.crs, "to_epsg", lambda: None)() != 4326:
        gdf = gdf.to_crs(4326)

    # Match DB geometry column name
    gdf = gdf.rename_geometry("geom")

    # Keep only columns your table has, in order
    gdf = gdf[["field_id", "name", "geom"]].copy()

    # Append to geofarm.fields (first time you may use if_exists="replace" to create it)
    gdf.to_postgis(
        name="fields",
        con=engine,
        schema="geofarm",                           # <- write to geofarm schema
        if_exists="append",                         # <- change to "replace" ONLY on first create
        index=False,
        dtype={"geom": Geometry("MULTIPOLYGON", srid=4326)},
    )
    log.info(f"Inserted/appended {len(gdf)} rows into geofarm.fields.")


def create_run(engine: sa.Engine, acq_date: str | None, aoi_bbox: str | None, s3_prefix: str | None) -> str:
    """
    Inserts one row into geofarm.ndvi_runs and returns run_id.
    """
    run_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO geofarm.ndvi_runs(run_id, acq_date, aoi_bbox, s3_prefix)
                VALUES (:rid, :ad, :bbox, :pfx)
            """),
            {"rid": run_id, "ad": acq_date, "bbox": aoi_bbox, "pfx": s3_prefix},
        )
    return run_id


def load_zonal_csv(engine: sa.Engine, run_id: str, csv_path: Path):
    """
    Loads NDVI stats from CSV into geofarm.ndvi_stats (non-geometry table),
    aligning key column to 'field_id'.
    """
    log = get_logger("ingest")
    df = pd.read_csv(csv_path)

    # Prefer 'field_id' if present, otherwise accept 'id'
    if "field_id" in df.columns:
        field_id_series = df["field_id"].astype(str)
    elif "id" in df.columns:
        field_id_series = df["id"].astype(str)
    else:
        field_id_series = df.index.astype(str)

    cols = {
        "field_id": field_id_series,
        "ndvi_mean": df.get("ndvi_mean"),
        "ndvi_min":  df.get("ndvi_min"),
        "ndvi_max":  df.get("ndvi_max"),
        "ndvi_count": df.get("ndvi_count", 0),
    }
    ins_df = pd.DataFrame(cols)
    ins_df["run_id"] = run_id

    # insert (pandas to_sql supports method="multi")
    with engine.begin() as conn:
        ins_df.to_sql("ndvi_stats", conn, schema="geofarm", if_exists="append", index=False, method="multi")
    log.info(f"Inserted {len(ins_df)} geofarm.ndvi_stats rows for run_id={run_id}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=False, help="Postgres DSN; overrides config.yaml if given")
    ap.add_argument("--fields", default="data/vector/fields.geojson")
    ap.add_argument("--zonal",  default="data/processed/ndvi_zonal.csv")
    ap.add_argument("--run-date", dest="run_date", default=None, help="Acquisition date, e.g., 2025-07-15")
    ap.add_argument("--aoi", default=None, help="AOI bbox string, e.g., '19.80,50.00,20.20,50.30'")
    ap.add_argument("--s3-prefix", default=None, help="S3 prefix for this run (optional)")
    args = ap.parse_args()

import os

# Load DSN from CLI, environment, or config.yaml
dsn = args.dsn or os.getenv("POSTGRES_DSN")
if not dsn:
    from utils.cfg import load_config
    cfg = load_config()
    dsn = cfg["postgres"]["dsn"]

engine = get_engine(dsn)
init_schema(engine)  # should create geofarm schema + tables if missing


    # Load DSN from CLI or config.yaml
    #dsn = args.dsn
    #if not dsn:
       # from utils.cfg import load_config
        #cfg = load_config()
        #dsn = cfg["postgres"]["dsn"]

   # engine = get_engine(dsn)
   # init_schema(engine)  # should create geofarm schema + tables if missing

    # 1) Upsert fields (optional if already present)
if Path(args.fields).exists():
        upsert_fields(engine, Path(args.fields))

    # 2) Create a run record
run_id = create_run(engine, args.run_date, args.aoi, args.s3_prefix)

    # 3) Insert stats
load_zonal_csv(engine, run_id, Path(args.zonal))

log = get_logger("ingest")
log.info(f"✅ Ingest completed. run_id={run_id}")


if __name__ == "__main__":
    main()