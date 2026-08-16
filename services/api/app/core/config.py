from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")
    qdrant_url: str = Field(..., alias="QDRANT_URL")

    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_expires_minutes: int = Field(10080, alias="JWT_EXPIRES_MINUTES")
    google_client_id: str | None = Field(None, alias="GOOGLE_CLIENT_ID")

    twilio_account_sid: str | None = Field(None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(None, alias="TWILIO_AUTH_TOKEN")
    twilio_verify_service_sid: str | None = Field(None, alias="TWILIO_VERIFY_SERVICE_SID")
    twilio_from_number: str | None = Field(None, alias="TWILIO_FROM_NUMBER")

    weather_provider: str = Field("openweather", alias="WEATHER_PROVIDER")
    openweather_api_key: str | None = Field(None, alias="OPENWEATHER_API_KEY")
    tomorrow_api_key: str | None = Field(None, alias="TOMORROW_API_KEY")
    weatherapi_key: str | None = Field(None, alias="WEATHERAPI_KEY")
    sentinelhub_client_id: str | None = Field(None, alias="SENTINELHUB_CLIENT_ID")
    sentinelhub_client_secret: str | None = Field(None, alias="SENTINELHUB_CLIENT_SECRET")

    s3_bucket: str = Field(..., alias="S3_BUCKET")
    s3_region: str = Field("us-east-1", alias="S3_REGION")
    s3_endpoint_url: AnyHttpUrl | None = Field(None, alias="S3_ENDPOINT_URL")
    s3_access_key_id: str = Field(..., alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(..., alias="S3_SECRET_ACCESS_KEY")
    s3_public_base_url: AnyHttpUrl | None = Field(None, alias="S3_PUBLIC_BASE_URL")

    disease_model_path: str | None = Field(None, alias="DISEASE_MODEL_PATH")
    disease_model_type: str = Field("yolo", alias="DISEASE_MODEL_TYPE")
    yield_model_path: str | None = Field(None, alias="YIELD_MODEL_PATH")

    firebase_credentials_json: str | None = Field(None, alias="FIREBASE_CREDENTIALS_JSON")
    smtp_host: str | None = Field(None, alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_username: str | None = Field(None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(None, alias="SMTP_PASSWORD")
    smtp_from: str | None = Field(None, alias="SMTP_FROM")
    cors_origins: str = Field("http://localhost:3000", alias="CORS_ORIGINS")

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
