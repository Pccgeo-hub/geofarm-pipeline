from __future__ import annotations
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from utils.log import get_logger

log = get_logger("aws")

def s3_client():
    # Uses default AWS CLI credentials/profile & region
    return boto3.client("s3")

def upload_file(bucket: str, local_path: str | Path, key: str, extra: dict | None = None) -> str:
    """
    Upload a single file to s3://bucket/key.
    Returns the s3 uri if successful.
    """
    client = s3_client()
    local_path = Path(local_path)
    if not local_path.exists():
        raise FileNotFoundError(local_path)
    extra = extra or {}  # e.g., {"ServerSideEncryption": "AES256"}
    try:
        client.upload_file(str(local_path), bucket, key, ExtraArgs=extra)
        log.info(f"Uploaded: {local_path} -> s3://{bucket}/{key}")
        return f"s3://{bucket}/{key}"
    except ClientError as e:
        log.error(f"Upload failed for {local_path}: {e}")
        raise