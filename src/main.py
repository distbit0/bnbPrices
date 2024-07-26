import pysnooper
from tabulate import tabulate
import utils
from utils import logger as logger
import requests
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
import openmeteo_requests
import requests_cache
from retry_requests import retry
from geopy.geocoders import Nominatim
import sys
import pandas as pd
from dataclasses import dataclass
import concurrent.futures
import time
import geopy

load_dotenv()

# Load configuration
currentDir = os.path.dirname(__file__)
jsonFile = os.path.join(currentDir, "../config.json")
with open(jsonFile, "r") as config_file:
    config = json.load(config_file)


def get_weather_data(city, start_date, end_date):
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Get coordinates for the city
    geolocator = Nominatim(user_agent="weather_app")
    location = geolocator.geocode(city)
    if not location:
        raise ValueError(f"Could not find coordinates for {city}")

    # Convert start_date and end_date to datetime objects
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    # Adjust dates to previous year
    start_date = start_date.replace(year=start_date.year - 1)
    end_date = end_date.replace(year=end_date.year - 1)

    # Set up API parameters
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "hourly": ["temperature_2m", "dew_point_2m"],
        "timezone": "auto",
    }

    # Make API request
    responses = openmeteo.weather_api(url, params=params)

    # Process first location
    response = responses[0]

    # Process hourly data
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_dew_point_2m = hourly.Variables(1).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }
    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["dew_point_2m"] = hourly_dew_point_2m

    hourly_dataframe = pd.DataFrame(data=hourly_data)

    # Group by date and calculate the maximum temperature for each day
    daily_max_temp = hourly_dataframe.groupby(hourly_dataframe["date"].dt.date)[
        "temperature_2m"
    ].max()

    # Calculate the average of daily maximum temperatures
    avg_max_temperature = daily_max_temp.mean()

    # Calculate average dew point (unchanged)
    avg_dew_point = hourly_dataframe["dew_point_2m"].mean()

    return round(float(avg_max_temperature), 1), round(float(avg_dew_point), 1)


def get_price_data(city, bedrooms, start_date, end_date, adults, max_price):
    apiKey = os.getenv("AIRBNB_API_KEY")
    headers = {
        "x-airbnb-api-key": apiKey,
    }
    params = {
        "operationName": "DynamicFilters",
        "locale": "en",
        "currency": "AUD",
    }
    json_data = {
        "operationName": "DynamicFilters",
        "variables": {
            "staysSearchRequest": {
                "metadataOnly": True,
                "treatmentFlags": [],
                "rawParams": [
                    {
                        "filterName": "adults",
                        "filterValues": [
                            str(adults),
                        ],
                    },
                    {
                        "filterName": "channel",
                        "filterValues": [
                            "EXPLORE",
                        ],
                    },
                    {
                        "filterName": "checkin",
                        "filterValues": [
                            start_date,
                        ],
                    },
                    {
                        "filterName": "checkout",
                        "filterValues": [
                            end_date,
                        ],
                    },
                    {
                        "filterName": "date_picker_type",
                        "filterValues": [
                            "calendar",
                        ],
                    },
                    {
                        "filterName": "location",
                        "filterValues": [
                            city,
                        ],
                    },
                    {
                        "filterName": "min_bedrooms",
                        "filterValues": [
                            str(bedrooms),
                        ],
                    },
                    {
                        "filterName": "min_beds",
                        "filterValues": [
                            str(bedrooms),
                        ],
                    },
                    {
                        "filterName": "price_filter_input_type",
                        "filterValues": [
                            "2",
                        ],
                    },
                    {
                        "filterName": "price_filter_num_nights",
                        "filterValues": [
                            str(
                                (
                                    datetime.strptime(end_date, "%Y-%m-%d")
                                    - datetime.strptime(start_date, "%Y-%m-%d")
                                ).days
                            ),
                        ],
                    },
                    {
                        "filterName": "query",
                        "filterValues": [
                            city,
                        ],
                    },
                    {
                        "filterName": "refinement_paths",
                        "filterValues": [
                            "/homes",
                        ],
                    },
                    {
                        "filterName": "room_types",
                        "filterValues": [
                            "Entire home/apt",
                        ],
                    },
                    {
                        "filterName": "search_mode",
                        "filterValues": [
                            "regular_search",
                        ],
                    },
                    {
                        "filterName": "search_type",
                        "filterValues": [
                            "filter_change",
                        ],
                    },
                    {
                        "filterName": "price_max",
                        "filterValues": [str(max_price)],
                    },
                    {
                        "filterName": "tab_id",
                        "filterValues": [
                            "home_tab",
                        ],
                    },
                ],
                "requestedPageType": "STAYS_SEARCH",
            },
            "isStaysSearch": True,
            "isExperiencesSearch": False,
            "isLeanTreatment": False,
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "d41301236ac7e50af23ebb44389773d88e24bc33ad7b88054e5bcb2533a17769",
            },
        },
    }
    response = requests.post(
        "https://www.airbnb.com.au/api/v3/DynamicFilters/d41301236ac7e50af23ebb44389773d88e24bc33ad7b88054e5bcb2533a17769",
        params=params,
        headers=headers,
        json=json_data,
    )
    unitCountText = response.json()["data"]["presentation"]["staysSearch"][
        "dynamicFilters"
    ]["searchButtonText"]
    unitCount = 0
    if unitCountText != "No homes available":
        unitCount = int(unitCountText.split()[1].replace(",", "").replace("+", ""))
    return unitCount


