from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartSip"
    DATABASE_URL: str = "sqlite:///./data/hydration.db"

    # --- Profil ---
    MIN_ADULT_AGE: int = 18

    # --- Cel bazowy ---
    BASE_ML_PER_KG: float = 35.0
    BASE_DRINK_SHARE: float = 0.8
    BASE_MIN_ML: int = 1500
    BASE_MAX_ML: int = 4000

    SEX_FACTOR_MALE: float = 1.0
    SEX_FACTOR_FEMALE: float = 0.9

    # --- Wiek ---
    AGE_FACTOR_START_AGE: int = 30
    AGE_FACTOR_END_AGE: int = 65
    AGE_FACTOR_DECLINE_PER_YEAR: float = 0.002
    AGE_FACTOR_MIN: float = 0.93

    # --- Pogoda ---
    WEATHER_THRESHOLD_C: float = 20.0  # poniżej brak dodatku
    WEATHER_ML_PER_DEGREE: float = 40.0
    WEATHER_BONUS_MAX_ML: int = 1000

    # --- Aktywność ---
    ACTIVITY_ML_PER_KCAL: float = 0.8
    ACTIVITY_HEAT_PER_DEGREE: float = 0.03
    ACTIVITY_HEAT_MULTIPLIER_MAX: float = 1.5

    # --- Limity bezpieczeństwa ---
    DAILY_TARGET_MAX_ML: int = 5000
    HOURLY_INTAKE_MAX_ML: int = 1000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
