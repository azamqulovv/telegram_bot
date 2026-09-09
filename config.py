import os
from dotenv import load_dotenv

load_dotenv()


def _safe_int(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = _safe_int(os.getenv("ADMIN_ID"), 0)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
ADMIN_ID_2 = _safe_int(os.getenv("ADMIN_ID_2"), 0)
ADMIN_USERNAME_2 = os.getenv("ADMIN_USERNAME_2", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
CARD_NUMBER = os.getenv("CARD_NUMBER", "8600 0000 0000 0000").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "KARTA EGASI").strip() or "KARTA EGASI"
CHECKS_CHANNEL_ID = os.getenv("CHECKS_CHANNEL_ID", "@kanalingiz_cheklari").strip()