"""Application settings (Section 5 environment variables)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    UPLOAD_MAX_SIZE_MB: int = 500

    # PostgreSQL
    POSTGRES_USER: str = "ulpin_admin"
    POSTGRES_PASSWORD: str = "ulpin_secure_2024"
    POSTGRES_DB: str = "ulpin_cadastre"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str | None = None

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "ulpin-access-key"
    MINIO_SECRET_KEY: str = "ulpin-secret-key"
    MINIO_BUCKET_RAW: str = "ulpin-raw-uploads"
    MINIO_BUCKET_PROCESSED: str = "ulpin-processed"
    MINIO_SECURE: bool = False

    # Celery / ML
    CELERY_TASK_TIME_LIMIT: int = 3600
    DEVICE: str = "cpu"
    SAM_CHECKPOINT_PATH: str = "/app/models/sam_vit_h.pth"

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
