import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from src.core.config import settings
import uuid

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL
        )
        self.bucket = settings.S3_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
            except ClientError as e:
                print(f"Error while creating bucket: {e}")

    async def upload_file(self, file: UploadFile) -> str:
        file_ext = file.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        s3_key = f"{unique_filename}" 

        try:
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket,
                s3_key,
                ExtraArgs={"ContentType": file.content_type}
            )
            return s3_key
        except ClientError as e:
            print(f"Storage Error: {e}")
            raise HTTPException(status_code=500, detail="Storage upload failed")

storage_service = S3Service()