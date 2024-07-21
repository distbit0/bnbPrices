import pysnooper
import utils
from utils import logger as logger
import requests
from datetime import datetime, timedelta
from datetime import datetime
import os
import json
from dotenv import load_dotenv


load_dotenv()

# Load configuration
currentDir = os.path.dirname(__file__)
jsonFile = os.path.join(currentDir, "../config.json")
with open(jsonFile, "r") as config_file:
    config = json.load(config_file)


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
        "https://www.airbnb.com/api/v3/DynamicFilters/d41301236ac7e50af23ebb44389773d88e24bc33ad7b88054e5bcb2533a17769",
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
):
    city_stats = {}
    for city in cities:
        price_histogram, min_value, max_value = get_price_data(
            city, bedrooms, start_date, end_date, adults
        )
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
            if nth_cheapest_price is None and (
                cumulative_count >= min(nth_cheapest, total_count)
            ):
                nth_cheapest_price = price
            if (
                bottom_nth_percentile_price is None
                and cumulative_count >= total_count * (bottom_nth_percentile / 100)
            ):
                bottom_nth_percentile_price = price
        city_stats[city] = {
            "median_price": median_price,
            "nth_cheapest_price": nth_cheapest_price,
            "bottom_nth_percentile_price": bottom_nth_percentile_price,
            "price_histogram": price_histogram,
            "min_value": min_value,
            "max_value": max_value,
            "units": filtered_count,
        }
    return city_stats


def print_price_histogram(city, price_histogram, min_value, max_value, median_price):
    if not config["print_histograms"]:
        return
    num_price_points = len(price_histogram)
    price_step = (max_value - min_value) / (num_price_points - 1)
    price_points = [min_value + i * price_step for i in range(num_price_points)]
    median_index = int((median_price - min_value) / price_step)

    # Expand the range to cover twice as many price points
    start_index = max(0, median_index - 20)
    end_index = min(num_price_points, median_index + 21)

    # Combine every two price points to keep the number of rows similar
    condensed_histogram = [
        sum(price_histogram[i : i + 2]) for i in range(start_index, end_index, 2)
    ]
    condensed_price_points = [price_points[i] for i in range(start_index, end_index, 2)]

    max_count = max(condensed_histogram)
    histogram_width = 50
    print(f"\nPrice Distribution for {city} (Median Price: ${median_price:.2f}):")
    for i, price in enumerate(condensed_price_points):
        lower_price = price
        upper_price = lower_price + 2 * price_step
        count = condensed_histogram[i]
        bar_length = int(count / max_count * histogram_width)
        print(f"${lower_price:8.2f} - ${upper_price:8.2f} | {'*' * bar_length}")


if __name__ == "__main__":
    cities = open(utils.getAbsPath("./../cities.txt")).read().split("\n")
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
    )

    # Create a list of dictionaries for each city's stats
    table_data = [
        {
            "City": city,
            "Units": stats["units"],
            "Median Price": stats["median_price"],
            f"{nth_cheapest}th cheapest": stats["nth_cheapest_price"],
            f"Bottom {bottom_nth_percentile}th Percentile": stats[
                "bottom_nth_percentile_price"
            ],
        }
        for city, stats in city_price_stats.items()
    ]
    # Sort the table data by median price in ascending order
    table_data.sort(key=lambda x: x["Median Price"])

    for row in table_data:
        city = row["City"]
        stats = city_price_stats[city]
        print_price_histogram(
            city,
            stats["price_histogram"],
            stats["min_value"],
            stats["max_value"],
            row["Median Price"],
        )
    # Print the table header
    print(
        "\n\n{:<25} {:<20} {:<15} {:<20} {:<25}".format(
            "City",
            f"#Units < ${max_price_per_night}/night",
            "Median Price",
            f"{nth_cheapest}th cheapest",
            f"Bottom {bottom_nth_percentile}th Percentile",
        )
    )
    print("-" * 105)  # Increased the line length to accommodate the longer header

    # Print the table rows
    for row in table_data:
        units = row.get("Units")
        median_price = row.get("Median Price")
        nth_cheapest_price = row.get(f"{nth_cheapest}th cheapest")
        bottom_percentile = row.get(f"Bottom {bottom_nth_percentile}th Percentile")
        # Format and print the row
        print(
            "{:<25} {:<20} ${:<14.2f} ${:<19.2f} ${:<24.2f}".format(
                row["City"],
                units,
                median_price,
                nth_cheapest_price,
                bottom_percentile,
            )
        )
