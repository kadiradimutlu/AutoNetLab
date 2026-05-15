from json import JSONDecodeError, loads

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AutoNetLab Backend API"
    api_prefix: str = "/api/v1"
    environment: str = "development"

    # Comma-separated or JSON-list CORS origins.
    #
    # Examples:
    # CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://139.59.151.126
    # CORS_ORIGINS=["http://localhost:5173","http://139.59.151.126"]
    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    def get_cors_origins(self) -> list[str]:
        raw_value = str(self.cors_origins or "").strip()

        if not raw_value:
            return []

        if raw_value.startswith("["):
            try:
                parsed = loads(raw_value)
            except JSONDecodeError:
                parsed = []

            if isinstance(parsed, list):
                return list(dict.fromkeys(
                    str(item).strip()
                    for item in parsed
                    if str(item).strip()
                ))

        return list(dict.fromkeys(
            item.strip()
            for item in raw_value.split(",")
            if item.strip()
        ))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
