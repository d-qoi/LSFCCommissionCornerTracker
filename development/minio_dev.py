from minio import Minio

from cctracker.server.config import config

client = Minio(config.minio_url, access_key=config.minio_access_key, secret_key=config.minio_secret_key, secure=False)
client.list_objects(config.minio_bucket)
