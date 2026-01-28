import csv
import os
import random
import time
import uuid

import requests
from apexomni.helpers.requests import session
from dotenv import load_dotenv
from solders.keypair import Keypair

from common.constants import REST_URL
from common.utils import sign_message

load_dotenv()

accApex = {
    "key": os.getenv("API_KEY_APEX"),
    "secretKey": os.getenv("SECRET_KEY_APEX"),
    "passphrase": os.getenv("PASS_PHRASE_APEX"),
    "seeds": os.getenv("SEEDS_APEX"),
    "l2Key": "",
}


def get_balance_pacifica():
    response = session.get(
        f"{REST_URL}/account?account=" + os.getenv("PACIFICA_ACC"),
        headers={"Accept": "*/*"},
    )

    data = response.json()

    return data["data"]["balance"]


def get_worst_price_pacifica():
    response = session.get(
        f"{REST_URL}/info/prices",
        headers={"Accept": "*/*"},
    )

    data = response.json()

    hype_data = next(
        (item for item in data.get("data", []) if item.get("symbol") == "HYPE"), None
    )
    if not hype_data:
        return None
    return hype_data["mark"]


def place_order_pacifica(agent_wallet_public_key, agent_wallet_private_key, bet=10.00):
    MARKET_ORDER_API_URL = f"{REST_URL}/orders/create_market"

    keypair = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_PACIFICA"))
    public_key = str(keypair.pubkey())

    timestamp = int(time.time() * 1_000)

    coin = random.randint(1, 2)
    side = ""

    price = get_worst_price_pacifica()
    size = round(bet / float(price), 1)
    tp = ""
    sl = ""

    if coin == 1:
        side = "bid"
        slippage = 0.005
        slPrice = float(price) - (float(price) * slippage)
        tpPrice = float(price) + (float(price) * slippage)
        tp = str(round(tpPrice, 2))
        sl = str(round(slPrice, 2))
    elif coin == 2:
        side = "ask"
        slippage = 0.005
        slPrice = float(price) + (float(price) * slippage)
        tpPrice = float(price) - (float(price) * slippage)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_market_order",
    }

    signature_payload = {
        "symbol": "HYPE",
        "reduce_only": False,
        "amount": str(size),
        "side": side,
        "slippage_percent": "0.1",
        "client_order_id": str(uuid.uuid4()),
    }

    # Use the helper function to sign the message, with the agent wallet's private key
    message, signature = sign_message(
        signature_header, signature_payload, agent_wallet_private_key
    )

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "agent_wallet": agent_wallet_public_key,  # use the agent wallet's public key
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = session.post(MARKET_ORDER_API_URL, json=request, headers=headers)
    print("Ордер Pacifica создан 🌊")

    entry = get_positions_pacifica_entry()

    tp_price = float(entry) * ((1 + 0.0004) / (1 - 0.0004))
    dif = tp_price - float(entry)

    tpf_price = round(float(entry) + (dif + dif), 3)
    slf_price = round(float(entry) - (dif + dif), 3)

    pos = get_positions_pacifica_size()
    worst_sell = get_worst_price_pacifica()

    place_positions_pacifica_tpsl(
        agent_wallet_public_key,
        agent_wallet_private_key,
        tpf_price,
        slf_price,
        pos,
        side,
    )


