import requests
import os
import dotenv

dotenv.load_dotenv()

apiKey = os.getenv("AIRBNB_API_KEY")
headers = {
    "x-airbnb-api-key": apiKey,
}
params = {
    "operationName": "DynamicFilters",
    "locale": "en-AU",
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
                        "2",
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
                        "2024-08-10",
                    ],
                },
                {
                    "filterName": "checkout",
                    "filterValues": [
                        "2024-08-17",
                    ],
                },
                {
                    "filterName": "date_picker_type",
                    "filterValues": [
                        "calendar",
                    ],
                },
                {
                    "filterName": "flexible_trip_lengths",
                    "filterValues": [
                        "one_week",
                    ],
                },
                {
                    "filterName": "location",
                    "filterValues": [
                        "Canggu, Bali, Indonesia",
                    ],
                },
                {
                    "filterName": "min_bedrooms",
                    "filterValues": [
                        "2",
                    ],
                },
                {
                    "filterName": "min_beds",
                    "filterValues": [
                        "2",
                    ],
                },
                {
                    "filterName": "monthly_end_date",
                    "filterValues": [
                        "2024-11-01",
                    ],
                },
                {
                    "filterName": "monthly_start_date",
                    "filterValues": [
                        "2024-08-01",
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
                        "7",
                    ],
                },
                {
                    "filterName": "price_max",
                    "filterValues": [
                        "1436",
                    ],
                },
                {
                    "filterName": "query",
                    "filterValues": [
                        "Canggu, Bali, Indonesia",
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

print(response.json())
