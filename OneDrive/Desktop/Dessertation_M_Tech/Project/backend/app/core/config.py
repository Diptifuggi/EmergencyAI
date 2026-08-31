from __future__ import annotations

from pathlib import Path
from typing import List, Any

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = 'EmergencyIQ'
    ENVIRONMENT: str = 'development'

    DATABASE_URL: str
    SECRET_KEY: str

    ALGORITHM: str = 'HS256'

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MAX_UPLOAD_SIZE_MB: int = 50

    # Store allowed audio extensions as a raw string in env to avoid pydantic dotenv parsing issues;
    # we'll normalize to a list after loading Settings.
    ALLOWED_AUDIO_EXTENSIONS: str = '.wav,.mp3,.m4a,.mp4,.ogg,.aac,.webm'

    # Store allowed origins as a raw string in env and normalize to a list at runtime.
    ALLOWED_ORIGINS: str = 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://10.0.2.2:8000'

    AUDIO_EVENT_DETECTOR_BACKEND: str = 'lightweight_fallback'

    OLLAMA_BASE_URL: str = 'http://localhost:11434'

    OLLAMA_MODEL: str = 'qwen2.5:0.5b'
    OLLAMA_DECODING_MODEL: str = 'qwen2.5:0.5b'
    OLLAMA_ENCODING_MODEL: str = 'kimi'

    # Optional local geospatial enrichment. Never use a public runtime service.
    NOMINATIM_URL: str = 'http://localhost:8080'
    NOMINATIM_TIMEOUT_SECONDS: float = 2.0
    NOMINATIM_COUNTRY_CODE: str = 'in'
    MAP_TILE_URL: str = 'http://localhost:8081/tiles/{z}/{x}/{y}.png'

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )


settings = Settings()

# Normalize raw comma-separated or JSON array strings into a list.
def _normalize_string_list(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        v_strip = raw.strip()
        if v_strip.startswith('[') and v_strip.endswith(']'):
            try:
                import json

                parsed = json.loads(v_strip)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                pass
        return [p.strip() for p in raw.split(',') if p.strip()]
    return []

settings.ALLOWED_AUDIO_EXTENSIONS = _normalize_string_list(settings.ALLOWED_AUDIO_EXTENSIONS)
settings.ALLOWED_ORIGINS = _normalize_string_list(settings.ALLOWED_ORIGINS)
