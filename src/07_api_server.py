from __future__ import annotations

#!/usr/bin/env python
"""
Epic 6 — FastAPI service for GeoFarm
Run:
  uvicorn src.07_api_server:app --reload --port 8000
"""
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlalchemy as sa

from sqlalchemy import text
from geoalchemy2.shape import to_shape
import json

from src.utils.cfg import load_config
from src.utils.db_utils import get_engine
from src.utils.api_utils import ok, fail

import os
cfg = load_config()             # reads src/config.yaml
DSN = os.getenv("POSTGRES_DSN", cfg["postgres"]["dsn"])    # postgresql://geofarmer:***@localhost:5432/geofarm
engine = get_engine(DSN)

app = FastAPI(title="GeoFarm API", version="0.1.0")

# CORS (allow local dev tools / dashboard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return ok("alive")

@app.get("/ndvi/runs")
def ndvi_runs(limit: int = 10):
    q = text("""
        SELECT run_id, acq_date, aoi_bbox, s3_prefix, created_at
        FROM ndvi_runs
        ORDER BY created_at DESC
        LIMIT :lim
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, {"lim": limit}).mappings().all()
    return ok([dict(r) for r in rows])

@app.get("/ndvi/latest")
def ndvi_latest():
    """
    Latest NDVI stats per field (by most recent run).
    """
    q = text("""
      WITH latest AS (
        SELECT run_id
        FROM ndvi_runs
        ORDER BY created_at DESC
        LIMIT 1
      )
      SELECT s.field_id, s.ndvi_mean, s.ndvi_min, s.ndvi_max, s.ndvi_count
      FROM ndvi_stats s
      JOIN latest l ON s.run_id = l.run_id
      ORDER BY s.field_id
    """)
    with engine.connect() as conn:
        rows = conn.execute(q).mappings().all()
    return ok([dict(r) for r in rows])

@app.get("/fields")
def fields(limit: Optional[int] = Query(None, ge=1, le=10000), simplify_tolerance: Optional[float] = Query(0.0, ge=0.0)):
    """
    Return field polygons as GeoJSON FeatureCollection.
    - limit: number of features (optional)
    - simplify_tolerance: simplification tolerance in degrees (optional)
    """
    # Build SQL dynamically for simplification
    geom_expr = "geom"
    if simplify_tolerance and simplify_tolerance > 0:
        geom_expr = f"ST_SimplifyPreserveTopology(geom, {simplify_tolerance})"

    sql = f"""
      SELECT field_id, name, ST_AsGeoJSON({geom_expr}) AS gj
      FROM fields
      ORDER BY field_id
      {"LIMIT :lim" if limit else ""}
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"lim": limit} if limit else {}).mappings().all()

    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "properties": {"field_id": r["field_id"], "name": r["name"]},
            "geometry": json.loads(r["gj"])
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }

@app.get("/")
def root():
    return {
        "service": "GeoFarm API",
        "endpoints": ["/health", "/fields", "/ndvi/runs", "/ndvi/latest"]
    }