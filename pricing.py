import json
import os

PRICES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prices.json")

DEFAULT_PRICES = {
    "stars": {
        "50": 15000,
        "75": 22500,
        "100": 28000,
        "150": 42000,
        "250": 65000,
        "300": 78000,
        "500": 125000,
        "750": 185000,
        "1000": 240000,
        "1500": 355000,
    },
    "premium_with": {
        "1": 35000,
        "12": 280000,
    },
    "premium_without": {
        "3": 95000,
        "6": 160000,
        "12": 280000,
    },
    "gifts": {
        "2985": 2985,
        "4975": 4975,
        "9950": 9950,
        "19900": 19900,
    },
}


def _copy_defaults() -> dict[str, dict[str, int]]:
    return {category: values.copy() for category, values in DEFAULT_PRICES.items()}


def load_prices() -> dict[str, dict[str, int]]:
    prices = _copy_defaults()
    try:
        with open(PRICES_FILE, "r", encoding="utf-8") as price_file:
            saved = json.load(price_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return prices

    if not isinstance(saved, dict):
        return prices

    for category, values in prices.items():
        saved_values = saved.get(category, {})
        if not isinstance(saved_values, dict):
            continue
        for key in values:
            value = saved_values.get(key)
            if isinstance(value, int) and value > 0:
                values[key] = value
    return prices


def save_prices(prices: dict[str, dict[str, int]]) -> None:
    temporary_file = f"{PRICES_FILE}.tmp"
    with open(temporary_file, "w", encoding="utf-8") as price_file:
        json.dump(prices, price_file, ensure_ascii=False, indent=2)
    os.replace(temporary_file, PRICES_FILE)


def get_price(category: str, key: str) -> int:
    return load_prices().get(category, {}).get(str(key), 0)


def update_price(category: str, key: str, value: int) -> None:
    prices = load_prices()
    if category not in prices or str(key) not in prices[category]:
        raise ValueError("Noma'lum tarif")
    prices[category][str(key)] = value
    save_prices(prices)


def format_price(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def gift_group(gift_name: str) -> str:
    name = gift_name.lower()
    if name in {"yurak", "ayiqcha"}:
        return "2985"
    if name in {"sovg'a", "atirgul"}:
        return "4975"
    if name in {"brilliant", "uzuk", "kubok"}:
        return "19900"
    return "9950"


def all_price_items() -> list[tuple[str, str, str, int]]:
    prices = load_prices()
    items = []
    for key, value in prices["stars"].items():
        items.append(("stars", key, f"Stars {key}", value))
    for key, value in prices["premium_with"].items():
        items.append(("premium_with", key, f"Premium {key} oy, akkauntga kirib", value))
    for key, value in prices["premium_without"].items():
        items.append(("premium_without", key, f"Premium {key} oy, akkauntga kirmasdan", value))
    for key, value in prices["gifts"].items():
        items.append(("gifts", key, f"Giftlar guruhi {format_price(int(key))}", value))
    return items
