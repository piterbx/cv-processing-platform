import logging
from collections.abc import AsyncGenerator
from typing import BinaryIO

import aioboto3
from botocore.exceptions import ClientError

from common.config import BaseAppSettings
from common.exceptions import S3DownloadError, S3UploadError

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self, settings: BaseAppSettings):
        self.session = aioboto3.Session()
        self.bucket = settings.S3_BUCKET_NAME

        self.s3_config = {
            "service_name": "s3",
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
            "endpoint_url": settings.S3_ENDPOINT_URL,
        }

    async def check_bucket_exists(self) -> None:
        """Checks if bucket exists. Fails if it doesn't."""
        async with self.session.client(**self.s3_config) as s3_client:
            await s3_client.head_bucket(Bucket=self.bucket)

    async def upload_file(
        self, file_obj: BinaryIO, s3_key: str, content_type: str
    ) -> str:
        try:
            async with self.session.client(**self.s3_config) as s3_client:
                await s3_client.upload_fileobj(
                    file_obj,
                    self.bucket,
                    s3_key,
                    ExtraArgs={"ContentType": content_type},
                )
            return s3_key
        except Exception as e:
            logger.error(f"Storage Error during upload: {e}")
            raise S3UploadError(s3_key=s3_key, original_error=e) from e

    async def download_file(self, s3_key: str, destination_path: str) -> None:
        try:
            async with self.session.client(**self.s3_config) as s3_client:
                await s3_client.download_file(self.bucket, s3_key, destination_path)
            logger.info(f"Successfully downloaded {s3_key} to {destination_path}")
        except Exception as e:
            logger.error(f"Storage Error during download: {e}")
            raise S3DownloadError(s3_key=s3_key, original_error=e) from e

    async def delete_file(self, s3_key: str) -> None:
        try:
            async with self.session.client(**self.s3_config) as s3_client:
                await s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Successfully deleted {s3_key} from S3.")
        except Exception as e:
            logger.exception(f"Unexpected Deletion Error for {s3_key}: {e}")
            raise

    async def stream_file(self, s3_key: str) -> AsyncGenerator[bytes, None]:
        async with self.session.client(**self.s3_config) as s3_client:
            try:
                response = await s3_client.get_object(Bucket=self.bucket, Key=s3_key)
                async for chunk in response["Body"]:
                    yield chunk
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.warning(f"File not found on S3: {s3_key}")
                    raise S3DownloadError(s3_key=s3_key, original_error=e) from e
                else:
                    logger.error(f"Storage Streaming ClientError: {e}")
                    raise S3DownloadError(s3_key=s3_key, original_error=e) from e
            except Exception as e:
                logger.error(f"Unexpected Storage Streaming Error: {e}")
                raise S3DownloadError(s3_key=s3_key, original_error=e) from e
