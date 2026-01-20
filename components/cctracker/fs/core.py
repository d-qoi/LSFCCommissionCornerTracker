from fastapi import UploadFile
from cctracker.log import get_logger

import json

from minio import Minio

_log = get_logger(__name__)

_client: Minio | None = None


def setup_minio(
    endpoint: str, access_key: str, secret_key: str, bucket: str | None = None
):
    global _client

    if _client:
        _log.debug("Minio connection established, returning existing client")
        return _client

    _log.info("Setting up Minio client")

    _client = Minio(endpoint, access_key, secret_key=secret_key, secure=False)

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
            },
        ],
    }

    if bucket:
        found = _client.bucket_exists(bucket)
        if not found:
            _log.warning(
                f"{bucket} does not exist, creating and setting read only policy"
            )
            _client.make_bucket(bucket)
            _client.set_bucket_policy(bucket, policy=json.dumps(policy))
            _log.debug("Done")
        else:
            _log.info(f"{bucket} exists.")

    return _client


async def with_bucket():
    return _client


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

