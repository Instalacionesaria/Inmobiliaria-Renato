import os
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    webhook_secret: str | None = None
    highlevel_api_token: str | None = None
    highlevel_location_id: str | None = None
    highlevel_api_base_url: str = "https://services.leadconnectorhq.com"
    highlevel_api_version: str = "2021-04-15"
    google_service_account_file: str | None = None
    sheet_id: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: str = "5432"
    db_name: str = "postgres"
    admin_username: str | None = None
    admin_password: str | None = None
    admin_jwt_secret: str | None = None
    admin_jwt_ttl_hours: int = 24
    cors_allowed_origins: list[str] = []
    log_level: str = "INFO"

    @property
    def database_url(self) -> str | None:
        if not (self.db_user and self.db_password and self.db_host):
            return None
        return (
            f"postgresql://{self.db_user}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurado en el entorno")

    return Settings(
        openai_api_key=api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        webhook_secret=os.getenv("HIGHLEVEL_WEBHOOK_SECRET"),
        highlevel_api_token=os.getenv("HIGHLEVEL_API_TOKEN"),
        highlevel_location_id=os.getenv("LOCATION_ID"),
        google_service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
        sheet_id=os.getenv("SHEET_ID"),
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        db_host=os.getenv("DB_HOST"),
        db_port=os.getenv("DB_PORT", "5432"),
        db_name=os.getenv("DB_NAME", "postgres"),
        admin_username=os.getenv("ADMIN_USERNAME"),
        admin_password=os.getenv("ADMIN_PASSWORD"),
        admin_jwt_secret=os.getenv("ADMIN_JWT_SECRET"),
        admin_jwt_ttl_hours=int(os.getenv("ADMIN_JWT_TTL_HOURS", "24")),
        cors_allowed_origins=_split_csv(os.getenv("CORS_ALLOWED_ORIGINS", "")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]
