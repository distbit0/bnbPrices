import pysnooper
import utils
from utils import logger as logger
import requests
from datetime import datetime, timedelta
from datetime import datetime
import os
from dotenv import load_dotenv


load_dotenv()


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
                    # {
                    #     "filterName": "zoom",
                    #     "filterValues": [
                    #         "15.478",
                    #     ],
                    # },
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


def calculate_weighted_average_price(price_histogram, min_value, max_value):
    num_price_points = len(price_histogram)
    price_step = (max_value - min_value) / (num_price_points - 1)
    price_points = [min_value + i * price_step for i in range(num_price_points)]
    total_price = sum(
        price * count for price, count in zip(price_points, price_histogram)
    )
    total_count = sum(price_histogram)
    weighted_average_price = total_price / total_count
    return weighted_average_price


def get_city_price_stats(cities, bedrooms, start_date, end_date, adults):
    city_stats = {}
    for city in cities:
        price_histogram, min_value, max_value = get_price_data(
            city, bedrooms, start_date, end_date, adults
        )
        weighted_average_price = calculate_weighted_average_price(
            price_histogram, min_value, max_value
        )
        num_price_points = len(price_histogram)
        price_step = (max_value - min_value) / (num_price_points - 1)
        price_points = [min_value + i * price_step for i in range(num_price_points)]
        total_count = sum(price_histogram)
        cumulative_count = 0
        median_price = None
        bottom_30_percentile = None
        top_30_percentile = None
        bottom_n = None
        for price, count in zip(price_points, price_histogram):
            cumulative_count += count
            if median_price is None and cumulative_count >= total_count / 2:
                median_price = price
            if bottom_n is None and (cumulative_count >= min(100, total_count)):
                bottom_n = price
            if bottom_30_percentile is None and cumulative_count >= total_count * 0.3:
                bottom_30_percentile = price
            if top_30_percentile is None and cumulative_count >= total_count * 0.7:
                top_30_percentile = price
        city_stats[city] = {
            "mean_price": weighted_average_price,
            "median_price": median_price,
            "bottom_n": bottom_n,
            "bottom_30_percentile": bottom_30_percentile,
            "top_30_percentile": top_30_percentile,
            "price_histogram": price_histogram,
            "min_value": min_value,
            "max_value": max_value,
        }
    return city_stats


def print_price_histogram(city, price_histogram, min_value, max_value, mean_price):
    num_price_points = len(price_histogram)
    price_step = (max_value - min_value) / (num_price_points - 1)
    price_points = [min_value + i * price_step for i in range(num_price_points)]
    mean_index = int((mean_price - min_value) / price_step)
    start_index = max(0, mean_index - 10)
    end_index = min(num_price_points, mean_index + 11)
    max_count = max(price_histogram[start_index:end_index])
    histogram_width = 50
    print(f"\nPrice Distribution for {city} (Mean Price: ${mean_price:.2f}):")
    for i in range(start_index, end_index):
        price = price_points[i]
        count = price_histogram[i]
        bar_length = int(count / max_count * histogram_width)
        print(f"${price:8.2f} | {'*' * bar_length}")


if __name__ == "__main__":
    cities = open(utils.getAbsPath("./../cities.txt")).read().split("\n")
    bedrooms = 2
    adults = 2
    ## one week two months from now
    start_date = (datetime.now() + timedelta(days=61)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=61 + 7)).strftime("%Y-%m-%d")
    city_price_stats = get_city_price_stats(
        cities, bedrooms, start_date, end_date, adults
    )

    # Create a list of dictionaries for each city's stats
    table_data = [
        {
            "City": city,
            "Mean Price": stats["mean_price"],
            "Median Price": stats["median_price"],
            "Bottom n": stats["bottom_n"],
            "Bottom 30th Percentile": stats["bottom_30_percentile"],
            "Top 30th Percentile": stats["top_30_percentile"],
        }
        for city, stats in city_price_stats.items()
    ]
    # Sort the table data by mean price in ascending order
    table_data.sort(key=lambda x: x["Mean Price"])

    for row in table_data:
        city = row["City"]
        stats = city_price_stats[city]
        print_price_histogram(
            city,
            stats["price_histogram"],
            stats["min_value"],
            stats["max_value"],
            row["Mean Price"],
        )
    # Print the table header
    print(
        "\n\n{:<25} {:<15} {:<15} {:<15} {:<25} {:<20}".format(
            "City",
            "Mean Price",
            "Median Price",
            "Bottom n",
            "Bottom 30th Percentile",
            "Top 30th Percentile",
        )
    )
    print("-" * 100)

    # Print the table rows
    for row in table_data:
        mean_price = row.get("Mean Price")
        median_price = row.get("Median Price")
        bottom_n = row.get("Bottom n")
        bottom_percentile = row.get("Bottom 30th Percentile")
        top_percentile = row.get("Top 30th Percentile")
        # Format and print the row
        print(
            "{:<25} ${:<14.2f} ${:<14.2f} ${:<14.2f} ${:<24.2f} ${:<19.2f}".format(
                row["City"],
                mean_price,
                median_price,
                bottom_n,
                bottom_percentile,
                top_percentile,
            )
        )
