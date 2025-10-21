from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from utils.log import get_logger

log = get_logger("db")

def get_engine(dsn: str) -> Engine:
    try:
        engine = sa.create_engine(dsn, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        log.info("Connected to Postgres.")
        return engine
    except Exception as e:
        log.error(f"DB connection failed: {e}")
        raise

def init_schema(engine: Engine):
    ddl = """
    CREATE TABLE IF NOT EXISTS fields (
        field_id TEXT PRIMARY KEY,
        name TEXT,
        geom geometry(Polygon, 4326)
    );

    CREATE TABLE IF NOT EXISTS ndvi_runs (
        run_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        acq_date DATE,
        aoi_bbox TEXT,
        s3_prefix TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS ndvi_stats (
        id BIGSERIAL PRIMARY KEY,
        run_id UUID REFERENCES ndvi_runs(run_id) ON DELETE CASCADE,
        field_id TEXT REFERENCES fields(field_id),
        ndvi_mean DOUBLE PRECISION,
        ndvi_min  DOUBLE PRECISION,
        ndvi_max  DOUBLE PRECISION,
        ndvi_count INTEGER
    );

    -- Extensions for UUID if needed
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE INDEX IF NOT EXISTS idx_fields_geom ON fields USING GIST(geom);
    CREATE INDEX IF NOT EXISTS idx_stats_field ON ndvi_stats(field_id);
    """
    with engine.begin() as conn:
        conn.exec_driver_sql(ddl)
    log.info("Schema ensured (tables & indexes).")