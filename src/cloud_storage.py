import os
import re
from pathlib import Path
from typing import Tuple, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError


def is_s3_uri(uri: str) -> bool:
    """Checks whether a URI string is an S3 URI (e.g. s3://bucket/path/to/file)."""
    return isinstance(uri, str) and uri.startswith("s3://")


def parse_s3_uri(s3_uri: str) -> Tuple[str, str]:
    """Parses an S3 URI into bucket name and key path.

    Args:
        s3_uri: S3 URI formatted as s3://<bucket>/<key>.

    Returns:
        Tuple of (bucket_name, key_path).

    Raises:
        ValueError: If the URI is malformed.
    """
    if not is_s3_uri(s3_uri):
        raise ValueError(f"Invalid S3 URI: {s3_uri}. Must start with 's3://'")

    path_part = s3_uri[5:]  # Strip 's3://'
    parts = path_part.split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""

    if not bucket or not key:
        raise ValueError(f"Malformed S3 URI '{s3_uri}'. Both bucket and key are required.")

    return bucket, key


def get_s3_client(endpoint_url: Optional[str] = None):
    """Initializes a boto3 S3 client with optional MinIO/custom endpoint URL.

    Checks environment variables:
      - S3_ENDPOINT_URL (e.g. http://localhost:9000 for MinIO)
      - AWS_ACCESS_KEY_ID
      - AWS_SECRET_ACCESS_KEY
      - AWS_REGION / AWS_DEFAULT_REGION
    """
    url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
    region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.client("s3", endpoint_url=url, region_name=region)


def download_s3_file(
    s3_uri: str, local_dest: Optional[Path | str] = None, s3_client=None
) -> Path:
    """Downloads a file from S3 / MinIO to local disk.

    Args:
        s3_uri: S3 URI of the source file.
        local_dest: Optional local destination path. If None, saves in data/downloads/<filename>.
        s3_client: Optional boto3 S3 client instance.

    Returns:
        Path object to the downloaded local file.
    """
    bucket, key = parse_s3_uri(s3_uri)
    filename = Path(key).name

    if local_dest:
        dest_path = Path(local_dest)
    else:
        dest_path = Path("data") / "downloads" / filename

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    client = s3_client or get_s3_client()
    client.download_file(bucket, key, str(dest_path))
    return dest_path


def upload_s3_file(
    local_path: Path | str, s3_uri: str, s3_client=None
) -> str:
    """Uploads a local file to S3 / MinIO.

    Args:
        local_path: Path to the local file to upload.
        s3_uri: Destination S3 URI (s3://bucket/key).
        s3_client: Optional boto3 S3 client instance.

    Returns:
        The destination S3 URI.
    """
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(f"Local file does not exist: {path}")

    bucket, key = parse_s3_uri(s3_uri)
    client = s3_client or get_s3_client()
    client.upload_file(str(path), bucket, key)
    return s3_uri

