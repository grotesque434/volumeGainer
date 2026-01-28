import requests

from common.constants import REST_URL

API_URL = f"{REST_URL}/orders/twap"
PUBLIC_KEY = ""  # e.g. "dev1S2tC8CSZXzTQzVacYvkqWwD37dTqiCKaeJCWhwM"


def main():
    request = API_URL + "?account=" + PUBLIC_KEY
    response = requests.get(request)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Account: {PUBLIC_KEY}")


if __name__ == "__main__":
    main()
