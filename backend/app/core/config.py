from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode
from typing import Any, Annotated

class Settings(BaseSettings):
    APP_NAME: str = "Verificacion de Etiquetas"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # Definimos el tipo como lista y asignamos los valores locales por defecto.
    # NoDecode evita que pydantic-settings intente parsear el valor como JSON
    # antes de ejecutar el validador (causa del SettingsError con CORS_ORIGINS).
    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://localhost:3000"]

    # Este validador toma el string de Railway (separado por comas) y lo convierte en lista
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # En Pydantic v2 se recomienda usar SettingsConfigDict en lugar de class Config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()