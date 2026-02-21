import logging
import uuid

import aioboto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile
from src.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        self.session = aioboto3.Session()
        self.bucket = settings.S3_BUCKET_NAME

        self.s3_config = {
            "service_name": "s3",
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
            "endpoint_url": settings.S3_ENDPOINT_URL,
        }

    async def ensure_bucket_exists(self):
        """Checks if bucket exists, creates it if not."""
        async with self.session.client(**self.s3_config) as s3_client:
            try:
                await s3_client.head_bucket(Bucket=self.bucket)
            except ClientError:
                try:
                    await s3_client.create_bucket(Bucket=self.bucket)
                    logger.info(f"Bucket '{self.bucket}' created successfully.")
                except ClientError as e:
                    logger.error(f"Error while creating bucket: {e}")

    async def upload_file(self, file: UploadFile) -> str:
        file_ext = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        s3_key = unique_filename

        try:
            async with self.session.client(**self.s3_config) as s3_client:
                await s3_client.upload_fileobj(
                    file.file,
                    self.bucket,
                    s3_key,
                    ExtraArgs={"ContentType": file.content_type},
                )

            return s3_key

        except ClientError as e:
            logger.error(f"Storage Error: {e}")
            raise HTTPException(
                status_code=500, detail="Storage upload failed"
            ) from None
        except Exception as e:
            logger.exception(f"Unexpected Error during upload: {e}")
            raise HTTPException(
                status_code=500, detail="Unexpected upload error"
            ) from None

    async def delete_file(self, s3_key: str) -> None:
        """Deletes a file from S3 bucket."""
        try:
            async with self.session.client(**self.s3_config) as s3_client:
                await s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Successfully deleted {s3_key} from S3.")

        except ClientError as e:
            logger.error(f"Storage Deletion Error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected Deletion Error: {e}")

    async def stream_file(self, s3_key: str):
        async with self.session.client(**self.s3_config) as s3_client:
            try:
                response = await s3_client.get_object(Bucket=self.bucket, Key=s3_key)

                async for chunk in response["Body"]:
                    yield chunk

            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.warning(f"File not found on S3: {s3_key}")
                else:
                    logger.error(f"Storage Streaming Error: {e}")


storage_service = S3Service()
