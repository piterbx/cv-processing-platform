class StorageError(Exception):
    """Base class for all storage-related errors in the platform."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error

    def __str__(self) -> str:
        base_msg = self.message
        if self.original_error:
            base_msg += f" | Cause: {str(self.original_error)}"
        return base_msg


class S3UploadError(StorageError):
    """Raised when uploading a file to S3 fails."""

    def __init__(self, s3_key: str, original_error: Exception | None = None):
        super().__init__(f"Failed to upload file to S3. Key: {s3_key}", original_error)


class S3DownloadError(StorageError):
    """Raised when downloading a file from S3 fails."""

    def __init__(self, s3_key: str, original_error: Exception | None = None):
        super().__init__(
            f"Failed to download file from S3. Key: {s3_key}", original_error
        )
