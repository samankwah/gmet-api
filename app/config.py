# """
# Application configuration using Pydantic settings.

# This module contains all configuration settings for the application,
# loaded from environment variables with sensible defaults.
# """

# import secrets
# from typing import List, Optional, Union

# from pydantic import AnyHttpUrl, field_validator, ValidationInfo, ConfigDict
# from pydantic_settings import BaseSettings


# class Settings(BaseSettings):
#     """
#     Application settings loaded from environment variables.

#     All settings can be overridden with environment variables.
#     """

#     # API Configuration
#     API_V1_STR: str = "/api/v1"
#     SECRET_KEY: str = secrets.token_urlsafe(32)
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

#     # Server Configuration
#     SERVER_NAME: str = "GMet Weather API"
#     SERVER_HOST: AnyHttpUrl = "http://localhost"
#     DEBUG: bool = True

#     # CORS Configuration
#     BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
#         "http://localhost:3000",  # React default
#         "http://localhost:8080",  # Vue default
#         "http://localhost:5173",  # Vite default
#     ]

#     @field_validator("BACKEND_CORS_ORIGINS", mode="before")
#     @classmethod
#     def assemble_cors_origins(
#         cls, v: Union[str, List[str]]
#     ) -> Union[List[str], str]:
#         """Parse CORS origins from environment variable."""
#         if isinstance(v, str) and not v.startswith("["):
#             return [i.strip() for i in v.split(",")]
#         elif isinstance(v, (list, str)):
#             return v
#         raise ValueError(v)

#     # Database Configuration
#     POSTGRES_SERVER: str = "localhost"
#     POSTGRES_USER: str = "gmet_user"
#     POSTGRES_PASSWORD: str = "gmet_password"
#     POSTGRES_DB: str = "gmet_weather"
#     POSTGRES_PORT: int = 5432

#     SQLALCHEMY_DATABASE_URI: Optional[str] = None

#     @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
#     @classmethod
#     def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
#         """Assemble database connection string from individual components."""
#         if isinstance(v, str):
#             return v
#         values = info.data
#         db_name = values.get('POSTGRES_DB')

#         # Check if it's a SQLite database (ends with .db)
#         if db_name and db_name.endswith('.db'):
#             return f"sqlite+aiosqlite:///{db_name}"

#         # Otherwise, construct PostgreSQL connection string
#         return (
#             f"postgresql://{values.get('POSTGRES_USER')}:"
#             f"{values.get('POSTGRES_PASSWORD')}@"
#             f"{values.get('POSTGRES_SERVER')}:"
#             f"{values.get('POSTGRES_PORT')}/"
#             f"{db_name}"
#         )

#     # Redis Configuration (Optional)
#     REDIS_HOST: str = "localhost"
#     REDIS_PORT: int = 6379
#     REDIS_PASSWORD: Optional[str] = None
#     REDIS_DB: int = 0

#     # Rate Limiting
#     RATE_LIMIT_REQUESTS: int = 100
#     RATE_LIMIT_WINDOW: int = 60  # seconds

#     # Weather API Configuration (for external data sources)
#     OPENWEATHER_API_KEY: Optional[str] = None
#     WEATHER_DATA_RETENTION_DAYS: int = 365

#     # Logging
#     LOG_LEVEL: str = "INFO"

#     model_config = ConfigDict(
#         env_file=".env",
#         case_sensitive=True,
#     )


# # Create global settings instance
# settings = Settings()


"""
Application configuration using Pydantic settings.

This module contains all configuration settings for the application,
loaded from environment variables with sensible defaults.
"""

import os
import secrets
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, Field, field_validator, ValidationInfo, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden with environment variables.
    """

    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY") or secrets.token_urlsafe(32),
        description="Secret key for JWT encoding. MUST be set via SECRET_KEY environment variable in production!"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Server Configuration
    SERVER_NAME: str = "GMet Weather API"
    SERVER_HOST: AnyHttpUrl = "http://localhost"
    DEBUG: bool = True

    # CORS Configuration
    # Note: Using Union[str, List] to avoid pydantic-settings 2.6+ JSON parsing issues
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:8080,http://localhost:5173"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> List[str]:
        """
        Parse CORS origins from environment variable.

        Supports:
        - Comma-separated string: "http://localhost,http://example.com"
        - Already parsed list: ["http://localhost"]
        - Empty string: returns empty list
        """
        if v is None or v == "":
            return []
        if isinstance(v, str):
            # Comma-separated values
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid CORS origins format: {v}")

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "gmet_user"
    POSTGRES_PASSWORD: str = "gmet_password"
    POSTGRES_DB: str = "gmet_weather"
    POSTGRES_PORT: int = 5432

    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Assemble database connection string from individual components."""
        # Check for explicit SQLALCHEMY_DATABASE_URI first
        if isinstance(v, str) and v:
            return v

        # Check for DATABASE_URL (Render/Railway/Heroku style)
        import os
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # Convert postgres:// to postgresql+asyncpg://
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql+asyncpg://', 1)
            elif database_url.startswith('postgresql://'):
                database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
            return database_url

        values = info.data
        db_name = values.get('POSTGRES_DB')

        # Check if it's a SQLite database (ends with .db)
        if db_name and db_name.endswith('.db'):
            return f"sqlite+aiosqlite:///{db_name}"

        # Otherwise, construct PostgreSQL connection string
        return (
            f"postgresql+asyncpg://{values.get('POSTGRES_USER')}:"
            f"{values.get('POSTGRES_PASSWORD')}@"
            f"{values.get('POSTGRES_SERVER')}:"
            f"{values.get('POSTGRES_PORT')}/"
            f"{db_name}"
        )

    # Redis Configuration (Optional)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Weather API Configuration (for external data sources)
    OPENWEATHER_API_KEY: Optional[str] = None
    WEATHER_DATA_RETENTION_DAYS: int = 365

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


# Create global settings instance
settings = Settings()