"""
S3-compatible storage driver — used when STORAGE_BACKEND=s3.

Works against AWS S3 or any S3-compatible provider (MinIO, DigitalOcean
Spaces, etc.) via S3_ENDPOINT_URL. Requires `boto3` (add to
requirements.txt when this backend is actually enabled in an environment).
"""
from app.core.config import get_settings
from app.storage.base_storage import BaseStorage


class S3Storage(BaseStorage):
    def __init__(self):
        import boto3  # imported lazily so `local` deployments don't need boto3 installed

        settings = get_settings()
        self.bucket_name = settings.s3_bucket_name
        self._client = boto3.client(
            "s3",
            region_name=settings.s3_region or None,
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
            endpoint_url=settings.s3_endpoint_url or None,
        )

    async def save(self, key: str, content: bytes) -> str:
        # boto3 is sync; run in a thread so the async event loop isn't blocked.
        import asyncio

        await asyncio.to_thread(self._client.put_object, Bucket=self.bucket_name, Key=key, Body=content)
        return key

    async def delete(self, key: str) -> None:
        import asyncio

        await asyncio.to_thread(self._client.delete_object, Bucket=self.bucket_name, Key=key)

    async def get_url(self, key: str) -> str:
        import asyncio

        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=3600,
        )
