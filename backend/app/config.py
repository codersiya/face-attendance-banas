# """
# Centralized application configuration.
# Reads values from environment variables / .env file.
# """
# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     DATABASE_URL: str = (
#         "postgresql+psycopg2://postgres:preya123@localhost:5432/banas_attendance_db"
#     )
#     ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
#     FACE_MATCH_TOLERANCE: float = 0.45

#     model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

#     @property
#     def allowed_origins_list(self) -> list[str]:
#         return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


# settings = Settings()






















"""
Centralized application configuration.
Reads values from environment variables / .env file.
No secrets are hardcoded as defaults - missing required values fail startup loudly
instead of silently falling back to a real credential.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    FACE_MATCH_TOLERANCE: float = 0.45
    ENVIRONMENT: str = "development"

    # --- Face photo quality / pose thresholds ---
    # Face bounding box area as a fraction of total image area.
    FACE_MIN_AREA_RATIO: float = 0.04   # face too small -> user too far away
    FACE_MAX_AREA_RATIO: float = 0.65   # face too large -> user too close

    # Mean pixel brightness (0-255).
    FACE_MIN_BRIGHTNESS: float = 55
    FACE_MAX_BRIGHTNESS: float = 225

    # Yaw offset = (nose_x - eye_center_x) / interocular_distance.
    # Near 0 = facing camera directly. Larger magnitude = turned more.
    # These are heuristic, tuned for a 30-45 degree turn as instructed in the UI.
    FACE_FRONT_MAX_OFFSET: float = 0.12
    FACE_PROFILE_MIN_OFFSET: float = 0.22

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()