def place_positions_pacifica_tpsl(
    agent_wallet_public_key, agent_wallet_private_key, tpf_price, slf_price, pos, side
):
    API_URL = f"{REST_URL}/positions/tpsl"
    # Generate account based on private key
    keypair = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_PACIFICA"))
    public_key = str(keypair.pubkey())

    # Scaffold the signature header
    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "set_position_tpsl",
    }

    signature_payload = None

    if side == "bid":
        # Construct the signature payload
        signature_payload = {
            "symbol": "HYPE",
            "side": "ask",
            "take_profit": {
                "stop_price": str(tpf_price),
                "amount": str(pos),
                "client_order_id": str(uuid.uuid4()),
            },
            "stop_loss": {
                "stop_price": str(slf_price),
                "amount": str(pos),
                "client_order_id": str(uuid.uuid4()),
            },
        }
    elif side == "ask":
        signature_payload = {
            "symbol": "HYPE",
            "side": "bid",
            "take_profit": {
                "stop_price": str(slf_price),
                "amount": str(pos),
                "client_order_id": str(uuid.uuid4()),
            },
            "stop_loss": {
                "stop_price": str(tpf_price),
                "amount": str(pos),
                "client_order_id": str(uuid.uuid4()),
            },
        }

    # Use the helper function to sign the message
    message, signature = sign_message(
        signature_header, signature_payload, agent_wallet_private_key
    )

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "agent_wallet": agent_wallet_public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = session.post(API_URL, json=request, headers=headers)
    print("TP/SL выставлены")


def get_orders_pacifica():
    response = session.get(
        f"{REST_URL}/orders?account=" + os.getenv("PACIFICA_ACC"),
        headers={"Accept": "*/*"},
    )

    data = response.json()
    if not data.get("data"):
        return None
    order = data["data"][0]
    return order.get("client_order_id")


def get_orders_history_pacifica():
    request = f"{REST_URL}/trades/history?account=" + os.getenv("PACIFICA_ACC")
    response = session.get(request)
    data = response.json()

    dataID = []
    dataSymbol = []
    dataSide = []
    dataPrice = []
    dataEntPrice = []
    dataFee = []
    dataSize = []
    dataPnL = []

    for i in data.get("data", []):
        dataID.append(i.get("order_id"))
        dataSymbol.append(i.get("symbol"))
        dataSide.append(i.get("side"))
        dataPrice.append(i.get("price"))
        dataEntPrice.append(i.get("entry_price"))
        dataPnL.append(i.get("pnl"))
        dataFee.append(i.get("fee"))
        dataSize.append(i.get("amount"))

    with open("dataPacifica.csv", "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            ["ID", "Symbol", "Side", "Price", "EntryPrice", "PnL", "Fee", "Size"]
        )
        for i in range(len(dataID)):
            writer.writerow(
                [
                    dataID[i],
                    dataSymbol[i],
                    dataSide[i],
                    dataPrice[i],
                    dataEntPrice[i],
                    dataPnL[i],
                    dataFee[i],
                    dataSize[i],
                ]
            )

    return data


def get_positions_pacifica_entry():
    response = session.get(
        f"{REST_URL}/positions?account={os.getenv('PACIFICA_ACC')}",
        headers={"Accept": "*/*"},
    )

    data = response.json()
    if not data.get("data"):
        return None
    return data["data"][0].get("entry_price")


def get_positions_pacifica_size():
    response = session.get(
        f"{REST_URL}/positions?account={os.getenv('PACIFICA_ACC')}",
        headers={"Accept": "*/*"},
    )

    data = response.json()
    if not data.get("data"):
        return None
    return data["data"][0].get("amount")


def get_orders_pacifica_coin():
    response = session.get(
        f"{REST_URL}/orders?account=" + os.getenv("PACIFICA_ACC"),
        headers={"Accept": "*/*"},
    )

    data = response.json()
    if not data.get("data"):
        return None
    order = data["data"][0]
    return order.get("side")


def get_orders_pacifica_logic():
    response = session.get(
        f"{REST_URL}/orders?account=" + os.getenv("PACIFICA_ACC"),
        headers={"Accept": "*/*"},
    )

    data = response.json()
    return bool(data.get("data"))


