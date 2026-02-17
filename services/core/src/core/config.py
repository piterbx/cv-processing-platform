import os
from pydantic_settings import BaseSettings

current_file_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_file_dir, "../../../../.env")
print(env_path)

class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    S3_BUCKET_NAME: str
    S3_ENDPOINT_URL: str # for MinIO

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file=env_path
        env_file_encoding='utf-8'
        env_ignore_empty=True
        extra='ignore'

settings = Settings()