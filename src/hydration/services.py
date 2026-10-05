import datetime

from src.core.config import settings
from src.users.models import Gender, Profile


def calculate_age(birth_date: datetime.date, today: datetime.date | None = None) -> int:
    today = today or datetime.date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def age_factor(age: int) -> float:
    """1.0 do START_AGE, potem liniowy spadek do END_AGE, dalej bez zmian."""
    years = _clamp(
        age - settings.AGE_FACTOR_START_AGE,
        0,
        settings.AGE_FACTOR_END_AGE - settings.AGE_FACTOR_START_AGE,
    )
    return 1.0 - settings.AGE_FACTOR_DECLINE_PER_YEAR * years


def calculate_base_target_ml(profile: Profile) -> int:
    """Wylicza bazowe dzienne zapotrzebowanie w ml."""
    age = calculate_age(profile.birth_date)
    if age < settings.MIN_ADULT_AGE:
        raise ValueError("Aplikacja przewidziana dla dorosłych")

    sex_factor = (
        settings.SEX_FACTOR_MALE if profile.gender == Gender.MALE else settings.SEX_FACTOR_FEMALE
    )

    base = (
        profile.weight_kg
        * settings.BASE_ML_PER_KG
        * sex_factor
        * age_factor(age)
        * settings.BASE_DRINK_SHARE
    )
    return round(_clamp(base, settings.BASE_MIN_ML, settings.BASE_MAX_ML))


def calculate_effective_ml(volume_ml: float, hydration_factor: float) -> float:
    """Fizyczna objętość -> realne nawodnienie."""
    return volume_ml * hydration_factor


def calculate_weather_bonus_ml(apparent_temp_c: float) -> int:
    bonus = settings.WEATHER_ML_PER_DEGREE * max(
        0.0, apparent_temp_c - settings.WEATHER_THRESHOLD_C
    )
    return round(_clamp(bonus, 0, settings.WEATHER_BONUS_MAX_ML))


def calculate_activity_bonus_ml(active_kcal: float, apparent_temp_c: float) -> int:
    heat_multiplier = _clamp(
        1.0
        + settings.ACTIVITY_HEAT_PER_DEGREE
        * max(0.0, apparent_temp_c - settings.WEATHER_THRESHOLD_C),
        1.0,
        settings.ACTIVITY_HEAT_MULTIPLIER_MAX,
    )
    return round(active_kcal * settings.ACTIVITY_ML_PER_KCAL * heat_multiplier)


def calculate_total_target_ml(profile: Profile, apparent_temp_c: float, active_kcal: float) -> int:
    total = (
        calculate_base_target_ml(profile)
        + calculate_weather_bonus_ml(apparent_temp_c)
        + calculate_activity_bonus_ml(active_kcal, apparent_temp_c)
    )
    return min(total, settings.DAILY_TARGET_MAX_ML)
