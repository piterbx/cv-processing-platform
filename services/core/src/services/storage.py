from src.core.config import settings

from common.services.storage import S3Service

storage_service = S3Service(settings)
