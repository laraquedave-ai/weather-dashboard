"""
Weather API Client
A Python client for fetching weather data from OpenWeatherMap API
"""

import requests
import json
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass
class WeatherData:
    """Data class for weather information"""
    city: str
    country: str
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    humidity: int
    weather: str
    description: str
    wind_speed: float
    wind_deg: int
    clouds: int
    timestamp: int

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'city': self.city,
            'country': self.country,
            'temperature': self.temperature,
            'feels_like': self.feels_like,
            'temp_min': self.temp_min,
            'temp_max': self.temp_max,
            'pressure': self.pressure,
            'humidity': self.humidity,
            'weather': self.weather,
            'description': self.description,
            'wind_speed': self.wind_speed,
            'wind_deg': self.wind_deg,
            'clouds': self.clouds,
            'timestamp': self.timestamp
        }


class WeatherClient:
    """Client for fetching weather data from OpenWeatherMap API"""

    BASE_URL = "https://api.openweathermap.org/data/2.5"
    CACHE_DIR = Path.home() / ".weather_cache"

    def __init__(self, api_key: Optional[str] = None, units: str = "metric"):
        """
        Initialize weather client

        Args:
            api_key: OpenWeatherMap API key (or set WEATHER_API_KEY env var)
            units: Temperature units - "metric" (Celsius) or "imperial" (Fahrenheit)
        """
        self.api_key = api_key or os.getenv("WEATHER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key not provided. Set WEATHER_API_KEY environment variable "
                "or pass api_key parameter"
            )
        self.units = units
        self.session = requests.Session()
        self.cache_dir = self.CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, city: str) -> Path:
        """Get cache file path for a city"""
        return self.cache_dir / f"{city.lower()}_weather.json"

    def _save_to_cache(self, city: str, data: Dict) -> None:
        """Save weather data to cache"""
        try:
            cache_path = self._get_cache_path(city)
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Warning: Could not save to cache: {e}")

    def _load_from_cache(self, city: str) -> Optional[Dict]:
        """Load weather data from cache"""
        try:
            cache_path = self._get_cache_path(city)
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load from cache: {e}")
        return None

    def get_current_weather(self, city: str, use_cache: bool = True) -> Optional[WeatherData]:
        """
        Get current weather for a city

        Args:
            city: City name
            use_cache: Use cached data if available

        Returns:
            WeatherData object or None if request fails
        """
        try:
            params = {
                "q": city,
                "appid": self.api_key,
                "units": self.units
            }

            response = self.session.get(
                f"{self.BASE_URL}/weather",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            self._save_to_cache(city, data)

            return self._parse_weather_data(data)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather for {city}: {e}")
            if use_cache:
                cached_data = self._load_from_cache(city)
                if cached_data:
                    print(f"Using cached data for {city}")
                    return self._parse_weather_data(cached_data)
            return None

    def get_forecast(self, city: str, days: int = 5) -> Optional[List[WeatherData]]:
        """
        Get weather forecast for a city

        Args:
            city: City name
            days: Number of days to forecast (1-5 for free tier)

        Returns:
            List of WeatherData objects or None if request fails
        """
        try:
            params = {
                "q": city,
                "appid": self.api_key,
                "units": self.units,
                "cnt": min(days * 8, 40)  # API returns data in 3-hour intervals
            }

            response = self.session.get(
                f"{self.BASE_URL}/forecast",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            forecasts = [self._parse_forecast_item(item) for item in data.get("list", [])]
            return forecasts

        except requests.exceptions.RequestException as e:
            print(f"Error fetching forecast for {city}: {e}")
            return None

    def get_weather_by_coordinates(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherData]:
        """
        Get current weather by latitude and longitude

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            WeatherData object or None if request fails
        """
        try:
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "units": self.units
            }

            response = self.session.get(
                f"{self.BASE_URL}/weather",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            return self._parse_weather_data(data)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather for coordinates ({latitude}, {longitude}): {e}")
            return None

    def get_weather_multiple_cities(self, cities: List[str]) -> Dict[str, Optional[WeatherData]]:
        """
        Get weather for multiple cities

        Args:
            cities: List of city names

        Returns:
            Dictionary with city names as keys and WeatherData objects as values
        """
        results = {}
        for city in cities:
            results[city] = self.get_current_weather(city)
        return results

    def _parse_weather_data(self, data: Dict) -> WeatherData:
        """Parse API response into WeatherData object"""
        return WeatherData(
            city=data['name'],
            country=data['sys']['country'],
            temperature=data['main']['temp'],
            feels_like=data['main']['feels_like'],
            temp_min=data['main']['temp_min'],
            temp_max=data['main']['temp_max'],
            pressure=data['main']['pressure'],
            humidity=data['main']['humidity'],
            weather=data['weather'][0]['main'],
            description=data['weather'][0]['description'],
            wind_speed=data['wind']['speed'],
            wind_deg=data['wind'].get('deg', 0),
            clouds=data['clouds']['all'],
            timestamp=data['dt']
        )

    def _parse_forecast_item(self, item: Dict) -> WeatherData:
        """Parse forecast item into WeatherData object"""
        return WeatherData(
            city=item.get('name', 'Unknown'),
            country=item.get('sys', {}).get('country', 'Unknown'),
            temperature=item['main']['temp'],
            feels_like=item['main']['feels_like'],
            temp_min=item['main']['temp_min'],
            temp_max=item['main']['temp_max'],
            pressure=item['main']['pressure'],
            humidity=item['main']['humidity'],
            weather=item['weather'][0]['main'],
            description=item['weather'][0]['description'],
            wind_speed=item['wind']['speed'],
            wind_deg=item['wind'].get('deg', 0),
            clouds=item['clouds']['all'],
            timestamp=item['dt']
        )

    def clear_cache(self, city: Optional[str] = None) -> None:
        """
        Clear cache files

        Args:
            city: Specific city to clear, or None to clear all
        """
        try:
            if city:
                cache_path = self._get_cache_path(city)
                if cache_path.exists():
                    cache_path.unlink()
                    print(f"Cleared cache for {city}")
            else:
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
                print("Cleared all cache files")
        except Exception as e:
            print(f"Error clearing cache: {e}")

    def close(self) -> None:
        """Close the session"""
        self.session.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Example usage
if __name__ == "__main__":
    # Set your API key or use environment variable
    # Get a free API key from: https://openweathermap.org/api

    try:
        # Using context manager (recommended)
        with WeatherClient() as client:
            # Get current weather
            print("=== Current Weather ===")
            weather = client.get_current_weather("London")
            if weather:
                print(f"City: {weather.city}, {weather.country}")
                print(f"Temperature: {weather.temperature}°C (feels like {weather.feels_like}°C)")
                print(f"Weather: {weather.description}")
                print(f"Humidity: {weather.humidity}%")
                print(f"Wind Speed: {weather.wind_speed} m/s")
                print()

            # Get forecast
            print("=== 5-Day Forecast ===")
            forecast = client.get_forecast("London", days=5)
            if forecast:
                for i, item in enumerate(forecast[:5]):
                    dt = datetime.fromtimestamp(item.timestamp)
                    print(f"{i+1}. {dt.strftime('%Y-%m-%d %H:%M')} - "
                          f"{item.temperature}°C, {item.description}")
                print()

            # Get weather by coordinates
            print("=== Weather by Coordinates (New York) ===")
            weather = client.get_weather_by_coordinates(40.7128, -74.0060)
            if weather:
                print(f"City: {weather.city}")
                print(f"Temperature: {weather.temperature}°C")
                print()

            # Get weather for multiple cities
            print("=== Multiple Cities ===")
            cities = ["Paris", "Tokyo", "Sydney"]
            results = client.get_weather_multiple_cities(cities)
            for city, weather_data in results.items():
                if weather_data:
                    print(f"{city}: {weather_data.temperature}°C - {weather_data.description}")

    except ValueError as e:
        print(f"Error: {e}")
        print("Please set the WEATHER_API_KEY environment variable or pass api_key parameter")