def cancel_order_pacifica(agent_wallet_public_key, agent_wallet_private_key, bet=12.00):
    API_URL = f"{REST_URL}/orders/cancel_all"
    MARKET_ORDER_API_URL = f"{REST_URL}/orders/create_market"

    keypair = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_PACIFICA"))
    public_key = str(keypair.pubkey())

    timestamp = int(time.time() * 1_000)

    side = ""
    search_pacifica_side = get_orders_pacifica_coin()
    if search_pacifica_side == "bid":
        side = "bid"
    elif search_pacifica_side == "ask":
        side = "ask"

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "cancel_all_orders",
    }

    signature_payload = {
        "all_symbols": True,
        "exclude_reduce_only": False,
    }

    message, signature = sign_message(signature_header, signature_payload, keypair)

    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = session.post(API_URL, json=request, headers=headers)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "create_market_order",
    }

    price = get_worst_price_pacifica()
    size = round(bet / float(price), 1)

    signature_payload = {
        "symbol": "HYPE",
        "reduce_only": True,
        "amount": str(size),
        "side": side,
        "slippage_percent": "0.1",
    }

    message, signature = sign_message(
        signature_header, signature_payload, agent_wallet_private_key
    )

    request_header = {
        "account": public_key,
        "agent_wallet": agent_wallet_public_key,  # use the agent wallet's public key
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    response = session.post(MARKET_ORDER_API_URL, json=request, headers=headers)

    if response.status_code == 200:
        try:
            data = response.json()
            print("Ордер Pacifica закрыт ❌")
        except requests.exceptions.JSONDecodeError:
            print("❌ Ответ не в формате JSON:")
            print(response.text)
            return None
    else:
        print(f"❌ Ошибка {response.status_code}: {response.text}")
        return None


def order_logic_test(agent_public_key, agent_private_key):
    count = 1
    countS = 0
    l_pr = []
    t = random.randint(100, 120)
    with open("scriptData.csv", "w") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Market", "ID", "Coin", "Bet", "Side", "Time"])
    while True:
        try:
            print(
                f"----------------------Итерация {count} начинается ----------------------"
            )
            print(f"Балансы: Pacifica {round(float(get_balance_pacifica()), 3)}")
            pr = float(get_balance_pacifica()) - 5
            l_pr.append(pr)
            print(f"Ставка: {pr} USDT 💰\n")
            if pr <= 10:
                print("Баланс кошелька меньше условия\nВыход из программы...")
                break
            if not get_orders_pacifica_logic():
                place_order_pacifica(agent_public_key, agent_private_key, pr)
                countS += 1
            elif get_orders_pacifica_logic():
                print(
                    f"Ордер не прошел, так как ордер уже есть\nСписок ордеров:\n"
                    f"Pacifica: {get_orders_pacifica_logic()}"
                )
                bet = l_pr[-2] if len(l_pr) >= 2 else pr
                cancel_order_pacifica(agent_public_key, agent_private_key, bet)
                print("\nОтменена ордера на Pacifica")
            print(f"\nУспешных итераций: {countS} из {count}")
            count += 1
            time.sleep(t)
        except Exception as e:
            print(e)
            pass


def add_ip_to_whitelist(agent_wallet_address, ip_address):
    """Add an IP address to the whitelist."""
    IP_ADD_ENDPOINT = f"{REST_URL}/agent/ip_whitelist/add"
    keypair = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_PACIFICA"))
    public_key = str(keypair.pubkey())

    timestamp = int(time.time() * 1000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5000,
        "type": "add_agent_whitelisted_ip",
    }

    signature_payload = {
        "agent_wallet": agent_wallet_address,
        "ip_address": ip_address,
    }

    message, signature = sign_message(signature_header, signature_payload, keypair)

    request_header = {
        "account": public_key,
        "agent_wallet": None,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}
    request = {
        **request_header,
        **signature_payload,
    }
    response = requests.post(IP_ADD_ENDPOINT, json=request, headers=headers)


def toggle_ip_whitelist(agent_wallet_address: str, enabled: bool):
    """Enable or disable IP whitelist enforcement."""
    IP_TOGGLE_ENDPOINT = f"{REST_URL}/agent/ip_whitelist/toggle"
    keypair = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_PACIFICA"))
    public_key = str(keypair.pubkey())

    # Scaffold the signature header.
    timestamp = int(time.time() * 1000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5000,
        "type": "set_agent_ip_whitelist_enabled",
    }

    # Construct the signature payload.
    signature_payload = {
        "agent_wallet": agent_wallet_address,
        "enabled": enabled,
    }

    # Use the helper function to sign the message.
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields.
    request_header = {
        "account": public_key,
        "agent_wallet": None,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}
    request = {
        **request_header,
        **signature_payload,
    }
    response = requests.post(IP_TOGGLE_ENDPOINT, json=request, headers=headers)


def create_api_pacifica():
    BIND_AGENT_WALLET_API_URL = f"{REST_URL}/agent/bind"

    keypair = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_PACIFICA"))
    public_key = str(keypair.pubkey())
    print(public_key)

    agent_wallet_private_key = Keypair()
    agent_wallet_public_key = str(agent_wallet_private_key.pubkey())

    timestamp = int(time.time() * 1_000)

    signature_header = {
        "timestamp": timestamp,
        "expiry_window": 5_000,
        "type": "bind_agent_wallet",
    }

    # Construct the signature payload
    signature_payload = {
        "agent_wallet": agent_wallet_public_key,
    }

    # Use the helper function to sign the message
    message, signature = sign_message(signature_header, signature_payload, keypair)

    # Construct the request reusing the payload and constructing common request fields
    request_header = {
        "account": public_key,
        "signature": signature,
        "timestamp": signature_header["timestamp"],
        "expiry_window": signature_header["expiry_window"],
    }

    # Send the request
    headers = {"Content-Type": "application/json"}

    request = {
        **request_header,
        **signature_payload,
    }

    agent_settings = {
        "agent_public_key": agent_wallet_public_key,
        "agent_private_key": agent_wallet_private_key,
    }

    response = requests.post(BIND_AGENT_WALLET_API_URL, json=request, headers=headers)

    add_ip_to_whitelist(agent_wallet_public_key, "176.104.207.116")
    add_ip_to_whitelist(agent_wallet_public_key, "5.129.210.55")
    add_ip_to_whitelist(agent_wallet_public_key, "195.200.18.70")
    add_ip_to_whitelist(agent_wallet_public_key, "93.157.120.199")

    toggle_ip_whitelist(agent_wallet_public_key, True)

    return agent_settings


def main():
    agent = create_api_pacifica()
    apub = agent["agent_public_key"]
    apri = agent["agent_private_key"]
    while True:
        print("\n--- Меню ---")
        print("Выберите действие 😎:")
        print("1 - Посмотреть баланс 💰")
        print("2 - Посмотреть открытые ордеры 📖")
        print("3 - Разместить ордер 📄")
        print("4 - Закрыть ордер ❌")
        print("5 - Запустить скрипт 👌")
        print("0 - Выйти")

        choice = input("Введите номер действия: ").strip()

        if choice == "1":
            print("\n💰 Вы выбрали: Посмотреть баланс")
            print(f"Pacifica баланс: {get_balance_pacifica()} USDT")
        elif choice == "2":
            print("\n📖 Вы выбрали: Посмотреть открытые ордеры")
            print(get_orders_pacifica())
        elif choice == "3":
            print("\n📄 Вы выбрали: Разместить ордер")
            print(place_order_pacifica(apub, apri))
        elif choice == "4":
            print("\n❌ Вы выбрали: Закрыть ордер")
            print("2 - Pacifica")
            print(cancel_order_pacifica(apub, apri))
        elif choice == "5":
            print("\n👌 Вы выбрали: Запустить скрипт")
            order_logic_test(apub, apri)

        elif choice == "0":
            print("\n👋 Выход из программы. Пока!")
            break

        else:
            print("\n⚠️ Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    main()
