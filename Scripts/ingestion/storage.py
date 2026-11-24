"""Write raw files to the GCS raw zone, or to a local folder when GCS_BUCKET is not set.

Layout (README): raw/YYYY-MM-DD/<source>/<file>
Raw files are never edited after they are written; every run gets its own dated folder.
"""

import gzip
import hashlib
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from Scripts.ingestion import config

log = logging.getLogger(__name__)


def run_date():
    """Today's date in Chicago time (not UTC), e.g. '2026-11-20'."""
    return datetime.now(ZoneInfo(config.TIMEZONE)).date().isoformat()


class RawStore:
    def __init__(self, bucket=None, prefix=None, local_dir=None):
        self.bucket_name = config.GCS_BUCKET if bucket is None else bucket
        self.prefix = prefix or config.GCS_RAW_PREFIX
        self.local_dir = local_dir or config.LOCAL_OUT_DIR
        self._bucket = None
        self.written = []  # one entry per file: uri, bytes, sha256 (for ingestion_run)
        if self.bucket_name:
            from google.cloud import storage  # only needed when writing to GCS

            self._bucket = storage.Client().bucket(self.bucket_name)

    def key(self, day, source, filename):
        return f"{self.prefix}/{day}/{source}/{filename}"

    def write_bytes(self, key, data, content_type):
        if self._bucket is not None:
            self._bucket.blob(key).upload_from_string(data, content_type=content_type)
            where = f"gs://{self.bucket_name}/{key}"
        else:
            target = self.local_dir / key
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            where = str(target)
        sha256 = hashlib.sha256(data).hexdigest()
        self.written.append({"uri": where, "bytes": len(data), "sha256": sha256})
        log.info("Saved %s (%.1f MB)", where, len(data) / 1e6)
        return where

    def write_json_gz(self, key, obj):
        return self.write_bytes(key, gzip.compress(json.dumps(obj).encode()), "application/gzip")

    def write_text(self, key, text, content_type="text/plain"):
        return self.write_bytes(key, text.encode(), content_type)

    def write_csv(self, key, df):
        return self.write_text(key, df.to_csv(index=False), "text/csv")
