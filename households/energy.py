"""Get local weather and score thermostat settings against comfort ranges."""
from datetime import timedelta
from hashlib import sha256
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from django.core.cache import cache
from django.utils import timezone


class WeatherUnavailable(Exception):
    pass


def _get_weather(url, params):
    try:
        response = requests.get(url, params=params, timeout=(3, 5))
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherUnavailable("Weather is temporarily unavailable. Try again in a moment.") from exc


def find_location(query):
    key = "energy-location:" + sha256(query.casefold().encode()).hexdigest()
    location = cache.get(key)
    if location is not None:
        return location
    data = _get_weather("https://geocoding-api.open-meteo.com/v1/search", {
        "name": query, "count": 1, "language": "en",
    })
    try:
        match = data["results"][0]
        label = ", ".join(dict.fromkeys(
            match[field] for field in ("name", "admin1", "country") if match.get(field)
        ))
        latitude, longitude = float(match["latitude"]), float(match["longitude"])
        if not label or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise WeatherUnavailable("No location found. Try a city and state or country.") from exc
    location = {"label": label, "latitude": latitude, "longitude": longitude}
    cache.set(key, location, 86400)
    return location


def _temperature(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def outdoor_temperatures(location, period):
    latitude, longitude = location["latitude"], location["longitude"]
    key = f"energy-forecast:{latitude}:{longitude}"
    data = cache.get(key)
    if data is None:
        data = _get_weather("https://api.open-meteo.com/v1/forecast", {
            "latitude": latitude, "longitude": longitude,
            "current": "temperature_2m", "hourly": "temperature_2m",
            "temperature_unit": "fahrenheit", "timezone": "auto", "timeformat": "unixtime",
            "forecast_days": 3,
        })
        cache.set(key, data, 600)
    try:
        if period == "day":
            current = data["current"]["temperature_2m"]
            if _temperature(current):
                return [current]
        else:
            local = timezone.now().astimezone(ZoneInfo(data["timezone"]))
            hour = local.replace(minute=0, second=0, microsecond=0)
            if local.hour < 6:
                start = hour
                end = hour.replace(hour=6)
            else:
                start = max(hour, hour.replace(hour=22))
                end = (hour + timedelta(days=1)).replace(hour=6)
            hourly = data["hourly"]
            temperatures = [
                value for timestamp, value in zip(hourly["time"], hourly["temperature_2m"])
                if start.timestamp() <= timestamp < end.timestamp() and _temperature(value)
            ]
            if temperatures:
                return temperatures
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        raise WeatherUnavailable("The weather provider returned incomplete temperature data.") from exc
    raise WeatherUnavailable("No outdoor temperature is available for that time period.")


def recommend_temperature(ranges, outdoors):
    """Favor comfort first, then minimize the average indoor/outdoor gap."""
    def score(temperature):
        misses = [max(low - temperature, temperature - high, 0) for low, high in ranges]
        weather_gap = sum(abs(temperature - outside) for outside in outdoors)
        midpoint_gap = sum(abs(2 * temperature - low - high) for low, high in ranges)
        return max(misses), sum(misses), weather_gap, midpoint_gap

    return min(range(min(low for low, _ in ranges), max(high for _, high in ranges) + 1),
               key=score)
