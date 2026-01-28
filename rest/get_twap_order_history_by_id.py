import requests

from common.constants import REST_URL

API_URL = f"{REST_URL}/orders/twap/history_by_id"
ORDER_ID = ""  # e.g. 6


def main():
    request = API_URL + "?order_id=" + ORDER_ID
    response = requests.get(request)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Request: {request}")

    # Print details for debugging
    print("\nDebug Info:")
    print(f"Order id: {ORDER_ID}")


if __name__ == "__main__":
    main()