@dataclass
class CitySearchParams:
    bedrooms: int
    start_date: str
    end_date: str
    adults: int
    max_price_per_night: float
    stay_duration: int


def get_weather_data_with_retry(city, params, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return get_weather_data(city, params.start_date, params.end_date)
        except (
            geopy.exc.GeocoderRateLimited
        ):  # Assume this exception is raised when rate limited
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                logger.warning(
                    f"Weather data not available for {city} due to rate limiting"
                )
                return None, None
        except Exception as e:
            logger.error(f"Error fetching weather data for {city}: {str(e)}")
            return None, None


def process_city(city, params, weather_data):
    unitCount = get_price_data(
        city,
        params.bedrooms,
        params.start_date,
        params.end_date,
        params.adults,
        params.max_price_per_night * params.stay_duration,
    )

    if unitCount == 0 and config["onlyNonZeroUnits"]:
        return None

    temperature, dew_point = weather_data.get(city, (None, None))
    if temperature is None or dew_point is None:
        logger.warning(f"Weather data not available for {city}")

    return (
        city,
        {
            "units": unitCount,
            "temperature": temperature,
            "dew_point": dew_point,
        },
    )


def get_city_info(cities, params):
    # Fetch weather data sequentially with rate limiting
    weather_data = {}
    for city in cities:
        sys.stdout.write(
            f"\rFetching weather data: {len(weather_data)+1}/{len(cities)}"
        )
        sys.stdout.flush()
        temperature, dew_point = get_weather_data_with_retry(city, params)
        weather_data[city] = (temperature, dew_point)
        time.sleep(0.1)
    print()

    city_stats = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(process_city, city, params, weather_data) for city in cities
        ]
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            sys.stdout.write(f"\rProcessing cities: {i}/{len(cities)}")
            sys.stdout.flush()
            result = future.result()
            if result:
                city, stats = result
                city_stats[city] = stats
    print()
    return city_stats


def getCities():
    cities = json.loads(open(utils.getAbsPath("./../cities.json")).read())
    filtered_cities = {}
    for city, data in cities.items():
        correctRegion = data["region"] in config["regions"] or config["regions"] == []
        correctBeaches = (not config["only_hasbeaches"]) or data["hasbeaches"]
        correctSchengen = (not config["only_nonschengen"]) or (not data["inschengen"])
        correctCountry = (
            city.split(",")[-1].strip().lower() == config["country"].lower()
        ) or config["country"] == ""
        if correctRegion and correctBeaches and correctSchengen and correctCountry:
            filtered_cities[city] = data
    cities = dict(filtered_cities)
    return cities


def print_city_price_stats(city_info, config):
    max_price_per_night = config["max_price_per_night"]
    # Prepare the table data
    table_data = []
    headers = [
        "City",
        f"#Units < ${max_price_per_night}/night",
    ]

    if config["show_temp"]:
        headers.append("Avg Max Daily Temp (°C)")
    if config["show_dew_point"]:
        headers.append("Dew Point (°C)")

    for city, stats in city_info.items():
        dewPointTooLow = (
            config["max_dew_point"]
            and float(stats["dew_point"]) > config["max_dew_point"]
        )
        tempTooLow = (
            config["min_temperature"]
            and float(stats["temperature"]) < config["min_temperature"]
        )
        tempTooHigh = (
            config["max_temperature"]
            and float(stats["temperature"]) > config["max_temperature"]
        )
        if dewPointTooLow or tempTooLow or tempTooHigh:
            continue
        row = [
            city,
            stats["units"],
        ]
        if config["show_temp"]:
            row.append(f"{stats['temperature']:.2f}")
        if config["show_dew_point"]:
            row.append(f"{stats['dew_point']:.2f}")

        table_data.append(row)

    # Sort the table data by median price
    table_data.sort(key=lambda row: row[1], reverse=True)

    # Print the table
    print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))


if __name__ == "__main__":
    cities = getCities()
    bedrooms = config["bedrooms"]
    adults = config["adults"]
    max_price_per_night = config["max_price_per_night"]
    days_from_now = config["days_from_now"]
    stay_duration = config["stay_duration"]

    start_date = (datetime.now() + timedelta(days=days_from_now)).strftime("%Y-%m-%d")
    end_date = (
        datetime.now() + timedelta(days=days_from_now + stay_duration)
    ).strftime("%Y-%m-%d")
    params = CitySearchParams(
        bedrooms=bedrooms,
        start_date=start_date,
        end_date=end_date,
        adults=adults,
        max_price_per_night=max_price_per_night,
        stay_duration=stay_duration,
    )

    city_info = get_city_info(cities, params)

    print_city_price_stats(city_info, config)
