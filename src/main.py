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

    # Calculate average temperature and dew point
    avg_temperature = hourly_dataframe["temperature_2m"].mean()
    avg_dew_point = hourly_dataframe["dew_point_2m"].mean()

    return round(float(avg_temperature), 1), round(float(avg_dew_point), 1)


def get_price_data(city, bedrooms, start_date, end_date, adults):
    cookies = {}
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
                "treatmentFlags": [
                    "stays_search_rehydration_treatment_desktop",
                    "stays_search_rehydration_treatment_moweb",
                    "filter_reordering_2024_price_treatment",
                ],
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
                            "0",
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
                        "filterName": "tab_id",
                        "filterValues": [
                            "home_tab",
                        ],
                    },
                    {
                        "filterName": "update_price_histogram",
                        "filterValues": [
                            "true",
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
        cookies=cookies,
        headers=headers,
        json=json_data,
    )

    data = response.json()["data"]["presentation"]["staysSearch"]["dynamicFilters"][
        "sectionReplacementsByID"
    ][0]["sectionData"]["discreteFilterItems"][0]
    price_histogram = data["priceHistogram"]
    min_value = data["minValue"]
    max_value = data["maxValue"]

    return price_histogram, min_value, max_value


def get_city_price_stats(
    cities,
    bedrooms,
    start_date,
    end_date,
    adults,
    max_price_per_night,
    nth_cheapest,
    bottom_nth_percentile,
    stay_duration,
):
    city_stats = {}
    for i, city in enumerate(cities):
        progress = f"Progress: {i+1}/{len(cities)}"
        sys.stdout.write("\r" + progress)
        sys.stdout.flush()
        price_histogram, min_value, max_value = get_price_data(
            city, bedrooms, start_date, end_date, adults
        )
        min_value /= stay_duration
        max_value /= stay_duration
        num_price_points = len(price_histogram)
        price_step = (max_value - min_value) / (num_price_points - 1)
        price_points = [min_value + i * price_step for i in range(num_price_points)]
        total_count = sum(price_histogram)
        cumulative_count = 0
        median_price = None
        bottom_nth_percentile_price = None
        nth_cheapest_price = None
        filtered_count = 0
        for price, count in zip(price_points, price_histogram):
            cumulative_count += count
            if price <= max_price_per_night:
                filtered_count += count
            if median_price is None and cumulative_count >= total_count / 2:
                median_price = price
            if (
                nth_cheapest_price is None
                and nth_cheapest is not None
                and (cumulative_count >= min(nth_cheapest, total_count))
            ):
                nth_cheapest_price = price
            if (
                bottom_nth_percentile_price is None
                and bottom_nth_percentile is not None
                and cumulative_count >= total_count * (bottom_nth_percentile / 100)
            ):
                bottom_nth_percentile_price = price
        if filtered_count == 0 and config["onlyNonZeroUnits"]:
            continue
        # Get weather data
        temperature, dew_point = get_weather_data(city, start_date, end_date)

        city_stats[city] = {
            "median_price": median_price,
            "nth_cheapest_price": nth_cheapest_price,
            "bottom_nth_percentile_price": bottom_nth_percentile_price,
            "price_histogram": price_histogram,
            "min_value": min_value,
            "max_value": max_value,
            "units": filtered_count,
            "temperature": temperature,
            "dew_point": dew_point,
        }

        if temperature is None or dew_point is None:
            logger.warning(f"Weather data not available for {city}")
    print()
    return city_stats


def getCities():
    cities = json.loads(open(utils.getAbsPath("./../cities.json")).read())
    filtered_cities = {}
    for city, data in cities.items():
        correctRegion = data["region"] == config["region"] or config["region"] == ""
        correctBeaches = (not config["only_hasbeaches"]) or data["hasbeaches"]
        correctSchengen = (not config["only_nonschengen"]) or (not data["inschengen"])
        correctCountry = (
            city.split(",")[1].strip().lower() == config["country"].lower()
        ) or config["country"] == ""
        if correctRegion and correctBeaches and correctSchengen and correctCountry:
            filtered_cities[city] = data
    cities = dict(filtered_cities)
    return cities


def print_city_price_stats(city_price_stats, config):
    max_price_per_night = config["max_price_per_night"]
    nth_cheapest = config["nth_cheapest"]
    bottom_nth_percentile = config["bottom_nth_percentile"]

    # Prepare the table data
    table_data = []
    headers = [
        "City",
        f"#Units < ${max_price_per_night}/night",
        "Median Price",
    ]

    if nth_cheapest is not None:
        headers.append(f"{nth_cheapest}th cheapest")
    if bottom_nth_percentile is not None:
        headers.append(f"Bottom {bottom_nth_percentile}th Percentile")
    if config["show_temp"]:
        headers.append("Temp (°C)")
    if config["show_dew_point"]:
        headers.append("Dew Point (°C)")

    for city, stats in city_price_stats.items():
        row = [
            city,
            stats["units"],
            f"${stats['median_price']:.2f}",
        ]

        if nth_cheapest is not None:
            row.append(f"${stats['nth_cheapest_price']:.2f}")
        if bottom_nth_percentile is not None:
            row.append(f"${stats['bottom_nth_percentile_price']:.2f}")
        if config["show_temp"]:
            row.append(f"{stats['temperature']:.2f}")
        if config["show_dew_point"]:
            row.append(f"{stats['dew_point']:.2f}")

        table_data.append(row)

    # Sort the table data by median price
    table_data.sort(key=lambda row: float(row[2].replace("$", "")), reverse=False)

    # Print the table
    print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))


if __name__ == "__main__":
    cities = getCities()
    bedrooms = config["bedrooms"]
    adults = config["adults"]
    max_price_per_night = config["max_price_per_night"]
    nth_cheapest = config["nth_cheapest"]
    days_from_now = config["days_from_now"]
    stay_duration = config["stay_duration"]
    bottom_nth_percentile = config["bottom_nth_percentile"]

    start_date = (datetime.now() + timedelta(days=days_from_now)).strftime("%Y-%m-%d")
    end_date = (
        datetime.now() + timedelta(days=days_from_now + stay_duration)
    ).strftime("%Y-%m-%d")
    city_price_stats = get_city_price_stats(
        cities,
        bedrooms,
        start_date,
        end_date,
        adults,
        max_price_per_night,
        nth_cheapest,
        bottom_nth_percentile,
        stay_duration,
    )

    print_city_price_stats(city_price_stats, config)
