from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "EmergencyIQ"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str
    SECRET_KEY: str

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MAX_UPLOAD_SIZE_MB: int = 50

    # Store as raw strings from .env
    ALLOWED_AUDIO_EXTENSIONS: str = "wav,mp3,m4a,ogg"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    AUDIO_EVENT_DETECTOR_BACKEND: str = "lightweight_fallback"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:0.5b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_audio_extensions(self):
        return [
            ext if ext.startswith(".") else f".{ext}"
            for ext in self.ALLOWED_AUDIO_EXTENSIONS.split(",")
            if ext.strip()
        ]

    @property
    def allowed_origins(self):
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()