#!/usr/bin/env python
"""
EPIC 4 — Upload processed outputs to S3 in a timestamped run folder.

Usage:
  python src/05_upload_s3.py --bucket geofarm-data-demo --prefix outputs
  # Optional:
  # python src/05_upload_s3.py --bucket <your-bucket> --prefix outputs --sse AES256
"""
from __future__ import annotations
from pathlib import Path
import argparse, datetime
from utils.log import get_logger
from utils.aws_utils import upload_file

def now_stamp():
    # ISO-ish timestamp for folder names, no colons (safe for S3)
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", required=True, help="Target S3 bucket name")
    ap.add_argument("--prefix", default="outputs", help="Top-level folder in S3")
    ap.add_argument("--sse", default=None, help="Server-side encryption (e.g., AES256 or aws:kms)")
    args = ap.parse_args()

    log = get_logger("upload")
    ts = now_stamp()
    base_prefix = f"{args.prefix}/{ts}"  # e.g., outputs/20251019T123456Z

    # Files to upload (add more if needed)
    files = [
        ("data/processed/ndvi.tif",          f"{base_prefix}/ndvi.tif"),
        ("data/processed/ndvi_zonal.geojson",f"{base_prefix}/ndvi_zonal.geojson"),
        ("data/processed/ndvi_zonal.csv",    f"{base_prefix}/ndvi_zonal.csv"),
    ]

    extra = {}
    if args.sse:
        extra["ServerSideEncryption"] = args.sse

    # Upload each file
    uploaded = []
    for local, key in files:
        uri = upload_file(args.bucket, local, key, extra=extra)
        uploaded.append(uri)

    log.info("✅ Upload complete.")
    for uri in uploaded:
        log.info(f"  - {uri}")

if __name__ == "__main__":
    main()