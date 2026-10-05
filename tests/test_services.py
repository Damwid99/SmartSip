import datetime

from src.core.config import settings
from src.hydration.services import (
    calculate_activity_bonus_ml,
    calculate_age,
    calculate_effective_ml,
    calculate_weather_bonus_ml,
)


def test_calculate_age():
    birth_date = datetime.date(1990, 5, 20)
    assert calculate_age(birth_date, today=datetime.date(2023, 5, 19)) == 32
    assert calculate_age(birth_date, today=datetime.date(2023, 5, 21)) == 33


def test_calculate_effective_ml():
    assert calculate_effective_ml(500, 1.0) == 500.0
    assert calculate_effective_ml(250, 0.8) == 200.0


def test_weather_bonus():
    assert calculate_weather_bonus_ml(15.0) == 0

    bonus = calculate_weather_bonus_ml(settings.WEATHER_THRESHOLD_C + 5.0)
    assert bonus == int(5.0 * settings.WEATHER_ML_PER_DEGREE)


def test_activity_bonus():
    assert calculate_activity_bonus_ml(500, 20.0) == int(500 * settings.ACTIVITY_ML_PER_KCAL)
